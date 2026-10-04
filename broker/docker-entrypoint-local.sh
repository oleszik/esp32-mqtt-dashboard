#!/bin/sh
set -eu

: "${MQTT_DEVICE_USERNAME:?MQTT_DEVICE_USERNAME is required}"
: "${MQTT_DEVICE_PASSWORD:?MQTT_DEVICE_PASSWORD is required}"
: "${MQTT_BACKEND_USERNAME:?MQTT_BACKEND_USERNAME is required}"
: "${MQTT_BACKEND_PASSWORD:?MQTT_BACKEND_PASSWORD is required}"
: "${MQTT_TEST_USERNAME:?MQTT_TEST_USERNAME is required}"
: "${MQTT_TEST_PASSWORD:?MQTT_TEST_PASSWORD is required}"

password_file=/mosquitto/runtime/passwords
chown -R mosquitto:mosquitto /mosquitto/runtime /mosquitto/data
rm -f "$password_file"
mosquitto_passwd -b -c "$password_file" "$MQTT_DEVICE_USERNAME" "$MQTT_DEVICE_PASSWORD"
mosquitto_passwd -b "$password_file" "$MQTT_BACKEND_USERNAME" "$MQTT_BACKEND_PASSWORD"
mosquitto_passwd -b "$password_file" "$MQTT_TEST_USERNAME" "$MQTT_TEST_PASSWORD"
chown mosquitto:mosquitto "$password_file"
chmod 600 "$password_file"

exec su-exec mosquitto "$@"

