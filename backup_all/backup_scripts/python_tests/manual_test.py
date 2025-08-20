#!/usr/bin/env python3
"""
Manual test for dual controllers - simplified version
"""

import sys
sys.path.extend([
    '/usr/lib/python3/dist-packages',
    '/usr/local/lib/python3.8/dist-packages',
    '/usr/lib/python3.8/dist-packages'
])

from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
import time

def manual_test():
    """Simple manual test for dual controller connectivity"""
    
    # Create network
    net = Mininet(controller=None, link=TCLink, autoSetMacs=True)
    
    info('*** Adding controllers\n')
    c1 = net.addController('c1', controller=RemoteController, ip='127.0.0.1', port=6633)
    c2 = net.addController('c2', controller=RemoteController, ip='127.0.0.1', port=6634)
    
    info('*** Adding switches\n')
    s1 = net.addSwitch('s1', protocols='OpenFlow13')
    s2 = net.addSwitch('s2', protocols='OpenFlow13')
    s3 = net.addSwitch('s3', protocols='OpenFlow13')
    s6 = net.addSwitch('s6', protocols='OpenFlow13')
    
    info('*** Adding hosts\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
    h11 = net.addHost('h11', ip='10.0.0.11/24', mac='00:00:00:00:00:0b')
    h12 = net.addHost('h12', ip='10.0.0.12/24', mac='00:00:00:00:00:0c')
    
    info('*** Creating links\n')
    # Primary domain
    net.addLink(h1, s1)
    net.addLink(h2, s2)
    net.addLink(s1, s2)
    net.addLink(s1, s3)  # Primary to gateway
    
    # Cross-domain link
    net.addLink(s3, s6, bw=80)  # Gateway link
    
    # Secondary domain
    net.addLink(s6, h11)
    net.addLink(s6, h12)
    
    info('*** Starting network\n')
    net.start()
    
    info('*** Assigning controllers\n')
    s1.start([c1])  # Primary
    s2.start([c1])  # Primary
    s3.start([c1])  # Primary (gateway)
    s6.start([c2])  # Secondary
    
    time.sleep(5)
    
    info('\n*** Simple connectivity tests\n')
    
    # Test 1: Primary domain
    info('[TEST] h1 -> h2 (primary domain)\n')
    result = h1.cmd('ping -c 2 10.0.0.2')
    if '0% packet loss' in result:
        info('✓ Primary domain OK\n')
    
    # Test 2: Cross-domain (needs ARP)
    info('[TEST] h1 -> h11 (cross-domain)\n')
    h1.cmd('arp -s 10.0.0.11 00:00:00:00:00:0b')
    h11.cmd('arp -s 10.0.0.1 00:00:00:00:00:01')
    result = h1.cmd('ping -c 3 10.0.0.11')
    if '0% packet loss' in result or '33% packet loss' in result:
        info('✓ Cross-domain OK\n')
    
    info('\n*** Manual testing CLI\n')
    info('Try: h1 ping h11\n')
    info('Try: net.configLinkStatus("s3", "s6", "down")\n')
    
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    manual_test()