#include "imagegpt/engine.hpp"

#include <stdexcept>

#ifdef IMGGPT_HAS_LCMS2
#include <lcms2.h>
#endif

namespace imagegpt {

void apply_output_icc_transform(ImageFrame* frame) {
  if (frame == nullptr || frame->pixels.empty()) {
    return;
  }

#ifdef IMGGPT_HAS_LCMS2
  cmsHPROFILE src_profile = cmsCreate_sRGBProfile();
  cmsHPROFILE dst_profile = cmsCreate_sRGBProfile();
  if (src_profile == nullptr || dst_profile == nullptr) {
    if (src_profile != nullptr) {
      cmsCloseProfile(src_profile);
    }
    if (dst_profile != nullptr) {
      cmsCloseProfile(dst_profile);
    }
    throw std::runtime_error("Failed to create sRGB profile in LittleCMS2.");
  }

  cmsHTRANSFORM transform =
      cmsCreateTransform(src_profile, TYPE_RGB_FLT, dst_profile, TYPE_RGB_FLT, INTENT_PERCEPTUAL, 0);
  if (transform == nullptr) {
    cmsCloseProfile(src_profile);
    cmsCloseProfile(dst_profile);
    throw std::runtime_error("Failed to create ICC transform in LittleCMS2.");
  }

  cmsDoTransform(
      transform,
      frame->pixels.data(),
      frame->pixels.data(),
      static_cast<cmsUInt32Number>(frame->width * frame->height));

  cmsDeleteTransform(transform);
  cmsCloseProfile(src_profile);
  cmsCloseProfile(dst_profile);
#endif
}

}  // namespace imagegpt

