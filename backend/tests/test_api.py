import json


def test_health(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"


def test_device_api(client, app, telemetry: dict) -> None:
    topic = "iot/v1/devices/esp32-demo-01/telemetry"
    app.state.processor.process(topic, json.dumps(telemetry).encode())
    devices = client.get("/api/devices").json()
    assert len(devices) == 1
    assert devices[0]["device_id"] == "esp32-demo-01"
    assert client.get("/api/devices/esp32-demo-01").status_code == 200
    assert len(client.get("/api/devices/esp32-demo-01/telemetry?limit=1").json()) == 1


def test_api_errors_and_limits(client) -> None:
    assert client.get("/api/devices/missing").status_code == 404
    assert client.get("/api/devices/BAD").status_code == 422
    assert client.get("/api/events?limit=0").status_code == 422
    assert client.get("/api/devices/demo/telemetry?limit=1001").status_code == 422


def test_dashboard_is_served(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "ESP32 MQTT Monitor" in response.text
