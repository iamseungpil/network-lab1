# Dual Controller SDN with Link Failure Demo

Advanced SDN demonstration with dual controllers managing separate network domains, featuring Dijkstra shortest path routing and cross-domain communication with automatic rerouting on link failures.

## Quick Start

**NEW: Use Conda Environment for Compatibility**
```bash
# Recommended (with conda environment)
./demo_conda.sh

# Alternative (if RYU is already installed)
./demo_all.sh
```

## File Structure

### Essential Files:
- `demo_all.sh` - Complete automated dual controller demonstration
- `start_dual_controllers.sh` - Start primary & secondary controllers
- `link_failure_test.py` - Cross-domain link failure test script  
- `ryu-controller/primary_controller.py` - Primary domain controller (s1-s5)
- `ryu-controller/secondary_controller.py` - Secondary domain controller (s6-s10)
- `mininet/dijkstra_graph_topo.py` - Dual controller network topology

### Alternative Demos:
- `demo_dijkstra.sh` - Interactive demonstration
- `stop_sdn.sh` - Cleanup script

## What the Demo Shows

1. **Dual Controller Architecture**: Primary (s1-s5) & Secondary (s6-s10) domains
2. **Cross-Domain Communication**: Gateway-based routing between controller domains
3. **Dijkstra Routing**: Shortest path calculation within and across domains
4. **Link Failure Detection**: OpenFlow PORT_STATUS event handling
5. **Advanced Rerouting**: Intra-domain and cross-domain path recalculation
6. **Network Recovery**: Optimal path restoration when links recover

## Network Topology

10-switch dual controller topology with cross-domain gateways:
- **Primary Domain**: s1-s5 managing h1-h10
- **Secondary Domain**: s6-s10 managing h11-h20
- **Cross-Domain Links**: s3↔s6, s3↔s7, s4↔s8, s4↔s9, s5↔s10
- **Total**: 10 switches, 20 hosts with fault-tolerant routing

## Manual Testing

After running the demo, you can test manually:
```bash
# In Mininet CLI:
net.configLinkStatus("s1", "s2", "down")  # Break link
h1 ping h8                                 # Test connectivity  
net.configLinkStatus("s1", "s2", "up")    # Restore link
```

All unnecessary backup files and duplicate controllers have been removed for simplicity.

## Installation & Setup

### Method 1: Conda Environment (Recommended)
```bash
# Create conda environment with Python 3.8
conda create -n sdn-env python=3.8 -y
conda activate sdn-env

# Install compatible versions
pip install setuptools==57.5.0
pip install eventlet==0.30.2
pip install ryu networkx

# Install system dependencies  
sudo apt-get install mininet openvswitch-switch

# Run demo
./demo_conda.sh
```

### Method 2: System Installation
```bash
# Install dependencies
sudo apt-get install mininet openvswitch-switch python3-pip
pip3 install ryu

# May have eventlet compatibility issues with newer Python versions

# Run demo
./demo_all.sh
```

## Environment Details

**Working Configuration:**
- Python 3.8.20
- RYU 4.34
- eventlet 0.30.2  
- setuptools 57.5.0
- Mininet 2.3.0+