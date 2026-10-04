#pragma once

#include <cstdint>
#include <string>

#include "telemetry.h"

class SimulatedTelemetrySource {
 public:
  SimulatedTelemetrySource(std::string device_id, std::string boot_id);
  TelemetrySample sample(std::uint64_t sequence, std::uint32_t uptime_seconds,
                         int wifi_rssi_dbm, std::string timestamp) const;

 private:
  std::string device_id_;
  std::string boot_id_;
};

