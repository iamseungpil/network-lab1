#!/usr/bin/env python
"""
Correct network startup with proper controller assignment
Based on search results for dual controller architecture
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
import sys
sys.path.append('mininet')
from dijkstra_graph_topo import DualControllerTopo

def start_network():
    """Start network with correct controller assignment"""
    
    info('*** Creating network\n')
    net = Mininet(topo=None, controller=None, switch=OVSSwitch, link=TCLink)
    
    # Add controllers
    info('*** Adding controllers\n')
    c1 = net.addController('c1', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    c2 = net.addController('c2', controller=RemoteController, 
                          ip='127.0.0.1', port=6634)
    
    # Create topology
    info('*** Creating topology\n')
    topo = DualControllerTopo()
    topo.build()
    
    # Add switches
    info('*** Adding switches\n')
    switches = []
    for i in range(1, 11):
        s = net.addSwitch(f's{i}', protocols='OpenFlow13')
        switches.append(s)
    
    # Add hosts
    info('*** Adding hosts\n')
    hosts = []
    for i in range(1, 21):
        h = net.addHost(f'h{i}', 
                       ip=f'10.0.0.{i}/24',
                       mac=f'00:00:00:00:00:{i:02x}')
        hosts.append(h)
    
    # Add links according to topology
    info('*** Creating links\n')
    # Host to switch connections (2 hosts per switch)
    for i in range(10):
        net.addLink(hosts[i*2], switches[i])
        net.addLink(hosts[i*2+1], switches[i])
    
    # Primary domain links
    net.addLink(switches[0], switches[1])  # s1-s2
    net.addLink(switches[0], switches[2])  # s1-s3
    net.addLink(switches[1], switches[3])  # s2-s4
    net.addLink(switches[1], switches[4])  # s2-s5
    net.addLink(switches[3], switches[2])  # s4-s3 (backup path - creates loop!)
    
    # Cross-domain links
    net.addLink(switches[2], switches[5])  # s3-s6
    net.addLink(switches[2], switches[6])  # s3-s7
    net.addLink(switches[3], switches[7])  # s4-s8
    net.addLink(switches[3], switches[8])  # s4-s9
    net.addLink(switches[4], switches[9])  # s5-s10
    
    # Secondary domain links
    net.addLink(switches[5], switches[6])  # s6-s7
    net.addLink(switches[7], switches[8])  # s8-s9
    
    # Start network
    info('*** Starting network\n')
    net.start()
    
    # CRITICAL: Assign switches to correct controllers
    info('*** Assigning controllers to switches\n')
    # Primary controller manages s1-s5
    for i in range(5):
        switches[i].start([c1])
        info(f's{i+1} -> Primary Controller (6633)\n')
    
    # Secondary controller manages s6-s10
    for i in range(5, 10):
        switches[i].start([c2])
        info(f's{i+1} -> Secondary Controller (6634)\n')
    
    info('*** Network ready!\n')
    info('*** 10 switches, 20 hosts\n')
    info('*** Primary: s1-s5, Secondary: s6-s10\n')
    info('*** Loop in topology: s1-s2-s4-s3-s1\n')
    
    # Run CLI
    CLI(net)
    
    # Clean up
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    start_network()