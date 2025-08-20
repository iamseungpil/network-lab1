#!/usr/bin/env python3
"""
Test with working controller
"""

import time
import subprocess
import os
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def test_working():
    # Clean up
    subprocess.run(['sudo', 'mn', '-c'], capture_output=True)
    subprocess.run(['pkill', '-9', 'ryu-manager'], capture_output=True)
    
    print("\n=== Testing with Working Controller ===\n")
    
    # Start single controller for all switches
    print("[1] Starting controller...")
    controller_proc = subprocess.Popen([
        'bash', '-c',
        'source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && '
        'ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/working_controller.py'
    ])
    
    time.sleep(3)
    
    # Create simple network first
    print("[2] Creating simple test network...")
    net = Mininet(controller=None, switch=OVSSwitch)
    
    # Add controller
    c0 = net.addController('c0', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    
    # Add just 3 switches for simple test
    s1 = net.addSwitch('s1', protocols='OpenFlow13')
    s2 = net.addSwitch('s2', protocols='OpenFlow13')
    s3 = net.addSwitch('s3', protocols='OpenFlow13')
    
    # Add hosts
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')
    h4 = net.addHost('h4', ip='10.0.0.4/24')
    
    # Create topology
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s2)
    net.addLink(h4, s3)
    net.addLink(s1, s2)
    net.addLink(s2, s3)
    
    print("[3] Starting network...")
    net.start()
    
    time.sleep(2)
    
    print("\n=== REAL CONNECTIVITY TESTS ===")
    print("-" * 40)
    
    # Test 1: Same switch
    print("\nTest 1: h1 -> h2 (same switch)")
    result = h1.cmd('ping -c 2 -W 1 10.0.0.2')
    if '0% packet loss' in result:
        print("✓ SUCCESS: Same switch works!")
    else:
        print("✗ FAILED: Even same switch doesn't work")
        print(f"Output: {result[:200]}")
    
    # Test 2: Adjacent switches
    print("\nTest 2: h1 -> h3 (adjacent switches s1->s2)")
    result = h1.cmd('ping -c 2 -W 1 10.0.0.3')
    if '0% packet loss' in result:
        print("✓ SUCCESS: Adjacent switches work!")
    else:
        print("✗ FAILED: Adjacent switches don't work")
        print(f"Output: {result[:200]}")
    
    # Test 3: Two hops
    print("\nTest 3: h1 -> h4 (two hops s1->s2->s3)")
    result = h1.cmd('ping -c 2 -W 1 10.0.0.4')
    if '0% packet loss' in result:
        print("✓ SUCCESS: Multi-hop works!")
    else:
        print("✗ FAILED: Multi-hop doesn't work")
        print(f"Output: {result[:200]}")
    
    print("\n" + "=" * 40)
    print("Entering CLI - Test manually")
    print("=" * 40)
    
    CLI(net)
    net.stop()
    subprocess.run(['pkill', '-9', 'ryu-manager'], capture_output=True)

if __name__ == '__main__':
    setLogLevel('info')
    test_working()