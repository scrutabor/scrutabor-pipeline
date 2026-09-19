"""Source-bound identities for the provider's unrelated ID-zero records.

The provider puts all irregular records under one integer. That integer is
not a dictionary entry. Only the families below have reviewed identity links;
other special records remain usable as form-level evidence.
"""

import copy
import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

import whitakers_words
from whitakers_words.datatypes import Unique
from whitakers_words.parser import UniqueInflection

SOURCE_HASHES = {
    "data/esse.py": "703502ba446dfb3a989365806790632bc087bb773533e4baa40fb4dcf7c5688e",
    "generated/uniques.py": "463cc7c14659330685cf3fc6c790f06bff42144e2dd8c880db2445f91f36fcf0",
    "data/UNIQUES.LAT": "bdbf601836c54086f2f9520d28dc137e3d9c8596a1df7cbc8434a3e596936539",
    "datagenerator.py": "d42f3573d818b151796113bb9a2c7edc045912a2a20598d3e1e55e7cef89930b",
    "parser.py": "ff6ecf6a01e701dfa8e999da43138a8c297dd844486d36669059816561ba8890",
}

# Lewis and Short: memini (memento/mementote); deus (vocative deus);
# quisquis (substantival quidquid); unus II.B.5 (unus quisque and fused forms).
# Sum's table has its own source module, imported by the provider's generator.
FAMILY_FORMS = {
    "memini": ("memento", "mementote"),
    "deus": ("deus",),
    "quisquis": ("quisquis", "quidquid"),
    "unusquisque": ("unusquisque", "uniuscuiusque", "unicuique", "unumquodque"),
}


def _stable(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _signature(inflection) -> str:
    # Follow each inflection, not the first lexeme in an aggregate analysis.
    return _stable(
        {
            "stem": inflection.stem,
            "pos": inflection.wordType.name,
            "category": list(getattr(inflection, "category", [])),
            "features": {key: value.name for key, value in inflection.features.items()},
        }
    )


def _bind_records(
    all_records: Sequence[Unique], reviewed: Sequence[tuple[str, Unique]]
) -> dict[str, str]:
    """Reject identities the parser cannot distinguish or that disagree."""
    raw_by_signature: dict[str, set[str]] = {}
    for record in all_records:
        signature = _signature(UniqueInflection(record))
        raw_by_signature.setdefault(signature, set()).add(_stable(record))
    identities: dict[str, str] = {}
    for family, record in reviewed:
        signature = _signature(UniqueInflection(record))
        if raw_by_signature.get(signature) != {_stable(record)}:
            raise ValueError("missing or ambiguous special record")
        if signature in identities and identities[signature] != family:
            raise ValueError("conflicting special-record families")
        identities[signature] = family
    return identities


@dataclass(frozen=True)
class Registry:
    identities: Mapping[str, str]
    source_hashes: Mapping[str, str | None]
    binding_sha256: str | None
    error: str | None = None

    def provenance(self) -> dict:
        return {
            "status": "inactive" if self.error else "active",
            "error": self.error,
            "expected_source_hashes": dict(SOURCE_HASHES),
            "actual_source_hashes": dict(self.source_hashes),
            "binding_sha256": self.binding_sha256,
            "record_count": len(self.identities),
            "family_counts": dict(sorted(Counter(self.identities.values()).items())),
        }


def build_registry(
    source_hashes: Mapping[str, str | None],
    unique_records: Mapping[str, Sequence[Unique]],
    esse_records: Sequence[Unique],
) -> Registry:
    """No expected word morphology or target lemma authorizes a binding."""
    hashes = MappingProxyType(dict(source_hashes))
    if dict(hashes) != SOURCE_HASHES:
        return Registry(MappingProxyType({}), hashes, None, "special-record source drift")
    reviewed = []
    for source in esse_records:
        record = copy.deepcopy(source)
        # These are exactly the generator's additions to the sum table.
        record["n"] = [5, 1]
        record["props"] = ["X", "X", "X", "A", "X"]
        reviewed.append(("sum", record))
    try:
        for family, forms in FAMILY_FORMS.items():
            for form in forms:
                reviewed.extend((family, record) for record in unique_records[form])
        identities = _bind_records(
            [record for records in unique_records.values() for record in records], reviewed
        )
    except (KeyError, ValueError) as error:
        return Registry(MappingProxyType({}), hashes, None, str(error))
    binding = hashlib.sha256(_stable(reviewed).encode()).hexdigest()
    return Registry(MappingProxyType(identities), hashes, binding)


@lru_cache(maxsize=1)
def registry() -> Registry:
    root = Path(whitakers_words.__file__).parent
    actual: dict[str, str | None] = {}
    for name in SOURCE_HASHES:
        try:
            actual[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
        except OSError:
            actual[name] = None
    if actual != SOURCE_HASHES:
        return build_registry(actual, {}, [])
    # Import special-only data after checking its source files. A missing
    # optional table must not prevent ordinary dictionary candidates.
    from whitakers_words.data.esse import esse
    from whitakers_words.generated.uniques import uniques

    return build_registry(actual, uniques, esse)


def identity(inflection) -> str | None:
    return registry().identities.get(_signature(inflection))
