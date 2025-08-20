# SDN Ring Topology Demo Guide

## 🚀 Quick Start

```bash
# Run the complete demo
./run_demo.sh

# Clean up when done
./run_demo.sh --clean
```

## 📺 TMux Session Layout

After running the demo, you'll see:

```
┌────────────────────────────────────────────────┐
│          Controller Logs (Top - 60%)           │ ← Main observation area
├─────────────────────┬──────────────────────────┤
│   Mininet CLI       │   Scenario Monitor       │
│  (Bottom Left)      │   (Bottom Right)         │
└─────────────────────┴──────────────────────────┘
```

## 🔍 How to View Logs

### Connect to TMux Session
```bash
tmux attach -t sdn_demo
```

### Navigate Between Panes
- `Ctrl+b + 0`: Controller logs (top pane)
- `Ctrl+b + 1`: Mininet CLI (bottom-left)
- `Ctrl+b + 2`: Monitor (bottom-right)
- `Ctrl+b + arrows`: Move between panes

### Scroll Through Controller Logs
1. Select controller pane: `Ctrl+b + 0`
2. Enter scroll mode: `Ctrl+b + [`
3. Use arrow keys or Page Up/Down to scroll
4. Exit scroll mode: `q`

## 📊 What to Look For

### 1. Initial Startup (~10 seconds)
Look for these messages in controller logs:

```
================================================================================
🚀 ENHANCED SDN CONTROLLER - RING TOPOLOGY OPTIMIZED
================================================================================
⏰ Started at: [timestamp]
🔍 Features: Complete STP, Flooding Prevention, Clear Path Logs
================================================================================

🔌 [SWITCH] s1 connected
🔌 [SWITCH] s2 connected
...
🔌 [SWITCH] s10 connected

🔗 [LINK] Discovered: s1:2 ↔ s2:3
🔗 [LINK] Discovered: s2:2 ↔ s3:3
...

============================================================
📊 [TOPOLOGY] Network topology stable
   Switches: 10
   Links: 20
🌳 [STP] Computing Spanning Tree Protocol
   Active edges: 9
   Edges to block: 1
   🚫 Blocking s10:2 (to s1)
   🚫 Blocking s1:3 (to s10)
✅ [STP] Loop prevention active: 2 ports blocked
============================================================
```

### 2. Normal Routing (Test 1-2)
When h1 pings h2 or h6:

```
📍 [HOST] Learned 00:00:00:00:00:01 at s1:1
📍 [HOST] Learned 00:00:00:00:00:02 at s2:1

🧮 [DIJKSTRA] Computing path from s1 to s2
   Source: 00:00:00:00:00:01 at s1:1
   Destination: 00:00:00:00:00:02 at s2:1
   ✅ PATH SELECTED: s1 → s2
   📊 Total hops: 1
   ➡️  Next hop: s2 via port 2
   💾 Flow installed for future packets
```

### 3. Link Failure (Test 3)
When link s1-s2 goes down:

```
============================================================
💥 [LINK FAILURE DETECTED]
   Failed link: s1:2 ↔ s2:3
============================================================
🗑️  [TOPOLOGY] Removed edge from graph
🧹 [FLOW] Cleared flows on s1
🧹 [FLOW] Cleared flows on s2
🌳 [STP] Computing Spanning Tree Protocol
   Active edges: 9
   Edges to block: 0  ← No blocking needed (ring broken)
🔄 [RECOVERY] Topology updated, paths will be recalculated
============================================================
```

### 4. Rerouting After Failure
h1 ping h2 after link failure:

```
🧮 [DIJKSTRA] Computing path from s1 to s2
   Source: 00:00:00:00:00:01 at s1:1
   Destination: 00:00:00:00:00:02 at s2:1
   ✅ PATH SELECTED: s1 → s10 → s9 → s8 → s7 → s6 → s5 → s4 → s3 → s2
   📊 Total hops: 9  ← Long path around the ring!
   ➡️  Next hop: s10 via port 3
   💾 Flow installed for future packets
```

### 5. Link Recovery
When link s1-s2 comes back up:

```
🔗 [LINK] Discovered: s1:2 ↔ s2:3
🌳 [STP] Computing Spanning Tree Protocol
   Active edges: 9
   Edges to block: 1
   🚫 Blocking s10:2 (to s1)  ← Loop prevention restored
✅ [STP] Loop prevention active: 2 ports blocked
```

## 🎮 Manual Testing

While in the Mininet CLI (bottom-left pane):

### Basic Tests
```bash
# Test connectivity
h1 ping -c 3 h2    # Adjacent hosts
h1 ping -c 3 h6    # Opposite side
pingall            # All 90 host pairs

# Check topology
nodes              # List all switches and hosts
links              # Show all links
net                # Network summary
```

### Link Failure Tests
```bash
# Simulate failures
link s1 s2 down    # Break link
link s1 s2 up      # Restore link

# Multiple failures
link s3 s4 down
link s5 s6 down
# Watch how STP handles multiple breaks
```

### Advanced Tests
```bash
# Check flow tables
sh ovs-ofctl -O OpenFlow13 dump-flows s1

# Monitor specific path
h1 traceroute h6   # See actual path taken

# Continuous ping during failure
h1 ping h2 &       # Start background ping
link s1 s2 down    # Break link while pinging
# Observe packet loss and recovery
```

## 🐛 Troubleshooting

### If controller doesn't start:
1. Check conda environment: `conda activate sdn-lab`
2. Verify Ryu installation: `ryu-manager --version`
3. Check for port conflicts: `sudo netstat -tlnp | grep 6633`

### If STP isn't blocking ports:
1. Wait longer for topology discovery (10-15 seconds)
2. Check if all 10 switches connected
3. Verify ring is complete: `links` in Mininet

### If paths aren't being calculated:
1. Ensure hosts have pinged at least once (MAC learning)
2. Check controller logs for errors
3. Verify topology graph is connected

### To see more details:
1. Enter controller pane: `Ctrl+b + 0`
2. Scroll up: `Ctrl+b + [` then Page Up
3. Look for startup messages and STP computation

## 📈 Expected Performance

- **STP Computation**: Within 3 seconds of topology stability
- **Link Failure Detection**: < 2 seconds
- **Path Recalculation**: Immediate after failure detection
- **Flow Installation**: < 100ms
- **Packet Loss**: 0-3 packets during rerouting

## 🔄 Cleanup

Always clean up after testing:
```bash
./run_demo.sh --clean
```

This will:
- Kill tmux session
- Stop controller and Mininet
- Clean up virtual networks
- Free up resources