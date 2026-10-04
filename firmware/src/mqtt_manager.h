#pragma once

#include <Arduino.h>
#include <MQTT.h>
#include <WiFiClient.h>

#include <cstdint>
#include <string>

#include "backoff.h"

class MqttManager {
 public:
  MqttManager(std::string device_id, std::string boot_id);
  void begin();
  void update(std::uint32_t now_ms, bool wifi_connected);
  bool publish_telemetry(const std::string& payload);
  [[nodiscard]] bool connected();
  [[nodiscard]] std::uint32_t telemetry_interval_seconds() const;

 private:
  void connect();
  void publish_online();
  void handle_message(String& topic, String& payload);
  void publish_config_ack(bool applied, std::uint32_t interval, const char* reason);

  std::string device_id_;
  std::string boot_id_;
  WiFiClient network_;
  MQTTClient client_{1024};
  Backoff backoff_{1000, 30000};
  std::uint32_t next_attempt_ms_{0};
  std::uint32_t telemetry_interval_seconds_{10};
};

