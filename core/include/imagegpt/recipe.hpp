#pragma once

#include <array>
#include <string>
#include <vector>

namespace imagegpt {

struct CurvePoint {
  float x = 0.0F;
  float y = 0.0F;
};

struct WhiteBalance {
  float temperature = 0.0F;  // [-100, 100]
  float tint = 0.0F;         // [-100, 100]
};

struct ToneAdjustments {
  float exposure = 0.0F;    // [-5, 5] stops
  float contrast = 0.0F;    // [-100, 100]
  float highlights = 0.0F;  // [-100, 100]
  float shadows = 0.0F;     // [-100, 100]
  float whites = 0.0F;      // [-100, 100]
  float blacks = 0.0F;      // [-100, 100]
};

struct HSLAdjust {
  float hue = 0.0F;         // [-100, 100]
  float saturation = 0.0F;  // [-100, 100]
  float luminance = 0.0F;   // [-100, 100]
};

struct ColorGradeTone {
  float hue = 0.0F;  // [0, 360]
  float sat = 0.0F;  // [0, 100]
};

struct ColorGrading {
  ColorGradeTone shadows{};
  ColorGradeTone midtones{};
  ColorGradeTone highlights{};
  float balance = 0.0F;  // [-100, 100]
  float blend = 50.0F;   // [0, 100]
};

struct Finishing {
  float clarity = 0.0F;   // [-100, 100]
  float dehaze = 0.0F;    // [-100, 100]
  float vignette = 0.0F;  // [-100, 100]
};

struct GlobalAdjustments {
  WhiteBalance white_balance{};
  ToneAdjustments tone{};
  float vibrance = 0.0F;    // [-100, 100]
  float saturation = 0.0F;  // [-100, 100]
  Finishing finishing{};
};

struct HSLBands {
  HSLAdjust red{};
  HSLAdjust orange{};
  HSLAdjust yellow{};
  HSLAdjust green{};
  HSLAdjust aqua{};
  HSLAdjust blue{};
  HSLAdjust purple{};
  HSLAdjust magenta{};
};

struct Recipe {
  std::string version = "1.0";
  std::string style_tag = "default";
  float confidence = 0.5F;
  GlobalAdjustments global{};
  std::vector<CurvePoint> tone_curve{{0.0F, 0.0F}, {1.0F, 1.0F}};
  HSLBands hsl{};
  ColorGrading grading{};
  std::string notes{};
  std::vector<std::string> warnings{};
};

Recipe default_recipe();

}  // namespace imagegpt

