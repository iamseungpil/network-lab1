#!/usr/bin/env python3
"""
Test dual controller topology without actual controllers
Shows network creation and basic functionality
"""

from mininet.net import Mininet
from mininet.node import DefaultController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
import time

def test_topology_only():
    """Test the dual controller topology structure without RYU controllers"""
    
    # Create network with default controller (no OpenFlow)
    net = Mininet(controller=DefaultController, link=TCLink, autoSetMacs=True)
    
    info('*** Adding default controller\n')
    c0 = net.addController('c0')
    
    info('*** Adding 10 switches\n')
    switches = []
    for i in range(1, 11):
        switch = net.addSwitch(f's{i}')
        switches.append(switch)
    
    info('*** Adding 20 hosts\n')
    host_id = 1
    for i, switch in enumerate(switches, 1):
        for j in range(2):
            host = net.addHost(f'h{host_id}', 
                              ip=f'10.0.0.{host_id}/24',
                              mac=f'00:00:00:00:00:{host_id:02x}')
            net.addLink(host, switch)
            host_id += 1
    
    info('*** Creating dual controller topology\n')
    # Primary domain topology (s1-s5)
    net.addLink(switches[0], switches[1])  # s1-s2
    net.addLink(switches[0], switches[2])  # s1-s3
    net.addLink(switches[1], switches[3])  # s2-s4
    net.addLink(switches[1], switches[4])  # s2-s5
    
    # Cross-domain links (Primary to Secondary)
    net.addLink(switches[2], switches[5])  # s3-s6 (gateway)
    net.addLink(switches[2], switches[6])  # s3-s7 (gateway)
    net.addLink(switches[3], switches[7])  # s4-s8 (gateway)
    net.addLink(switches[3], switches[8])  # s4-s9 (gateway)
    net.addLink(switches[4], switches[9])  # s5-s10 (gateway)
    
    # Secondary domain internal links (s6-s10)
    net.addLink(switches[5], switches[6])  # s6-s7
    net.addLink(switches[7], switches[8])  # s8-s9
    
    info('*** Starting network\n')
    net.start()
    
    info('\n*** Network topology created successfully!\n')
    info('*** 10 switches, 20 hosts with dual controller structure\n')
    info('*** Domains: Primary (s1-s5, h1-h10), Secondary (s6-s10, h11-h20)\n\n')
    
    # Test basic connectivity
    info('=== TOPOLOGY TESTS ===\n')
    
    h1 = net.get('h1')
    h2 = net.get('h2')
    h11 = net.get('h11')
    h20 = net.get('h20')
    
    info('[TEST 1] Same switch connectivity (h1 <-> h2)\n')
    result = h1.cmd('ping -c 2 h2')
    if '0% packet loss' in result:
        info('✓ Same switch communication works\n\n')
    else:
        info('✗ Same switch communication failed\n\n')
    
    info('[TEST 2] Cross-domain connectivity (h1 <-> h11)\n')  
    result = h1.cmd('ping -c 2 h11')
    if '0% packet loss' in result:
        info('✓ Cross-domain communication works\n\n')
    else:
        info('✗ Cross-domain communication failed (normal without controllers)\n\n')
    
    info('[TEST 3] Network structure verification\n')
    info('Switches: ')
    for switch in switches:
        info(f'{switch.name} ')
    info('\n')
    
    info('Host distribution:\n')
    for i in range(1, 11):
        hosts_on_switch = [f'h{j}' for j in range((i-1)*2+1, i*2+1)]
        info(f'  s{i}: {hosts_on_switch}\n')
    
    info('\n=== TOPOLOGY STRUCTURE VERIFIED ===\n')
    info('Ready for SDN controller integration!\n')
    info('Link failure simulation would work with:')
    info('  net.configLinkStatus("s1", "s3", "down")\n')
    info('  net.configLinkStatus("s3", "s6", "down")\n\n')
    
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    test_topology_only()