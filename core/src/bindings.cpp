#include <algorithm>
#include <stdexcept>
#include <string>

#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "imagegpt/engine.hpp"

namespace py = pybind11;
using namespace imagegpt;

namespace {

float clampf(const float value, const float lo, const float hi) {
  return std::max(lo, std::min(hi, value));
}

float read_float(const py::dict& src, const char* key, const float fallback) {
  if (!src.contains(py::str(key))) {
    return fallback;
  }
  return py::cast<float>(src[py::str(key)]);
}

std::string read_string(const py::dict& src, const char* key, const std::string& fallback) {
  if (!src.contains(py::str(key))) {
    return fallback;
  }
  return py::cast<std::string>(src[py::str(key)]);
}

HSLAdjust parse_hsl_band(const py::dict& band) {
  HSLAdjust out{};
  out.hue = clampf(read_float(band, "hue", 0.0F), -100.0F, 100.0F);
  out.saturation = clampf(read_float(band, "saturation", 0.0F), -100.0F, 100.0F);
  out.luminance = clampf(read_float(band, "luminance", 0.0F), -100.0F, 100.0F);
  return out;
}

ColorGradeTone parse_grading_tone(const py::dict& src) {
  ColorGradeTone tone{};
  tone.hue = clampf(read_float(src, "hue", 0.0F), 0.0F, 360.0F);
  tone.sat = clampf(read_float(src, "sat", 0.0F), 0.0F, 100.0F);
  return tone;
}

Recipe parse_recipe(py::dict src) {
  Recipe recipe = default_recipe();
  recipe.version = read_string(src, "version", "1.0");
  recipe.style_tag = read_string(src, "style_tag", "default");
  recipe.confidence = clampf(read_float(src, "confidence", 0.5F), 0.0F, 1.0F);

  if (src.contains("global_adjustments")) {
    py::dict global = py::cast<py::dict>(src["global_adjustments"]);
    if (global.contains("white_balance")) {
      py::dict wb = py::cast<py::dict>(global["white_balance"]);
      recipe.global.white_balance.temperature = clampf(read_float(wb, "temperature", 0.0F), -100.0F, 100.0F);
      recipe.global.white_balance.tint = clampf(read_float(wb, "tint", 0.0F), -100.0F, 100.0F);
    }
    if (global.contains("tone")) {
      py::dict tone = py::cast<py::dict>(global["tone"]);
      recipe.global.tone.exposure = clampf(read_float(tone, "exposure", 0.0F), -5.0F, 5.0F);
      recipe.global.tone.contrast = clampf(read_float(tone, "contrast", 0.0F), -100.0F, 100.0F);
      recipe.global.tone.highlights = clampf(read_float(tone, "highlights", 0.0F), -100.0F, 100.0F);
      recipe.global.tone.shadows = clampf(read_float(tone, "shadows", 0.0F), -100.0F, 100.0F);
      recipe.global.tone.whites = clampf(read_float(tone, "whites", 0.0F), -100.0F, 100.0F);
      recipe.global.tone.blacks = clampf(read_float(tone, "blacks", 0.0F), -100.0F, 100.0F);
    }
    recipe.global.vibrance = clampf(read_float(global, "vibrance", 0.0F), -100.0F, 100.0F);
    recipe.global.saturation = clampf(read_float(global, "saturation", 0.0F), -100.0F, 100.0F);
    if (global.contains("finishing")) {
      py::dict finishing = py::cast<py::dict>(global["finishing"]);
      recipe.global.finishing.clarity = clampf(read_float(finishing, "clarity", 0.0F), -100.0F, 100.0F);
      recipe.global.finishing.dehaze = clampf(read_float(finishing, "dehaze", 0.0F), -100.0F, 100.0F);
      recipe.global.finishing.vignette = clampf(read_float(finishing, "vignette", 0.0F), -100.0F, 100.0F);
    }
  }

  if (src.contains("tone_curve")) {
    recipe.tone_curve.clear();
    py::list points = py::cast<py::list>(src["tone_curve"]);
    for (const auto& item : points) {
      py::dict point = py::cast<py::dict>(item);
      recipe.tone_curve.push_back(
          {clampf(read_float(point, "x", 0.0F), 0.0F, 1.0F), clampf(read_float(point, "y", 0.0F), 0.0F, 1.0F)});
    }
    if (recipe.tone_curve.size() < 2) {
      recipe.tone_curve = {{0.0F, 0.0F}, {1.0F, 1.0F}};
    }
  }

  if (src.contains("hsl_bands")) {
    py::dict bands = py::cast<py::dict>(src["hsl_bands"]);
    if (bands.contains("red")) recipe.hsl.red = parse_hsl_band(py::cast<py::dict>(bands["red"]));
    if (bands.contains("orange")) recipe.hsl.orange = parse_hsl_band(py::cast<py::dict>(bands["orange"]));
    if (bands.contains("yellow")) recipe.hsl.yellow = parse_hsl_band(py::cast<py::dict>(bands["yellow"]));
    if (bands.contains("green")) recipe.hsl.green = parse_hsl_band(py::cast<py::dict>(bands["green"]));
    if (bands.contains("aqua")) recipe.hsl.aqua = parse_hsl_band(py::cast<py::dict>(bands["aqua"]));
    if (bands.contains("blue")) recipe.hsl.blue = parse_hsl_band(py::cast<py::dict>(bands["blue"]));
    if (bands.contains("purple")) recipe.hsl.purple = parse_hsl_band(py::cast<py::dict>(bands["purple"]));
    if (bands.contains("magenta")) recipe.hsl.magenta = parse_hsl_band(py::cast<py::dict>(bands["magenta"]));
  }

  if (src.contains("color_grading")) {
    py::dict grading = py::cast<py::dict>(src["color_grading"]);
    if (grading.contains("shadows")) {
      recipe.grading.shadows = parse_grading_tone(py::cast<py::dict>(grading["shadows"]));
    }
    if (grading.contains("midtones")) {
      recipe.grading.midtones = parse_grading_tone(py::cast<py::dict>(grading["midtones"]));
    }
    if (grading.contains("highlights")) {
      recipe.grading.highlights = parse_grading_tone(py::cast<py::dict>(grading["highlights"]));
    }
    recipe.grading.balance = clampf(read_float(grading, "balance", 0.0F), -100.0F, 100.0F);
    recipe.grading.blend = clampf(read_float(grading, "blend", 50.0F), 0.0F, 100.0F);
  }

  recipe.notes = read_string(src, "notes", "");
  return recipe;
}

ImageFrame frame_from_numpy(const py::array_t<float, py::array::c_style | py::array::forcecast>& array) {
  if (array.ndim() != 3 || array.shape(2) < 3) {
    throw std::runtime_error("Expected float32 array in shape [H, W, 3].");
  }
  ImageFrame frame{};
  frame.height = static_cast<int>(array.shape(0));
  frame.width = static_cast<int>(array.shape(1));
  frame.channels = 3;
  frame.pixels.resize(static_cast<size_t>(frame.width) * static_cast<size_t>(frame.height) * 3U);

  auto view = array.unchecked<3>();
  for (int y = 0; y < frame.height; ++y) {
    for (int x = 0; x < frame.width; ++x) {
      const size_t idx = (static_cast<size_t>(y) * frame.width + x) * 3U;
      frame.pixels[idx + 0] = view(y, x, 0);
      frame.pixels[idx + 1] = view(y, x, 1);
      frame.pixels[idx + 2] = view(y, x, 2);
    }
  }
  return frame;
}

py::array_t<float> frame_to_numpy(const ImageFrame& frame) {
  py::array_t<float> output({frame.height, frame.width, 3});
  auto view = output.mutable_unchecked<3>();
  for (int y = 0; y < frame.height; ++y) {
    for (int x = 0; x < frame.width; ++x) {
      const size_t idx = (static_cast<size_t>(y) * frame.width + x) * 3U;
      view(y, x, 0) = frame.pixels[idx + 0];
      view(y, x, 1) = frame.pixels[idx + 1];
      view(y, x, 2) = frame.pixels[idx + 2];
    }
  }
  return output;
}

}  // namespace

PYBIND11_MODULE(imagegpt_core, m) {
  m.doc() = "ImageGPT native color engine";

  py::class_<ColorEngine>(m, "ColorEngine")
      .def(py::init<>())
      .def("probe_metadata", [](const ColorEngine& engine, const std::string& path) {
        const Metadata metadata = engine.probe_metadata(path);
        py::dict out;
        out["width"] = metadata.width;
        out["height"] = metadata.height;
        out["channels"] = metadata.channels;
        out["is_raw"] = metadata.is_raw;
        out["tags"] = metadata.tags;
        return out;
      })
      .def(
          "render_preview",
          [](const ColorEngine& engine,
             const std::string& input_path,
             py::dict recipe_dict,
             const int max_edge,
             const bool prefer_raw) {
            const Recipe recipe = parse_recipe(std::move(recipe_dict));
            const ImageFrame preview = engine.load_preview(input_path, max_edge, prefer_raw);
            const ImageFrame edited = engine.apply_recipe(preview, recipe);
            return frame_to_numpy(edited);
          },
          py::arg("input_path"),
          py::arg("recipe"),
          py::arg("max_edge") = 1536,
          py::arg("prefer_raw") = true)
      .def(
          "apply_to_array",
          [](const ColorEngine& engine,
             const py::array_t<float, py::array::c_style | py::array::forcecast>& array,
             py::dict recipe_dict) {
            const Recipe recipe = parse_recipe(std::move(recipe_dict));
            const ImageFrame frame = frame_from_numpy(array);
            const ImageFrame edited = engine.apply_recipe(frame, recipe);
            return frame_to_numpy(edited);
          },
          py::arg("image"),
          py::arg("recipe"))
      .def(
          "export_image",
          [](const ColorEngine& engine,
             const std::string& input_path,
             py::dict recipe_dict,
             const std::string& output_path,
             const std::string& format,
             const int quality,
             const bool prefer_raw) {
            const Recipe recipe = parse_recipe(std::move(recipe_dict));
            const ImageFrame source = engine.load_image(input_path, prefer_raw);
            const ImageFrame edited = engine.apply_recipe(source, recipe);
            if (format == "jpeg" || format == "jpg") {
              engine.save_jpeg(edited, output_path, quality);
            } else if (format == "tiff" || format == "tif") {
              engine.save_tiff(edited, output_path);
            } else {
              throw std::runtime_error("Unsupported export format: " + format);
            }
          },
          py::arg("input_path"),
          py::arg("recipe"),
          py::arg("output_path"),
          py::arg("format"),
          py::arg("quality") = 92,
          py::arg("prefer_raw") = true);

  m.def("capabilities", []() {
    py::dict out;
#ifdef IMGGPT_HAS_OIIO
    out["oiio"] = true;
#else
    out["oiio"] = false;
#endif
#ifdef IMGGPT_HAS_LIBRAW
    out["libraw"] = true;
#else
    out["libraw"] = false;
#endif
#ifdef IMGGPT_HAS_LCMS2
    out["lcms2"] = true;
#else
    out["lcms2"] = false;
#endif
    return out;
  });
}

