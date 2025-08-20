# SDN Lab - Complete Technical Guide

## 📚 Table of Contents
1. [Overview](#-overview)
2. [Quick Start](#-quick-start)
3. [Core Concepts](#-core-concepts)
   - [OpenFlow vs LLDP](#openflow-vs-lldp)
   - [How They Work Together](#how-they-work-together)
4. [Implementation Details](#-implementation-details)
   - [Dijkstra Routing](#dijkstra-routing)
   - [Link Failure & Rerouting](#link-failure--rerouting)
   - [STP for Loop Prevention](#stp-for-loop-prevention)
5. [Configuration](#-configuration)
6. [Testing & Monitoring](#-testing--monitoring)
7. [Troubleshooting](#-troubleshooting)

---

## 🎯 Overview

This SDN implementation demonstrates:
- **Dijkstra shortest-path routing** with NetworkX
- **Automatic rerouting** on link failures  
- **10-switch ring topology** with loop prevention
- **Real-time topology discovery** using LLDP

### Project Structure
```
network-lab1/
├── start_sdn_demo.sh         # Main execution script
├── demo_dijkstra_routing.sh  # Automated demo
├── ryu-controller/
│   ├── main_controller.py    # Basic Dijkstra controller
│   └── main_controller_stp.py # With STP protection
└── mininet/
    ├── ring_topology.py      # 10-switch ring
    ├── diamond_topology.py   # 4-switch diamond
    └── graph_topology.py     # Complex graph
```

---

## 🚀 Quick Start

### Basic Commands
```bash
# Start with ring topology (10 switches)
./start_sdn_demo.sh ring

# Run automated demo
./demo_dijkstra_routing.sh

# In Mininet CLI
h1 ping h6           # Test connectivity
link s1 s2 down      # Simulate failure
h1 ping h2           # Test rerouting
```

### What You'll See
```
📦 [PACKET #1] Received on s1:1
   └── SRC: 00:00:00:00:00:01 → DST: 00:00:00:00:00:06
   └── 🛤️  Using DIJKSTRA PATH: s1 → s2 → s3 → s4 → s5 → s6
   └── 🎯 Next hop: s2 via port 2
   └── 📊 Path length: 5 hops
```

---

## 🔍 Core Concepts

### OpenFlow vs LLDP

These are **completely different protocols** working together:

| Aspect | OpenFlow | LLDP |
|--------|----------|------|
| **Purpose** | Control switches | Discover topology |
| **Layer** | L4 (TCP 6633/6653) | L2 (Ethernet 0x88cc) |
| **Direction** | Bidirectional | Unidirectional |
| **Messages** | FLOW_MOD, PACKET_IN/OUT | Advertisement only |

### How They Work Together

#### 1️⃣ **Startup Phase**
```bash
ryu-manager --observe-links controller.py
            ↑                    ↑
        Enable LLDP        OpenFlow controller
```

#### 2️⃣ **LLDP: Building the Map**
```
Every 5 seconds:
s1:port2 → [LLDP packet] → s2:port3 → PACKET_IN → Controller
                                            ↓
                              "Link discovered: s1:2 ↔ s2:3"
```

LLDP discovers the network structure automatically:
- Sends probe packets through all ports
- Learns which switches are connected
- Updates topology graph in controller

#### 3️⃣ **OpenFlow: Controlling Traffic**
```python
# When h1 pings h6:
1. s1 → Controller: "Unknown packet!" (PACKET_IN)
2. Controller: "Let me check LLDP topology..."
3. Controller: "Path is s1→s2→s3→s4→s5→s6"
4. Controller → s1: "Send to port 2" (FLOW_MOD)
```

#### 4️⃣ **Working Example**
```
Time 0s: Controller starts
├─ OpenFlow: Switches connect (s1...s10)
└─ LLDP: Start topology discovery

Time 5s: Topology ready
├─ LLDP: "Found 20 links (10 physical × 2 directions)"
└─ Controller: Builds NetworkX graph

Time 10s: h1 pings h6
├─ OpenFlow: s1 sends PACKET_IN
├─ Controller: Uses LLDP topology for Dijkstra
├─ OpenFlow: Installs flows with FLOW_MOD
└─ Result: Ping success!

Time 15s: Link s1-s2 fails
├─ OpenFlow: PORT_STATUS event (immediate)
├─ LLDP: Removes link from topology
├─ Next packet: Rerouted via s1→s10→s9→...→s2
```

---

## 💻 Implementation Details

### Dijkstra Routing

#### Path Calculation
```python
def calculate_shortest_path(self, src_dpid, dst_dpid):
    """Uses NetworkX with LLDP-discovered topology"""
    try:
        # NetworkX Dijkstra on LLDP topology
        path = nx.shortest_path(
            self.topology_graph,  # Built from LLDP
            src_dpid, 
            dst_dpid,
            weight='weight'
        )
        
        path_str = " → ".join([f"s{s}" for s in path])
        print(f"   └── 🛤️  DIJKSTRA PATH: {path_str}")
        return path
        
    except nx.NetworkXNoPath:
        print(f"   └── ❌ No path exists")
        return None
```

#### Packet Processing Flow
```python
@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
def packet_in_handler(self, ev):
    # 1. Check packet type
    if eth.ethertype == 0x88cc:  # LLDP
        return  # Let Ryu handle it
    
    # 2. Learn host location
    self.learn_host_location(dpid, src_mac, in_port)
    
    # 3. Calculate path using LLDP topology
    if dst_mac in self.host_locations:
        path = self.calculate_shortest_path(dpid, dst_dpid)
        
        # 4. Install flow with OpenFlow
        self.install_path_flow(datapath, src_mac, dst_mac, out_port)
        
        # 5. Forward packet
        self.forward_packet(datapath, msg, out_port)
```

### Link Failure & Rerouting

#### Detection Methods

**1. OpenFlow PORT_STATUS (Immediate)**
```python
@set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
def port_status_handler(self, ev):
    if port.state == 1:  # OFPPS_LINK_DOWN
        print(f"🔴 [PORT EVENT] Link down on s{dpid}:{port_no}")
```

**2. LLDP Timeout (Slower)**
```python
# No LLDP for 120s = link dead
@set_ev_cls(event.EventLinkDelete)
def link_delete_handler(self, ev):
    self.topology_graph.remove_edge(src_dpid, dst_dpid)
```

#### Rerouting Example
```
Before failure (h1 → h2):
Path: s1 → s2 (1 hop)

After s1-s2 link fails:
🔴 [PORT EVENT] Port 2 LINK_DOWN on s1
📊 [TOPOLOGY] Links: 18 (was 20)
🛤️  NEW PATH: s1 → s10 → s9 → s8 → s7 → s6 → s5 → s4 → s3 → s2 (9 hops)
✅ Connectivity maintained!
```

### STP for Loop Prevention

#### Why Needed in Ring?
```
Without STP: Broadcast → s1 → s2 → ... → s10 → s1 → ... (infinite loop!)
With STP: One link blocked, creating tree structure
```

#### Two Controller Versions

**main_controller.py (No STP)**
- Simple flooding
- Risk of broadcast storms
- Works due to flow tables and MAC learning

**main_controller_stp.py (With STP)**
```python
# Three protection mechanisms:
self.blocked_ports = set()           # Block redundant links
self.broadcast_cache = deque(1000)   # Prevent duplicates
self.spanning_tree = nx.minimum_spanning_tree(graph)

# Block packets on redundant ports
if (dpid, in_port) in self.blocked_ports:
    return  # Drop packet
```

#### STP in Action
```
Original Ring:
s1 -- s2 -- s3 -- s4 -- s5
|                         |
s10 - s9 -- s8 -- s7 -- s6

After STP (s10→s1 blocked):
s1 -- s2 -- s3 -- s4 -- s5
                          |
s10 - s9 -- s8 -- s7 -- s6
     🚫 (blocked port)
```

---

## ⚙️ Configuration

### Mininet Settings
```python
net = Mininet(
    controller=RemoteController,
    switch=OVSKernelSwitch,      # Open vSwitch
    link=TCLink,                  # Traffic control
    autoSetMacs=True              # Auto MAC assignment
)

# Port conventions:
# Port 1: Always host connection
# Port 2-3: Inter-switch links
```

### Controller Startup
```bash
# Basic version
ryu-manager --observe-links ryu-controller/main_controller.py

# STP version (recommended for ring)
ryu-manager --observe-links ryu-controller/main_controller_stp.py
```

Key flags:
- `--observe-links`: Enables LLDP topology discovery
- Without this, no automatic topology detection!

---

## 📊 Testing & Monitoring

### Key Log Messages
```
🔌 [OPENFLOW] Switch connected      # OpenFlow handshake
🔗 [LINK UP] s1:2 ↔ s2:3           # LLDP discovery
📦 [PACKET #1] Received             # OpenFlow PACKET_IN
🛤️  Using DIJKSTRA PATH            # Path calculation
📝 [FLOW #1] Installed              # OpenFlow FLOW_MOD
🔴 [PORT EVENT] Link down           # Failure detection
```

### Monitoring Commands
```bash
# Watch controller logs
tmux attach -t sdn_demo

# Filter specific events
tmux capture-pane -p | grep "DIJKSTRA"

# In Mininet CLI
dpctl dump-flows     # Check installed flows
links                 # Show topology
```

### Test Scenarios
```bash
# 1. Basic connectivity
h1 ping h6

# 2. Link failure
link s1 s2 down
h1 ping h2  # Should work via alternate path

# 3. Recovery
link s1 s2 up
h1 ping h2  # Back to optimal path

# 4. Broadcast storm test (STP version)
h1 ping -b 10.0.0.255  # Should not loop
```

---

## 🐛 Troubleshooting

### Common Issues

**Ping doesn't work:**
1. Check controller: `ps aux | grep ryu`
2. Verify LLDP: Look for "Links discovered" in logs
3. Check flows: `dpctl dump-flows`

**No topology discovery:**
- Did you use `--observe-links`?
- Wait 5-10 seconds for LLDP
- Check for "🔗 [LINK UP]" messages

**Broadcast storms (ring topology):**
- Use `main_controller_stp.py` instead
- Check for "🌳 [STP] Spanning tree computed"

**Link failure not detected:**
- OpenFlow detects immediately
- LLDP takes up to 120s
- Check "🔴 [PORT EVENT]" logs

### Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| LLDP interval | 5s | Topology refresh rate |
| Path calculation | <1ms | 10-switch topology |
| Rerouting time | ~3s | Detection + recalculation |
| Flow timeout | 30s | Adapts to changes |

---

## 📝 Summary

This implementation combines:
- **LLDP** for automatic topology discovery (the "map")
- **OpenFlow** for switch control (the "driver")
- **Dijkstra** for optimal path calculation
- **STP** for loop prevention in ring topology

Together, they create a robust SDN system with automatic failure recovery!

### Key Takeaways
1. LLDP and OpenFlow are different but work together
2. LLDP discovers topology, OpenFlow controls switches
3. Dijkstra uses LLDP topology for path calculation
4. STP prevents broadcast storms in ring topology
5. Link failures trigger automatic rerouting

### Commands Reference
```bash
# Start
./start_sdn_demo.sh ring

# Test
h1 ping h6
link s1 s2 down
pingall

# Monitor
tmux attach -t sdn_demo
```