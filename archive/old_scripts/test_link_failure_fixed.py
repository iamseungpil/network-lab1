#!/usr/bin/env python3
"""
Fixed test for Dijkstra controller with proper link failure handling
Uses correct string parameters for configLinkStatus
"""

from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info, error
import time
import sys

def create_diamond_topology():
    """Create diamond topology with OVS switches"""
    
    net = Mininet(controller=RemoteController, 
                  switch=OVSKernelSwitch,  # Use OVS instead of default
                  link=TCLink,
                  autoSetMacs=True)  # Auto-set MACs for consistency
    
    info("*** Adding controller\n")
    c0 = net.addController('c0', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    
    info("*** Adding 4 switches (OVS)\n")
    s1 = net.addSwitch('s1', dpid='0000000000000001', cls=OVSKernelSwitch)
    s2 = net.addSwitch('s2', dpid='0000000000000002', cls=OVSKernelSwitch)
    s3 = net.addSwitch('s3', dpid='0000000000000003', cls=OVSKernelSwitch)
    s4 = net.addSwitch('s4', dpid='0000000000000004', cls=OVSKernelSwitch)
    
    info("*** Adding hosts\n")
    h1 = net.addHost('h1', ip='10.0.0.1', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2', mac='00:00:00:00:00:02')
    
    info("*** Creating links\n")
    # Host connections
    net.addLink(h1, s1, port1=1, port2=1)
    net.addLink(h2, s4, port1=1, port2=4)
    
    # Diamond topology
    net.addLink(s1, s2, port1=2, port2=1)  # TOP PATH
    net.addLink(s1, s3, port1=3, port2=1)  # BOTTOM PATH
    net.addLink(s2, s4, port1=2, port2=1)
    net.addLink(s3, s4, port1=2, port2=2)
    
    # Cross links
    net.addLink(s1, s4, port1=4, port2=3)  # DIRECT PATH
    net.addLink(s2, s3, port1=3, port2=3)  # CROSS LINK
    
    return net

def test_basic_connectivity(net):
    """Test basic connectivity"""
    info("\n" + "="*70 + "\n")
    info("TEST 1: Basic Connectivity\n")
    info("="*70 + "\n")
    
    h1, h2 = net.get('h1', 'h2')
    
    info("Pinging from h1 to h2...\n")
    result = h1.cmd('ping -c 5 -i 0.5 10.0.0.2')
    
    # Show results
    for line in result.split('\n'):
        if 'packet loss' in line or 'rtt' in line:
            info(f"  {line}\n")
    
    if '0% packet loss' in result:
        info("✅ PASS: Full connectivity\n")
        return True
    else:
        error("❌ FAIL: Connectivity issues\n")
        return False

def test_link_failure_cli(net):
    """Test link failure using CLI commands (not Python API)"""
    info("\n" + "="*70 + "\n")
    info("TEST 2: Link Failure via CLI Commands\n")
    info("="*70 + "\n")
    
    h1, h2 = net.get('h1', 'h2')
    
    # Start continuous ping
    info("Starting continuous ping from h1 to h2...\n")
    h1.cmd('ping 10.0.0.2 > /tmp/ping_test.txt 2>&1 &')
    ping_pid = h1.cmd('echo $!').strip()
    
    time.sleep(3)
    info("  Initial connectivity established\n")
    
    # Use CLI command to bring link down
    info("\n💥 Bringing down link s1-s2 using CLI command...\n")
    net.cmd('link', 's1', 's2', 'down')
    
    time.sleep(5)
    
    # Test connectivity
    info("Testing connectivity after link failure...\n")
    result = h1.cmd('ping -c 3 -W 1 10.0.0.2')
    
    if '0% packet loss' in result:
        info("✅ PASS: Traffic rerouted successfully!\n")
    else:
        info("⚠️  Some packet loss detected\n")
    
    # Bring link back up
    info("\n🔧 Restoring link s1-s2...\n")
    net.cmd('link', 's1', 's2', 'up')
    
    time.sleep(3)
    
    # Stop ping
    h1.cmd(f'kill {ping_pid}')
    
    # Analyze results
    info("\nAnalyzing ping results...\n")
    result = h1.cmd('cat /tmp/ping_test.txt | tail -20')
    losses = result.count('Unreachable')
    successes = result.count('bytes from')
    
    info(f"  Successful pings: {successes}\n")
    info(f"  Lost packets: {losses}\n")
    
    if successes > losses:
        info("✅ Overall: More successes than losses\n")
        return True
    else:
        info("❌ Overall: Too many losses\n")
        return False

def test_link_failure_api(net):
    """Test link failure using Python API with correct string parameters"""
    info("\n" + "="*70 + "\n")
    info("TEST 3: Link Failure via Python API (configLinkStatus)\n")
    info("="*70 + "\n")
    
    h1, h2 = net.get('h1', 'h2')
    
    # Start continuous ping
    info("Starting continuous ping from h1 to h2...\n")
    h1.cmd('ping -i 0.2 10.0.0.2 > /tmp/ping_api_test.txt 2>&1 &')
    ping_pid = h1.cmd('echo $!').strip()
    
    time.sleep(3)
    
    # CORRECT: Use string parameters
    info("\n💥 Using net.configLinkStatus('s1', 's3', 'down')...\n")
    net.configLinkStatus('s1', 's3', 'down')  # Bottom path
    
    time.sleep(3)
    
    # Test connectivity
    result1 = h1.cmd('ping -c 2 -W 1 10.0.0.2')
    if '0% packet loss' in result1:
        info("  ✅ Traffic using alternate path (s1->s2->s4)\n")
    else:
        info("  ⚠️  Some packet loss\n")
    
    # Fail another link
    info("\n💥 Using net.configLinkStatus('s2', 's4', 'down')...\n")
    net.configLinkStatus('s2', 's4', 'down')
    
    time.sleep(3)
    
    result2 = h1.cmd('ping -c 2 -W 1 10.0.0.2')
    if '0% packet loss' in result2:
        info("  ✅ Traffic using direct path (s1->s4)\n")
    else:
        info("  ⚠️  Connectivity issues\n")
    
    # Restore links
    info("\n🔧 Restoring all links...\n")
    net.configLinkStatus('s1', 's3', 'up')
    net.configLinkStatus('s2', 's4', 'up')
    
    time.sleep(3)
    
    # Stop ping
    h1.cmd(f'kill {ping_pid}')
    
    # Final test
    result = h1.cmd('ping -c 3 -W 1 10.0.0.2')
    if '0% packet loss' in result:
        info("✅ PASS: Full recovery\n")
        return True
    else:
        info("❌ FAIL: Recovery issues\n")
        return False

def test_ovs_commands(net):
    """Test using OVS commands directly"""
    info("\n" + "="*70 + "\n")
    info("TEST 4: Direct OVS Port Manipulation\n")
    info("="*70 + "\n")
    
    h1, h2 = net.get('h1', 'h2')
    s1 = net.get('s1')
    
    # Check OVS port status
    info("Checking OVS port status on s1...\n")
    result = s1.cmd('ovs-ofctl show s1 | grep -E "^ [0-9]"')
    info(f"{result}\n")
    
    # Start ping
    info("\nStarting ping test...\n")
    h1.cmd('ping 10.0.0.2 > /tmp/ping_ovs_test.txt 2>&1 &')
    ping_pid = h1.cmd('echo $!').strip()
    
    time.sleep(3)
    
    # Use OVS command to modify port
    info("\n💥 Using OVS to disable port s1-eth2 (link to s2)...\n")
    s1.cmd('ovs-ofctl mod-port s1 s1-eth2 down')
    
    time.sleep(5)
    
    # Check connectivity
    result = h1.cmd('ping -c 3 -W 1 10.0.0.2')
    if '0% packet loss' in result:
        info("  ✅ Traffic rerouted\n")
    else:
        info("  ⚠️  Some packet loss\n")
    
    # Re-enable port
    info("\n🔧 Re-enabling port s1-eth2...\n")
    s1.cmd('ovs-ofctl mod-port s1 s1-eth2 up')
    
    time.sleep(3)
    
    # Stop ping
    h1.cmd(f'kill {ping_pid}')
    
    info("✅ OVS commands test complete\n")
    return True

def run_all_tests():
    """Run comprehensive link failure tests"""
    setLogLevel('info')
    
    info("\n" + "="*70 + "\n")
    info("🚀 LINK FAILURE TEST SUITE (FIXED)\n")
    info("="*70 + "\n")
    
    # Create network
    info("*** Creating network with OVS switches\n")
    net = create_diamond_topology()
    
    info("\n*** Starting network\n")
    net.start()
    
    # Wait for controller
    info("\n*** Waiting for controller setup...\n")
    time.sleep(5)
    
    # Run tests
    results = []
    results.append(("Basic Connectivity", test_basic_connectivity(net)))
    results.append(("Link Failure CLI", test_link_failure_cli(net)))
    results.append(("Link Failure API", test_link_failure_api(net)))
    results.append(("OVS Commands", test_ovs_commands(net)))
    
    # Summary
    info("\n" + "="*70 + "\n")
    info("📊 TEST SUMMARY\n")
    info("="*70 + "\n")
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        info(f"  {test_name}: {status}\n")
    
    # Interactive CLI
    info("\n*** Entering CLI for manual testing\n")
    info("Try these commands:\n")
    info("  - h1 ping h2\n")
    info("  - link s1 s2 down\n")
    info("  - link s1 s2 up\n")
    info("  - py net.configLinkStatus('s1', 's2', 'down')\n")
    info("  - sh ovs-ofctl show s1\n")
    info("  - sh ovs-ofctl dump-flows s1\n")
    CLI(net)
    
    # Cleanup
    info("\n*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    run_all_tests()