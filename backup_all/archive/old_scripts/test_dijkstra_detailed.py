#!/usr/bin/env python3
"""
Detailed test for Dijkstra controller with enhanced logging
Tests link failure, recovery, and multiple path scenarios
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info
import time
import sys
import threading

def create_diamond_topology():
    """Create diamond topology matching topology_config.json"""
    
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch, link=TCLink)
    
    info("*** Adding controller\n")
    c0 = net.addController('c0', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    
    info("*** Adding 4 switches for diamond topology\n")
    s1 = net.addSwitch('s1', dpid='0000000000000001')
    s2 = net.addSwitch('s2', dpid='0000000000000002')
    s3 = net.addSwitch('s3', dpid='0000000000000003')
    s4 = net.addSwitch('s4', dpid='0000000000000004')
    
    info("*** Adding hosts\n")
    h1 = net.addHost('h1', ip='10.0.0.1', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2', mac='00:00:00:00:00:02')
    
    info("*** Creating links (Diamond topology with redundant paths)\n")
    # Host connections
    net.addLink(h1, s1, port1=1, port2=1)  # h1 to s1 port 1
    net.addLink(h2, s4, port1=1, port2=4)  # h2 to s4 port 4
    
    # Diamond topology links
    info("    - Main diamond paths\n")
    net.addLink(s1, s2, port1=2, port2=1)  # s1:2 <-> s2:1 (TOP PATH)
    net.addLink(s1, s3, port1=3, port2=1)  # s1:3 <-> s3:1 (BOTTOM PATH)
    net.addLink(s2, s4, port1=2, port2=1)  # s2:2 <-> s4:1
    net.addLink(s3, s4, port1=2, port2=2)  # s3:2 <-> s4:2
    
    # Redundant cross paths
    info("    - Redundant cross paths\n")
    net.addLink(s1, s4, port1=4, port2=3)  # s1:4 <-> s4:3 (DIRECT PATH)
    net.addLink(s2, s3, port1=3, port2=3)  # s2:3 <-> s3:3 (CROSS LINK)
    
    return net

def monitor_ping(h1, h2, duration=30):
    """Monitor ping continuously and report statistics"""
    info("\n" + "="*70 + "\n")
    info("📊 CONTINUOUS PING MONITORING\n")
    info("="*70 + "\n")
    
    # Start ping with timestamp
    h1.cmd(f'ping -i 0.5 {h2.IP()} > /tmp/ping_monitor.txt 2>&1 &')
    ping_pid = h1.cmd('echo $!').strip()
    
    start_time = time.time()
    last_success = True
    failure_start = None
    
    while time.time() - start_time < duration:
        # Check last ping result
        result = h1.cmd('tail -1 /tmp/ping_monitor.txt')
        
        if 'bytes from' in result:
            if not last_success:
                recovery_time = time.time() - failure_start
                info(f"    ✅ RECOVERED after {recovery_time:.1f} seconds\n")
                last_success = True
        elif 'Unreachable' in result or 'Destination' in result:
            if last_success:
                failure_start = time.time()
                info(f"    ❌ CONNECTIVITY LOST at {time.time() - start_time:.1f}s\n")
                last_success = False
        
        time.sleep(0.5)
    
    # Stop ping
    h1.cmd(f'kill {ping_pid}')
    
    # Get final statistics
    stats = h1.cmd('grep -E "packet loss|rtt" /tmp/ping_monitor.txt | tail -2')
    info("\n📈 Final Statistics:\n")
    for line in stats.split('\n'):
        if line:
            info(f"    {line}\n")

def test_scenario_1(net):
    """Test Scenario 1: Basic connectivity"""
    info("\n" + "="*70 + "\n")
    info("🧪 TEST SCENARIO 1: Basic Connectivity\n")
    info("="*70 + "\n")
    
    h1, h2 = net.get('h1', 'h2')
    
    info("Testing h1 (10.0.0.1) -> h2 (10.0.0.2)\n")
    result = h1.cmd('ping -c 5 -W 1 10.0.0.2')
    
    if '0% packet loss' in result:
        info("    ✅ PASS: Full connectivity\n")
        # Extract RTT
        for line in result.split('\n'):
            if 'min/avg/max' in line:
                info(f"    📊 RTT: {line.split('=')[1].strip()}\n")
    else:
        info("    ❌ FAIL: Packet loss detected\n")
        for line in result.split('\n'):
            if 'packet loss' in line:
                info(f"    {line}\n")

def test_scenario_2(net):
    """Test Scenario 2: Single link failure"""
    info("\n" + "="*70 + "\n")
    info("🧪 TEST SCENARIO 2: Single Link Failure (s1-s2)\n")
    info("="*70 + "\n")
    
    h1, h2 = net.get('h1', 'h2')
    
    # Start background ping
    info("Starting continuous ping...\n")
    h1.cmd('ping 10.0.0.2 > /tmp/test2_ping.txt 2>&1 &')
    ping_pid = h1.cmd('echo $!').strip()
    
    time.sleep(3)
    info("    📍 Initial path established\n")
    
    # Fail link
    info("\n💥 FAILING LINK: s1 <-X-> s2\n")
    net.configLinkStatus('s1', 's2', 'down')
    
    time.sleep(5)
    
    # Test connectivity
    info("\nTesting connectivity after failure...\n")
    result = h1.cmd('ping -c 3 -W 1 10.0.0.2')
    
    if '0% packet loss' in result:
        info("    ✅ PASS: Traffic successfully rerouted!\n")
    else:
        info("    ❌ FAIL: Rerouting failed\n")
    
    # Restore link
    info("\n🔧 RESTORING LINK: s1 <--> s2\n")
    net.configLinkStatus('s1', 's2', 'up')
    
    time.sleep(3)
    
    # Stop ping and analyze
    h1.cmd(f'kill {ping_pid}')
    
    # Count packet loss during test
    total = h1.cmd('grep -c "bytes from" /tmp/test2_ping.txt').strip()
    loss = h1.cmd('grep -c "Unreachable" /tmp/test2_ping.txt').strip()
    
    if total.isdigit() and loss.isdigit():
        info(f"\n📊 Packet Statistics:\n")
        info(f"    Total successful: {total}\n")
        info(f"    Total lost: {loss}\n")
        if int(total) > 0:
            loss_rate = (int(loss) / (int(total) + int(loss))) * 100
            info(f"    Loss rate: {loss_rate:.1f}%\n")

def test_scenario_3(net):
    """Test Scenario 3: Multiple link failures"""
    info("\n" + "="*70 + "\n")
    info("🧪 TEST SCENARIO 3: Multiple Link Failures\n")
    info("="*70 + "\n")
    
    h1, h2 = net.get('h1', 'h2')
    
    # Start monitoring
    info("Starting continuous ping...\n")
    h1.cmd('ping 10.0.0.2 > /tmp/test3_ping.txt 2>&1 &')
    ping_pid = h1.cmd('echo $!').strip()
    
    time.sleep(3)
    
    # First failure
    info("\n💥 FAILURE 1: s1 <-X-> s2 (Top path)\n")
    net.configLinkStatus('s1', 's2', 'down')
    time.sleep(3)
    
    result1 = h1.cmd('ping -c 2 -W 1 10.0.0.2')
    if '0% packet loss' in result1:
        info("    ✅ Rerouted through bottom path (s1->s3->s4)\n")
    
    # Second failure
    info("\n💥 FAILURE 2: s3 <-X-> s4 (Bottom path)\n")
    net.configLinkStatus('s3', 's4', 'down')
    time.sleep(3)
    
    result2 = h1.cmd('ping -c 2 -W 1 10.0.0.2')
    if '0% packet loss' in result2:
        info("    ✅ Rerouted through direct path (s1->s4)\n")
    else:
        info("    ⚠️  Testing alternate paths...\n")
    
    # Restore first link
    info("\n🔧 RESTORING: s1 <--> s2\n")
    net.configLinkStatus('s1', 's2', 'up')
    time.sleep(3)
    
    result3 = h1.cmd('ping -c 2 -W 1 10.0.0.2')
    if '0% packet loss' in result3:
        info("    ✅ Connectivity restored\n")
    
    # Restore second link
    info("\n🔧 RESTORING: s3 <--> s4\n")
    net.configLinkStatus('s3', 's4', 'up')
    
    # Stop monitoring
    h1.cmd(f'kill {ping_pid}')

def test_scenario_4(net):
    """Test Scenario 4: Rapid link flapping"""
    info("\n" + "="*70 + "\n")
    info("🧪 TEST SCENARIO 4: Rapid Link Flapping\n")
    info("="*70 + "\n")
    
    h1, h2 = net.get('h1', 'h2')
    
    info("Testing controller stability under rapid changes...\n")
    
    # Start ping
    h1.cmd('ping 10.0.0.2 > /tmp/test4_ping.txt 2>&1 &')
    ping_pid = h1.cmd('echo $!').strip()
    
    # Rapid flapping
    for i in range(3):
        info(f"\n🔄 Flap cycle {i+1}/3\n")
        
        info("    DOWN: s1-s2\n")
        net.configLinkStatus('s1', 's2', 'down')
        time.sleep(1)
        
        info("    UP: s1-s2\n")
        net.configLinkStatus('s1', 's2', 'up')
        time.sleep(1)
    
    # Final test
    time.sleep(2)
    result = h1.cmd('ping -c 3 -W 1 10.0.0.2')
    
    if '0% packet loss' in result:
        info("\n    ✅ PASS: Controller handled rapid changes\n")
    else:
        info("\n    ❌ FAIL: Controller unstable\n")
    
    h1.cmd(f'kill {ping_pid}')

def run_all_tests():
    """Run all test scenarios"""
    setLogLevel('info')
    
    info("\n" + "="*70 + "\n")
    info("🚀 DIJKSTRA CONTROLLER COMPREHENSIVE TEST SUITE\n")
    info("="*70 + "\n")
    
    info("*** Creating diamond topology network\n")
    net = create_diamond_topology()
    
    info("\n*** Starting network\n")
    net.start()
    
    info("\n*** Waiting for controller initialization...\n")
    time.sleep(5)
    
    # Run all test scenarios
    test_scenario_1(net)
    test_scenario_2(net)
    test_scenario_3(net)
    test_scenario_4(net)
    
    # Summary
    info("\n" + "="*70 + "\n")
    info("📋 TEST SUITE COMPLETE\n")
    info("="*70 + "\n")
    
    # Interactive CLI
    info("\n*** Entering CLI for manual testing\n")
    info("Commands to try:\n")
    info("  - h1 ping h2\n")
    info("  - links\n")
    info("  - link s1 s2 down\n")
    info("  - link s1 s2 up\n")
    info("  - dpctl dump-flows\n")
    CLI(net)
    
    info("\n*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    run_all_tests()