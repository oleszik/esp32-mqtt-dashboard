#include <Arduino.h>
#include <WiFi.h>
#include <time.h>

#include <cstdio>
#include <string>

#include "app_config.h"
#include "mqtt_manager.h"
#include "simulated_telemetry.h"
#include "telemetry.h"
#include "topics.h"
#include "wifi_manager.h"

namespace {
std::string make_boot_id() {
  char value[9];
  std::snprintf(value, sizeof(value), "%08lx", static_cast<unsigned long>(esp_random()));
  return value;
}

std::string timestamp_if_synchronized() {
  const time_t now = time(nullptr);
  if (now < 1700000000) return {};
  struct tm utc {};
  gmtime_r(&now, &utc);
  char timestamp[24];
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &utc);
  return timestamp;
}

WifiManager wifi;
std::string boot_id;
MqttManager* mqtt = nullptr;
SimulatedTelemetrySource* telemetry_source = nullptr;
std::uint64_t sequence = 0;
std::uint32_t last_publish_ms = 0;
}  // namespace

void setup() {
  Serial.begin(115200);
  if (!topics::valid_device_id(app_config::kDeviceId)) {
    Serial.println("fatal: invalid device ID");
    return;
  }
  boot_id = make_boot_id();
  static MqttManager mqtt_instance(app_config::kDeviceId, boot_id);
  static SimulatedTelemetrySource source(app_config::kDeviceId, boot_id);
  mqtt = &mqtt_instance;
  telemetry_source = &source;
  wifi.begin();
  mqtt->begin();
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  Serial.printf("firmware started device=%s boot=%s source=simulated\n",
                app_config::kDeviceId, boot_id.c_str());
}

void loop() {
  if (!mqtt || !telemetry_source) return;
  const std::uint32_t now_ms = millis();
  wifi.update(now_ms);
  mqtt->update(now_ms, wifi.connected());
  const std::uint32_t interval_ms = mqtt->telemetry_interval_seconds() * 1000U;
  if (mqtt->connected() && now_ms - last_publish_ms >= interval_ms) {
    const auto sample = telemetry_source->sample(sequence, now_ms / 1000U, WiFi.RSSI(),
                                                  timestamp_if_synchronized());
    const auto payload = serialize_telemetry(sample);
    if (mqtt->publish_telemetry(payload)) {
      Serial.printf("telemetry published sequence=%llu\n",
                    static_cast<unsigned long long>(sequence));
      ++sequence;
      last_publish_ms = now_ms;
    }
  }
  delay(5);
}

