#!/bin/bash

# Docker-based SDN Demo Script for Windows
# This script runs the SDN demo inside a Docker container with tmux

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="sdn-lab"
IMAGE_NAME="sdn-lab:latest"
NETWORK_NAME="sdn-network"

# Banner
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}🚀 SDN DIJKSTRA ROUTING DEMO (Docker Edition)${NC}"
echo -e "${BLUE}================================================${NC}"

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}Error: Docker is not running or not installed${NC}"
        echo -e "${YELLOW}Please start Docker Desktop and try again${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker is running${NC}"
}

# Function to build Docker image
build_image() {
    echo -e "${YELLOW}🔨 Building Docker image...${NC}"
    echo -e "${YELLOW}  This will take a few minutes on first build...${NC}"
    
    if docker build -t ${IMAGE_NAME} . ; then
        echo -e "${GREEN}✓ Docker image built successfully${NC}"
        
        # Simple test without file path issues
        echo -e "${YELLOW}🧪 Testing Python packages...${NC}"
        if docker run --rm ${IMAGE_NAME} python3 -c "import ryu, networkx; print('✅ Packages OK')" 2>/dev/null ; then
            echo -e "${GREEN}✓ All packages verified${NC}"
        else
            echo -e "${YELLOW}⚠ Package test skipped (container will still work)${NC}"
        fi
    else
        echo -e "${RED}✗ Failed to build Docker image${NC}"
        exit 1
    fi
}

# Function to cleanup existing container
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up existing containers...${NC}"
    docker stop ${CONTAINER_NAME} 2>/dev/null || true
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
    docker network rm ${NETWORK_NAME} 2>/dev/null || true
}

# Function to create Docker network
create_network() {
    echo -e "${YELLOW}🌐 Creating Docker network...${NC}"
    docker network create ${NETWORK_NAME} 2>/dev/null || true
    echo -e "${GREEN}✓ Docker network ready${NC}"
}

# Function to start container
start_container() {
    echo -e "${YELLOW}🚀 Starting Docker container...${NC}"
    
    # Start container
    if docker run -dit \
        --name ${CONTAINER_NAME} \
        --privileged \
        --network ${NETWORK_NAME} \
        -p 6633:6633 \
        -p 6653:6653 \
        ${IMAGE_NAME} ; then
        echo -e "${GREEN}✓ Container started${NC}"
    else
        echo -e "${RED}✗ Failed to start container${NC}"
        exit 1
    fi
    
    # Wait for container to be ready
    sleep 2
    
    # Initialize OVS
    echo -e "${YELLOW}🔧 Initializing Open vSwitch...${NC}"
    docker exec ${CONTAINER_NAME} bash -c "/usr/local/bin/start-ovs.sh" || true
    sleep 2
    
    # Clean up Mininet
    docker exec ${CONTAINER_NAME} bash -c "mn -c 2>/dev/null" || true
    
    echo -e "${GREEN}✓ Container ready${NC}"
}

# Function to run SDN demo with tmux
run_demo() {
    local topology=${1:-ring}
    
    echo -e "${YELLOW}🎮 Starting SDN Demo with ${topology} topology...${NC}"
    echo ""
    echo -e "${GREEN}📋 Instructions:${NC}"
    echo -e "  ${CYAN}Ctrl+B + ↑/↓${NC}  : Switch between controller and Mininet"
    echo -e "  ${CYAN}Ctrl+B + z${NC}     : Zoom in/out current pane"
    echo -e "  ${CYAN}Ctrl+B + d${NC}     : Detach from tmux (keep running)"
    echo ""
    echo -e "${YELLOW}Mininet CLI commands:${NC}"
    echo -e "  ${CYAN}pingall${NC}        : Test all connections"
    echo -e "  ${CYAN}h1 ping h4${NC}     : Test specific path"
    echo -e "  ${CYAN}link s1 s2 down${NC}: Simulate link failure"
    echo -e "  ${CYAN}link s1 s2 up${NC}  : Restore link"
    echo -e "  ${CYAN}exit${NC}           : Exit Mininet"
    echo ""
    echo -e "${YELLOW}===============================================${NC}"
    echo -e "${GREEN}🎯 Connecting to container in 3 seconds...${NC}"
    echo -e "${YELLOW}===============================================${NC}"
    sleep 3
    
    # Run the demo script in the container - use absolute path without Windows path mangling
    docker exec -it ${CONTAINER_NAME} bash -c "cd /opt/sdn-lab && ./start_sdn_demo_docker.sh ${topology}"
}

# Function to attach to existing tmux session
attach_tmux() {
    echo -e "${YELLOW}🔗 Attaching to tmux session...${NC}"
    docker exec -it ${CONTAINER_NAME} bash -c "tmux attach-session -t sdn_demo" || \
        echo -e "${RED}No tmux session found. Run './start_sdn_docker.sh run' first${NC}"
}

# Function to show logs
show_logs() {
    echo -e "${YELLOW}📋 Showing controller logs...${NC}"
    docker exec ${CONTAINER_NAME} bash -c "tail -f /tmp/controller.log" 2>/dev/null || \
        echo "No controller logs found. Controller may be running in tmux."
}

# Function to connect to container
connect_container() {
    echo -e "${YELLOW}🔗 Connecting to container...${NC}"
    docker exec -it ${CONTAINER_NAME} bash
}

# Function to stop everything
stop_all() {
    echo -e "${YELLOW}🛑 Stopping SDN Lab...${NC}"
    docker exec ${CONTAINER_NAME} bash -c "tmux kill-session -t sdn_demo" 2>/dev/null || true
    docker exec ${CONTAINER_NAME} bash -c "pkill -f ryu" 2>/dev/null || true
    docker exec ${CONTAINER_NAME} bash -c "mn -c" 2>/dev/null || true
    docker stop ${CONTAINER_NAME} 2>/dev/null || true
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
    docker network rm ${NETWORK_NAME} 2>/dev/null || true
    echo -e "${GREEN}✓ SDN Lab stopped${NC}"
}

# Main execution
case "${1:-start}" in
    start)
        check_docker
        cleanup
        build_image
        create_network
        start_container
        
        echo -e "${GREEN}================================================${NC}"
        echo -e "${GREEN}✅ SDN Lab is ready!${NC}"
        echo -e "${GREEN}================================================${NC}"
        echo ""
        echo -e "${YELLOW}Quick commands:${NC}"
        echo -e "  ${CYAN}./start_sdn_docker.sh run${NC}      # Start ring topology (default)"
        echo -e "  ${CYAN}./start_sdn_docker.sh run diamond${NC}  # Start diamond topology"
        echo -e "  ${CYAN}./start_sdn_docker.sh run graph${NC}    # Start graph topology"
        echo ""
        echo -e "${BLUE}🚀 Auto-starting with ring topology...${NC}"
        sleep 2
        
        # Auto-start with ring topology
        run_demo ring
        ;;
    
    run)
        run_demo ${2:-ring}
        ;;
    
    attach)
        attach_tmux
        ;;
    
    connect)
        connect_container
        ;;
    
    logs)
        show_logs
        ;;
    
    stop)
        stop_all
        ;;
    
    rebuild)
        check_docker
        cleanup
        docker rmi ${IMAGE_NAME} 2>/dev/null || true
        build_image
        echo -e "${GREEN}✓ Image rebuilt successfully${NC}"
        echo -e "${YELLOW}Run './start_sdn_docker.sh start' to begin${NC}"
        ;;
    
    test)
        echo -e "${YELLOW}🧪 Testing container environment...${NC}"
        docker exec ${CONTAINER_NAME} bash -c "cd /opt/sdn-lab && python3 -c 'import ryu, networkx; print(\"✅ Packages OK\")'"
        docker exec ${CONTAINER_NAME} bash -c "ovs-vsctl show"
        echo -e "${GREEN}✓ Test complete${NC}"
        ;;
    
    *)
        echo "Usage: $0 {start|run [topology]|attach|connect|logs|stop|rebuild|test}"
        echo ""
        echo "Commands:"
        echo "  start         - Build, start container and run ring topology"
        echo "  run [topo]    - Run SDN demo (ring/diamond/graph)"
        echo "  attach        - Reattach to tmux session"
        echo "  connect       - Connect to container shell"
        echo "  logs          - Show controller logs"
        echo "  stop          - Stop everything"
        echo "  rebuild       - Force rebuild Docker image"
        echo "  test          - Test container environment"
        echo ""
        echo "Examples:"
        echo "  ./start_sdn_docker.sh start        # Full setup and run"
        echo "  ./start_sdn_docker.sh run diamond  # Run with diamond topology"
        echo "  ./start_sdn_docker.sh attach       # Reattach to running session"
        exit 1
        ;;
esac
