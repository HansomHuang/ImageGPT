#include "imagegpt/engine.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace imagegpt {

namespace {

constexpr float kEps = 1e-6F;
constexpr float kPi = 3.14159265358979323846F;

inline float clampf(const float v, const float lo, const float hi) {
  return std::max(lo, std::min(hi, v));
}

inline float wrap_degrees(float deg) {
  while (deg < 0.0F) {
    deg += 360.0F;
  }
  while (deg >= 360.0F) {
    deg -= 360.0F;
  }
  return deg;
}

inline float srgb_to_linear(float v) {
  v = clampf(v, 0.0F, 1.0F);
  if (v <= 0.04045F) {
    return v / 12.92F;
  }
  return std::pow((v + 0.055F) / 1.055F, 2.4F);
}

inline float linear_to_srgb(float v) {
  v = clampf(v, 0.0F, 1.0F);
  if (v <= 0.0031308F) {
    return v * 12.92F;
  }
  return 1.055F * std::pow(v, 1.0F / 2.4F) - 0.055F;
}

std::array<float, 3> hsv_to_rgb(float h, float s, float v) {
  h = wrap_degrees(h);
  s = clampf(s, 0.0F, 1.0F);
  v = clampf(v, 0.0F, 1.0F);

  const float c = v * s;
  const float hp = h / 60.0F;
  const float x = c * (1.0F - std::fabs(std::fmod(hp, 2.0F) - 1.0F));
  float r = 0.0F;
  float g = 0.0F;
  float b = 0.0F;

  if (hp < 1.0F) {
    r = c;
    g = x;
  } else if (hp < 2.0F) {
    r = x;
    g = c;
  } else if (hp < 3.0F) {
    g = c;
    b = x;
  } else if (hp < 4.0F) {
    g = x;
    b = c;
  } else if (hp < 5.0F) {
    r = x;
    b = c;
  } else {
    r = c;
    b = x;
  }

  const float m = v - c;
  return {r + m, g + m, b + m};
}

void rgb_to_hsl(float r, float g, float b, float* h, float* s, float* l) {
  const float max_c = std::max(r, std::max(g, b));
  const float min_c = std::min(r, std::min(g, b));
  const float delta = max_c - min_c;

  *l = (max_c + min_c) * 0.5F;
  if (delta < kEps) {
    *h = 0.0F;
    *s = 0.0F;
    return;
  }

  *s = delta / (1.0F - std::fabs(2.0F * (*l) - 1.0F) + kEps);
  if (max_c == r) {
    *h = 60.0F * std::fmod(((g - b) / delta), 6.0F);
  } else if (max_c == g) {
    *h = 60.0F * (((b - r) / delta) + 2.0F);
  } else {
    *h = 60.0F * (((r - g) / delta) + 4.0F);
  }
  *h = wrap_degrees(*h);
}

float hue_to_rgb(const float p, const float q, float t) {
  if (t < 0.0F) {
    t += 1.0F;
  }
  if (t > 1.0F) {
    t -= 1.0F;
  }
  if (t < 1.0F / 6.0F) {
    return p + (q - p) * 6.0F * t;
  }
  if (t < 1.0F / 2.0F) {
    return q;
  }
  if (t < 2.0F / 3.0F) {
    return p + (q - p) * (2.0F / 3.0F - t) * 6.0F;
  }
  return p;
}

std::array<float, 3> hsl_to_rgb(float h, float s, float l) {
  h = wrap_degrees(h) / 360.0F;
  s = clampf(s, 0.0F, 1.0F);
  l = clampf(l, 0.0F, 1.0F);
  if (s < kEps) {
    return {l, l, l};
  }
  const float q = l < 0.5F ? l * (1.0F + s) : (l + s - l * s);
  const float p = 2.0F * l - q;
  return {hue_to_rgb(p, q, h + 1.0F / 3.0F), hue_to_rgb(p, q, h), hue_to_rgb(p, q, h - 1.0F / 3.0F)};
}

float luma(const float r, const float g, const float b) { return 0.2126F * r + 0.7152F * g + 0.0722F * b; }

float tone_curve_value(const std::vector<CurvePoint>& points, const float x) {
  if (points.empty()) {
    return x;
  }
  if (x <= points.front().x) {
    return points.front().y;
  }
  if (x >= points.back().x) {
    return points.back().y;
  }

  for (size_t i = 1; i < points.size(); ++i) {
    if (x <= points[i].x) {
      const float x0 = points[i - 1].x;
      const float y0 = points[i - 1].y;
      const float x1 = points[i].x;
      const float y1 = points[i].y;
      const float t = (x - x0) / std::max(kEps, (x1 - x0));
      return y0 + (y1 - y0) * t;
    }
  }
  return x;
}

float hue_distance_deg(const float a, const float b) {
  const float diff = std::fabs(a - b);
  return std::min(diff, 360.0F - diff);
}

void apply_hsl_bands(float* r, float* g, float* b, const HSLBands& bands) {
  float h = 0.0F;
  float s = 0.0F;
  float l = 0.0F;
  rgb_to_hsl(*r, *g, *b, &h, &s, &l);

  struct BandSpec {
    float center;
    HSLAdjust adj;
  };
  const std::array<BandSpec, 8> specs{{
      {0.0F, bands.red},       {30.0F, bands.orange}, {60.0F, bands.yellow}, {120.0F, bands.green},
      {180.0F, bands.aqua},    {240.0F, bands.blue},  {275.0F, bands.purple}, {320.0F, bands.magenta},
  }};

  float w_sum = 0.0F;
  float hue_shift = 0.0F;
  float sat_shift = 0.0F;
  float lum_shift = 0.0F;
  constexpr float sigma = 38.0F;

  for (const auto& spec : specs) {
    const float d = hue_distance_deg(h, spec.center);
    const float w = std::exp(-0.5F * (d * d) / (sigma * sigma));
    w_sum += w;
    hue_shift += w * spec.adj.hue;
    sat_shift += w * spec.adj.saturation;
    lum_shift += w * spec.adj.luminance;
  }

  if (w_sum > kEps) {
    hue_shift /= w_sum;
    sat_shift /= w_sum;
    lum_shift /= w_sum;
  }

  h = wrap_degrees(h + hue_shift * 1.8F);
  s = clampf(s * (1.0F + sat_shift / 100.0F), 0.0F, 1.0F);
  l = clampf(l + lum_shift / 100.0F * 0.25F, 0.0F, 1.0F);
  const auto rgb = hsl_to_rgb(h, s, l);
  *r = rgb[0];
  *g = rgb[1];
  *b = rgb[2];
}

void apply_vibrance_and_saturation(float* r, float* g, float* b, const float vibrance, const float saturation) {
  float h = 0.0F;
  float s = 0.0F;
  float l = 0.0F;
  rgb_to_hsl(*r, *g, *b, &h, &s, &l);
  const float sat_factor = 1.0F + saturation / 100.0F;
  const float vib_gain = (vibrance / 100.0F) * (1.0F - s);
  s = clampf(s * sat_factor * (1.0F + vib_gain), 0.0F, 1.0F);
  const auto rgb = hsl_to_rgb(h, s, l);
  *r = rgb[0];
  *g = rgb[1];
  *b = rgb[2];
}

void apply_color_grading(float* r, float* g, float* b, const ColorGrading& grading) {
  const float lum = luma(*r, *g, *b);
  const float balance_shift = grading.balance / 100.0F * 0.25F;
  const float shadow_w = clampf((0.6F - lum) + balance_shift, 0.0F, 1.0F);
  const float highlight_w = clampf((lum - 0.4F) - balance_shift, 0.0F, 1.0F);
  const float mid_w = clampf(1.0F - std::max(shadow_w, highlight_w), 0.0F, 1.0F);
  const float blend = clampf(grading.blend / 100.0F, 0.0F, 1.0F);

  const auto s_tint = hsv_to_rgb(grading.shadows.hue, grading.shadows.sat / 100.0F, 1.0F);
  const auto m_tint = hsv_to_rgb(grading.midtones.hue, grading.midtones.sat / 100.0F, 1.0F);
  const auto h_tint = hsv_to_rgb(grading.highlights.hue, grading.highlights.sat / 100.0F, 1.0F);

  const float s_strength = shadow_w * blend * (grading.shadows.sat / 100.0F) * 0.25F;
  const float m_strength = mid_w * blend * (grading.midtones.sat / 100.0F) * 0.2F;
  const float h_strength = highlight_w * blend * (grading.highlights.sat / 100.0F) * 0.25F;

  *r = *r * (1.0F - s_strength) + s_tint[0] * s_strength;
  *g = *g * (1.0F - s_strength) + s_tint[1] * s_strength;
  *b = *b * (1.0F - s_strength) + s_tint[2] * s_strength;

  *r = *r * (1.0F - m_strength) + m_tint[0] * m_strength;
  *g = *g * (1.0F - m_strength) + m_tint[1] * m_strength;
  *b = *b * (1.0F - m_strength) + m_tint[2] * m_strength;

  *r = *r * (1.0F - h_strength) + h_tint[0] * h_strength;
  *g = *g * (1.0F - h_strength) + h_tint[1] * h_strength;
  *b = *b * (1.0F - h_strength) + h_tint[2] * h_strength;
}

void apply_finishing(
    float* r, float* g, float* b, const int x, const int y, const int w, const int h, const Finishing& f) {
  const float clarity_amount = f.clarity / 100.0F;
  const float dehaze_amount = f.dehaze / 100.0F;
  const float vignette_amount = f.vignette / 100.0F;

  // Midtone clarity approximation.
  for (float* c : {r, g, b}) {
    const float delta = *c - 0.5F;
    const float mid_weight = 1.0F - clampf(std::fabs(delta) * 2.0F, 0.0F, 1.0F);
    *c = *c + delta * clarity_amount * 0.35F * mid_weight;
  }

  // Global dehaze approximation based on linear contrast pivot.
  if (dehaze_amount >= 0.0F) {
    const float denom = std::max(0.1F, 1.0F - dehaze_amount * 0.35F);
    *r = (*r - 0.5F * dehaze_amount * 0.08F) / denom;
    *g = (*g - 0.5F * dehaze_amount * 0.08F) / denom;
    *b = (*b - 0.5F * dehaze_amount * 0.08F) / denom;
  } else {
    const float haze = -dehaze_amount;
    *r = *r * (1.0F - haze * 0.25F) + 0.5F * haze * 0.25F;
    *g = *g * (1.0F - haze * 0.25F) + 0.5F * haze * 0.25F;
    *b = *b * (1.0F - haze * 0.25F) + 0.5F * haze * 0.25F;
  }

  const float cx = (static_cast<float>(w) - 1.0F) * 0.5F;
  const float cy = (static_cast<float>(h) - 1.0F) * 0.5F;
  const float nx = (static_cast<float>(x) - cx) / std::max(1.0F, cx);
  const float ny = (static_cast<float>(y) - cy) / std::max(1.0F, cy);
  const float radial = std::pow(clampf(std::sqrt(nx * nx + ny * ny), 0.0F, 1.0F), 1.8F);
  float vignette_factor = 1.0F;
  if (vignette_amount < 0.0F) {
    vignette_factor = 1.0F + vignette_amount * radial * 0.7F;
  } else {
    vignette_factor = 1.0F + vignette_amount * radial * 0.25F;
  }

  *r *= vignette_factor;
  *g *= vignette_factor;
  *b *= vignette_factor;
}

}  // namespace

ImageFrame run_pipeline(const ImageFrame& frame, const Recipe& recipe) {
  if (frame.channels < 3 || frame.pixels.empty()) {
    throw std::runtime_error("Invalid frame for pipeline.");
  }

  ImageFrame out = frame;

  // 1) decode is done before this function
  // 2) normalize/linearize
  for (float& px : out.pixels) {
    px = srgb_to_linear(px);
  }

  // 3) white balance
  const float temp = clampf(recipe.global.white_balance.temperature, -100.0F, 100.0F);
  const float tint = clampf(recipe.global.white_balance.tint, -100.0F, 100.0F);
  const float r_mul = 1.0F + temp * 0.0022F + tint * 0.0003F;
  const float g_mul = 1.0F + tint * 0.0012F;
  const float b_mul = 1.0F - temp * 0.0022F - tint * 0.0003F;

  const float exp_mul = std::pow(2.0F, clampf(recipe.global.tone.exposure, -5.0F, 5.0F));
  const float contrast_factor = 1.0F + clampf(recipe.global.tone.contrast, -100.0F, 100.0F) / 100.0F;
  const float highlights = clampf(recipe.global.tone.highlights, -100.0F, 100.0F) / 100.0F;
  const float shadows = clampf(recipe.global.tone.shadows, -100.0F, 100.0F) / 100.0F;
  const float whites = clampf(recipe.global.tone.whites, -100.0F, 100.0F) / 100.0F;
  const float blacks = clampf(recipe.global.tone.blacks, -100.0F, 100.0F) / 100.0F;

  for (int y = 0; y < out.height; ++y) {
    for (int x = 0; x < out.width; ++x) {
      const size_t idx = (static_cast<size_t>(y) * out.width + x) * 3U;
      float r = out.pixels[idx + 0] * r_mul;
      float g = out.pixels[idx + 1] * g_mul;
      float b = out.pixels[idx + 2] * b_mul;

      // 4) exposure
      r *= exp_mul;
      g *= exp_mul;
      b *= exp_mul;

      // 5) highlights/shadows/whites/blacks
      const float lum = luma(r, g, b);
      float tone_scale = 1.0F;
      if (lum > 0.5F) {
        tone_scale += highlights * (lum - 0.5F) * 1.6F;
      } else {
        tone_scale += shadows * (0.5F - lum) * 1.6F;
      }
      if (lum > 0.75F) {
        tone_scale += whites * (lum - 0.75F) * 2.0F;
      } else if (lum < 0.25F) {
        tone_scale += blacks * (0.25F - lum) * 2.0F;
      }

      r *= tone_scale;
      g *= tone_scale;
      b *= tone_scale;

      // 6) contrast
      constexpr float pivot = 0.18F;
      r = (r - pivot) * contrast_factor + pivot;
      g = (g - pivot) * contrast_factor + pivot;
      b = (b - pivot) * contrast_factor + pivot;

      // 7) tone curve
      r = tone_curve_value(recipe.tone_curve, clampf(r, 0.0F, 1.0F));
      g = tone_curve_value(recipe.tone_curve, clampf(g, 0.0F, 1.0F));
      b = tone_curve_value(recipe.tone_curve, clampf(b, 0.0F, 1.0F));

      // 8) color grading
      apply_color_grading(&r, &g, &b, recipe.grading);

      // 9) HSL bands
      apply_hsl_bands(&r, &g, &b, recipe.hsl);

      // 10) vibrance/saturation
      apply_vibrance_and_saturation(&r, &g, &b, recipe.global.vibrance, recipe.global.saturation);

      // 11) finishing
      apply_finishing(&r, &g, &b, x, y, out.width, out.height, recipe.global.finishing);

      out.pixels[idx + 0] = clampf(r, 0.0F, 1.0F);
      out.pixels[idx + 1] = clampf(g, 0.0F, 1.0F);
      out.pixels[idx + 2] = clampf(b, 0.0F, 1.0F);
    }
  }

  // Convert back to display-referred sRGB
  for (float& px : out.pixels) {
    px = linear_to_srgb(clampf(px, 0.0F, 1.0F));
  }

  return out;
}

}  // namespace imagegpt

