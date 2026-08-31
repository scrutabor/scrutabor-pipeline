import hashlib
import json
from pathlib import Path

from scrutabor_pipeline.agree import Verdict
from scrutabor_pipeline.agreement import confirmation_attestation, corpus_identity


def test_confirmation_attestation_binds_every_token_and_corpus_bytes(tmp_path):
    corpus = tmp_path / "corpus"
    text = corpus / "texts" / "orationes" / "alpha.json"
    text.parent.mkdir(parents=True)
    text.write_text('{"id":"orationes.alpha"}\n', encoding="utf-8")
    verdicts = [Verdict("orationes.alpha.w001", "AGREE", sources="collatinus")]
    confirmations = [
        {
            "token": "orationes.alpha.w001",
            "verdict": "AGREE",
            "declared": ["collatinus"],
            "confirmed": ["collatinus"],
        }
    ]
    attestation = confirmation_attestation(
        corpus, 1, verdicts, [], confirmations, include_confirmations=True
    )
    assert attestation["counts"]["tokens"] == 1
    assert attestation["counts"]["provenance_mismatch"] == 0
    assert attestation["confirmations"] == confirmations
    assert attestation["confirmation_groups"] == [
        {
            "declared": "collatinus",
            "confirmed": "collatinus",
            "verdict": "AGREE",
            "tokens": 1,
        }
    ]
    expected = hashlib.sha256(
        json.dumps(
            confirmations, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    assert attestation["confirmations_sha256"] == expected

    before = corpus_identity(corpus)["texts_sha256"]
    text.write_text('{"id":"orationes.beta"}\n', encoding="utf-8")
    assert corpus_identity(corpus)["texts_sha256"] != before


def test_attestation_records_a_provenance_mismatch():
    verdicts = [Verdict("t.w001", "AGREE", sources="collatinus")]
    attestation = confirmation_attestation(
        corpus=Path("."),
        texts=1,
        verdicts=verdicts,
        provenance=["t.w001 mismatch"],
        confirmations=[
            {
                "token": "t.w001",
                "verdict": "AGREE",
                "declared": ["whitakers"],
                "confirmed": ["collatinus"],
            }
        ],
    )
    assert attestation["counts"]["provenance_mismatch"] == 1
