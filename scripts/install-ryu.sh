#!/bin/bash

echo "=== RYU 컨트롤러 설치 시작 ==="

# 필요한 패키지 설치
sudo apt update
sudo apt install -y python3 python3-pip python3-dev

# RYU 설치
pip3 install ryu

# 추가 의존성 설치
pip3 install eventlet netaddr oslo.config routes webob

echo "=== RYU 설치 완료 ==="
echo "테스트: ryu-manager --help"