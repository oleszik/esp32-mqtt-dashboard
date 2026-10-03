# Architecture

The repository contains one embedded publisher, one behaviorally equivalent software publisher,
an MQTT broker, and one backend process. The backend deliberately combines ingestion, REST, SSE,
and static asset hosting to keep the MVP operationally small.

## Data path

1. ESP32 or simulator creates a schema-v1 telemetry sample.
2. It publishes to Mosquitto with QoS 1 and no retain flag.
3. Paho's callback copies the topic and payload into a bounded queue.
4. A worker validates the exact topic, payload size, JSON, schema, ranges, and identity.
5. SQLite inserts the `(device_id, boot_id, sequence)` identity or counts a duplicate.
6. The worker schedules an event onto FastAPI's asyncio loop.
7. REST exposes current/history state; SSE fans live events to browsers.
8. The dashboard refreshes device projections and redraws its history chart.

The callback never performs SQLite or application validation work. A bounded queue prevents
unbounded memory growth during a downstream slowdown.

## Device state

`devices` is a materialized current-state table. Status messages control `online`/`offline`.
Telemetry controls last-seen, latest values, sequence, and message counters. `stale` is calculated
when the API response is created using the last telemetry receipt, independent of retained status.

## Reliability boundaries

- ESP32 Wi-Fi and MQTT retry independently with bounded exponential backoff and jitter.
- Paho reconnects with a 1–30 second delay and resubscribes after every connection.
- QoS 1 duplicates are expected and harmless.
- Mosquitto and SQLite use named volumes.
- Invalid input is reduced to safe metadata and never crashes the worker.
- SSE subscriber queues are bounded and drop the oldest live notification when a browser is slow;
  canonical data remains in SQLite and can be refreshed through REST.

