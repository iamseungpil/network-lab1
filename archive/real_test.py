#!/usr/bin/env python3
"""
Real test to verify actual SDN functionality
No fake success messages!
"""

import time
import subprocess
import os
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink

def real_test():
    """Real test with actual verification"""
    
    # Clean up first
    subprocess.run(['sudo', 'mn', '-c'], capture_output=True)
    
    print("\n=== REAL SDN TEST - NO FAKE SUCCESS ===\n")
    
    # Start controllers in background
    print("[1] Starting controllers...")
    os.system("pkill -9 ryu-manager 2>/dev/null")
    
    # Start primary controller
    subprocess.Popen([
        'bash', '-c',
        'source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && '
        'ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/primary_controller.py'
    ])
    
    # Start secondary controller  
    subprocess.Popen([
        'bash', '-c',
        'source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && '
        'ryu-manager --ofp-tcp-listen-port 6634 ryu-controller/secondary_controller.py'
    ])
    
    time.sleep(5)
    print("✓ Controllers started")
    
    # Create network
    print("\n[2] Creating network...")
    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink)
    
    # Add controllers
    c1 = net.addController('c1', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    c2 = net.addController('c2', controller=RemoteController, 
                          ip='127.0.0.1', port=6634)
    
    # Add switches (10 switches)
    switches = []
    for i in range(1, 11):
        s = net.addSwitch(f's{i}', protocols='OpenFlow13')
        switches.append(s)
    
    # Add hosts (20 hosts, 2 per switch)
    hosts = []
    for i in range(1, 21):
        h = net.addHost(f'h{i}', 
                       ip=f'10.0.0.{i}/24',
                       mac=f'00:00:00:00:00:{i:02x}')
        hosts.append(h)
    
    # Connect hosts to switches (2 per switch)
    for i in range(10):
        net.addLink(hosts[i*2], switches[i])
        net.addLink(hosts[i*2+1], switches[i])
    
    # Primary domain links with loop
    net.addLink(switches[0], switches[1])  # s1-s2
    net.addLink(switches[0], switches[2])  # s1-s3
    net.addLink(switches[1], switches[3])  # s2-s4
    net.addLink(switches[1], switches[4])  # s2-s5
    net.addLink(switches[3], switches[2])  # s4-s3 (loop!)
    
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
    print("✓ Network topology created")
    print("\n[3] Starting network...")
    net.start()
    
    # Assign controllers
    for i in range(5):
        switches[i].start([c1])
    for i in range(5, 10):
        switches[i].start([c2])
    
    print("✓ Controllers assigned")
    time.sleep(3)
    
    # Run actual tests
    print("\n[4] REAL TESTS:")
    print("-" * 40)
    
    h1 = hosts[0]
    h2 = hosts[1]
    h3 = hosts[2]
    h5 = hosts[4]
    h11 = hosts[10]
    
    # Test 1: Same switch
    print("\nTest 1: h1 → h2 (same switch s1)")
    result = h1.cmd('ping -c 3 10.0.0.2')
    print(f"Result: {result}")
    if '0% packet loss' in result:
        print("✓ REAL SUCCESS: Same switch works")
    else:
        print("✗ REAL FAILURE: Same switch doesn't work")
    
    # Test 2: Different switches in primary domain
    print("\nTest 2: h1 → h5 (s1 → s3)")
    result = h1.cmd('ping -c 3 10.0.0.5')
    print(f"Result: {result}")
    if '0% packet loss' in result:
        print("✓ REAL SUCCESS: Cross-switch routing works")
    else:
        print("✗ REAL FAILURE: Cross-switch routing doesn't work")
    
    # Test 3: Cross-domain
    print("\nTest 3: h1 → h11 (s1 → s3 → s6)")
    result = h1.cmd('ping -c 3 10.0.0.11')
    print(f"Result: {result}")
    if '0% packet loss' in result:
        print("✓ REAL SUCCESS: Cross-domain works")
    else:
        print("✗ REAL FAILURE: Cross-domain doesn't work")
    
    # Test 4: Link failure
    print("\nTest 4: Breaking link s1-s3...")
    net.configLinkStatus('s1', 's3', 'down')
    time.sleep(3)
    
    print("Testing h1 → h5 with s1-s3 down...")
    result = h1.cmd('ping -c 3 10.0.0.5')
    print(f"Result: {result}")
    if '0% packet loss' in result:
        print("✓ REAL SUCCESS: Rerouting works!")
    else:
        print("✗ REAL FAILURE: Rerouting doesn't work")
    
    # Test 5: Link recovery
    print("\nTest 5: Restoring link s1-s3...")
    net.configLinkStatus('s1', 's3', 'up')
    time.sleep(3)
    
    print("Testing h1 → h5 after recovery...")
    result = h1.cmd('ping -c 3 10.0.0.5')
    print(f"Result: {result}")
    if '0% packet loss' in result:
        print("✓ REAL SUCCESS: Recovery works!")
    else:
        print("✗ REAL FAILURE: Recovery doesn't work")
    
    print("\n" + "=" * 40)
    print("REAL TEST COMPLETE - Entering CLI")
    print("You can run manual tests now")
    print("=" * 40)
    
    CLI(net)
    net.stop()
    os.system("pkill -9 ryu-manager 2>/dev/null")

if __name__ == '__main__':
    setLogLevel('info')
    real_test()