#!/bin/bash

echo "=== Starting SDN Lab Environment ==="

# Docker Compose 실행
cd "$(dirname "$0")/../docker/compose"

echo "Building and starting containers..."
sudo docker compose up --build -d

echo "Waiting for services to start..."
sleep 10

echo "=== Service Status ==="
sudo docker compose ps

echo ""
echo "=== Access Information ==="
echo "Primary Controller REST API: http://localhost:8080"
echo "Secondary Controller REST API: http://localhost:8081"
echo "Mininet Monitor: http://localhost:8082"
echo ""
echo "To access CLI: docker exec -it sdn-cli python3 /app/cli/flow_cli.py interactive"
echo "To stop: ./stop-sdn.sh"