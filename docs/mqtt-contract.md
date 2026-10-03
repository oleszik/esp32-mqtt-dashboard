# MQTT contract v1

## Topics

| Topic | QoS | Retain | Producer |
|---|---:|---:|---|
| `iot/v1/devices/{device_id}/telemetry` | 1 | false | device |
| `iot/v1/devices/{device_id}/status` | 1 | true | device/broker LWT |
| `iot/v1/devices/{device_id}/config` | 1 | true | operator |
| `iot/v1/devices/{device_id}/config/ack` | 1 | true | device |

`device_id` must match `[a-z0-9][a-z0-9_-]{0,63}`. The parser requires the entire topic to match;
wildcards and additional path levels are invalid.

## Telemetry

| Field | Contract |
|---|---|
| `schema_version` | integer literal `1` |
| `device_id` | valid ID and identical to topic ID |
| `boot_id` | 1–64 alphanumeric, `_`, or `-` characters |
| `sequence` | integer 0 through 2^63−1, monotonic within a boot |
| `sampled_at` | UTC ISO 8601 timestamp or `null` |
| `uptime_seconds` | integer 0 through 2^32−1 |
| `temperature_c` | finite number −50 through 100 |
| `humidity_percent` | finite number 0 through 100 |
| `pressure_hpa` | finite number 300 through 1200 |
| `wifi_rssi_dbm` | integer −127 through 0 |

Extra fields, malformed JSON, `NaN`, `Infinity`, oversized payloads, and identity mismatches are
rejected. The backend assigns `received_at`; it does not use an LWT's device timestamp for receipt.

QoS 1 can redeliver. `(device_id, boot_id, sequence)` is the unique telemetry identity. Duplicate
delivery increments a diagnostic counter without inserting a second history row. This is
at-least-once transport with idempotent storage, not exactly-once delivery.

## Status and Last Will

Online status includes schema version, device ID, boot ID, `online`, `connected`, and firmware
version. Before connecting, the device registers this retained will:

```json
{"schema_version":1,"device_id":"esp32-demo-01","status":"offline","reason":"connection_lost"}
```

After every connection it publishes retained online state and re-subscribes to configuration.
Graceful shutdown uses reason `graceful_shutdown`. Retained online state and stale state are
separate concepts.

## Configuration

The retained configuration object contains only:

```json
{"schema_version":1,"telemetry_interval_seconds":10}
```

The interval must be an integer from 1 through 3600 seconds. A device publishes a retained
acknowledgement containing its ID, boot ID, interval, result (`applied` or `rejected`), and a
bounded reason. No arbitrary command execution is supported.

