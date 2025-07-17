#!/bin/bash
set -e

echo "=== Starting SDN Lab Environment ==="

# OVS 초기화
if [ ! -f /etc/openvswitch/conf.db ]; then
    echo "Creating OVS database..."
    ovsdb-tool create /etc/openvswitch/conf.db /usr/share/openvswitch/vswitch.ovsschema
fi

# OVS 데이터베이스 서버가 실행 중인지 확인
if ! pgrep -f ovsdb-server > /dev/null; then
    echo "Starting OVS database server..."
    ovsdb-server --remote=punix:/var/run/openvswitch/db.sock \
        --remote=db:Open_vSwitch,Open_vSwitch,manager_options \
        --pidfile --detach --log-file
fi

# OVS vswitchd가 실행 중인지 확인
if ! pgrep -f ovs-vswitchd > /dev/null; then
    echo "Starting OVS vswitchd..."
    ovs-vswitchd --pidfile --detach --log-file
    sleep 2
fi

# OVS 상태 확인
echo "Checking OVS status..."
ovs-vsctl show

# 로그 디렉토리 생성
mkdir -p /var/log
touch /var/log/sdn-lab.log

# screen 세션에서 start_sdn.sh 실행
cd /network-lab
echo "Starting SDN environment in screen session..."

# 기존 sdn-lab 세션이 있으면 종료
screen -S sdn-lab -X quit 2>/dev/null || true

# 새 screen 세션에서 start_sdn.sh를 직접 실행 (tee 제거)
screen -dmS sdn-lab ./start_sdn.sh

echo "SDN Lab started in screen session 'sdn-lab'"

# 서비스가 계속 실행되도록 유지
while screen -list | grep -q sdn-lab; do
    sleep 30
done
