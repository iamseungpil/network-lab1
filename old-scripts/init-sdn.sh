#!/bin/bash

echo "=== Initializing SDN Lab Environment ==="

# OVS 데이터베이스 디렉토리 생성
mkdir -p /var/run/openvswitch /var/log/openvswitch /etc/openvswitch

# OVS 데이터베이스 초기화 (이미 있으면 스킵)
if [ ! -f /etc/openvswitch/conf.db ]; then
    echo "Creating OVS database..."
    ovsdb-tool create /etc/openvswitch/conf.db /usr/share/openvswitch/vswitch.ovsschema
fi

# OVS 데이터베이스 서버 시작
echo "Starting OVS database server..."
ovsdb-server --remote=punix:/var/run/openvswitch/db.sock \
    --remote=db:Open_vSwitch,Open_vSwitch,manager_options \
    --pidfile --detach --log-file

# OVS 초기화
echo "Initializing OVS..."
ovs-vsctl --no-wait init

# OVS vswitchd 시작
echo "Starting OVS vswitchd..."
ovs-vswitchd --pidfile --detach --log-file

# OVS 상태 확인
echo "Checking OVS status..."
ovs-vsctl show

# 로그 파일 생성
touch /var/log/sdn-lab.log

echo "OVS is ready!"
echo

# SDN 환경 시작
cd /network-lab
echo "Starting SDN environment..."
exec ./start_sdn.sh 2>&1 | tee -a /var/log/sdn-lab.log
