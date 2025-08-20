# SDN Ring Topology with Dijkstra Routing

## 🚀 Quick Start

```bash
# Run complete demo
./run_demo.sh

# Clean up
./run_demo.sh --clean
```

## 📋 Features

- **10-switch ring topology** with STP loop prevention
- **Dijkstra shortest path** routing with clear logs
- **Link failure recovery** with automatic rerouting
- **Packet flooding prevention** (3-layer defense)
- **Real-time monitoring** via tmux 3-pane layout

## 📁 Project Structure

```
network-lab1/
├── run_demo.sh                    # Main demo script (USE THIS!)
├── ryu-controller/
│   └── enhanced_controller.py     # Complete SDN controller
├── mininet/
│   └── ring_topology.py          # 10-switch ring topology
├── docs/                         # Documentation
│   └── IMPLEMENTATION_ANALYSIS.md # Detailed analysis
└── scripts/                      # Additional scripts
```

## 🎯 What You'll See

### Normal Operation
- STP blocks one link to prevent loops
- Dijkstra calculates shortest paths
- Clear path logs: `s1 → s2 → s3 → s4 → s5`

### Link Failure
```
💥 [LINK FAILURE DETECTED]
   Failed link: s1:2 ↔ s2:3
🔄 [RECOVERY] Topology updated, paths will be recalculated
🧮 [DIJKSTRA] Computing path from s1 to s2
   ✅ PATH SELECTED: s1 → s10 → s9 → ... → s3 → s2
```

## 📊 TMux Layout

```
┌────────────────────────────────┐
│     Controller Logs (60%)      │  ← Watch here!
├─────────────┬──────────────────┤
│ Mininet CLI │ Monitor (20%)    │
└─────────────┴──────────────────┘
```

## 🔧 Requirements

- Ubuntu 22.04
- Python 3.9 (conda environment: `sdn-lab`)
- Mininet 2.3.0+
- Ryu 4.34
- tmux

## 📚 Documentation

See `docs/IMPLEMENTATION_ANALYSIS.md` for:
- Detailed implementation analysis
- STP and flooding prevention mechanisms
- Complete scenario walkthrough
- Performance metrics

## 🎮 Manual Testing

After running `./run_demo.sh`, connect to tmux:
```bash
tmux attach -t sdn_demo
```

Test commands in Mininet (Pane 1):
```
h1 ping h6          # Test long path
link s1 s2 down     # Simulate failure
link s1 s2 up       # Recover link
pingall             # Test all paths
```

## 👀 Key Observations

1. **STP in action**: One port blocked at startup
2. **Path calculation**: Full path shown for each flow
3. **Link failure**: Immediate detection and rerouting
4. **No flooding**: Broadcasts controlled by STP

## 📈 Performance

- Link failure detection: < 2 seconds
- Path recalculation: Immediate
- STP convergence: ~3 seconds
- Packet loss: 0% (with buffering)