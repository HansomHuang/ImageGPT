# Pipeline Mathematics (v1)

ImageGPT uses deterministic global color operations in this order:

1. Decode input (OpenImageIO for JPEG/TIFF; LibRaw for RAW when available).
2. Normalize to float32 RGB in `[0, 1]`.
3. White balance:
   - Temperature and tint produce channel multipliers.
4. Exposure:
   - Multiply by `2^exposure`.
5. Highlights / Shadows / Whites / Blacks:
   - Luma-dependent scalar adjustment.
6. Contrast:
   - Linear contrast around pivot `0.18`.
7. Tone curve:
   - Piecewise linear interpolation with monotonic validation.
8. Color grading:
   - Split-toning style weighted tinting of shadows/midtones/highlights.
9. HSL bands:
   - Eight hue-band weighted adjustments (hue/sat/luminance).
10. Vibrance / saturation:
    - Global saturation and low-saturation-weighted vibrance.
11. Finishing:
    - Clarity/dehaze/vignette approximations.
12. Output transform:
    - LittleCMS2 ICC path (sRGB output profile in v1).
13. Export:
    - JPEG (quality control) or TIFF.

## Tradeoffs

- v1 favors deterministic and robust behavior over camera-specific scientific matching.
- Finishing controls are conservative approximations, not full local operators.
- RAW color rendition is LibRaw-based baseline, not a proprietary camera-science stack.

