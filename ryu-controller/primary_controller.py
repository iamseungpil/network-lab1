"""
Primary Controller for Dual-Controller SDN with Dijkstra Routing
Manages switches s1-s5 and handles cross-domain communication
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, arp, ipv4
import networkx as nx
import logging

class PrimaryController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(PrimaryController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.topology = self._build_topology()
        self.switches = set()
        # Cross-controller communication can be added later if needed
        
        # Domain configuration
        self.my_switches = {1, 2, 3, 4, 5}  # s1-s5
        self.gateway_switches = {3, 4, 5}   # Can communicate with secondary
        
        # Host mapping (MAC addresses)
        self.primary_hosts = set(f"00:00:00:00:00:{i:02x}" for i in range(1, 11))  # h1-h10
        
        logging.basicConfig(level=logging.INFO)
        self.logger.info("[PRIMARY] Controller started - managing s1-s5")

    def _build_topology(self):
        """Build network topology graph"""
        G = nx.Graph()
        
        # Add nodes (switches 1-10)
        for i in range(1, 11):
            G.add_node(i)
        
        # Primary domain topology (s1-s5)
        edges = [
            (1, 2, 1), (1, 3, 1),  # s1 connections
            (2, 4, 1), (2, 5, 1),  # s2 connections  
            (3, 6, 2), (3, 7, 2),  # s3 to secondary (cross-domain)
            (4, 8, 2), (4, 9, 2),  # s4 to secondary (cross-domain)
            (5, 10, 2)             # s5 to secondary (cross-domain)
        ]
        
        for src, dst, weight in edges:
            G.add_edge(src, dst, weight=weight)
            
        return G

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch connection"""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        
        if dpid in self.my_switches:
            self.switches.add(dpid)
            self.logger.info(f"[PRIMARY] Switch s{dpid} connected")
            
            # Install table-miss flow entry
            match = parser.OFPMatch()
            actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                            ofproto.OFPCML_NO_BUFFER)]
            self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """Add flow entry to switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                  priority=priority, match=match, instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                  match=match, instructions=inst)
        datapath.send_msg(mod)

    def _dijkstra_path(self, src, dst):
        """Calculate shortest path using Dijkstra algorithm"""
        self.logger.info(f"[PRIMARY][DIJKSTRA] Computing path from s{src} to s{dst}")
        try:
            if self.topology.has_node(src) and self.topology.has_node(dst):
                # Calculate all possible paths for comparison
                all_paths = list(nx.all_simple_paths(self.topology, src, dst, cutoff=5))
                self.logger.info(f"[PRIMARY][DIJKSTRA] Found {len(all_paths)} possible paths")
                
                # Calculate shortest path using Dijkstra
                path = nx.shortest_path(self.topology, src, dst, weight='weight')
                cost = nx.shortest_path_length(self.topology, src, dst, weight='weight')
                
                # Log the chosen path
                path_str = " -> ".join([f"s{node}" for node in path])
                self.logger.info(f"[PRIMARY][DIJKSTRA] ✓ OPTIMAL PATH: {path_str} (cost={cost})")
                
                # Log alternative paths for comparison
                for i, alt_path in enumerate(all_paths[:3]):  # Show up to 3 alternatives
                    if alt_path != path:
                        alt_cost = sum(self.topology[alt_path[j]][alt_path[j+1]].get('weight', 1) 
                                     for j in range(len(alt_path)-1))
                        alt_str = " -> ".join([f"s{node}" for node in alt_path])
                        self.logger.info(f"[PRIMARY][DIJKSTRA]   Alternative {i+1}: {alt_str} (cost={alt_cost})")
                
                return path, cost
        except nx.NetworkXNoPath:
            self.logger.error(f"[PRIMARY][DIJKSTRA] ✗ NO PATH found from s{src} to s{dst}")
        except Exception as e:
            self.logger.error(f"[PRIMARY][DIJKSTRA] Error: {e}")
        return None, float('inf')

    def _get_next_hop_port(self, current_switch, next_switch):
        """Get output port for next hop"""
        # Port mapping based on topology
        port_map = {
            1: {2: 3, 3: 4},           # s1: s2->port3, s3->port4
            2: {1: 3, 4: 4, 5: 5},     # s2: s1->port3, s4->port4, s5->port5
            3: {1: 3, 6: 4, 7: 5},     # s3: s1->port3, s6->port4, s7->port5
            4: {2: 3, 8: 4, 9: 5},     # s4: s2->port3, s8->port4, s9->port5
            5: {2: 3, 10: 4}           # s5: s2->port3, s10->port4
        }
        return port_map.get(current_switch, {}).get(next_switch, None)

    def _is_cross_domain_dst(self, dst_mac):
        """Check if destination is in secondary domain"""
        return dst_mac not in self.primary_hosts

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """Handle packet-in messages"""
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id
        
        if dpid not in self.my_switches:
            return
            
        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocols(ethernet.ethernet)[0]
        
        if eth_pkt.ethertype == ether_types.ETH_TYPE_LLDP:
            return
            
        dst_mac = eth_pkt.dst
        src_mac = eth_pkt.src
        
        self.logger.info(f"[PRIMARY] Packet: {src_mac} -> {dst_mac} on s{dpid}:{in_port}")
        
        # Learn source MAC
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src_mac] = in_port
        
        # Determine output port
        if dst_mac in self.mac_to_port.get(dpid, {}):
            # Known local destination
            out_port = self.mac_to_port[dpid][dst_mac]
            self.logger.info(f"[PRIMARY] Local forwarding s{dpid}: {src_mac}->{dst_mac} via port {out_port}")
        elif self._is_cross_domain_dst(dst_mac):
            # Cross-domain communication
            if dpid in self.gateway_switches:
                # Use appropriate gateway port
                if dpid == 3:
                    out_port = 4 if dst_mac.endswith(('0b', '0c', '0d', '0e')) else 5  # s6 or s7
                elif dpid == 4:
                    out_port = 4 if dst_mac.endswith(('0f', '10', '11', '12')) else 5  # s8 or s9
                elif dpid == 5:
                    out_port = 4  # s10
                else:
                    out_port = ofproto.OFPP_FLOOD
                    
                self.logger.info(f"[PRIMARY] Cross-domain: s{dpid} -> Secondary via port {out_port}")
            else:
                # Route to gateway
                path, cost = self._dijkstra_path(dpid, 3)  # Route to s3 as default gateway
                if path and len(path) > 1:
                    next_hop = path[1]
                    out_port = self._get_next_hop_port(dpid, next_hop)
                    self.logger.info(f"[PRIMARY] Route to gateway s3: {path} via port {out_port}")
                else:
                    out_port = ofproto.OFPP_FLOOD
        else:
            # Unknown destination - flood
            out_port = ofproto.OFPP_FLOOD
            self.logger.info(f"[PRIMARY] Flooding unknown destination {dst_mac}")
        
        # Install flow and forward packet
        actions = [parser.OFPActionOutput(out_port)]
        
        if out_port != ofproto.OFPP_FLOOD:
            # Install flow entry
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst_mac)
            self.add_flow(datapath, 1, match, actions)
            
        # Forward packet
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
            
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        """Handle port status changes (link failures)"""
        msg = ev.msg
        dpid = msg.datapath.id
        port = msg.desc.port_no
        reason = msg.reason
        
        if dpid not in self.my_switches:
            return
            
        if reason == msg.datapath.ofproto.OFPPR_DELETE:
            self.logger.warning(f"[PRIMARY][LINK-DOWN] s{dpid} port {port} failed")
            # Update topology by removing failed link
            self._update_topology_on_failure(dpid, port)
        elif reason == msg.datapath.ofproto.OFPPR_ADD:
            self.logger.info(f"[PRIMARY][LINK-UP] s{dpid} port {port} restored")
            # Could restore topology here

    def _update_topology_on_failure(self, switch_id, port):
        """Update topology when link fails"""
        # Port to neighbor mapping
        port_to_neighbor = {
            1: {3: 2, 4: 3},           # s1
            2: {3: 1, 4: 4, 5: 5},     # s2
            3: {3: 1, 4: 6, 5: 7},     # s3
            4: {3: 2, 4: 8, 5: 9},     # s4
            5: {3: 2, 4: 10}           # s5
        }
        
        neighbor = port_to_neighbor.get(switch_id, {}).get(port)
        if neighbor and self.topology.has_edge(switch_id, neighbor):
            self.topology.remove_edge(switch_id, neighbor)
            self.logger.warning(f"[PRIMARY][TOPOLOGY] Removed link s{switch_id}-s{neighbor}")