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
        self.datapaths = {}  # Store datapath objects
        self.mac_to_switch = {}  # Track which switch a MAC is connected to
        
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
            # Primary domain with loop
            (1, 2, 1), (1, 3, 1),
            (2, 4, 1), (2, 5, 1),
            (4, 3, 2),  # s4-s3 backup (creates loop!)
            # Cross-domain links
            (3, 6, 2), (3, 7, 2),
            (4, 8, 2), (4, 9, 2),
            (5, 10, 2),
            # Secondary domain internal
            (6, 7, 1), (8, 9, 1)
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
            self.datapaths[dpid] = datapath  # Store datapath
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
        
        # Learn source MAC and which switch it's on
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src_mac] = in_port
        self.mac_to_switch[src_mac] = dpid
        
        # Determine output port
        if dst_mac in self.mac_to_port.get(dpid, {}):
            # Known local destination
            out_port = self.mac_to_port[dpid][dst_mac]
            self.logger.info(f"[SECONDARY] Local forwarding s{dpid}: {src_mac}->{dst_mac} via port {out_port}")
        elif dst_mac in self.mac_to_switch:
            # Destination MAC is known but on a different switch
            dst_switch = self.mac_to_switch[dst_mac]
            if dst_switch in self.my_switches:
                # Calculate path to destination switch
                path, cost = self._dijkstra_path(dpid, dst_switch)
                if path and len(path) > 1:
                    next_hop = path[1]
                    out_port = self._get_next_hop_port(dpid, next_hop)
                    self.logger.info(f"[SECONDARY] Routing to s{dst_switch}: path={path} via port {out_port}")
                    
                    # Install flows along the entire path
                    self._install_path_flows(src_mac, dst_mac, path)
                else:
                    out_port = ofproto.OFPP_FLOOD
            else:
                # Destination is in primary domain
                out_port = self._get_gateway_port(dpid)
                self.logger.info(f"[SECONDARY] Cross-domain via port {out_port}")
        elif self._is_cross_domain_dst(dst_mac):
            # Cross-domain communication to primary
            out_port = self._get_gateway_port(dpid)
            self.logger.info(f"[SECONDARY] Cross-domain: s{dpid} -> Primary via port {out_port}")
        else:
            # Unknown destination - flood
            out_port = ofproto.OFPP_FLOOD
            self.logger.info(f"[SECONDARY] Flooding unknown destination {dst_mac}")
        
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
            # Restore topology
            self._restore_topology_on_recovery(dpid, port)
    
    def _clear_flows_for_rerouting(self):
        """Clear flows on all switches to trigger rerouting"""
        for dpid, datapath in self.datapaths.items():
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            
            # Delete all flows except table-miss
            match = parser.OFPMatch()
            mod = parser.OFPFlowMod(
                datapath=datapath,
                command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY,
                out_group=ofproto.OFPG_ANY,
                priority=1,
                match=match
            )
            datapath.send_msg(mod)
            self.logger.info(f"[SECONDARY] Cleared flows on s{dpid} for rerouting")
    
    def _restore_topology_on_recovery(self, switch_id, port):
        """Restore topology when link recovers"""
        # Port to neighbor mapping for secondary switches
        port_to_neighbor = {
            6: {3: 3, 4: 7},           # s6
            7: {3: 3, 4: 6},           # s7
            8: {3: 4, 4: 9},           # s8
            9: {3: 4, 4: 8},           # s9
            10: {3: 5}                 # s10
        }
        
        neighbor = port_to_neighbor.get(switch_id, {}).get(port)
        if neighbor and not self.topology.has_edge(switch_id, neighbor):
            # Restore link with appropriate weight
            weight = 1 if neighbor in self.my_switches else 2
            self.topology.add_edge(switch_id, neighbor, weight=weight)
            self.logger.info(f"[SECONDARY][TOPOLOGY] Restored link s{switch_id}-s{neighbor}")
            
            # Clear flows to use new topology
            self._clear_flows_for_rerouting()

    def _install_path_flows(self, src_mac, dst_mac, path):
        """Install flow entries along the entire path"""
        dst_switch = path[-1]
        dst_port = self.mac_to_port.get(dst_switch, {}).get(dst_mac)
        
        if not dst_port:
            return
            
        # Install flows on each switch in the path
        for i in range(len(path) - 1):
            curr_switch = path[i]
            next_switch = path[i + 1]
            
            if curr_switch not in self.datapaths:
                continue
                
            datapath = self.datapaths[curr_switch]
            parser = datapath.ofproto_parser
            out_port = self._get_next_hop_port(curr_switch, next_switch)
            
            if out_port:
                # Install flow for this destination
                match = parser.OFPMatch(eth_dst=dst_mac)
                actions = [parser.OFPActionOutput(out_port)]
                self.add_flow(datapath, 10, match, actions)
                self.logger.info(f"[SECONDARY] Installed flow on s{curr_switch}: dst={dst_mac} -> port {out_port}")
        
        # Install flow on destination switch
        if dst_switch in self.datapaths:
            datapath = self.datapaths[dst_switch]
            parser = datapath.ofproto_parser
            match = parser.OFPMatch(eth_dst=dst_mac)
            actions = [parser.OFPActionOutput(dst_port)]
            self.add_flow(datapath, 10, match, actions)
            self.logger.info(f"[SECONDARY] Installed flow on s{dst_switch}: dst={dst_mac} -> port {dst_port}")
    
    def _get_gateway_port(self, dpid):
        """Get gateway port back to primary domain"""
        if dpid in {6, 7}:
            return 3  # Back to s3
        elif dpid in {8, 9}:
            return 3  # Back to s4
        elif dpid == 10:
            return 3  # Back to s5
        return None
    
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
            
            # Clear all flows to trigger rerouting
            self._clear_flows_for_rerouting()