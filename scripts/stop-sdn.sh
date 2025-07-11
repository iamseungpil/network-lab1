#!/bin/bash

echo "=== Stopping SDN Lab Environment ==="

cd "$(dirname "$0")/../docker/compose"

echo "Stopping containers..."
sudo docker compose down

echo "Cleaning up..."
sudo docker system prune -f

echo "SDN Lab stopped."