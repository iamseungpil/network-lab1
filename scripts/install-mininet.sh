#!/bin/bash

echo "=== Mininet 설치 시작 ==="

# 필요한 패키지 설치
sudo apt update
sudo apt install -y python3 python3-pip git

# Mininet 설치
sudo apt install -y mininet

# 추가 도구 설치
sudo apt install -y openvswitch-switch openvswitch-testcontroller

# Python 의존성 설치
pip3 install eventlet

echo "=== Mininet 설치 완료 ==="
echo "테스트: sudo mn --test pingall"