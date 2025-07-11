#!/bin/bash

echo "Starting SDN CLI Interface..."

# CLI 컨테이너를 계속 실행 상태로 유지
cd /app/cli

# 간단한 CLI 사용 가능 알림
echo "SDN CLI is ready!"
echo "Use: docker exec -it sdn-cli python3 /app/cli/simple_cli.py interactive"
echo "Or: docker exec -it sdn-cli python3 /app/cli/flow_cli.py interactive"

# 컨테이너를 계속 실행시키기 위해 무한 대기
tail -f /dev/null