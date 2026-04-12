from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import ExifTags, Image

try:
    import rawpy
except Exception as exc:  # pragma: no cover - optional dependency
    rawpy = None
    _RAWPY_IMPORT_ERROR = exc
else:  # pragma: no cover - exercised indirectly in tests
    _RAWPY_IMPORT_ERROR = None


RAW_EXTENSIONS = {".arw", ".cr2", ".cr3", ".nef", ".nrw", ".dng"}


def _clamp01(arr: np.ndarray) -> np.ndarray:
    return np.clip(arr, 0.0, 1.0)


def _srgb_to_linear(arr: np.ndarray) -> np.ndarray:
    return np.where(arr <= 0.04045, arr / 12.92, np.power((arr + 0.055) / 1.055, 2.4))


def _linear_to_srgb(arr: np.ndarray) -> np.ndarray:
    return np.where(arr <= 0.0031308, arr * 12.92, 1.055 * np.power(arr, 1.0 / 2.4) - 0.055)


def _apply_curve(values: np.ndarray, points: list[dict[str, float]]) -> np.ndarray:
    x = np.array([float(p["x"]) for p in points], dtype=np.float32)
    y = np.array([float(p["y"]) for p in points], dtype=np.float32)
    return np.interp(values, x, y).astype(np.float32)


def _rgb_to_hsl(r: np.ndarray, g: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    l = (maxc + minc) / 2.0
    delta = maxc - minc
    s = np.zeros_like(l)
    non_zero = delta > 1e-6
    s[non_zero] = delta[non_zero] / (1.0 - np.abs(2.0 * l[non_zero] - 1.0) + 1e-6)

    h = np.zeros_like(l)
    mask = non_zero & (maxc == r)
    h[mask] = ((g[mask] - b[mask]) / (delta[mask] + 1e-6)) % 6.0
    mask = non_zero & (maxc == g)
    h[mask] = ((b[mask] - r[mask]) / (delta[mask] + 1e-6)) + 2.0
    mask = non_zero & (maxc == b)
    h[mask] = ((r[mask] - g[mask]) / (delta[mask] + 1e-6)) + 4.0
    h = (h * 60.0) % 360.0
    return h, s, l


def _hsl_to_rgb(h: np.ndarray, s: np.ndarray, l: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    h = (h % 360.0) / 360.0

    def hue_to_rgb(p: np.ndarray, q: np.ndarray, t: np.ndarray) -> np.ndarray:
        t = t.copy()
        t[t < 0] += 1
        t[t > 1] -= 1
        out = np.empty_like(t)
        cond1 = t < 1 / 6
        cond2 = (t >= 1 / 6) & (t < 1 / 2)
        cond3 = (t >= 1 / 2) & (t < 2 / 3)
        out[cond1] = p[cond1] + (q[cond1] - p[cond1]) * 6 * t[cond1]
        out[cond2] = q[cond2]
        out[cond3] = p[cond3] + (q[cond3] - p[cond3]) * (2 / 3 - t[cond3]) * 6
        out[~(cond1 | cond2 | cond3)] = p[~(cond1 | cond2 | cond3)]
        return out

    q = np.where(l < 0.5, l * (1 + s), l + s - l * s)
    p = 2 * l - q
    r = hue_to_rgb(p, q, h + 1 / 3)
    g = hue_to_rgb(p, q, h)
    b = hue_to_rgb(p, q, h - 1 / 3)
    return r, g, b


def _require_rawpy() -> Any:
    if rawpy is None:
        message = "RAW decode requires the optional 'rawpy' package or the native core with LibRaw."
        if _RAWPY_IMPORT_ERROR is not None:
            message = f"{message} Import error: {_RAWPY_IMPORT_ERROR}"
        raise RuntimeError(message)
    return rawpy


def _resize_float_image(image: np.ndarray, max_edge: int) -> np.ndarray:
    if max(image.shape[0], image.shape[1]) <= max_edge:
        return image
    rgb8 = (_clamp01(image) * 255.0).astype(np.uint8)
    preview = Image.fromarray(rgb8, mode="RGB")
    preview.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    return np.asarray(preview).astype(np.float32) / 255.0


def _load_raw_image(path: Path, max_edge: int | None = None) -> np.ndarray:
    rawpy_module = _require_rawpy()
    with rawpy_module.imread(str(path)) as raw:
        rgb = raw.postprocess(
            use_camera_wb=True,
            no_auto_bright=True,
            output_color=rawpy_module.ColorSpace.sRGB,
            output_bps=16,
        )
    image = rgb.astype(np.float32) / 65535.0
    if max_edge is not None:
        image = _resize_float_image(image, max_edge=max_edge)
    return image


def load_image(path: Path, max_edge: int | None = None) -> np.ndarray:
    if path.suffix.lower() in RAW_EXTENSIONS:
        return _load_raw_image(path, max_edge=max_edge)
    with Image.open(path) as image:
        image = image.convert("RGB")
        if max_edge and max(image.size) > max_edge:
            image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        arr = np.asarray(image).astype(np.float32) / 255.0
    return arr


def image_metadata(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {"path": str(path), "is_raw": path.suffix.lower() in RAW_EXTENSIONS}
    if not path.exists():
        return payload
    if payload["is_raw"]:
        try:
            rawpy_module = _require_rawpy()
            with rawpy_module.imread(str(path)) as raw:
                sizes = raw.sizes
                payload["width"] = int(getattr(sizes, "width", getattr(sizes, "raw_width", 0)))
                payload["height"] = int(getattr(sizes, "height", getattr(sizes, "raw_height", 0)))
                payload["decoder"] = "rawpy"
                if hasattr(sizes, "raw_width"):
                    payload["raw_width"] = int(sizes.raw_width)
                if hasattr(sizes, "raw_height"):
                    payload["raw_height"] = int(sizes.raw_height)
        except Exception as exc:
            payload["warning"] = f"RAW metadata extraction unavailable: {exc}"
        return payload
    with Image.open(path) as image:
        payload["width"], payload["height"] = image.size
        payload["mode"] = image.mode
        exif = image.getexif() or {}
        exif_map = {ExifTags.TAGS.get(k, str(k)): v for k, v in exif.items()}
        for key in ("Make", "Model", "DateTimeOriginal", "LensModel"):
            if key in exif_map:
                payload[key.lower()] = str(exif_map[key])
    return payload


def apply_recipe(image: np.ndarray, recipe: dict[str, Any]) -> np.ndarray:
    out = _srgb_to_linear(_clamp01(image.astype(np.float32)))

    wb = recipe["global_adjustments"]["white_balance"]
    tone = recipe["global_adjustments"]["tone"]
    finishing = recipe["global_adjustments"]["finishing"]

    temp = wb["temperature"]
    tint = wb["tint"]
    r_mul = 1.0 + temp * 0.0022 + tint * 0.0003
    g_mul = 1.0 + tint * 0.0012
    b_mul = 1.0 - temp * 0.0022 - tint * 0.0003

    out[..., 0] *= r_mul
    out[..., 1] *= g_mul
    out[..., 2] *= b_mul

    exposure = np.power(2.0, tone["exposure"])
    out *= exposure

    lum = out[..., 0] * 0.2126 + out[..., 1] * 0.7152 + out[..., 2] * 0.0722
    highlights = tone["highlights"] / 100.0
    shadows = tone["shadows"] / 100.0
    whites = tone["whites"] / 100.0
    blacks = tone["blacks"] / 100.0

    tone_scale = np.ones_like(lum)
    hi_mask = lum > 0.5
    sh_mask = ~hi_mask
    tone_scale[hi_mask] += highlights * (lum[hi_mask] - 0.5) * 1.6
    tone_scale[sh_mask] += shadows * (0.5 - lum[sh_mask]) * 1.6
    w_mask = lum > 0.75
    b_mask = lum < 0.25
    tone_scale[w_mask] += whites * (lum[w_mask] - 0.75) * 2.0
    tone_scale[b_mask] += blacks * (0.25 - lum[b_mask]) * 2.0
    out *= tone_scale[..., None]

    contrast = 1.0 + tone["contrast"] / 100.0
    pivot = 0.18
    out = (out - pivot) * contrast + pivot

    curve = recipe["tone_curve"]
    out[..., 0] = _apply_curve(_clamp01(out[..., 0]), curve)
    out[..., 1] = _apply_curve(_clamp01(out[..., 1]), curve)
    out[..., 2] = _apply_curve(_clamp01(out[..., 2]), curve)

    h, s, l = _rgb_to_hsl(out[..., 0], out[..., 1], out[..., 2])

    # HSL bands: weighted hue influence.
    centers = {
        "red": 0.0,
        "orange": 30.0,
        "yellow": 60.0,
        "green": 120.0,
        "aqua": 180.0,
        "blue": 240.0,
        "purple": 275.0,
        "magenta": 320.0,
    }
    hsl = recipe["hsl_bands"]
    sigma = 38.0
    hue_shift = np.zeros_like(h)
    sat_shift = np.zeros_like(h)
    lum_shift = np.zeros_like(h)
    wsum = np.zeros_like(h)
    for band, center in centers.items():
        diff = np.abs(h - center)
        diff = np.minimum(diff, 360.0 - diff)
        weight = np.exp(-0.5 * (diff**2) / (sigma**2))
        hue_shift += weight * hsl[band]["hue"]
        sat_shift += weight * hsl[band]["saturation"]
        lum_shift += weight * hsl[band]["luminance"]
        wsum += weight

    wsum = np.maximum(wsum, 1e-6)
    h = (h + (hue_shift / wsum) * 1.8) % 360.0
    s = np.clip(s * (1.0 + (sat_shift / wsum) / 100.0), 0.0, 1.0)
    l = np.clip(l + (lum_shift / wsum) / 100.0 * 0.25, 0.0, 1.0)

    # Vibrance / saturation.
    vibrance = recipe["global_adjustments"]["vibrance"] / 100.0
    saturation = recipe["global_adjustments"]["saturation"] / 100.0
    s = np.clip(s * (1.0 + saturation) * (1.0 + vibrance * (1.0 - s)), 0.0, 1.0)
    out = np.stack(_hsl_to_rgb(h, s, l), axis=-1)

    # Finishing approximations.
    clarity = finishing["clarity"] / 100.0
    out = out + (out - 0.5) * clarity * 0.2
    dehaze = finishing["dehaze"] / 100.0
    if dehaze >= 0:
        out = (out - 0.5 * dehaze * 0.08) / np.maximum(0.1, 1.0 - dehaze * 0.35)
    else:
        haze = -dehaze
        out = out * (1.0 - haze * 0.25) + 0.5 * haze * 0.25

    vignette = finishing["vignette"] / 100.0
    h_px, w_px = out.shape[:2]
    yy, xx = np.meshgrid(np.arange(h_px), np.arange(w_px), indexing="ij")
    cx = (w_px - 1) * 0.5
    cy = (h_px - 1) * 0.5
    nx = (xx - cx) / max(cx, 1.0)
    ny = (yy - cy) / max(cy, 1.0)
    radial = np.clip(np.sqrt(nx**2 + ny**2), 0.0, 1.0) ** 1.8
    if vignette < 0:
        factor = 1.0 + vignette * radial * 0.7
    else:
        factor = 1.0 + vignette * radial * 0.25
    out *= factor[..., None]

    return _clamp01(_linear_to_srgb(_clamp01(out)))


def save_image(image: np.ndarray, output_path: Path, image_format: str, quality: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    uint8_image = (_clamp01(image) * 255.0).astype(np.uint8)
    pil = Image.fromarray(uint8_image, mode="RGB")
    if image_format == "jpeg":
        pil.save(output_path, format="JPEG", quality=int(np.clip(quality, 1, 100)))
    elif image_format == "tiff":
        pil.save(output_path, format="TIFF", compression="tiff_deflate")
    else:
        raise ValueError(f"Unsupported format {image_format}")
