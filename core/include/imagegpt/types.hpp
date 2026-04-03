#pragma once

#include <string>
#include <unordered_map>
#include <vector>

namespace imagegpt {

struct ImageFrame {
  int width = 0;
  int height = 0;
  int channels = 3;
  std::vector<float> pixels;
};

struct Metadata {
  int width = 0;
  int height = 0;
  int channels = 0;
  bool is_raw = false;
  std::unordered_map<std::string, std::string> tags;
};

}  // namespace imagegpt

