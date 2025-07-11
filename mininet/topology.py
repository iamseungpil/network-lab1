#!/usr/bin/env python3

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
import time

class SDNTopology(Topo):
    """10개 스위치를 가진 SDN 토폴로지"""
    
    def build(self):
        # 10개 스위치 생성
        switches = []
        for i in range(1, 11):
            switch = self.addSwitch(f's{i}', dpid=f'000000000000000{i:x}')
            switches.append(switch)
        
        # 각 스위치에 2개씩 호스트 연결 (총 20개 호스트)
        for i, switch in enumerate(switches, 1):
            host1 = self.addHost(f'h{i*2-1}', ip=f'10.0.0.{i*2-1}/24')
            host2 = self.addHost(f'h{i*2}', ip=f'10.0.0.{i*2}/24')
            
            self.addLink(host1, switch)
            self.addLink(host2, switch)
        
        # 스위치 간 연결 (트리 구조)
        # s1을 루트로 하는 트리 구조
        # s1 - s2, s3
        # s2 - s4, s5
        # s3 - s6, s7
        # s4 - s8, s9
        # s5 - s10
        
        self.addLink(switches[0], switches[1])  # s1-s2
        self.addLink(switches[0], switches[2])  # s1-s3
        self.addLink(switches[1], switches[3])  # s2-s4
        self.addLink(switches[1], switches[4])  # s2-s5
        self.addLink(switches[2], switches[5])  # s3-s6
        self.addLink(switches[2], switches[6])  # s3-s7
        self.addLink(switches[3], switches[7])  # s4-s8
        self.addLink(switches[3], switches[8])  # s4-s9
        self.addLink(switches[4], switches[9])  # s5-s10

def run_topology():
    """토폴로지 실행"""
    topo = SDNTopology()
    
    # 컨트롤러 설정
    controllers = []
    try:
        # Primary Controller
        c1 = RemoteController('c1', ip='controller1', port=6633)
        controllers.append(c1)
        info("Primary Controller configured: controller1:6633\n")
        
        # Secondary Controller (백업)
        c2 = RemoteController('c2', ip='controller2', port=6633)
        controllers.append(c2)
        info("Secondary Controller configured: controller2:6633\n")
        
    except Exception as e:
        info(f"Controller configuration error: {e}\n")
        # 기본 컨트롤러 사용
        c1 = RemoteController('c1', ip='127.0.0.1', port=6633)
        controllers = [c1]
    
    # 네트워크 생성
    net = Mininet(
        topo=topo,
        controller=controllers,
        switch=OVSSwitch,
        link=TCLink,
        autoSetMacs=True,
        autoStaticArp=True
    )
    
    try:
        info("*** Starting network\n")
        net.start()
        
        # 네트워크 상태 확인
        info("*** Network topology:\n")
        for switch in net.switches:
            info(f"Switch {switch.name}: {switch.dpid}\n")
        
        info("*** Testing connectivity\n")
        net.pingAll()
        
        info("*** Running CLI\n")
        CLI(net)
        
    except Exception as e:
        info(f"Error running network: {e}\n")
    finally:
        info("*** Stopping network\n")
        net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run_topology()