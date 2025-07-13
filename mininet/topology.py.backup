#!/usr/bin/env python3
"""
로컬 실행용 Mininet 토폴로지
10개 스위치, 20개 호스트, 2개 컨트롤러
"""

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
        info('*** Building SDN topology\n')
        
        # 10개 스위치 생성 (s1-s10)
        switches = []
        for i in range(1, 11):
            switch = self.addSwitch(f's{i}', 
                                  dpid=f'{i:016x}',
                                  protocols='OpenFlow13')
            switches.append(switch)
            info(f'Added switch s{i}\n')
        
        # 각 스위치에 2개씩 호스트 연결 (총 20개 호스트)
        for i, switch in enumerate(switches, 1):
            host1 = self.addHost(f'h{i*2-1}', 
                               ip=f'10.0.0.{i*2-1}/24',
                               mac=f'00:00:00:00:00:{i*2-1:02x}')
            host2 = self.addHost(f'h{i*2}', 
                               ip=f'10.0.0.{i*2}/24',
                               mac=f'00:00:00:00:00:{i*2:02x}')
            
            self.addLink(host1, switch)
            self.addLink(host2, switch)
            info(f'Added hosts h{i*2-1}, h{i*2} to switch s{i}\n')
        
        # 스위치 간 연결 (트리 구조)
        # s1을 루트로 하는 트리 구조
        info('*** Adding switch-to-switch links\n')
        self.addLink(switches[0], switches[1])  # s1-s2
        self.addLink(switches[0], switches[2])  # s1-s3
        self.addLink(switches[1], switches[3])  # s2-s4
        self.addLink(switches[1], switches[4])  # s2-s5
        self.addLink(switches[2], switches[5])  # s3-s6
        self.addLink(switches[2], switches[6])  # s3-s7
        self.addLink(switches[3], switches[7])  # s4-s8
        self.addLink(switches[3], switches[8])  # s4-s9
        self.addLink(switches[4], switches[9])  # s5-s10
        
        info('Tree topology created successfully\n')


def run_topology():
    """토폴로지 실행"""
    info('*** Starting SDN Topology\n')
    
    # 컨트롤러 설정
    info('*** Setting up controllers\n')
    c1 = RemoteController('c1', ip='127.0.0.1', port=6700)  # Primary
    c2 = RemoteController('c2', ip='127.0.0.1', port=6800)  # Secondary
    
    info('Primary Controller: 127.0.0.1:6700 (s1-s5)\n')
    info('Secondary Controller: 127.0.0.1:6800 (s6-s10)\n')
    
    # 토폴로지 생성
    topo = SDNTopology()
    
    # 네트워크 생성
    net = Mininet(
        topo=topo,
        switch=OVSSwitch,
        link=TCLink,
        controller=None,  # 수동으로 컨트롤러 할당
        autoSetMacs=False,  # 자동 MAC 설정 비활성화 (컨트롤러가 학습하도록)
        autoStaticArp=False,
        build=False
    )
    
    # 컨트롤러 추가
    net.addController(c1)
    net.addController(c2)
    
    # 네트워크 빌드
    net.build()
    
    try:
        info('*** Starting network\n')
        net.start()
        
        info('*** Assigning switches to controllers\n')
        
        # Primary Controller: s1-s5
        primary_switches = []
        for i in range(1, 6):
            switch = net.get(f's{i}')
            primary_switches.append(switch)
            info(f's{i} will connect to Primary Controller (127.0.0.1:6700)\n')
        
        # Secondary Controller: s6-s10  
        secondary_switches = []
        for i in range(6, 11):
            switch = net.get(f's{i}')
            secondary_switches.append(switch)
            info(f's{i} will connect to Secondary Controller (127.0.0.1:6800)\n')
        
        # 스위치들을 각각의 컨트롤러에 연결
        for switch in primary_switches:
            switch.start([c1])
            info(f'Starting {switch.name} with Primary Controller\n')
            time.sleep(0.5)
            
        for switch in secondary_switches:
            switch.start([c2])
            info(f'Starting {switch.name} with Secondary Controller\n') 
            time.sleep(0.5)
        
        # 컨트롤러 연결 대기
        info('*** Waiting for controller connections...\n')
        time.sleep(5)  # 더 긴 대기 시간
        
        # 스위치 연결 상태 확인
        info('*** Verifying switch connections...\n')
        for switch in net.switches:
            if switch.connected():
                info(f'{switch.name}: Connected\n')
            else:
                info(f'{switch.name}: Not connected - Check controller!\n')
        
        # 네트워크 정보 출력
        info('*** Network Summary\n')
        info('Switches: 10 (s1-s10)\n')
        info('Hosts: 20 (h1-h20)\n')
        info('Controllers: 2 (Primary: s1-s5, Secondary: s6-s10)\n')
        
        info('*** Network topology:\n')
        for switch in net.switches:
            info(f'Switch {switch.name}: DPID {switch.dpid}\n')
        
        info('\n*** Testing basic connectivity\n')
        
        # 기본 연결성 테스트
        info('*** Testing ping between hosts\n')
        h1 = net.get('h1')
        h2 = net.get('h2')
        info(f'Ping from h1 to h2: ')
        result = net.ping([h1, h2])
        
        if result == 0:
            info('SUCCESS - Controllers are working!\n')
        else:
            info('Check controller connections\n')
        
        info('\n*** Available commands in CLI:\n')
        info('- pingall: Test connectivity between all hosts\n')
        info('- h1 ping h10: Test cross-controller communication\n')
        info('- dump: Show network information\n')
        info('- links: Show link information\n')
        info('- exit: Exit Mininet\n')
        
        info('*** Running CLI (type "exit" to quit)\n')
        CLI(net)
        
    except Exception as e:
        info(f'Error running network: {e}\n')
    finally:
        info('*** Stopping network\n')
        net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run_topology()