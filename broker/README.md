# Local Mosquitto broker

The broker image generates its password file at container startup from Compose
environment variables. The generated file lives only inside the container and is
never committed. Copy `.env.example` to `.env` and replace all demo passwords.

The checked-in ACL confines the standard `device` user to `esp32-demo-01`, gives
the backend read-only ingestion access, and provides a separate `tester` identity
for local integration tests. Add a dedicated username and ACL section for each
additional physical device.

This is local-development security. Use TLS, per-device credentials, certificate
provisioning, rotation, and network isolation in production.

