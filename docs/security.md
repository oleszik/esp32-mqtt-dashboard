# Security

## Local development controls

- MQTT anonymous access is disabled.
- Password hashes are generated at broker startup and are not stored in Git.
- Device, backend, and test identities have separate ACL sections.
- The standard device can access only the `esp32-demo-01` namespace.
- MQTT and HTTP bind to host loopback unless the LAN override is explicitly selected.
- `.env`, firmware secrets, databases, logs, build output, and password files are ignored.
- MQTT payload size, topic grammar, identifiers, JSON fields, numeric values, and API query limits
  are validated.
- Database statements use bound parameters.
- Rejected messages store topic, reason, byte count, and receipt time—not hostile raw bodies.
- Containers run as non-root where their runtime supports it.

The committed passwords are examples only. Copy `.env.example` to `.env` and replace them.
Environment variables can still be inspected by a privileged local Docker user, so this is not
a production secret-management design.

## LAN use

`compose.lan.yaml` changes MQTT from loopback to all host interfaces so a physical ESP32 can
connect. Use it only on a trusted network, configure the host firewall, and return to the default
Compose file afterward.

## Production recommendations

A production deployment should add:

- TLS with broker certificate verification
- unique per-device credentials or mutual TLS certificates
- secure manufacturing/provisioning and credential rotation
- a managed secret store instead of environment-file secrets
- network segmentation and restrictive ingress controls
- brute-force protection, audit logs, alerting, and operational metrics
- signed firmware, secure boot/flash encryption where appropriate
- backup, retention, and privacy policies for telemetry
- dependency and container vulnerability scanning

Full PKI and fleet provisioning are intentionally outside this focused portfolio MVP.

