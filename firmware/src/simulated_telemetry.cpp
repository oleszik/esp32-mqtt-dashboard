#include "simulated_telemetry.h"

#include <cmath>
#include <optional>
#include <utility>

SimulatedTelemetrySource::SimulatedTelemetrySource(std::string device_id, std::string boot_id)
    : device_id_(std::move(device_id)), boot_id_(std::move(boot_id)) {}

TelemetrySample SimulatedTelemetrySource::sample(std::uint64_t sequence,
                                                 std::uint32_t uptime_seconds,
                                                 int wifi_rssi_dbm,
                                                 std::string timestamp) const {
  const double phase = static_cast<double>(sequence) / 12.0;
  return {
      device_id_,
      boot_id_,
      sequence,
      timestamp.empty() ? std::nullopt : std::optional<std::string>(std::move(timestamp)),
      uptime_seconds,
      22.5 + 2.4 * std::sin(phase),
      48.0 + 5.5 * std::sin(phase / 2.0 + 0.7),
      1013.2 + 2.1 * std::sin(phase / 3.0 + 1.1),
      wifi_rssi_dbm,
  };
}

