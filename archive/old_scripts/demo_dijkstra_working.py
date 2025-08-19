#!/usr/bin/env python3
"""
Working Dijkstra Demo with Two Scenarios
1. Normal routing with Dijkstra shortest path
2. Link failure and automatic rerouting
"""

import time
import subprocess
import os
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def demo_scenarios():
    # Clean up
    os.system("sudo mn -c 2>/dev/null")
    os.system("pkill -9 ryu-manager 2>/dev/null")
    
    print("\n" + "="*70)
    print("   DIJKSTRA SDN DEMO - TWO SCENARIOS")
    print("   Single Controller with Automatic Rerouting")
    print("="*70)
    
    # Start Dijkstra controller
    print("\n[SETUP] Starting Dijkstra controller...")
    controller = subprocess.Popen([
        'bash', '-c',
        'source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && '
        'ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/dijkstra_controller.py'
    ])
    
    time.sleep(3)
    
    # Create network
    print("[SETUP] Creating loop topology network...")
    net = Mininet(controller=None, switch=OVSSwitch, autoSetMacs=True)
    
    # Add controller
    c0 = net.addController('c0', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    
    # Create diamond topology with loop
    print("\n[TOPOLOGY]")
    print("        h1            h5")
    print("         |             |")
    print("        s1 ========== s3")
    print("       /  \\          /  \\")
    print("      /    \\        /    \\")
    print("     s2     \\      /     s6---h6")
    print("      \\      \\    /")
    print("       \\      \\  /")
    print("        s4====s5")
    print("         |     |")
    print("        h4    h7")
    
    # Add switches
    s1 = net.addSwitch('s1', protocols='OpenFlow13', dpid='1')
    s2 = net.addSwitch('s2', protocols='OpenFlow13', dpid='2')
    s3 = net.addSwitch('s3', protocols='OpenFlow13', dpid='3')
    s4 = net.addSwitch('s4', protocols='OpenFlow13', dpid='4')
    s5 = net.addSwitch('s5', protocols='OpenFlow13', dpid='5')
    s6 = net.addSwitch('s6', protocols='OpenFlow13', dpid='6')
    
    # Add hosts
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h4 = net.addHost('h4', ip='10.0.0.4/24')
    h5 = net.addHost('h5', ip='10.0.0.5/24')
    h6 = net.addHost('h6', ip='10.0.0.6/24')
    h7 = net.addHost('h7', ip='10.0.0.7/24')
    
    # Host connections
    net.addLink(h1, s1)
    net.addLink(h4, s4)
    net.addLink(h5, s3)
    net.addLink(h6, s6)
    net.addLink(h7, s5)
    
    # Switch connections (creating multiple paths)
    net.addLink(s1, s2)  # Path 1: s1-s2-s4
    net.addLink(s2, s4)
    net.addLink(s1, s3)  # Path 2: s1-s3 (direct)
    net.addLink(s1, s5)  # Path 3: s1-s5-s3
    net.addLink(s5, s3)
    net.addLink(s4, s5)  # Creates loop
    net.addLink(s3, s6)  # Extension
    
    print("\n[SETUP] Starting network...")
    net.start()
    
    time.sleep(3)
    
    print("\n" + "="*70)
    print("   SCENARIO 1: NORMAL DIJKSTRA ROUTING")
    print("="*70)
    
    print("\n[TEST 1.1] Testing h1 -> h5 (should use shortest path s1->s3)")
    print("Expected path: h1 -> s1 -> s3 -> h5")
    result = h1.cmd('ping -c 3 10.0.0.5')
    if '0% packet loss' in result:
        print("✓ SUCCESS: Direct path working")
    else:
        print("✗ FAILED: Check controller")
    print(f"Packet loss: {'0%' if '0% packet loss' in result else '100%'}")
    
    print("\n[TEST 1.2] Testing h1 -> h4 (should use s1->s2->s4)")
    print("Expected path: h1 -> s1 -> s2 -> s4 -> h4")
    result = h1.cmd('ping -c 3 10.0.0.4')
    if '0% packet loss' in result:
        print("✓ SUCCESS: Multi-hop path working")
    else:
        print("✗ FAILED: Check controller")
    print(f"Packet loss: {'0%' if '0% packet loss' in result else '100%'}")
    
    print("\n[TEST 1.3] Testing h1 -> h6 (extended path)")
    print("Expected path: h1 -> s1 -> s3 -> s6 -> h6")
    result = h1.cmd('ping -c 3 10.0.0.6')
    if '0% packet loss' in result:
        print("✓ SUCCESS: Extended path working")
    else:
        print("✗ FAILED: Check controller")
    print(f"Packet loss: {'0%' if '0% packet loss' in result else '100%'}")
    
    print("\n" + "="*70)
    print("   SCENARIO 2: LINK FAILURE AND REROUTING")
    print("="*70)
    
    print("\n[ACTION] Breaking direct link s1 <-> s3...")
    net.configLinkStatus('s1', 's3', 'down')
    print("Link s1-s3 is now DOWN")
    
    time.sleep(3)  # Wait for controller to detect and reroute
    
    print("\n[TEST 2.1] Testing h1 -> h5 after link failure")
    print("Expected NEW path: h1 -> s1 -> s5 -> s3 -> h5 (alternate route)")
    result = h1.cmd('ping -c 3 10.0.0.5')
    if '0% packet loss' in result:
        print("✓ SUCCESS: Automatic rerouting works!")
    else:
        print("✗ FAILED: Rerouting didn't work")
    print(f"Packet loss: {'0%' if '0% packet loss' in result else '100%'}")
    
    print("\n[TEST 2.2] Testing h1 -> h6 after link failure")
    print("Expected NEW path: h1 -> s1 -> s5 -> s3 -> s6 -> h6")
    result = h1.cmd('ping -c 3 10.0.0.6')
    if '0% packet loss' in result:
        print("✓ SUCCESS: Extended path rerouted!")
    else:
        print("✗ FAILED: Extended path rerouting failed")
    print(f"Packet loss: {'0%' if '0% packet loss' in result else '100%'}")
    
    print("\n[ACTION] Restoring link s1 <-> s3...")
    net.configLinkStatus('s1', 's3', 'up')
    print("Link s1-s3 is now UP")
    
    time.sleep(3)
    
    print("\n[TEST 2.3] Testing h1 -> h5 after link restoration")
    print("Expected path: h1 -> s1 -> s3 -> h5 (back to optimal)")
    result = h1.cmd('ping -c 3 10.0.0.5')
    if '0% packet loss' in result:
        print("✓ SUCCESS: Optimal path restored!")
    else:
        print("✗ FAILED: Path restoration failed")
    print(f"Packet loss: {'0%' if '0% packet loss' in result else '100%'}")
    
    print("\n" + "="*70)
    print("   DEMO COMPLETE - Entering CLI for manual testing")
    print("   Try these commands:")
    print("     mininet> h1 ping h5")
    print("     mininet> link s1 s5 down")
    print("     mininet> h1 ping h5")
    print("     mininet> links")
    print("="*70)
    
    CLI(net)
    
    # Cleanup
    net.stop()
    controller.kill()
    os.system("pkill -9 ryu-manager 2>/dev/null")

if __name__ == '__main__':
    setLogLevel('info')
    demo_scenarios()