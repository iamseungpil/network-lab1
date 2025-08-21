# Dockerfile for SDN Lab with Mininet, Ryu, and Open vSwitch
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Seoul
ENV EVENTLET_NO_GREENDNS=yes

# Update and install basic packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    gcc \
    make \
    git \
    wget \
    curl \
    net-tools \
    iputils-ping \
    iproute2 \
    iptables \
    tmux \
    vim \
    nano \
    sudo \
    software-properties-common \
    build-essential \
    psmisc \
    lsb-release \
    dbus \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Install Open vSwitch
RUN apt-get update && apt-get install -y \
    openvswitch-switch \
    openvswitch-common \
    && rm -rf /var/lib/apt/lists/*

# Install Mininet
RUN apt-get update && apt-get install -y \
    mininet \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install --upgrade pip && \
    pip3 install setuptools==65.5.0 wheel && \
    pip3 install eventlet==0.33.0 && \
    pip3 install dnspython && \
    pip3 install greenlet && \
    pip3 install msgpack && \
    pip3 install oslo.config && \
    pip3 install ovs && \
    pip3 install pbr && \
    pip3 install Routes && \
    pip3 install six && \
    pip3 install tinyrpc && \
    pip3 install WebOb && \
    pip3 install networkx && \
    pip3 install ryu

# Patch Ryu for eventlet 0.33 compatibility
RUN sed -i 's/from eventlet.wsgi import ALREADY_HANDLED/ALREADY_HANDLED = None  # Patched for eventlet 0.33+/g' \
    /usr/local/lib/python3.10/dist-packages/ryu/app/wsgi.py || true && \
    sed -i 's/class _AlreadyHandledResponse(Response):/class _AlreadyHandledResponse(Response):\n    ALREADY_HANDLED = None  # Patched/g' \
    /usr/local/lib/python3.10/dist-packages/ryu/app/wsgi.py || true

# Create working directory
WORKDIR /opt/sdn-lab

# Create necessary directories for OVS
RUN mkdir -p /var/run/openvswitch /var/log/openvswitch /etc/openvswitch

# Create OVS startup script
RUN echo '#!/bin/bash' > /usr/local/bin/start-ovs.sh && \
    echo 'mkdir -p /var/run/openvswitch /var/log/openvswitch /etc/openvswitch' >> /usr/local/bin/start-ovs.sh && \
    echo 'if [ ! -f /etc/openvswitch/conf.db ]; then' >> /usr/local/bin/start-ovs.sh && \
    echo '    ovsdb-tool create /etc/openvswitch/conf.db /usr/share/openvswitch/vswitch.ovsschema' >> /usr/local/bin/start-ovs.sh && \
    echo 'fi' >> /usr/local/bin/start-ovs.sh && \
    echo 'ovsdb-server --remote=punix:/var/run/openvswitch/db.sock --remote=db:Open_vSwitch,Open_vSwitch,manager_options --pidfile --detach --log-file' >> /usr/local/bin/start-ovs.sh && \
    echo 'ovs-vsctl --no-wait init' >> /usr/local/bin/start-ovs.sh && \
    echo 'ovs-vswitchd --pidfile --detach --log-file' >> /usr/local/bin/start-ovs.sh && \
    echo 'echo "OVS started successfully"' >> /usr/local/bin/start-ovs.sh && \
    echo 'ovs-vsctl show' >> /usr/local/bin/start-ovs.sh && \
    chmod +x /usr/local/bin/start-ovs.sh

# Copy project files
COPY . /opt/sdn-lab/

# Create wrapper script for Ryu with compatibility fixes
RUN echo '#!/usr/bin/env python3' > /opt/sdn-lab/ryu_runner.py && \
    echo 'import sys' >> /opt/sdn-lab/ryu_runner.py && \
    echo 'import os' >> /opt/sdn-lab/ryu_runner.py && \
    echo '' >> /opt/sdn-lab/ryu_runner.py && \
    echo '# Monkey patch for eventlet 0.33+ compatibility' >> /opt/sdn-lab/ryu_runner.py && \
    echo 'import eventlet' >> /opt/sdn-lab/ryu_runner.py && \
    echo 'import eventlet.wsgi' >> /opt/sdn-lab/ryu_runner.py && \
    echo 'eventlet.wsgi.ALREADY_HANDLED = None' >> /opt/sdn-lab/ryu_runner.py && \
    echo '' >> /opt/sdn-lab/ryu_runner.py && \
    echo '# Now import and run Ryu' >> /opt/sdn-lab/ryu_runner.py && \
    echo 'from ryu.cmd import manager' >> /opt/sdn-lab/ryu_runner.py && \
    echo 'sys.argv = ["ryu-manager", "--observe-links", "ryu-controller/main_controller_stp.py"]' >> /opt/sdn-lab/ryu_runner.py && \
    echo 'manager.main()' >> /opt/sdn-lab/ryu_runner.py && \
    chmod +x /opt/sdn-lab/ryu_runner.py

# Create the simplified demo script
RUN echo '#!/bin/bash' > /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'set -e' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '# Colors' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'RED="\\033[0;31m"' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'GREEN="\\033[0;32m"' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'YELLOW="\\033[1;33m"' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'BLUE="\\033[0;34m"' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'CYAN="\\033[0;36m"' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'NC="\\033[0m"' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'echo -e "${BLUE}================================================${NC}"' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'echo -e "${BLUE}🚀 SDN DIJKSTRA ROUTING DEMO${NC}"' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'echo -e "${BLUE}================================================${NC}"' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'TOPOLOGY=${1:-ring}' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '# Cleanup' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'echo -e "${YELLOW}Cleaning up...${NC}"' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'tmux kill-session -t sdn_demo 2>/dev/null || true' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'pkill -f ryu 2>/dev/null || true' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'mn -c 2>/dev/null || true' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '# Start OVS if needed' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'if ! pgrep ovsdb-server > /dev/null; then' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '    echo -e "${YELLOW}Starting OVS...${NC}"' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '    /usr/local/bin/start-ovs.sh' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '    sleep 2' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'fi' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '# Choose topology' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'case "$TOPOLOGY" in' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '    ring) TOPO="mininet/ring_topology.py"; NAME="Ring" ;;' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '    graph) TOPO="mininet/graph_topology.py"; NAME="Graph" ;;' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '    *) TOPO="mininet/diamond_topology.py"; NAME="Diamond" ;;' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'esac' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'echo -e "${GREEN}Using $NAME topology${NC}"' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '# Create tmux session' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'tmux new-session -d -s sdn_demo' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'tmux split-window -v -t sdn_demo' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '# Start controller using wrapper' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'tmux send-keys -t sdn_demo:0.0 "cd /opt/sdn-lab && echo '"'"'=== CONTROLLER ==='"'"' && python3 ryu_runner.py" Enter' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '# Start Mininet' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'tmux send-keys -t sdn_demo:0.1 "cd /opt/sdn-lab && echo '"'"'=== MININET ==='"'"' && sleep 5 && python3 $TOPO" Enter' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '# Setup tmux' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'tmux set -t sdn_demo status on' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'tmux select-pane -t sdn_demo:0.1' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'echo -e "${GREEN}Ready!${NC}"' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'echo -e "${CYAN}Ctrl+B + ↑/↓${NC} : Switch panes"' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'echo -e "${CYAN}Ctrl+B + d${NC}   : Detach"' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'echo -e "Commands: pingall, h1 ping h4"' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'sleep 2' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo '' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    echo 'tmux attach-session -t sdn_demo' >> /opt/sdn-lab/start_sdn_demo_docker.sh && \
    chmod +x /opt/sdn-lab/start_sdn_demo_docker.sh

# Fix permissions and line endings
RUN find /opt/sdn-lab -type f \( -name "*.py" -o -name "*.sh" \) -exec dos2unix {} \; 2>/dev/null || true && \
    chmod +x /opt/sdn-lab/*.sh 2>/dev/null || true && \
    chmod +x /opt/sdn-lab/*.py 2>/dev/null || true && \
    chmod +x /opt/sdn-lab/mininet/*.py 2>/dev/null || true && \
    chmod +x /opt/sdn-lab/ryu-controller/*.py 2>/dev/null || true

# Expose ports
EXPOSE 6633 6653

# Default command
CMD ["/bin/bash"]
