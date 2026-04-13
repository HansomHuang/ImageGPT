from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from app.config import Settings
from app.services.core_adapter import CoreAdapter


class ImageService:
    def __init__(self, settings: Settings, core: CoreAdapter) -> None:
        self.settings = settings
        self.core = core
        self.preview_dir = settings.export_dir / "previews"
        self.preview_dir.mkdir(parents=True, exist_ok=True)

    def import_metadata(self, image_path: Path) -> dict[str, Any]:
        metadata = self.core.probe_metadata(image_path)
        metadata["path"] = str(image_path.resolve())
        metadata["exists"] = image_path.exists()
        return metadata

    def render_preview(
        self, image_path: Path, recipe: dict[str, Any], prefer_raw: bool, variant: str = "preview"
    ) -> tuple[Path, int, int]:
        preview = self.core.render_preview(
            image_path=image_path,
            recipe=recipe,
            max_edge=self.settings.preview_max_edge,
            prefer_raw=prefer_raw,
        )
        safe_variant = "".join(ch for ch in variant.lower() if ch.isalnum() or ch in {"_", "-"})
        safe_variant = safe_variant or "preview"
        preview_path = self.preview_dir / f"{image_path.stem}_{safe_variant}.jpg"
        self._save_preview(preview, preview_path)
        height, width = preview.shape[:2]
        return preview_path, width, height

    def export_image(
        self,
        image_path: Path,
        recipe: dict[str, Any],
        output_path: Path | None,
        image_format: str,
        quality: int,
        prefer_raw: bool,
    ) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_path is None:
            suffix = ".jpg" if image_format == "jpeg" else ".tiff"
            output_path = self.settings.export_dir / f"{image_path.stem}_{timestamp}{suffix}"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.core.export_image(
            image_path=image_path,
            recipe=recipe,
            output_path=output_path,
            image_format=image_format,
            quality=quality,
            prefer_raw=prefer_raw,
        )
        return output_path.resolve()

    @staticmethod
    def _save_preview(image: np.ndarray, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        array = np.clip(image, 0.0, 1.0)
        rgb = (array * 255.0).astype(np.uint8)
        Image.fromarray(rgb, mode="RGB").save(output_path, format="JPEG", quality=90)
