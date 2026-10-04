#!/usr/bin/env sh
set -eu
docker compose --profile demo up --build -d
echo "Dashboard: http://localhost:8000"
echo "Stop with: docker compose --profile demo down"

