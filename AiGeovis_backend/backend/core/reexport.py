"""Import helpers that include underscore-prefixed names (unlike ``import *``)."""
from __future__ import annotations

from types import ModuleType
from typing import Any, Dict


def pull(module: ModuleType, dest: Dict[str, Any]) -> None:
    """Copy all non-dunder attributes from *module* into *dest* (e.g. ``globals()``)."""
    for key, value in vars(module).items():
        if key.startswith("__") and key.endswith("__"):
            continue
        dest[key] = value
