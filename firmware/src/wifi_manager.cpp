#include "wifi_manager.h"

#include <WiFi.h>

#include "secrets.h"

void WifiManager::begin() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(false);
}

void WifiManager::update(std::uint32_t now_ms) {
  const bool online = connected();
  if (online) {
    if (!was_connected_) {
      Serial.printf("wifi connected ip=%s rssi=%d\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
      backoff_.reset();
    }
    was_connected_ = true;
    return;
  }
  if (was_connected_) Serial.println("wifi disconnected");
  was_connected_ = false;
  if (static_cast<std::int32_t>(now_ms - next_attempt_ms_) >= 0) {
    Serial.println("wifi connection attempt");
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    next_attempt_ms_ = now_ms + backoff_.next_delay(esp_random() % 250);
  }
}

bool WifiManager::connected() const { return WiFi.status() == WL_CONNECTED; }

