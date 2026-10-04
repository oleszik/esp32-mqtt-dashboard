#include "telemetry.h"

#include <cmath>
#include <iomanip>
#include <sstream>

#include "topics.h"

namespace {
std::string quoted_or_null(const std::optional<std::string>& value) {
  return value ? "\"" + *value + "\"" : "null";
}
}  // namespace

bool valid_telemetry(const TelemetrySample& sample) {
  return topics::valid_device_id(sample.device_id) && !sample.boot_id.empty() &&
         std::isfinite(sample.temperature_c) && sample.temperature_c >= -50.0 &&
         sample.temperature_c <= 100.0 && std::isfinite(sample.humidity_percent) &&
         sample.humidity_percent >= 0.0 && sample.humidity_percent <= 100.0 &&
         std::isfinite(sample.pressure_hpa) && sample.pressure_hpa >= 300.0 &&
         sample.pressure_hpa <= 1200.0 && sample.wifi_rssi_dbm >= -127 &&
         sample.wifi_rssi_dbm <= 0;
}

std::string serialize_telemetry(const TelemetrySample& sample) {
  if (!valid_telemetry(sample)) return {};
  std::ostringstream output;
  output << std::fixed << std::setprecision(2)
         << "{\"schema_version\":1,\"device_id\":\"" << sample.device_id
         << "\",\"boot_id\":\"" << sample.boot_id << "\",\"sequence\":"
         << sample.sequence << ",\"sampled_at\":" << quoted_or_null(sample.sampled_at)
         << ",\"uptime_seconds\":" << sample.uptime_seconds << ",\"temperature_c\":"
         << sample.temperature_c << ",\"humidity_percent\":" << sample.humidity_percent
         << ",\"pressure_hpa\":" << sample.pressure_hpa << ",\"wifi_rssi_dbm\":"
         << sample.wifi_rssi_dbm << "}";
  return output.str();
}

std::string serialize_status(const std::string& device_id,
                             const std::optional<std::string>& boot_id,
                             const std::string& status, const std::string& reason,
                             const std::optional<std::string>& firmware_version) {
  if (!topics::valid_device_id(device_id)) return {};
  std::ostringstream output;
  output << "{\"schema_version\":1,\"device_id\":\"" << device_id
         << "\",\"status\":\"" << status << "\",\"reason\":\"" << reason << "\"";
  if (boot_id) output << ",\"boot_id\":\"" << *boot_id << "\"";
  if (firmware_version) output << ",\"firmware_version\":\"" << *firmware_version << "\"";
  output << "}";
  return output.str();
}

bool valid_interval(std::uint32_t seconds) {
  return seconds >= 1 && seconds <= 3600;
}

