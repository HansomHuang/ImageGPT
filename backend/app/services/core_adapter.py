from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np

from app.services import python_pipeline


LOGGER = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).resolve().parents[3]


def _add_native_search_paths() -> None:
    candidates = [
        ROOT_DIR / "core" / "build",
        ROOT_DIR / "core" / "build" / "Release",
        ROOT_DIR / "core" / "python",
    ]
    for path in candidates:
        text = str(path)
        if path.exists() and text not in sys.path:
            sys.path.insert(0, text)


class CoreAdapter:
    def __init__(self) -> None:
        self._native_engine: Any | None = None
        self._native_module: Any | None = None
        _add_native_search_paths()
        try:
            module = importlib.import_module("imagegpt_core")
            self._native_module = module
            self._native_engine = module.ColorEngine()
            LOGGER.info("Native imagegpt_core module loaded.")
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("Native core unavailable, using Python fallback pipeline: %s", exc)

    @property
    def using_native(self) -> bool:
        return self._native_engine is not None

    def capabilities(self) -> dict[str, Any]:
        if self._native_module is not None:
            capabilities = dict(self._native_module.capabilities())
            capabilities["native"] = True
            return capabilities
        return {
            "native": False,
            "oiio": False,
            "libraw": False,
            "lcms2": False,
            "fallback_python_pipeline": True,
        }

    def probe_metadata(self, image_path: Path) -> dict[str, Any]:
        if self._native_engine is not None:
            return dict(self._native_engine.probe_metadata(str(image_path)))
        return python_pipeline.image_metadata(image_path)

    def render_preview(
        self, image_path: Path, recipe: dict[str, Any], max_edge: int, prefer_raw: bool
    ) -> np.ndarray:
        if self._native_engine is not None:
            return np.asarray(
                self._native_engine.render_preview(
                    input_path=str(image_path),
                    recipe=recipe,
                    max_edge=max_edge,
                    prefer_raw=prefer_raw,
                ),
                dtype=np.float32,
            )
        image = python_pipeline.load_image(image_path, max_edge=max_edge)
        return python_pipeline.apply_recipe(image, recipe).astype(np.float32)

    def export_image(
        self,
        image_path: Path,
        recipe: dict[str, Any],
        output_path: Path,
        image_format: str,
        quality: int,
        prefer_raw: bool,
    ) -> None:
        if self._native_engine is not None:
            self._native_engine.export_image(
                input_path=str(image_path),
                recipe=recipe,
                output_path=str(output_path),
                format=image_format,
                quality=quality,
                prefer_raw=prefer_raw,
            )
            return
        image = python_pipeline.load_image(image_path, max_edge=None)
        edited = python_pipeline.apply_recipe(image, recipe)
        python_pipeline.save_image(edited, output_path, image_format=image_format, quality=quality)

