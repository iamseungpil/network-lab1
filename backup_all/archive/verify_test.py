#!/usr/bin/env python3
"""
VERIFICATION TEST - Show REAL ping output, no fake success
"""

import time
import subprocess
import os
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

def verify_test():
    # Kill everything first
    os.system("sudo mn -c 2>/dev/null")
    os.system("pkill -9 ryu-manager 2>/dev/null")
    
    print("\n" + "="*60)
    print("  VERIFICATION TEST - RAW PING OUTPUT")
    print("  No interpretation, just raw results")
    print("="*60)
    
    # Start controllers
    print("\n[STEP 1] Starting controllers...")
    p1 = subprocess.Popen([
        'bash', '-c',
        'source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && '
        'ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/primary_fixed.py 2>&1'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    p2 = subprocess.Popen([
        'bash', '-c',
        'source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && '
        'ryu-manager --ofp-tcp-listen-port 6634 ryu-controller/secondary_fixed.py 2>&1'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    time.sleep(3)
    
    # Create network
    print("[STEP 2] Creating network...")
    net = Mininet(controller=None, switch=OVSSwitch, autoSetMacs=True)
    
    # Controllers
    c1 = net.addController('c1', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    c2 = net.addController('c2', controller=RemoteController, 
                          ip='127.0.0.1', port=6634)
    
    # Create simple test network
    # Primary domain: s1, s2, s3
    s1 = net.addSwitch('s1', protocols='OpenFlow13')
    s2 = net.addSwitch('s2', protocols='OpenFlow13')
    s3 = net.addSwitch('s3', protocols='OpenFlow13')
    
    # Secondary domain: s6, s7
    s6 = net.addSwitch('s6', protocols='OpenFlow13')
    s7 = net.addSwitch('s7', protocols='OpenFlow13')
    
    # Hosts
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')
    h6 = net.addHost('h6', ip='10.0.0.6/24')
    h7 = net.addHost('h7', ip='10.0.0.7/24')
    
    # Links
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s3)
    net.addLink(h6, s6)
    net.addLink(h7, s7)
    
    # Switch interconnections
    net.addLink(s1, s2)
    net.addLink(s2, s3)
    net.addLink(s1, s3)  # Direct link for testing
    net.addLink(s3, s6)  # Cross-domain
    net.addLink(s6, s7)  # Secondary internal
    
    print("[STEP 3] Starting network...")
    net.start()
    
    # Assign controllers
    s1.start([c1])
    s2.start([c1])
    s3.start([c1])
    s6.start([c2])
    s7.start([c2])
    
    print("[STEP 4] Waiting for network to stabilize...")
    time.sleep(3)
    
    print("\n" + "-"*60)
    print("RAW PING TESTS - EXACT OUTPUT")
    print("-"*60)
    
    # Test 1: Same switch
    print("\n>>> TEST 1: h1 ping -c 2 h2 (same switch)")
    print("Command: h1.cmd('ping -c 2 -W 1 10.0.0.2')")
    result = h1.cmd('ping -c 2 -W 1 10.0.0.2')
    print("RAW OUTPUT:")
    print(result)
    print(">>> Packet loss check: ", "0% packet loss" in result)
    
    # Test 2: Different switches  
    print("\n>>> TEST 2: h1 ping -c 2 h3 (different switches)")
    print("Command: h1.cmd('ping -c 2 -W 1 10.0.0.3')")
    result = h1.cmd('ping -c 2 -W 1 10.0.0.3')
    print("RAW OUTPUT:")
    print(result)
    print(">>> Packet loss check: ", "0% packet loss" in result)
    
    # Test 3: Cross-domain
    print("\n>>> TEST 3: h1 ping -c 2 h6 (cross-domain)")
    print("Command: h1.cmd('ping -c 2 -W 1 10.0.0.6')")
    result = h1.cmd('ping -c 2 -W 1 10.0.0.6')
    print("RAW OUTPUT:")
    print(result)
    print(">>> Packet loss check: ", "0% packet loss" in result)
    
    # Test 4: Secondary domain
    print("\n>>> TEST 4: h6 ping -c 2 h7 (secondary domain)")
    print("Command: h6.cmd('ping -c 2 -W 1 10.0.0.7')")
    result = h6.cmd('ping -c 2 -W 1 10.0.0.7')
    print("RAW OUTPUT:")
    print(result)
    print(">>> Packet loss check: ", "0% packet loss" in result)
    
    # Test 5: Link down
    print("\n>>> TEST 5: Breaking link s1-s3")
    print("Command: net.configLinkStatus('s1', 's3', 'down')")
    net.configLinkStatus('s1', 's3', 'down')
    time.sleep(2)
    
    print("\nAfter link down - h1 ping -c 2 h3")
    print("Command: h1.cmd('ping -c 2 -W 1 10.0.0.3')")
    result = h1.cmd('ping -c 2 -W 1 10.0.0.3')
    print("RAW OUTPUT:")
    print(result)
    print(">>> Packet loss check: ", "0% packet loss" in result)
    
    # Check flow table
    print("\n>>> FLOW TABLE CHECK on s1:")
    print("Command: s1.cmd('ovs-ofctl -O OpenFlow13 dump-flows s1')")
    flows = s1.cmd('ovs-ofctl -O OpenFlow13 dump-flows s1')
    print("RAW OUTPUT:")
    print(flows[:500])  # First 500 chars
    
    print("\n" + "="*60)
    print("  MANUAL VERIFICATION - Try yourself")
    print("  Commands to try:")
    print("  mininet> h1 ping -c 3 h2")
    print("  mininet> h1 ping -c 3 h3")
    print("  mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s1")
    print("="*60)
    
    CLI(net)
    
    # Cleanup
    net.stop()
    p1.kill()
    p2.kill()
    os.system("pkill -9 ryu-manager 2>/dev/null")

if __name__ == '__main__':
    setLogLevel('info')
    verify_test()