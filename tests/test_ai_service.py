from __future__ import annotations

from app.config import get_settings
from app.services.ai_service import AIService


def _service() -> AIService:
    return AIService(get_settings())


def test_parse_response_payload_accepts_fenced_json() -> None:
    payload = _service()._parse_response_payload(
        """```json
{
  "version": "1.0",
  "style_tag": "test",
  "confidence": 0.8
}
```"""
    )
    assert payload["version"] == "1.0"
    assert payload["style_tag"] == "test"


def test_parse_response_payload_repairs_trailing_commas() -> None:
    payload = _service()._parse_response_payload(
        """
Here is the recipe:
{
  "recipe": {
    "exposure": 0.25,
    "contrast": 0.18,
    "warnings": ["watch highlights",],
  },
}
"""
    )
    assert payload["recipe"]["exposure"] == 0.25
    assert payload["recipe"]["contrast"] == 0.18


def test_parse_response_payload_accepts_python_literal_dict() -> None:
    payload = _service()._parse_response_payload(
        """{
  'recipe': {
    'exposure': 0.35,
    'contrast': 0.28,
    'skin_tone_protection': True,
    'warnings': ['test']
  }
}"""
    )
    assert payload["recipe"]["exposure"] == 0.35
    assert payload["recipe"]["skin_tone_protection"] is True
