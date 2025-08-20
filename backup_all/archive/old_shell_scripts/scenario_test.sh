#!/bin/bash
# Automated scenario testing for 10-switch topology

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${MAGENTA}============================================================${NC}"
echo -e "${MAGENTA}    AUTOMATED DIJKSTRA ROUTING SCENARIOS${NC}"
echo -e "${MAGENTA}============================================================${NC}"

# Clean up
echo -e "${BLUE}[CLEANUP]${NC} Preparing environment..."
sudo mn -c 2>/dev/null || true
pkill -9 ryu-manager 2>/dev/null || true

# Start controller
echo -e "${BLUE}[CONTROLLER]${NC} Starting Dijkstra controller..."
source /data/miniforge3/etc/profile.d/conda.sh && conda activate sdn-lab 2>/dev/null || true
ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/dijkstra_controller_10sw.py > /tmp/controller.log 2>&1 &
CONTROLLER_PID=$!
sleep 5

# Create scenario test script
cat > /tmp/scenario_runner.py << 'EOF'
#!/usr/bin/env python3
import time
import sys
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.log import setLogLevel

class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'

def print_scenario(name):
    print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
    print(f"{Colors.CYAN} SCENARIO: {name}{Colors.NC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")

def test_connectivity(h1, h2, expected=True):
    """Test connectivity between two hosts"""
    result = h1.cmd(f'ping -c 2 -W 1 {h2.IP()}')
    success = '0% packet loss' in result
    
    if success == expected:
        status = f"{Colors.GREEN}✅ PASS{Colors.NC}"
    else:
        status = f"{Colors.RED}❌ FAIL{Colors.NC}"
    
    print(f"   {h1.name} -> {h2.name}: {status}")
    return success == expected

def scenario_1_normal_routing(net, hosts):
    """Scenario 1: Test normal routing paths"""
    print_scenario("1. NORMAL ROUTING")
    
    tests = [
        (hosts[1], hosts[2], "Adjacent switches"),
        (hosts[1], hosts[5], "Diagonal path"),
        (hosts[1], hosts[9], "Corner to corner"),
        (hosts[3], hosts[7], "Cross topology"),
        (hosts[1], hosts[10], "To isolated switch")
    ]
    
    passed = 0
    for h1, h2, desc in tests:
        print(f"\n   📍 Test: {desc}")
        if test_connectivity(h1, h2):
            passed += 1
    
    print(f"\n   Result: {passed}/{len(tests)} tests passed")
    return passed == len(tests)

def scenario_2_single_failure(net, hosts):
    """Scenario 2: Single link failure and recovery"""
    print_scenario("2. SINGLE LINK FAILURE")
    
    print("\n   🔗 Testing initial path h1 -> h2")
    test_connectivity(hosts[1], hosts[2])
    
    print("\n   🔴 Breaking link s1 <-> s2")
    net.configLinkStatus('s1', 's2', 'down')
    time.sleep(3)
    
    print("   🔄 Testing rerouting h1 -> h2")
    rerouted = test_connectivity(hosts[1], hosts[2])
    
    print("\n   🟢 Restoring link s1 <-> s2")
    net.configLinkStatus('s1', 's2', 'up')
    time.sleep(3)
    
    print("   📍 Testing restored path h1 -> h2")
    restored = test_connectivity(hosts[1], hosts[2])
    
    return rerouted and restored

def scenario_3_multiple_failures(net, hosts):
    """Scenario 3: Multiple simultaneous failures"""
    print_scenario("3. MULTIPLE LINK FAILURES")
    
    print("\n   🔗 Initial test h1 -> h5")
    test_connectivity(hosts[1], hosts[5])
    
    failures = [
        ('s1', 's2', "horizontal"),
        ('s1', 's4', "vertical"),
        ('s2', 's5', "to center")
    ]
    
    print("\n   🔴 Breaking multiple links:")
    for s1, s2, desc in failures:
        print(f"      - {s1} <-> {s2} ({desc})")
        net.configLinkStatus(s1, s2, 'down')
    time.sleep(3)
    
    print("\n   🔄 Testing rerouting h1 -> h5 (via diagonal)")
    rerouted = test_connectivity(hosts[1], hosts[5])
    
    print("\n   🟢 Restoring all links")
    for s1, s2, _ in failures:
        net.configLinkStatus(s1, s2, 'up')
    time.sleep(3)
    
    return rerouted

def scenario_4_network_partition(net, hosts):
    """Scenario 4: Network partition and recovery"""
    print_scenario("4. NETWORK PARTITION")
    
    print("\n   🔗 Testing h1 -> h10 (through s8)")
    test_connectivity(hosts[1], hosts[10])
    
    print("\n   🔴 Isolating s10 by breaking s8 <-> s10")
    net.configLinkStatus('s8', 's10', 'down')
    time.sleep(3)
    
    print("   ❌ Testing isolation (should fail)")
    isolated = test_connectivity(hosts[1], hosts[10], expected=False)
    
    print("\n   🟢 Reconnecting s10")
    net.configLinkStatus('s8', 's10', 'up')
    time.sleep(3)
    
    print("   ✅ Testing reconnection")
    reconnected = test_connectivity(hosts[1], hosts[10])
    
    return isolated and reconnected

def scenario_5_stress_test(net, hosts):
    """Scenario 5: Rapid link changes"""
    print_scenario("5. STRESS TEST - RAPID CHANGES")
    
    print("\n   ⚡ Rapidly breaking and restoring links...")
    
    links = [('s5', 's8'), ('s2', 's5'), ('s5', 's6')]
    
    for i in range(3):
        print(f"\n   Round {i+1}/3:")
        for s1, s2 in links:
            net.configLinkStatus(s1, s2, 'down')
            print(f"      🔴 {s1} <-> {s2} down")
            time.sleep(1)
            net.configLinkStatus(s1, s2, 'up')
            print(f"      🟢 {s1} <-> {s2} up")
            time.sleep(1)
    
    print("\n   📍 Final connectivity test")
    final = test_connectivity(hosts[1], hosts[9])
    
    return final

def main():
    setLogLevel('warning')
    
    # Create network
    print("\n🔨 Building 10-switch topology...")
    net = Mininet(controller=None, switch=OVSSwitch, autoSetMacs=True)
    
    c0 = net.addController('c0', controller=RemoteController, 
                          ip='127.0.0.1', port=6633)
    
    # Create topology
    switches = {}
    hosts = {}
    for i in range(1, 11):
        switches[i] = net.addSwitch(f's{i}', protocols='OpenFlow13', dpid=str(i))
        hosts[i] = net.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
        net.addLink(hosts[i], switches[i], port1=0, port2=1)
    
    # Add all links
    links = [
        (1,2,2,2), (2,3,3,2), (4,5,3,2), (5,6,3,2), (7,8,2,2), (8,9,3,2),
        (1,4,4,3), (2,5,4,3), (3,6,4,3), (4,7,5,3), (5,8,5,3), (6,9,5,3),
        (1,5,5,4), (2,4,5,4), (2,6,6,4), (3,5,5,6), (4,8,6,4), (5,7,7,4),
        (5,9,8,4), (6,8,6,5), (8,10,10,2)
    ]
    for s1,s2,p1,p2 in links:
        net.addLink(switches[s1], switches[s2], port1=p1, port2=p2)
    
    print("✅ Starting network...")
    net.start()
    time.sleep(5)
    
    # Run scenarios
    scenarios = [
        scenario_1_normal_routing,
        scenario_2_single_failure,
        scenario_3_multiple_failures,
        scenario_4_network_partition,
        scenario_5_stress_test
    ]
    
    results = []
    for scenario in scenarios:
        try:
            result = scenario(net, hosts)
            results.append(result)
        except Exception as e:
            print(f"   {Colors.RED}Error: {e}{Colors.NC}")
            results.append(False)
        time.sleep(2)
    
    # Summary
    print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
    print(f"{Colors.CYAN} TEST SUMMARY{Colors.NC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")
    
    passed = sum(results)
    total = len(results)
    
    for i, result in enumerate(results, 1):
        status = f"{Colors.GREEN}PASS{Colors.NC}" if result else f"{Colors.RED}FAIL{Colors.NC}"
        print(f"   Scenario {i}: {status}")
    
    print(f"\n   Overall: {passed}/{total} scenarios passed")
    
    if passed == total:
        print(f"\n{Colors.GREEN}🎉 All tests passed!{Colors.NC}")
    else:
        print(f"\n{Colors.YELLOW}⚠️ Some tests failed{Colors.NC}")
    
    net.stop()
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
EOF

# Run scenarios
echo -e "\n${GREEN}[TEST]${NC} Running automated scenarios..."
sudo python3 /tmp/scenario_runner.py
TEST_RESULT=$?

# Show controller logs
echo -e "\n${YELLOW}[LOGS]${NC} Controller event summary:"
grep -E "DIJKSTRA CALCULATION|LINK FAILURE|REROUTING" /tmp/controller.log | tail -20

# Cleanup
echo -e "\n${BLUE}[CLEANUP]${NC} Stopping controller..."
kill $CONTROLLER_PID 2>/dev/null || true
rm -f /tmp/scenario_runner.py /tmp/controller.log

if [ $TEST_RESULT -eq 0 ]; then
    echo -e "\n${GREEN}✅ All scenarios completed successfully!${NC}"
else
    echo -e "\n${RED}❌ Some scenarios failed${NC}"
fi

exit $TEST_RESULT