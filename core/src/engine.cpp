#include "imagegpt/engine.hpp"

#include <algorithm>
#include <cctype>
#include <stdexcept>

namespace imagegpt {

namespace {

std::string lowercase(std::string value) {
  std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
    return static_cast<char>(std::tolower(c));
  });
  return value;
}

}  // namespace

Recipe default_recipe() { return Recipe{}; }

bool is_raw_extension(const std::string& path) {
  const auto dot_index = path.find_last_of('.');
  if (dot_index == std::string::npos) {
    return false;
  }

  const auto ext = lowercase(path.substr(dot_index + 1));
  return ext == "arw" || ext == "cr2" || ext == "cr3" || ext == "nef" || ext == "nrw" ||
         ext == "raf" || ext == "dng";
}

Metadata ColorEngine::probe_metadata(const std::string& path) const {
  Metadata metadata{};
  if (is_raw_extension(path)) {
    metadata.is_raw = true;
  }
  Metadata decoded_metadata{};
  try {
    if (metadata.is_raw) {
      (void)decode_raw_file(path, &decoded_metadata);
    } else {
      (void)decode_image_file(path, &decoded_metadata);
    }
    return decoded_metadata;
  } catch (...) {
    return metadata;
  }
}

ImageFrame ColorEngine::load_image(const std::string& path, bool prefer_raw) const {
  const bool is_raw_file = is_raw_extension(path);
  Metadata metadata{};
  if (prefer_raw && is_raw_file) {
    return decode_raw_file(path, &metadata);
  }
  if (is_raw_file) {
    return decode_raw_file(path, &metadata);
  }
  return decode_image_file(path, &metadata);
}

ImageFrame ColorEngine::load_preview(
    const std::string& path, const int max_edge, const bool prefer_raw) const {
  const ImageFrame full = load_image(path, prefer_raw);
  if (max_edge <= 0) {
    return full;
  }
  return resize_bilinear(full, max_edge);
}

ImageFrame ColorEngine::apply_recipe(const ImageFrame& frame, const Recipe& recipe) const {
  return run_pipeline(frame, recipe);
}

void ColorEngine::save_jpeg(const ImageFrame& frame, const std::string& path, const int quality) const {
  ImageFrame transformed = frame;
  apply_output_icc_transform(&transformed);
  write_image_file(transformed, path, "jpeg", quality);
}

void ColorEngine::save_tiff(const ImageFrame& frame, const std::string& path) const {
  ImageFrame transformed = frame;
  apply_output_icc_transform(&transformed);
  write_image_file(transformed, path, "tiff", 100);
}

}  // namespace imagegpt

