#pragma once

#include <Arduino.h>

#include "backoff.h"

class WifiManager {
 public:
  void begin();
  void update(std::uint32_t now_ms);
  [[nodiscard]] bool connected() const;

 private:
  Backoff backoff_{1000, 30000};
  std::uint32_t next_attempt_ms_{0};
  bool was_connected_{false};
};

