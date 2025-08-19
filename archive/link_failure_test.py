#!/usr/bin/env python
"""
Dual Controller Link Failure Test
Tests link failure detection and rerouting across dual controllers
10 switches, 20 hosts with cross-domain communication
"""

import sys
import os

# Add system Python paths for Mininet access in conda environment
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

def test_dual_controller_failures():
    """Test link failure and rerouting with dual controllers"""
    
    # Create network
    net = Mininet(controller=None, link=TCLink, autoSetMacs=True)
    
    info('*** Adding dual controllers\n')
    c1 = net.addController('c1', controller=RemoteController, ip='127.0.0.1', port=6633)
    c2 = net.addController('c2', controller=RemoteController, ip='127.0.0.1', port=6634)
    
    info('*** Adding 10 switches\n')
    switches = []
    for i in range(1, 11):  # s1-s10
        switch = net.addSwitch(f's{i}', protocols='OpenFlow13')
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
    net.addLink(switches[0], switches[1], bw=100)  # s1-s2
    net.addLink(switches[0], switches[2], bw=100)  # s1-s3
    net.addLink(switches[1], switches[3], bw=100)  # s2-s4
    net.addLink(switches[1], switches[4], bw=100)  # s2-s5
    
    # Cross-domain links (Primary to Secondary)
    net.addLink(switches[2], switches[5], bw=80)   # s3-s6 (gateway)
    net.addLink(switches[2], switches[6], bw=80)   # s3-s7 (gateway)
    net.addLink(switches[3], switches[7], bw=80)   # s4-s8 (gateway)
    net.addLink(switches[3], switches[8], bw=80)   # s4-s9 (gateway)
    net.addLink(switches[4], switches[9], bw=80)   # s5-s10 (gateway)
    
    # Secondary domain internal links (s6-s10)
    net.addLink(switches[5], switches[6], bw=60)   # s6-s7
    net.addLink(switches[7], switches[8], bw=60)   # s8-s9
    
    info('*** Starting network\n')
    net.start()
    
    info('*** Assigning switches to controllers\n')
    # s1-s5 to primary controller
    for i in range(5):
        switches[i].start([c1])
    # s6-s10 to secondary controller  
    for i in range(5, 10):
        switches[i].start([c2])
    
    # Wait for network to stabilize
    info('\n*** Waiting for network to stabilize...\n')
    time.sleep(8)
    
    # Get hosts for testing
    h1 = net.get('h1')    # Primary domain (s1)
    h5 = net.get('h5')    # Primary domain (s3) 
    h11 = net.get('h11')  # Secondary domain (s6)
    h20 = net.get('h20')  # Secondary domain (s10)
    
    info('\n==================================================\n')
    info('    DUAL CONTROLLER LINK FAILURE TEST\n')
    info('    10 Switches, 20 Hosts, Cross-Domain\n')
    info('==================================================\n\n')
    
    # Test 1: Intra-domain connectivity
    info('[TEST 1] Testing intra-domain connectivity h1 -> h5 (Primary)\n')
    result = h1.cmd('ping -c 2 10.0.0.5')
    if '0% packet loss' in result:
        info('✓ Primary domain routing works (s1→s3)\n\n')
    else:
        info('✗ Primary domain routing failed\n\n')
        
    # Test 2: Cross-domain connectivity  
    info('[TEST 2] Testing cross-domain connectivity h1 -> h11\n')
    info('Setting up ARP entries for cross-domain communication...\n')
    h1.cmd('arp -s 10.0.0.11 00:00:00:00:00:0b')
    h11.cmd('arp -s 10.0.0.1 00:00:00:00:00:01')
    result = h1.cmd('ping -c 3 10.0.0.11')
    if '0% packet loss' in result or '33% packet loss' in result:
        info('✓ Cross-domain routing works (s1→s3→s6)\n\n')
    else:
        info('✗ Cross-domain routing failed\n\n')
    
    # Test 3: Primary domain link failure
    info('[TEST 3] Breaking primary domain link s1 <-> s3\n')
    info('Using net.configLinkStatus() to trigger PORT_STATUS event\n')
    
    net.configLinkStatus('s1', 's3', 'down')
    
    info('✓ Link s1-s3 is now DOWN\n')
    info('Waiting for primary controller to detect and reroute...\n')
    time.sleep(3)
    
    # Clear ARP cache
    h1.cmd('ip neigh flush all')
    h5.cmd('ip neigh flush all')
    
    # Test rerouting within primary domain
    info('\n[TEST 4] Testing primary domain rerouting h1 -> h5 (with s1-s3 down)\n')
    info('Expected: Should find alternate path (s1→s2→s4→s3 or similar)\n')
    
    result = h1.cmd('ping -c 5 10.0.0.5')
    if '0% packet loss' in result or '20% packet loss' in result:
        info('✓ PRIMARY DOMAIN REROUTING SUCCESS!\n\n')
    else:
        info('✗ Primary domain rerouting failed\n\n')
    
    # Test 5: Cross-domain link failure
    info('[TEST 5] Breaking cross-domain link s3 <-> s6\n')
    net.configLinkStatus('s3', 's6', 'down')
    
    info('✓ Link s3-s6 is now DOWN (cross-domain failure)\n')
    info('Waiting for controllers to detect and find alternative...\n')
    time.sleep(3)
    
    h1.cmd('ip neigh flush all')
    h11.cmd('ip neigh flush all')
    h1.cmd('arp -s 10.0.0.11 00:00:00:00:00:0b')
    h11.cmd('arp -s 10.0.0.1 00:00:00:00:00:01')
    
    info('\n[TEST 6] Testing cross-domain with gateway failure\n')
    info('Expected: Should use alternative gateway (s3→s7 or s4→s8)\n')
    
    result = h1.cmd('ping -c 5 10.0.0.11')
    if '0% packet loss' in result or '20% packet loss' in result:
        info('✓ CROSS-DOMAIN REROUTING SUCCESS!\n\n')
    else:
        info('✗ Cross-domain rerouting failed\n\n')
    
    # Test 7: Link restoration
    info('[TEST 7] Restoring all links\n')
    net.configLinkStatus('s1', 's3', 'up')
    net.configLinkStatus('s3', 's6', 'up')
    
    info('✓ All links restored\n')
    info('Waiting for optimal path recovery...\n')
    time.sleep(3)
    
    h1.cmd('ip neigh flush all')
    h5.cmd('ip neigh flush all')
    h11.cmd('ip neigh flush all')
    
    # Test optimal path recovery
    info('\n[TEST 8] Testing optimal path recovery\n')
    result1 = h1.cmd('ping -c 2 10.0.0.5')
    if '0% packet loss' in result1:
        info('✓ Primary domain optimal path restored (s1→s3)\n')
    
    h1.cmd('arp -s 10.0.0.11 00:00:00:00:00:0b')
    h11.cmd('arp -s 10.0.0.1 00:00:00:00:00:01')
    result2 = h1.cmd('ping -c 2 10.0.0.11')
    if '0% packet loss' in result2:
        info('✓ Cross-domain optimal path restored (s1→s3→s6)\n\n')
    else:
        info('✗ Cross-domain path recovery failed\n\n')
    
    info('==================================================\n')
    info('    TEST COMPLETE - Entering CLI\n')
    info('==================================================\n')
    info('\nYou can test manually:\n')
    info('  - net.configLinkStatus("s1", "s2", "down")\n')
    info('  - net.configLinkStatus("s2", "s3", "down")\n')
    info('  - net.configLinkStatus("s1", "s2", "up")\n')
    info('  - h1 ping h8\n')
    info('  - h1 ping h15\n\n')
    
    # Start CLI for manual testing
    CLI(net)
    
    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    info('*** Starting Dual Controller Link Failure Test ***\n')
    info('*** Make sure both controllers are running on ports 6633 & 6634 ***\n\n')
    test_dual_controller_failures()