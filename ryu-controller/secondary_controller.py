"""
Secondary Controller for Dual-Controller SDN with Dijkstra Routing
Manages switches s6-s10 and handles cross-domain communication
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, arp, ipv4
import networkx as nx
import logging

class SecondaryController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SecondaryController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.topology = self._build_topology()
        self.switches = set()
        
        # Domain configuration
        self.my_switches = {6, 7, 8, 9, 10}  # s6-s10
        self.gateway_switches = {6, 7, 8, 9, 10}  # All can communicate with primary
        
        # Host mapping (MAC addresses)
        self.secondary_hosts = set(f"00:00:00:00:00:{i:02x}" for i in range(11, 21))  # h11-h20
        
        logging.basicConfig(level=logging.INFO)
        self.logger.info("[SECONDARY] Controller started - managing s6-s10")

    def _build_topology(self):
        """Build network topology graph"""
        G = nx.Graph()
        
        # Add nodes (switches 1-10)
        for i in range(1, 11):
            G.add_node(i)
        
        # Full topology including cross-domain links
        edges = [
            # Primary domain
            (1, 2, 1), (1, 3, 1),
            (2, 4, 1), (2, 5, 1),
            # Cross-domain links
            (3, 6, 2), (3, 7, 2),
            (4, 8, 2), (4, 9, 2),
            (5, 10, 2),
            # Secondary domain internal (if any)
            (6, 7, 1), (8, 9, 1)  # Add some internal connections
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
            self.logger.info(f"[SECONDARY] Switch s{dpid} connected")
            
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
        self.logger.info(f"[SECONDARY][DIJKSTRA] Computing path from s{src} to s{dst}")
        try:
            if self.topology.has_node(src) and self.topology.has_node(dst):
                # Calculate all possible paths for comparison
                all_paths = list(nx.all_simple_paths(self.topology, src, dst, cutoff=5))
                self.logger.info(f"[SECONDARY][DIJKSTRA] Found {len(all_paths)} possible paths")
                
                # Calculate shortest path using Dijkstra
                path = nx.shortest_path(self.topology, src, dst, weight='weight')
                cost = nx.shortest_path_length(self.topology, src, dst, weight='weight')
                
                # Log the chosen path
                path_str = " -> ".join([f"s{node}" for node in path])
                self.logger.info(f"[SECONDARY][DIJKSTRA] ✓ OPTIMAL PATH: {path_str} (cost={cost})")
                
                # Log alternative paths for comparison
                for i, alt_path in enumerate(all_paths[:3]):  # Show up to 3 alternatives
                    if alt_path != path:
                        alt_cost = sum(self.topology[alt_path[j]][alt_path[j+1]].get('weight', 1) 
                                     for j in range(len(alt_path)-1))
                        alt_str = " -> ".join([f"s{node}" for node in alt_path])
                        self.logger.info(f"[SECONDARY][DIJKSTRA]   Alternative {i+1}: {alt_str} (cost={alt_cost})")
                
                return path, cost
        except nx.NetworkXNoPath:
            self.logger.error(f"[SECONDARY][DIJKSTRA] ✗ NO PATH found from s{src} to s{dst}")
        except Exception as e:
            self.logger.error(f"[SECONDARY][DIJKSTRA] Error: {e}")
        return None, float('inf')

    def _get_next_hop_port(self, current_switch, next_switch):
        """Get output port for next hop"""
        # Port mapping based on topology
        port_map = {
            6: {3: 3, 7: 4},           # s6: s3->port3, s7->port4
            7: {3: 3, 6: 4},           # s7: s3->port3, s6->port4
            8: {4: 3, 9: 4},           # s8: s4->port3, s9->port4
            9: {4: 3, 8: 4},           # s9: s4->port3, s8->port4
            10: {5: 3}                 # s10: s5->port3
        }
        return port_map.get(current_switch, {}).get(next_switch, None)

    def _is_cross_domain_dst(self, dst_mac):
        """Check if destination is in primary domain"""
        return dst_mac not in self.secondary_hosts

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
        
        self.logger.info(f"[SECONDARY] Packet: {src_mac} -> {dst_mac} on s{dpid}:{in_port}")
        
        # Learn source MAC
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src_mac] = in_port
        
        # Determine output port
        if dst_mac in self.mac_to_port.get(dpid, {}):
            # Known local destination
            out_port = self.mac_to_port[dpid][dst_mac]
            self.logger.info(f"[SECONDARY] Local forwarding s{dpid}: {src_mac}->{dst_mac} via port {out_port}")
        elif self._is_cross_domain_dst(dst_mac):
            # Cross-domain communication to primary
            if dpid in {6, 7}:
                out_port = 3  # Back to s3
            elif dpid in {8, 9}:
                out_port = 3  # Back to s4
            elif dpid == 10:
                out_port = 3  # Back to s5
            else:
                out_port = ofproto.OFPP_FLOOD
                
            self.logger.info(f"[SECONDARY] Cross-domain: s{dpid} -> Primary via port {out_port}")
        else:
            # Unknown destination in secondary domain
            if dpid in self.my_switches:
                # Try to find path within secondary domain
                known_switches = [sw for sw in self.my_switches if sw in self.mac_to_port and dst_mac in self.mac_to_port[sw]]
                if known_switches:
                    target_switch = known_switches[0]
                    path, cost = self._dijkstra_path(dpid, target_switch)
                    if path and len(path) > 1:
                        next_hop = path[1]
                        out_port = self._get_next_hop_port(dpid, next_hop)
                        self.logger.info(f"[SECONDARY] Dijkstra route: {path} via port {out_port}")
                    else:
                        out_port = ofproto.OFPP_FLOOD
                else:
                    out_port = ofproto.OFPP_FLOOD
            else:
                out_port = ofproto.OFPP_FLOOD
                
            self.logger.info(f"[SECONDARY] Unknown destination {dst_mac}, using port {out_port}")
        
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
            self.logger.warning(f"[SECONDARY][LINK-DOWN] s{dpid} port {port} failed")
            # Update topology by removing failed link
            self._update_topology_on_failure(dpid, port)
        elif reason == msg.datapath.ofproto.OFPPR_ADD:
            self.logger.info(f"[SECONDARY][LINK-UP] s{dpid} port {port} restored")

    def _update_topology_on_failure(self, switch_id, port):
        """Update topology when link fails"""
        # Port to neighbor mapping for secondary switches
        port_to_neighbor = {
            6: {3: 3, 4: 7},           # s6
            7: {3: 3, 4: 6},           # s7
            8: {3: 4, 4: 9},           # s8
            9: {3: 4, 4: 8},           # s9
            10: {3: 5}                 # s10
        }
        
        neighbor = port_to_neighbor.get(switch_id, {}).get(port)
        if neighbor and self.topology.has_edge(switch_id, neighbor):
            self.topology.remove_edge(switch_id, neighbor)
            self.logger.warning(f"[SECONDARY][TOPOLOGY] Removed link s{switch_id}-s{neighbor}")