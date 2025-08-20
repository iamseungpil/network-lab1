#!/bin/bash

# Fixed Dual Controller Test Script
# Ensures proper cleanup and controller startup timing

echo "=== Dual Controller Test (Fixed) ==="

# Function to check if port is open
wait_for_port() {
    local port=$1
    local max_wait=30
    local count=0
    
    echo "Waiting for port $port to be ready..."
    while [ $count -lt $max_wait ]; do
        if netstat -ln | grep ":$port " > /dev/null; then
            echo "✓ Port $port is ready"
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    echo "✗ Port $port not ready after $max_wait seconds"
    return 1
}

# Step 1: Complete cleanup
echo "Step 1: Complete cleanup..."
sudo mn -c 2>/dev/null
sudo pkill -f ryu-manager 2>/dev/null
sudo pkill -f python3 2>/dev/null
tmux kill-session -t dual_controllers 2>/dev/null
sleep 3

# Step 2: Start controllers in background
echo "Step 2: Starting controllers..."

# Start primary controller
echo "Starting primary controller (port 6633)..."
ryu-manager --ofp-tcp-listen-port 6633 ryu-controller/primary_controller.py &
PRIMARY_PID=$!
sleep 2

# Start secondary controller  
echo "Starting secondary controller (port 6634)..."
ryu-manager --ofp-tcp-listen-port 6634 ryu-controller/secondary_controller.py &
SECONDARY_PID=$!
sleep 3

# Step 3: Wait for controllers to be ready
echo "Step 3: Waiting for controllers..."
if ! wait_for_port 6633; then
    echo "ERROR: Primary controller failed to start"
    kill $PRIMARY_PID $SECONDARY_PID 2>/dev/null
    exit 1
fi

if ! wait_for_port 6634; then
    echo "ERROR: Secondary controller failed to start"
    kill $PRIMARY_PID $SECONDARY_PID 2>/dev/null
    exit 1
fi

echo "✓ Both controllers are ready"

# Step 4: Run test
echo "Step 4: Running dual controller test..."
sudo python3 link_failure_test.py

# Step 5: Cleanup
echo "Step 5: Cleaning up..."
kill $PRIMARY_PID $SECONDARY_PID 2>/dev/null
sudo mn -c 2>/dev/null

echo "=== Test Complete ==="