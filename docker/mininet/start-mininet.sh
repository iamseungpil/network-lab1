#!/bin/bash

echo "Starting Mininet Network..."

# OVS 서비스 시작
service openvswitch-switch start
sleep 2

# 컨트롤러 연결 대기
echo "Waiting for controllers..."
sleep 10

# 토폴로지 실행
cd /app/topology
echo "Starting network topology..."
python3 topology.py &

# 컨테이너 유지
tail -f /dev/null