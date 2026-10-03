import argparse
import os

from .device import SimulatedDevice


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Deterministic MQTT telemetry simulator")
    result.add_argument("--host", default=os.getenv("MQTT_HOST", "localhost"))
    result.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    result.add_argument("--username", default=os.getenv("MQTT_USERNAME", "device"))
    result.add_argument("--password", default=os.getenv("MQTT_PASSWORD", "change-device-password"))
    result.add_argument("--device-id", default=os.getenv("DEVICE_ID", "esp32-demo-01"))
    result.add_argument("--interval", type=float, default=float(os.getenv("INTERVAL_SECONDS", "2")))
    result.add_argument("--seed", type=int, default=int(os.getenv("SIMULATOR_SEED", "42")))
    result.add_argument("--boot-id", default=os.getenv("BOOT_ID"))
    result.add_argument("--count", type=int, default=None)
    result.add_argument("--abrupt", action="store_true", help="close transport without DISCONNECT")
    return result


def main() -> None:
    args = parser().parse_args()
    if args.interval <= 0 or (args.count is not None and args.count < 1):
        raise SystemExit("interval and count must be positive")
    device = SimulatedDevice(
        args.host,
        args.port,
        args.username,
        args.password,
        args.device_id,
        args.interval,
        args.seed,
        args.boot_id,
    )
    device.run(args.count, args.abrupt)


if __name__ == "__main__":
    main()
