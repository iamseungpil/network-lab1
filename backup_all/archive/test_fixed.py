#!/usr/bin/env python3
"""
Test with fixed controllers
"""

import time
import subprocess
import os
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def test_fixed():
    # Clean up
    subprocess.run(['sudo', 'mn', '-c'], capture_output=True)
    subprocess.run(['pkill', '-9', 'ryu-manager'], capture_output=True)
    
    print("\n=== Testing with FIXED Controllers ===\n")
    
    # Start controllers
    print("[1] Starting fixed controllers...")
    p1 = subprocess.Popen([
        'bash', '-c',
        'source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && '
        'ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/primary_fixed.py'
    ])
    
    p2 = subprocess.Popen([
        'bash', '-c',
        'source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && '
        'ryu-manager --ofp-tcp-listen-port 6634 ryu-controller/secondary_fixed.py'
    ])
    
    time.sleep(3)
    
    print("[2] Creating full network...")
    net = Mininet(controller=None, switch=OVSSwitch)
    
    # Add controllers
    c1 = net.addController('c1', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    c2 = net.addController('c2', controller=RemoteController, 
                          ip='127.0.0.1', port=6634)
    
    # Add all 10 switches
    switches = []
    for i in range(1, 11):
        s = net.addSwitch(f's{i}', protocols='OpenFlow13')
        switches.append(s)
    
    # Add hosts (simplified - 1 per switch for testing)
    hosts = []
    for i in range(1, 11):
        h = net.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
        hosts.append(h)
        net.addLink(h, switches[i-1])
    
    # Primary domain links
    net.addLink(switches[0], switches[1])  # s1-s2
    net.addLink(switches[0], switches[2])  # s1-s3
    net.addLink(switches[1], switches[3])  # s2-s4
    net.addLink(switches[1], switches[4])  # s2-s5
    net.addLink(switches[3], switches[2])  # s4-s3 (loop)
    
    # Cross-domain links
    net.addLink(switches[2], switches[5])  # s3-s6
    net.addLink(switches[2], switches[6])  # s3-s7
    net.addLink(switches[3], switches[7])  # s4-s8
    net.addLink(switches[3], switches[8])  # s4-s9
    net.addLink(switches[4], switches[9])  # s5-s10
    
    # Secondary domain links
    net.addLink(switches[5], switches[6])  # s6-s7
    net.addLink(switches[7], switches[8])  # s8-s9
    
    print("[3] Starting network...")
    net.start()
    
    # Assign controllers
    for i in range(5):
        switches[i].start([c1])
    for i in range(5, 10):
        switches[i].start([c2])
    
    time.sleep(3)
    
    print("\n=== CONNECTIVITY TESTS ===")
    print("-" * 40)
    
    # Test within primary domain
    print("\nTest 1: h1 -> h2 (Primary domain)")
    result = hosts[0].cmd('ping -c 2 -W 2 10.0.0.2')
    if '0% packet loss' in result:
        print("✓ SUCCESS: Primary domain works!")
    else:
        print("✗ FAILED: Primary domain doesn't work")
    
    # Test within secondary domain
    print("\nTest 2: h6 -> h7 (Secondary domain)")
    result = hosts[5].cmd('ping -c 2 -W 2 10.0.0.7')
    if '0% packet loss' in result:
        print("✓ SUCCESS: Secondary domain works!")
    else:
        print("✗ FAILED: Secondary domain doesn't work")
    
    # Test cross-domain
    print("\nTest 3: h1 -> h6 (Cross-domain)")
    result = hosts[0].cmd('ping -c 2 -W 2 10.0.0.6')
    if '0% packet loss' in result:
        print("✓ SUCCESS: Cross-domain works!")
    else:
        print("✗ FAILED: Cross-domain doesn't work (expected - needs gateway config)")
    
    # Test link failure
    print("\nTest 4: Link failure s1-s3...")
    net.configLinkStatus('s1', 's3', 'down')
    time.sleep(2)
    
    print("Testing h1 -> h3 with s1-s3 down...")
    result = hosts[0].cmd('ping -c 2 -W 2 10.0.0.3')
    if '0% packet loss' in result:
        print("✓ SUCCESS: Rerouting works!")
    else:
        print("✗ PARTIAL: Rerouting needs more work")
    
    print("\n" + "=" * 40)
    print("Entering CLI - Test manually")
    print("Try: h1 ping h2, h1 ping h3, etc.")
    print("=" * 40)
    
    CLI(net)
    net.stop()
    subprocess.run(['pkill', '-9', 'ryu-manager'], capture_output=True)

if __name__ == '__main__':
    setLogLevel('info')
    test_fixed()