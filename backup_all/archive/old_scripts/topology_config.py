"""
Unified topology configuration for 10-switch network
This file defines the exact topology used by both controller and Mininet
"""

# 10-Switch Graph Topology Definition
# Using a more structured approach with clear port assignments

TOPOLOGY_LINKS = [
    # Format: (switch1, switch2, port_on_sw1, port_on_sw2)
    # Horizontal connections (Row 1: s1-s2-s3)
    (1, 2, 2, 2),  # s1:2 <-> s2:2
    (2, 3, 3, 2),  # s2:3 <-> s3:2
    
    # Horizontal connections (Row 2: s4-s5-s6)
    (4, 5, 2, 2),  # s4:2 <-> s5:2
    (5, 6, 3, 2),  # s5:3 <-> s6:2
    
    # Horizontal connections (Row 3: s7-s8-s9)
    (7, 8, 2, 2),  # s7:2 <-> s8:2
    (8, 9, 3, 2),  # s8:3 <-> s9:2
    
    # Vertical connections (Column 1: s1-s4-s7)
    (1, 4, 3, 3),  # s1:3 <-> s4:3
    (4, 7, 4, 3),  # s4:4 <-> s7:3
    
    # Vertical connections (Column 2: s2-s5-s8)
    (2, 5, 4, 4),  # s2:4 <-> s5:4
    (5, 8, 5, 3),  # s5:5 <-> s8:3
    
    # Vertical connections (Column 3: s3-s6-s9)
    (3, 6, 3, 3),  # s3:3 <-> s6:3
    (6, 9, 4, 3),  # s6:4 <-> s9:3
    
    # Diagonal connections for redundancy
    (1, 5, 4, 6),  # s1:4 <-> s5:6 (diagonal)
    (5, 9, 7, 4),  # s5:7 <-> s9:4 (diagonal)
    (2, 6, 5, 5),  # s2:5 <-> s6:5 (cross)
    (4, 8, 5, 4),  # s4:5 <-> s8:4 (cross)
    
    # Connect s10 to center of network
    (5, 10, 8, 2),  # s5:8 <-> s10:2 (s10 connected to central s5)
]

# Visual representation of the topology
TOPOLOGY_DIAGRAM = """
    Grid Layout (3x3 + 1):
    
         s1 --- s2 --- s3
         |  \\   |   /  |
         |    \\ | /    |
         s4 --- s5 --- s6
         |    / | \\    |
         |  /   |   \\  |
         s7 --- s8 --- s9
                |
               s10
               
    - Horizontal links: Direct connections in rows
    - Vertical links: Direct connections in columns  
    - Diagonal links: Cross connections for redundancy
    - s10: Connected to central switch s5
"""

def get_topology_links():
    """Return the topology links configuration"""
    return TOPOLOGY_LINKS

def get_host_connections():
    """Return host to switch connections (host on port 1 of each switch)"""
    return [(i, 1) for i in range(1, 11)]  # Each host i connects to switch i on port 1