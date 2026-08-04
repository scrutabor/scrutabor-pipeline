"""Compatibility shim for pycollatinus 0.1.6.

The package (last released for Python 3.7) imports abstract base classes
from `collections`, aliases removed in Python 3.10. Restoring the aliases
before import is the entire fix; the package's own logic runs unchanged.
Applied automatically by the collatinus adapter; pinned in requirements.
"""

import collections
import collections.abc

_ALIASES = (
    "Callable",
    "Iterable",
    "Iterator",
    "Generator",
    "Hashable",
    "Mapping",
    "MutableMapping",
    "Sequence",
    "Set",
)


def apply() -> None:
    for name in _ALIASES:
        if not hasattr(collections, name):
            setattr(collections, name, getattr(collections.abc, name))
