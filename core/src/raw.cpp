#include "imagegpt/engine.hpp"

#include <stdexcept>
#include <string>
#include <vector>

#ifdef IMGGPT_HAS_LIBRAW
#include <libraw/libraw.h>
#endif

namespace imagegpt {

ImageFrame decode_raw_file(const std::string& path, Metadata* metadata) {
#ifdef IMGGPT_HAS_LIBRAW
  LibRaw processor;

  int result = processor.open_file(path.c_str());
  if (result != LIBRAW_SUCCESS) {
    throw std::runtime_error("LibRaw open_file failed: " + std::string(libraw_strerror(result)));
  }

  result = processor.unpack();
  if (result != LIBRAW_SUCCESS) {
    processor.recycle();
    throw std::runtime_error("LibRaw unpack failed: " + std::string(libraw_strerror(result)));
  }

  processor.imgdata.params.output_bps = 16;
  processor.imgdata.params.use_camera_wb = 1;
  processor.imgdata.params.no_auto_bright = 1;
  result = processor.dcraw_process();
  if (result != LIBRAW_SUCCESS) {
    processor.recycle();
    throw std::runtime_error(
        "LibRaw dcraw_process failed: " + std::string(libraw_strerror(result)));
  }

  libraw_processed_image_t* image = processor.dcraw_make_mem_image(&result);
  if (image == nullptr || result != LIBRAW_SUCCESS) {
    processor.recycle();
    throw std::runtime_error(
        "LibRaw dcraw_make_mem_image failed: " + std::string(libraw_strerror(result)));
  }

  if (image->colors < 3 || image->bits != 16) {
    LibRaw::dcraw_clear_mem(image);
    processor.recycle();
    throw std::runtime_error("Unsupported RAW output format from LibRaw.");
  }

  ImageFrame frame{};
  frame.width = image->width;
  frame.height = image->height;
  frame.channels = 3;
  frame.pixels.resize(static_cast<size_t>(frame.width) * static_cast<size_t>(frame.height) * 3U);

  const auto* src = reinterpret_cast<const unsigned short*>(image->data);
  const size_t pixel_count = static_cast<size_t>(frame.width) * static_cast<size_t>(frame.height);
  for (size_t i = 0; i < pixel_count; ++i) {
    frame.pixels[i * 3 + 0] = static_cast<float>(src[i * image->colors + 0]) / 65535.0F;
    frame.pixels[i * 3 + 1] = static_cast<float>(src[i * image->colors + 1]) / 65535.0F;
    frame.pixels[i * 3 + 2] = static_cast<float>(src[i * image->colors + 2]) / 65535.0F;
  }

  if (metadata != nullptr) {
    metadata->width = frame.width;
    metadata->height = frame.height;
    metadata->channels = frame.channels;
    metadata->is_raw = true;
    metadata->tags["camera_make"] = processor.imgdata.idata.make;
    metadata->tags["camera_model"] = processor.imgdata.idata.model;
    metadata->tags["iso"] = std::to_string(processor.imgdata.other.iso_speed);
    metadata->tags["shutter"] = std::to_string(processor.imgdata.other.shutter);
    metadata->tags["aperture"] = std::to_string(processor.imgdata.other.aperture);
    metadata->tags["focal_length"] = std::to_string(processor.imgdata.other.focal_len);
  }

  LibRaw::dcraw_clear_mem(image);
  processor.recycle();
  return frame;
#else
  (void)path;
  (void)metadata;
  throw std::runtime_error("LibRaw support is unavailable in this native core build");
#endif
}

}  // namespace imagegpt

