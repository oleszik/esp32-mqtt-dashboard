$ErrorActionPreference = 'Stop'
$testUser = if ($env:MQTT_TEST_USERNAME) { $env:MQTT_TEST_USERNAME } else { 'tester' }
$testPassword = if ($env:MQTT_TEST_PASSWORD) { $env:MQTT_TEST_PASSWORD } else { 'change-test-password' }
$output = docker compose exec -T broker mosquitto_sub `
  -h 127.0.0.1 -u $testUser -P $testPassword `
  -t 'iot/v1/devices/+/telemetry' -q 1 -C 3 -v -W 30
$output | Set-Content -Encoding utf8 docs/example-mqtt-session.txt
Write-Host 'Captured docs/example-mqtt-session.txt from the live broker.'

