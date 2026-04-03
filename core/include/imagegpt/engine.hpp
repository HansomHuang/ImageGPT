#pragma once

#include <string>

#include "imagegpt/recipe.hpp"
#include "imagegpt/types.hpp"

namespace imagegpt {

class ColorEngine {
 public:
  Metadata probe_metadata(const std::string& path) const;
  ImageFrame load_image(const std::string& path, bool prefer_raw) const;
  ImageFrame load_preview(const std::string& path, int max_edge, bool prefer_raw) const;
  ImageFrame apply_recipe(const ImageFrame& frame, const Recipe& recipe) const;
  void save_jpeg(const ImageFrame& frame, const std::string& path, int quality) const;
  void save_tiff(const ImageFrame& frame, const std::string& path) const;
};

bool is_raw_extension(const std::string& path);
ImageFrame run_pipeline(const ImageFrame& frame, const Recipe& recipe);

ImageFrame decode_image_file(const std::string& path, Metadata* metadata);
ImageFrame decode_raw_file(const std::string& path, Metadata* metadata);
void write_image_file(
    const ImageFrame& frame, const std::string& path, const std::string& format, int quality);
ImageFrame resize_bilinear(const ImageFrame& frame, int max_edge);
void apply_output_icc_transform(ImageFrame* frame);

}  // namespace imagegpt

