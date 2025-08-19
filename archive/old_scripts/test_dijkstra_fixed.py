#!/usr/bin/env python3
"""
Test script for fixed Dijkstra controller
Creates diamond topology and tests routing with link failures
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info
import time
import sys

def create_diamond_topology():
    """Create diamond topology matching topology_config.json"""
    
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch, link=TCLink)
    
    info("*** Adding controller\n")
    c0 = net.addController('c0', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    
    info("*** Adding switches\n")
    s1 = net.addSwitch('s1', dpid='0000000000000001')
    s2 = net.addSwitch('s2', dpid='0000000000000002')
    s3 = net.addSwitch('s3', dpid='0000000000000003')
    s4 = net.addSwitch('s4', dpid='0000000000000004')
    
    info("*** Adding hosts\n")
    h1 = net.addHost('h1', ip='10.0.0.1', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2', mac='00:00:00:00:00:02')
    
    info("*** Creating links\n")
    # Host connections
    net.addLink(h1, s1, port1=1, port2=1)  # h1 to s1 port 1
    net.addLink(h2, s4, port1=1, port2=4)  # h2 to s4 port 4
    
    # Diamond topology links (matching topology_config.json)
    net.addLink(s1, s2, port1=2, port2=1)  # s1:2 <-> s2:1
    net.addLink(s1, s3, port1=3, port2=1)  # s1:3 <-> s3:1
    net.addLink(s2, s4, port1=2, port2=1)  # s2:2 <-> s4:1
    net.addLink(s3, s4, port1=2, port2=2)  # s3:2 <-> s4:2
    
    # Redundant paths
    net.addLink(s1, s4, port1=4, port2=3)  # s1:4 <-> s4:3
    net.addLink(s2, s3, port1=3, port2=3)  # s2:3 <-> s3:3
    
    return net

def test_connectivity(net):
    """Test basic connectivity"""
    info("\n*** Testing connectivity\n")
    h1, h2 = net.get('h1', 'h2')
    
    # Ping test
    info("Testing h1 -> h2: ")
    result = h1.cmd('ping -c 3 -W 1 10.0.0.2')
    if '0% packet loss' in result:
        info("SUCCESS\n")
        return True
    else:
        info("FAILED\n")
        return False

def test_link_failure(net):
    """Test link failure and recovery"""
    info("\n*** Testing link failure handling\n")
    
    # Get nodes
    h1, h2 = net.get('h1', 'h2')
    s1, s2 = net.get('s1', 's2')
    
    # Start continuous ping in background
    info("Starting continuous ping from h1 to h2...\n")
    h1.cmd('ping 10.0.0.2 > /tmp/ping_log.txt 2>&1 &')
    ping_pid = h1.cmd('echo $!').strip()
    
    time.sleep(3)
    
    # Simulate link failure
    info("Simulating link failure: s1 <-> s2\n")
    net.configLinkStatus('s1', 's2', 'down')
    
    time.sleep(5)
    
    # Check if ping still works (should reroute)
    info("Checking connectivity after failure...\n")
    result = h1.cmd('ping -c 3 -W 1 10.0.0.2')
    if '0% packet loss' in result:
        info("SUCCESS - Traffic rerouted!\n")
    else:
        info("FAILED - No reroute\n")
    
    # Restore link
    info("Restoring link: s1 <-> s2\n")
    net.configLinkStatus('s1', 's2', 'up')
    
    time.sleep(3)
    
    # Stop continuous ping
    h1.cmd(f'kill {ping_pid}')
    
    # Show ping statistics
    info("\nPing statistics during test:\n")
    stats = h1.cmd('tail -20 /tmp/ping_log.txt')
    for line in stats.split('\n')[-5:]:
        if line:
            info(f"  {line}\n")

def run_tests():
    """Run all tests"""
    setLogLevel('info')
    
    info("*** Creating network\n")
    net = create_diamond_topology()
    
    info("*** Starting network\n")
    net.start()
    
    # Wait for topology discovery
    info("*** Waiting for controller setup...\n")
    time.sleep(3)
    
    # Run tests
    test_connectivity(net)
    test_link_failure(net)
    
    # Interactive CLI for debugging
    info("\n*** Entering CLI for manual testing\n")
    info("Try: h1 ping h2\n")
    info("Try: links\n")
    info("Try: dpctl dump-flows\n")
    CLI(net)
    
    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    run_tests()
