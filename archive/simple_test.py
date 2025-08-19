#!/usr/bin/env python3
"""
Simple test with single controller
"""

import time
import subprocess
import os
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

def simple_test():
    # Clean everything
    os.system("sudo mn -c 2>/dev/null")
    os.system("pkill -9 ryu-manager 2>/dev/null")
    
    print("\n=== SIMPLE TEST - Single Controller ===\n")
    
    # Start working controller (the one we tested that works)
    print("[1] Starting simple working controller...")
    proc = subprocess.Popen([
        'bash', '-c',
        'source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-env && '
        'ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/working_controller.py'
    ])
    
    time.sleep(3)
    
    # Create very simple network
    print("[2] Creating simple network...")
    net = Mininet(controller=None, switch=OVSSwitch, autoSetMacs=True)
    
    c0 = net.addController('c0', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    
    # Just 2 switches and 3 hosts
    s1 = net.addSwitch('s1', protocols='OpenFlow13')
    s2 = net.addSwitch('s2', protocols='OpenFlow13')
    
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')
    
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s2)
    net.addLink(s1, s2)
    
    print("[3] Starting network...")
    net.start()
    
    time.sleep(2)
    
    print("\n=== RAW TEST RESULTS ===\n")
    
    # Test 1
    print("TEST: h1 ping h2 (same switch)")
    result = h1.cmd('ping -c 2 -W 1 10.0.0.2')
    print(result)
    
    # Test 2
    print("\nTEST: h1 ping h3 (different switch)")
    result = h1.cmd('ping -c 2 -W 1 10.0.0.3')
    print(result)
    
    # Check controller is actually seeing packets
    print("\n=== Checking controller activity ===")
    print("Mininet CLI - try: h1 ping h2")
    
    CLI(net)
    
    net.stop()
    os.system("pkill -9 ryu-manager")

if __name__ == '__main__':
    setLogLevel('info')
    simple_test()