#include "mqtt_manager.h"

#include <ArduinoJson.h>

#include <cstdio>

#include "app_config.h"
#include "secrets.h"
#include "telemetry.h"
#include "topics.h"

MqttManager::MqttManager(std::string device_id, std::string boot_id)
    : device_id_(std::move(device_id)), boot_id_(std::move(boot_id)) {}

void MqttManager::begin() {
  client_.begin(app_config::kMqttHost, app_config::kMqttPort, network_);
  const std::string will = serialize_status(device_id_, std::nullopt, "offline",
                                            "connection_lost", std::nullopt);
  client_.setWill(topics::status(device_id_).c_str(), will.c_str(), true, 1);
  client_.onMessage([this](String& topic, String& payload) { handle_message(topic, payload); });
}

void MqttManager::update(std::uint32_t now_ms, bool wifi_connected) {
  client_.loop();
  if (!wifi_connected || client_.connected()) return;
  if (static_cast<std::int32_t>(now_ms - next_attempt_ms_) >= 0) {
    connect();
    if (!client_.connected()) next_attempt_ms_ = now_ms + backoff_.next_delay(esp_random() % 250);
  }
}

void MqttManager::connect() {
  Serial.printf("mqtt connection attempt host=%s\n", app_config::kMqttHost);
  if (client_.connect(device_id_.c_str(), MQTT_USERNAME, MQTT_PASSWORD)) {
    backoff_.reset();
    client_.subscribe(topics::config(device_id_).c_str(), 1);
    publish_online();
    Serial.println("mqtt connected");
  } else {
    Serial.printf("mqtt connection failed error=%d\n", client_.lastError());
  }
}

void MqttManager::publish_online() {
  const std::string payload = serialize_status(device_id_, boot_id_, "online", "connected",
                                               app_config::kFirmwareVersion);
  client_.publish(topics::status(device_id_).c_str(), payload.c_str(), true, 1);
}

bool MqttManager::publish_telemetry(const std::string& payload) {
  return connected() && payload.size() <= app_config::kMaxPayloadBytes &&
         client_.publish(topics::telemetry(device_id_).c_str(), payload.c_str(), false, 1);
}

void MqttManager::handle_message(String& topic, String& payload) {
  if (topic != topics::config(device_id_).c_str() || payload.length() > 256) return;
  JsonDocument document;
  const DeserializationError error = deserializeJson(document, payload);
  const bool exact_shape = document.size() == 2 && document["schema_version"].is<int>() &&
                           document["telemetry_interval_seconds"].is<unsigned long>();
  const unsigned long value = document["telemetry_interval_seconds"] | 0UL;
  if (!error && exact_shape && document["schema_version"] == 1 && valid_interval(value)) {
    telemetry_interval_seconds_ = value;
    publish_config_ack(true, value, "configuration applied");
  } else {
    publish_config_ack(false, telemetry_interval_seconds_, "invalid configuration");
  }
}

void MqttManager::publish_config_ack(bool applied, std::uint32_t interval, const char* reason) {
  char payload[320];
  std::snprintf(payload, sizeof(payload),
                "{\"schema_version\":1,\"device_id\":\"%s\",\"boot_id\":\"%s\","
                "\"telemetry_interval_seconds\":%lu,\"result\":\"%s\",\"reason\":\"%s\"}",
                device_id_.c_str(), boot_id_.c_str(), static_cast<unsigned long>(interval),
                applied ? "applied" : "rejected", reason);
  client_.publish(topics::config_ack(device_id_).c_str(), payload, true, 1);
}

bool MqttManager::connected() { return client_.connected(); }

std::uint32_t MqttManager::telemetry_interval_seconds() const {
  return telemetry_interval_seconds_;
}

