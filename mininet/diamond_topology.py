#!/usr/bin/env python3
"""
Simple 4-switch diamond topology for testing
"""

import sys
import argparse
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info

def create_diamond_topology(controller_port=6633):
    """Create simple 4-switch diamond topology"""
    
    net = Mininet(
        controller=RemoteController,
        switch=OVSKernelSwitch,
        link=TCLink,
        autoSetMacs=True
    )
    
    info("*** Creating Diamond Topology: 4 switches, 4 hosts\n")
    
    # Add controller
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=controller_port)
    
    # Add switches
    s1 = net.addSwitch('s1', dpid='0000000000000001')
    s2 = net.addSwitch('s2', dpid='0000000000000002')  
    s3 = net.addSwitch('s3', dpid='0000000000000003')
    s4 = net.addSwitch('s4', dpid='0000000000000004')
    
    # Add hosts
    h1 = net.addHost('h1', ip='10.0.0.1', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2', mac='00:00:00:00:00:02')
    h3 = net.addHost('h3', ip='10.0.0.3', mac='00:00:00:00:00:03')
    h4 = net.addHost('h4', ip='10.0.0.4', mac='00:00:00:00:00:04')
    
    # Connect hosts to switches
    net.addLink(h1, s1)
    net.addLink(h2, s2)
    net.addLink(h3, s3)
    net.addLink(h4, s4)
    
    # Create diamond topology
    net.addLink(s1, s2)  # Upper path
    net.addLink(s1, s3)  # Lower path
    net.addLink(s2, s4)  # Upper convergence
    net.addLink(s3, s4)  # Lower convergence
    
    info("*** Topology created:\n")
    info("    h1--s1--s2--h2\n")
    info("        |\\  /|\n") 
    info("        | \\/ |\n")
    info("        | /\\ |\n")
    info("        |/  \\|\n")
    info("    h3--s3--s4--h4\n")
    
    return net

def main():
    parser = argparse.ArgumentParser(description='Diamond topology with configurable controller port')
    parser.add_argument('--controller-port', type=int, default=6633, 
                       help='Controller port (default: 6633)')
    args = parser.parse_args()
    
    setLogLevel('info')
    
    info("*** Starting Simple Diamond Topology\n")
    info(f"*** Controller port: {args.controller_port}\n")
    
    net = create_diamond_topology(controller_port=args.controller_port)
    
    info("*** Starting network\n")
    net.start()
    
    info("*** Waiting for controller connection...\n")
    import time
    time.sleep(5)
    
    info("*** Network ready. Starting CLI...\n")
    info("*** Try: h1 ping h4, h2 ping h3, link s1 s2 down\n")
    CLI(net)
    
    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    main()