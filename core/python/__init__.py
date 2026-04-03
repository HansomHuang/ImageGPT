"""ImageGPT core Python package shim.

Prefers native `imagegpt_core` pybind module if available.
"""

from __future__ import annotations

try:
    import imagegpt_core as native  # type: ignore
except Exception:  # pragma: no cover
    native = None

__all__ = ["native"]
