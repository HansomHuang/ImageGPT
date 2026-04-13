from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.config import Settings
from app.db import db_conn


def _slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip().lower()).strip("_") or "preset"


class PresetService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def list_presets(self) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        for file in sorted(self.settings.presets_dir.glob("*.json")):
            items.append({"name": file.stem, "path": str(file.resolve())})
        return items

    def load_preset(self, name: str) -> dict[str, Any]:
        file = self.settings.presets_dir / f"{name}.json"
        if not file.exists():
            raise FileNotFoundError(f"Preset not found: {name}")
        return json.loads(file.read_text(encoding="utf-8"))

    def save_preset(self, name: str, recipe: dict[str, Any]) -> Path:
        slug = _slugify(name)
        target = self.settings.presets_dir / f"{slug}.json"
        target.write_text(json.dumps(recipe, indent=2), encoding="utf-8")
        with db_conn(self.settings.db_path) as conn:
            conn.execute(
                """
                INSERT INTO presets(name, path) VALUES(?, ?)
                ON CONFLICT(name) DO UPDATE SET path=excluded.path
                """,
                (slug, str(target.resolve())),
            )
        return target

    def save_recipe_sidecar(self, image_path: Path, recipe: dict[str, Any]) -> Path:
        sidecar = self.settings.recipes_dir / f"{image_path.stem}.imagegpt.recipe.json"
        sidecar.write_text(json.dumps(recipe, indent=2), encoding="utf-8")
        return sidecar

