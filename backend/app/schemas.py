from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WhiteBalanceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    temperature: float = Field(default=0, ge=-100, le=100)
    tint: float = Field(default=0, ge=-100, le=100)


class ToneModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exposure: float = Field(default=0, ge=-5, le=5)
    contrast: float = Field(default=0, ge=-100, le=100)
    highlights: float = Field(default=0, ge=-100, le=100)
    shadows: float = Field(default=0, ge=-100, le=100)
    whites: float = Field(default=0, ge=-100, le=100)
    blacks: float = Field(default=0, ge=-100, le=100)


class FinishingModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clarity: float = Field(default=0, ge=-100, le=100)
    dehaze: float = Field(default=0, ge=-100, le=100)
    vignette: float = Field(default=0, ge=-100, le=100)


class GlobalAdjustmentsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    white_balance: WhiteBalanceModel = Field(default_factory=WhiteBalanceModel)
    tone: ToneModel = Field(default_factory=ToneModel)
    vibrance: float = Field(default=0, ge=-100, le=100)
    saturation: float = Field(default=0, ge=-100, le=100)
    finishing: FinishingModel = Field(default_factory=FinishingModel)


class CurvePointModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class HSLBandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hue: float = Field(default=0, ge=-100, le=100)
    saturation: float = Field(default=0, ge=-100, le=100)
    luminance: float = Field(default=0, ge=-100, le=100)


class HSLBandsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    red: HSLBandModel = Field(default_factory=HSLBandModel)
    orange: HSLBandModel = Field(default_factory=HSLBandModel)
    yellow: HSLBandModel = Field(default_factory=HSLBandModel)
    green: HSLBandModel = Field(default_factory=HSLBandModel)
    aqua: HSLBandModel = Field(default_factory=HSLBandModel)
    blue: HSLBandModel = Field(default_factory=HSLBandModel)
    purple: HSLBandModel = Field(default_factory=HSLBandModel)
    magenta: HSLBandModel = Field(default_factory=HSLBandModel)


class GradingToneModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hue: float = Field(default=0, ge=0, le=360)
    sat: float = Field(default=0, ge=0, le=100)


class ColorGradingModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    shadows: GradingToneModel = Field(default_factory=GradingToneModel)
    midtones: GradingToneModel = Field(default_factory=GradingToneModel)
    highlights: GradingToneModel = Field(default_factory=GradingToneModel)
    balance: float = Field(default=0, ge=-100, le=100)
    blend: float = Field(default=50, ge=0, le=100)


class RecipeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal["1.0"] = "1.0"
    style_tag: str = Field(default="default", min_length=1, max_length=64)
    confidence: float = Field(default=0.5, ge=0, le=1)
    global_adjustments: GlobalAdjustmentsModel = Field(default_factory=GlobalAdjustmentsModel)
    tone_curve: list[CurvePointModel] = Field(default_factory=lambda: [CurvePointModel(x=0, y=0), CurvePointModel(x=1, y=1)])
    hsl_bands: HSLBandsModel = Field(default_factory=HSLBandsModel)
    color_grading: ColorGradingModel = Field(default_factory=ColorGradingModel)
    notes: str = Field(default="", max_length=256)
    warnings: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_curve(self) -> "RecipeModel":
        if len(self.tone_curve) < 2:
            raise ValueError("tone_curve must contain at least 2 points")
        prev_x = -1.0
        prev_y = -1.0
        for point in self.tone_curve:
            if point.x < prev_x:
                raise ValueError("tone_curve x values must be non-decreasing")
            if point.y < prev_y:
                raise ValueError("tone_curve y values must be non-decreasing")
            prev_x = point.x
            prev_y = point.y
        return self


class ImportImageRequest(BaseModel):
    path: str
    prefer_raw: bool = True


class ImportImageResponse(BaseModel):
    path: str
    exists: bool
    metadata: dict[str, Any]
    preview_path: str | None = None
    preview_width: int | None = None
    preview_height: int | None = None


class AnalyzeRequest(BaseModel):
    image_path: str
    style_intent: str = Field(default="")
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyzeResponse(BaseModel):
    recipe: RecipeModel
    fallback_used: bool = False
    messages: list[str] = Field(default_factory=list)


class ApplyRequest(BaseModel):
    image_path: str
    recipe: RecipeModel
    prefer_raw: bool = True


class ApplyResponse(BaseModel):
    preview_path: str
    width: int
    height: int


class ExportRequest(BaseModel):
    image_path: str
    recipe: RecipeModel
    output_path: str | None = None
    format: Literal["jpeg", "tiff"] = "jpeg"
    quality: int = Field(default=92, ge=1, le=100)
    prefer_raw: bool = True


class ExportResponse(BaseModel):
    output_path: str
    format: Literal["jpeg", "tiff"]


class PresetSaveRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    recipe: RecipeModel


class PresetSummary(BaseModel):
    name: str
    path: str


class PresetLoadResponse(BaseModel):
    name: str
    recipe: RecipeModel


class ErrorResponse(BaseModel):
    error: str


def default_recipe() -> RecipeModel:
    return RecipeModel()


def recipe_to_dict(recipe: RecipeModel) -> dict[str, Any]:
    return recipe.model_dump(mode="json")


def coerce_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()
