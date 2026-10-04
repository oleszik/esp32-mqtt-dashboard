#pragma once

#include <regex>
#include <string>

namespace topics {
inline bool valid_device_id(const std::string& value) {
  static const std::regex pattern("^[a-z0-9][a-z0-9_-]{0,63}$");
  return std::regex_match(value, pattern);
}

inline std::string base(const std::string& device_id) {
  return "iot/v1/devices/" + device_id + "/";
}
inline std::string telemetry(const std::string& device_id) { return base(device_id) + "telemetry"; }
inline std::string status(const std::string& device_id) { return base(device_id) + "status"; }
inline std::string config(const std::string& device_id) { return base(device_id) + "config"; }
inline std::string config_ack(const std::string& device_id) { return base(device_id) + "config/ack"; }
}  // namespace topics

