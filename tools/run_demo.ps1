$ErrorActionPreference = 'Stop'
docker compose --profile demo up --build -d
Write-Host 'Dashboard: http://localhost:8000'
Write-Host 'Stop with: docker compose --profile demo down'

