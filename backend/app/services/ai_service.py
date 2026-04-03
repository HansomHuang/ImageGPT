from __future__ import annotations

import base64
import json
import logging
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

from app.config import Settings
from app.schemas import default_recipe

LOGGER = logging.getLogger(__name__)

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


SYSTEM_PROMPT = """You are ImageGPT, a photo color analyst.
You must return JSON only, strictly matching the provided schema.
Do not output prose except the notes/warnings fields in JSON.
Use conservative values when uncertain.
Do not invent unsupported fields.
"""


class AIService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = None
        if OpenAI and settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key)

    def _build_preview_data_url(self, image_path: Path, max_edge: int = 1024) -> str:
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            if max(image.size) > max_edge:
                image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=90)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"

    @staticmethod
    def _response_text(response: Any) -> str:
        text = getattr(response, "output_text", "")
        if text:
            return text
        chunks: list[str] = []
        output = getattr(response, "output", [])
        for item in output:
            content = getattr(item, "content", [])
            for part in content:
                if getattr(part, "type", "") in {"output_text", "text"}:
                    maybe_text = getattr(part, "text", "")
                    if maybe_text:
                        chunks.append(maybe_text)
        return "\n".join(chunks).strip()

    def analyze(
        self,
        *,
        image_path: Path,
        style_intent: str,
        metadata: dict[str, Any],
        schema: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str], bool]:
        if self.client is None:
            return (
                default_recipe().model_dump(mode="json"),
                ["OpenAI client unavailable or OPENAI_API_KEY missing. Using conservative fallback recipe."],
                True,
            )

        data_url = self._build_preview_data_url(image_path)
        user_text = (
            "Analyze this photo and output a color recipe.\n"
            f"Style intent: {style_intent or 'none'}\n"
            f"Metadata: {json.dumps(metadata, ensure_ascii=True)}\n"
            "Prioritize natural highlight rolloff, safe skin tones, and avoid clipping."
        )

        try:
            response = self.client.responses.create(
                model=self.settings.openai_model,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": user_text},
                            {"type": "input_image", "image_url": data_url},
                        ],
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "imagegpt_recipe",
                        "schema": schema,
                        "strict": True,
                    }
                },
            )
            raw_text = self._response_text(response)
            payload = json.loads(raw_text)
            return payload, [], False
        except Exception as exc:
            LOGGER.exception("OpenAI analyze failed: %s", exc)
            return (
                default_recipe().model_dump(mode="json"),
                [f"OpenAI analyze failed ({exc}). Using fallback recipe."],
                True,
            )

