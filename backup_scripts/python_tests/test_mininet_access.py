#!/usr/bin/env python3
"""
Test script to check Mininet access from conda environment
"""

import sys
import os

# Add system Python paths for Mininet access
sys.path.extend([
    '/usr/lib/python3/dist-packages',
    '/usr/local/lib/python3.8/dist-packages',
    '/usr/lib/python3.8/dist-packages'
])

try:
    from mininet.net import Mininet
    from mininet.node import RemoteController
    print("✓ Successfully imported Mininet")
    print("✓ Can access system Mininet from conda environment")
    
    # Test basic network creation
    net = Mininet(controller=None)
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    s1 = net.addSwitch('s1')
    h1 = net.addHost('h1')
    net.addLink(h1, s1)
    
    print("✓ Basic network topology created successfully")
    print("✓ Dual controller test should work now")
    
    # Don't actually start the network, just verify creation
    net.stop()
    
except ImportError as e:
    print(f"✗ Failed to import Mininet: {e}")
    print("Available paths:")
    for p in sys.path:
        if 'python' in p:
            print(f"  {p}")
            
except Exception as e:
    print(f"✗ Error: {e}")
    
print("\nPython version:", sys.version)
print("Python executable:", sys.executable)