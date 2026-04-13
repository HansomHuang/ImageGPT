#include "imagegpt/engine.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

#ifdef IMGGPT_HAS_OIIO
#include <OpenImageIO/imageio.h>
#endif

namespace imagegpt {

namespace {

inline float clamp01(const float v) { return std::max(0.0F, std::min(1.0F, v)); }

}  // namespace

ImageFrame decode_image_file(const std::string& path, Metadata* metadata) {
#ifdef IMGGPT_HAS_OIIO
  using namespace OIIO;
  auto input = ImageInput::open(path);
  if (!input) {
    throw std::runtime_error("Failed to open image: " + path);
  }

  const ImageSpec& spec = input->spec();
  if (spec.nchannels < 3) {
    input->close();
    throw std::runtime_error("Image must have at least 3 channels: " + path);
  }

  ImageFrame frame{};
  frame.width = spec.width;
  frame.height = spec.height;
  frame.channels = 3;
  frame.pixels.resize(static_cast<size_t>(frame.width) * static_cast<size_t>(frame.height) * 3U);

  std::vector<float> all_channels(
      static_cast<size_t>(frame.width) * static_cast<size_t>(frame.height) *
      static_cast<size_t>(spec.nchannels));
  if (!input->read_image(TypeDesc::FLOAT, all_channels.data())) {
    const std::string error = input->geterror();
    input->close();
    throw std::runtime_error("Failed to read image pixels: " + error);
  }
  input->close();

  const size_t pixel_count = static_cast<size_t>(frame.width) * static_cast<size_t>(frame.height);
  for (size_t i = 0; i < pixel_count; ++i) {
    frame.pixels[i * 3 + 0] = all_channels[i * static_cast<size_t>(spec.nchannels) + 0];
    frame.pixels[i * 3 + 1] = all_channels[i * static_cast<size_t>(spec.nchannels) + 1];
    frame.pixels[i * 3 + 2] = all_channels[i * static_cast<size_t>(spec.nchannels) + 2];
  }

  if (metadata != nullptr) {
    metadata->width = frame.width;
    metadata->height = frame.height;
    metadata->channels = 3;
    metadata->is_raw = false;
    metadata->tags["format_name"] = spec.format.c_str();
    const auto make_attr = spec.get_string_attribute("Exif:Make");
    const auto model_attr = spec.get_string_attribute("Exif:Model");
    if (!make_attr.empty()) {
      metadata->tags["camera_make"] = make_attr;
    }
    if (!model_attr.empty()) {
      metadata->tags["camera_model"] = model_attr;
    }
  }

  return frame;
#else
  (void)path;
  (void)metadata;
  throw std::runtime_error("OpenImageIO not available in native core build");
#endif
}

void write_image_file(
    const ImageFrame& frame, const std::string& path, const std::string& format, const int quality) {
#ifdef IMGGPT_HAS_OIIO
  using namespace OIIO;
  if (frame.channels < 3) {
    throw std::runtime_error("Frame must contain at least 3 channels.");
  }

  const bool as_jpeg = (format == "jpeg" || format == "jpg");
  const bool as_tiff = (format == "tiff" || format == "tif");
  if (!as_jpeg && !as_tiff) {
    throw std::runtime_error("Unsupported format: " + format);
  }

  auto output = ImageOutput::create(path);
  if (!output) {
    throw std::runtime_error("Failed to create output image: " + path);
  }

  if (as_jpeg) {
    std::vector<unsigned char> pixels(
        static_cast<size_t>(frame.width) * static_cast<size_t>(frame.height) * 3U);
    for (size_t i = 0; i < pixels.size(); ++i) {
      pixels[i] = static_cast<unsigned char>(std::round(clamp01(frame.pixels[i]) * 255.0F));
    }

    ImageSpec spec(frame.width, frame.height, 3, TypeDesc::UINT8);
    spec.attribute("CompressionQuality", std::max(1, std::min(100, quality)));
    if (!output->open(path, spec)) {
      throw std::runtime_error("Failed to open JPEG writer: " + output->geterror());
    }
    if (!output->write_image(TypeDesc::UINT8, pixels.data())) {
      const std::string error = output->geterror();
      output->close();
      throw std::runtime_error("Failed to write JPEG: " + error);
    }
  } else {
    std::vector<unsigned short> pixels(
        static_cast<size_t>(frame.width) * static_cast<size_t>(frame.height) * 3U);
    for (size_t i = 0; i < pixels.size(); ++i) {
      pixels[i] = static_cast<unsigned short>(std::round(clamp01(frame.pixels[i]) * 65535.0F));
    }
    ImageSpec spec(frame.width, frame.height, 3, TypeDesc::UINT16);
    spec.attribute("compression", "zip");
    if (!output->open(path, spec)) {
      throw std::runtime_error("Failed to open TIFF writer: " + output->geterror());
    }
    if (!output->write_image(TypeDesc::UINT16, pixels.data())) {
      const std::string error = output->geterror();
      output->close();
      throw std::runtime_error("Failed to write TIFF: " + error);
    }
  }

  output->close();
#else
  (void)frame;
  (void)path;
  (void)format;
  (void)quality;
  throw std::runtime_error("OpenImageIO not available in native core build");
#endif
}

ImageFrame resize_bilinear(const ImageFrame& frame, const int max_edge) {
  if (max_edge <= 0 || (frame.width <= max_edge && frame.height <= max_edge)) {
    return frame;
  }

  const float scale = static_cast<float>(max_edge) /
                      static_cast<float>(std::max(frame.width, frame.height));
  const int dst_w = std::max(1, static_cast<int>(std::round(static_cast<float>(frame.width) * scale)));
  const int dst_h =
      std::max(1, static_cast<int>(std::round(static_cast<float>(frame.height) * scale)));

  ImageFrame resized{};
  resized.width = dst_w;
  resized.height = dst_h;
  resized.channels = 3;
  resized.pixels.resize(static_cast<size_t>(dst_w) * static_cast<size_t>(dst_h) * 3U);

  for (int y = 0; y < dst_h; ++y) {
    const float src_y = (static_cast<float>(y) + 0.5F) / scale - 0.5F;
    const int y0 = std::max(0, static_cast<int>(std::floor(src_y)));
    const int y1 = std::min(frame.height - 1, y0 + 1);
    const float wy = src_y - static_cast<float>(y0);

    for (int x = 0; x < dst_w; ++x) {
      const float src_x = (static_cast<float>(x) + 0.5F) / scale - 0.5F;
      const int x0 = std::max(0, static_cast<int>(std::floor(src_x)));
      const int x1 = std::min(frame.width - 1, x0 + 1);
      const float wx = src_x - static_cast<float>(x0);

      for (int c = 0; c < 3; ++c) {
        const float p00 = frame.pixels[(static_cast<size_t>(y0) * frame.width + x0) * 3U + c];
        const float p10 = frame.pixels[(static_cast<size_t>(y0) * frame.width + x1) * 3U + c];
        const float p01 = frame.pixels[(static_cast<size_t>(y1) * frame.width + x0) * 3U + c];
        const float p11 = frame.pixels[(static_cast<size_t>(y1) * frame.width + x1) * 3U + c];
        const float top = p00 + (p10 - p00) * wx;
        const float bottom = p01 + (p11 - p01) * wx;
        resized.pixels[(static_cast<size_t>(y) * dst_w + x) * 3U + c] =
            top + (bottom - top) * wy;
      }
    }
  }
  return resized;
}

}  // namespace imagegpt

