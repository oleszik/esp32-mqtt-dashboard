#pragma once

#include <algorithm>
#include <cstdint>

class Backoff {
 public:
  constexpr Backoff(std::uint32_t minimum_ms, std::uint32_t maximum_ms)
      : minimum_ms_(minimum_ms), maximum_ms_(maximum_ms), attempts_(0) {}

  [[nodiscard]] constexpr std::uint32_t next_delay(std::uint32_t jitter = 0) {
    const std::uint32_t shift = std::min<std::uint32_t>(attempts_, 30);
    const std::uint64_t exponential = static_cast<std::uint64_t>(minimum_ms_) << shift;
    ++attempts_;
    const std::uint32_t bounded = static_cast<std::uint32_t>(
        std::min<std::uint64_t>(exponential, maximum_ms_));
    return std::min<std::uint32_t>(bounded + jitter, maximum_ms_);
  }

  constexpr void reset() { attempts_ = 0; }
  [[nodiscard]] constexpr std::uint32_t attempts() const { return attempts_; }

 private:
  std::uint32_t minimum_ms_;
  std::uint32_t maximum_ms_;
  std::uint32_t attempts_;
};

