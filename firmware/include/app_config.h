#pragma once

#include <cstddef>
#include <cstdint>

namespace app_config {
inline constexpr char kFirmwareVersion[] = "1.0.0";
inline constexpr char kDeviceId[] = "esp32-demo-01";
inline constexpr char kMqttHost[] = "192.168.1.100";  // Replace with Docker host LAN address.
inline constexpr std::uint16_t kMqttPort = 1883;
inline constexpr std::uint32_t kDefaultTelemetryIntervalSeconds = 10;
inline constexpr std::uint32_t kMinTelemetryIntervalSeconds = 1;
inline constexpr std::uint32_t kMaxTelemetryIntervalSeconds = 3600;
inline constexpr std::size_t kMaxPayloadBytes = 1024;
}  // namespace app_config

