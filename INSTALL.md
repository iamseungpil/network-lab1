# Installation Guide for SDN Dual Controller

## Prerequisites

- Ubuntu 20.04 or later
- Python 3.8 (recommended)
- Mininet 2.3.0+
- Open vSwitch

## Quick Setup

### 1. Install System Dependencies

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Mininet and Open vSwitch
sudo apt-get install -y mininet openvswitch-switch

# Install Python development tools
sudo apt-get install -y python3-pip python3-dev build-essential

# Install network tools
sudo apt-get install -y net-tools tmux
```

### 2. Setup Conda Environment (Recommended)

```bash
# Install Miniconda if not installed
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

# Create environment from file
conda env create -f environment.yml

# Activate environment
conda activate sdn-env
```

### 3. Alternative: Install with pip

```bash
# Create virtual environment
python3.8 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
# Check RYU version
ryu-manager --version  # Should show 4.34

# Check Python version
python --version  # Should be 3.8.x

# Test Mininet
sudo mn --test pingall
```

## Running the Demos

### Basic Demo (8 Test Scenarios)
```bash
./cleanup_network.sh
./demo_all.sh auto
```

### Dijkstra Algorithm Demo
```bash
./cleanup_network.sh
./demo_dijkstra.sh auto
```

## Troubleshooting

### Issue: eventlet TypeError with Python 3.10+
**Solution**: Use Python 3.8 with eventlet 0.30.2
```bash
conda activate sdn-env
```

### Issue: RTNETLINK answers: File exists
**Solution**: Clean up network interfaces
```bash
./cleanup_network.sh
sudo mn -c
```

### Issue: Unable to contact remote controller
**Solution**: Check if controllers are running
```bash
netstat -ln | grep -E "6633|6634"
tmux ls
```

### Issue: ModuleNotFoundError: No module named 'mininet'
**Solution**: Add system Python paths (already included in scripts)
```python
sys.path.extend([
    '/usr/lib/python3/dist-packages',
    '/usr/local/lib/python3.8/dist-packages'
])
```

## Environment Variables

Optional configuration:
```bash
export RYU_APP_LISTS=/home/ubuntu/network-lab1/ryu-controller
export PYTHONPATH=/home/ubuntu/network-lab1:$PYTHONPATH
```

## Testing

Run all tests:
```bash
# Full system test
./demo_all.sh auto

# Watch controller logs
tmux attach -t dual_controllers:0  # Primary
tmux attach -t dual_controllers:1  # Secondary
```

## Cleanup

To completely clean the environment:
```bash
./cleanup_network.sh
tmux kill-server  # Kill all tmux sessions
sudo mn -c        # Clean Mininet
```