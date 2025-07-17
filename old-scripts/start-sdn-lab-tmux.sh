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

# tmux 세션에서 start_sdn.sh 실행
cd /network-lab
echo "Starting SDN environment in tmux session..."

# 기존 sdn-lab 세션이 있으면 종료
tmux kill-session -t sdn-lab 2>/dev/null || true

# 새 tmux 세션에서 start_sdn.sh를 직접 실행
tmux new-session -d -s sdn-lab ./start_sdn.sh

echo "SDN Lab started in tmux session 'sdn-lab'"

# 서비스가 계속 실행되도록 유지
while tmux has-session -t sdn-lab 2>/dev/null; do
    sleep 30
done
