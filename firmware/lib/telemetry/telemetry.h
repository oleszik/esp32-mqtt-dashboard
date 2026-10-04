#pragma once

#include <cstdint>
#include <optional>
#include <string>

struct TelemetrySample {
  std::string device_id;
  std::string boot_id;
  std::uint64_t sequence;
  std::optional<std::string> sampled_at;
  std::uint32_t uptime_seconds;
  double temperature_c;
  double humidity_percent;
  double pressure_hpa;
  int wifi_rssi_dbm;
};

[[nodiscard]] bool valid_telemetry(const TelemetrySample& sample);
[[nodiscard]] std::string serialize_telemetry(const TelemetrySample& sample);
[[nodiscard]] std::string serialize_status(const std::string& device_id,
                                           const std::optional<std::string>& boot_id,
                                           const std::string& status,
                                           const std::string& reason,
                                           const std::optional<std::string>& firmware_version);
[[nodiscard]] bool valid_interval(std::uint32_t seconds);

