"""
Unified Dijkstra SDN Controller
Uses exact topology from topology_config.py
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types
import networkx as nx
import logging
from collections import defaultdict
import sys
import os

# Add parent directory to path to import topology_config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from topology_config import get_topology_links, TOPOLOGY_DIAGRAM

class UnifiedDijkstraController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(UnifiedDijkstraController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.mac_to_dpid = {}
        self.topology = nx.Graph()
        self.switch_ports = defaultdict(dict)
        self.path_count = 0
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)8s] %(message)s',
            datefmt='%H:%M:%S'
        )
        
        self.logger.info("="*70)
        self.logger.info("   UNIFIED DIJKSTRA CONTROLLER STARTED")
        self.logger.info("="*70)
        
        # Initialize topology from config
        self.setup_topology()

    def setup_topology(self):
        """Setup topology from configuration file"""
        self.logger.info("\n🔧 INITIALIZING TOPOLOGY FROM CONFIG")
        self.logger.info(TOPOLOGY_DIAGRAM)
        
        # Get links from configuration
        links = get_topology_links()
        
        # Add all links to topology
        for sw1, sw2, port1, port2 in links:
            self.topology.add_edge(sw1, sw2, weight=1)
            self.switch_ports[sw1][sw2] = port1
            self.switch_ports[sw2][sw1] = port2
            self.logger.info(f"  ➕ Added link: s{sw1}:{port1} <--> s{sw2}:{port2}")
        
        # Print summary
        self.logger.info(f"\n📊 TOPOLOGY SUMMARY:")
        self.logger.info(f"  • Switches: {self.topology.number_of_nodes()}")
        self.logger.info(f"  • Links: {self.topology.number_of_edges()}")
        
        # Show connectivity for each switch
        self.logger.info(f"\n🔗 SWITCH CONNECTIVITY:")
        for node in sorted(self.topology.nodes()):
            neighbors = sorted(list(self.topology.neighbors(node)))
            ports = [f"s{n}(p{self.switch_ports[node][n]})" for n in neighbors]
            self.logger.info(f"  s{node} -> {', '.join(ports)}")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch connection"""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        
        self.datapaths[dpid] = datapath
        self.logger.info(f"\n✅ SWITCH CONNECTED: s{dpid}")
        
        # Install table-miss flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                        ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        
        # Show connected switches count
        connected = len(self.datapaths)
        total = self.topology.number_of_nodes()
        self.logger.info(f"  Connected switches: {connected}/{total}")

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """Add flow to switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                  priority=priority, match=match,
                                  instructions=inst, idle_timeout=30, hard_timeout=60)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                  match=match, instructions=inst,
                                  idle_timeout=30, hard_timeout=60)
        datapath.send_msg(mod)

    def calculate_path(self, src_dpid, dst_dpid):
        """Calculate shortest path using Dijkstra"""
        if src_dpid == dst_dpid:
            return [src_dpid]
        
        if src_dpid not in self.topology or dst_dpid not in self.topology:
            self.logger.error(f"  ❌ Switch s{src_dpid} or s{dst_dpid} not in topology")
            return None
        
        try:
            path = nx.shortest_path(self.topology, src_dpid, dst_dpid, weight='weight')
            self.path_count += 1
            
            # Log path calculation
            path_str = " → ".join([f"s{dpid}" for dpid in path])
            self.logger.info(f"\n🧮 PATH CALCULATION #{self.path_count}")
            self.logger.info(f"  From: s{src_dpid} To: s{dst_dpid}")
            self.logger.info(f"  Path ({len(path)-1} hops): {path_str}")
            
            return path
            
        except nx.NetworkXNoPath:
            self.logger.error(f"  ❌ NO PATH from s{src_dpid} to s{dst_dpid}")
            return None

    def install_path(self, path, src_mac, dst_mac):
        """Install flows along the path"""
        self.logger.info(f"  📝 Installing flows for {src_mac} -> {dst_mac}")
        
        for i in range(len(path) - 1):
            curr_dpid = path[i]
            next_dpid = path[i + 1]
            
            if curr_dpid not in self.datapaths:
                continue
            
            # Get output port
            out_port = self.switch_ports[curr_dpid].get(next_dpid)
            if not out_port:
                continue
            
            datapath = self.datapaths[curr_dpid]
            parser = datapath.ofproto_parser
            
            # Install forward flow
            match = parser.OFPMatch(eth_dst=dst_mac, eth_src=src_mac)
            actions = [parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, 10, match, actions)
            
            self.logger.info(f"    s{curr_dpid}: out_port={out_port} -> s{next_dpid}")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """Handle packet in events"""
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id
        
        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocols(ethernet.ethernet)[0]
        
        # Ignore LLDP
        if eth_pkt.ethertype == ether_types.ETH_TYPE_LLDP:
            return
        
        dst_mac = eth_pkt.dst
        src_mac = eth_pkt.src
        
        # Learn MAC location
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src_mac] = in_port
        self.mac_to_dpid[src_mac] = dpid
        
        # Ignore multicast/broadcast (reduce log spam)
        if dst_mac[:5] in ['33:33', 'ff:ff', '01:00']:
            out_port = ofproto.OFPP_FLOOD
        elif dst_mac in self.mac_to_dpid:
            dst_dpid = self.mac_to_dpid[dst_mac]
            
            if dpid == dst_dpid:
                # Same switch
                if dst_mac in self.mac_to_port[dpid]:
                    out_port = self.mac_to_port[dpid][dst_mac]
                else:
                    out_port = ofproto.OFPP_FLOOD
            else:
                # Different switch - calculate path
                self.logger.info(f"\n📨 PACKET_IN at s{dpid}: {src_mac} -> {dst_mac}")
                path = self.calculate_path(dpid, dst_dpid)
                
                if path and len(path) > 1:
                    next_dpid = path[1]
                    out_port = self.switch_ports[dpid].get(next_dpid, ofproto.OFPP_FLOOD)
                    
                    if out_port != ofproto.OFPP_FLOOD:
                        # Install flows for entire path
                        self.install_path(path, src_mac, dst_mac)
                else:
                    out_port = ofproto.OFPP_FLOOD
        else:
            out_port = ofproto.OFPP_FLOOD
        
        # Send packet out
        actions = [parser.OFPActionOutput(out_port)]
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        """Handle port status changes"""
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no
        dpid = msg.datapath.id
        ofproto = msg.datapath.ofproto
        
        if reason == ofproto.OFPPR_ADD:
            self.logger.info(f"✅ PORT UP: s{dpid}:{port_no}")
        elif reason == ofproto.OFPPR_DELETE:
            self.logger.warning(f"❌ PORT DOWN: s{dpid}:{port_no}")
            self.handle_port_down(dpid, port_no)
        elif reason == ofproto.OFPPR_MODIFY:
            self.logger.info(f"🔧 PORT MODIFIED: s{dpid}:{port_no}")

    def handle_port_down(self, dpid, port_no):
        """Handle port down event"""
        self.logger.warning(f"\n⚠️  LINK FAILURE DETECTED at s{dpid}:{port_no}")
        
        # Find and remove the failed link
        for neighbor in list(self.switch_ports[dpid].keys()):
            if self.switch_ports[dpid][neighbor] == port_no:
                if self.topology.has_edge(dpid, neighbor):
                    self.logger.error(f"  💥 Removing link: s{dpid} <--> s{neighbor}")
                    self.topology.remove_edge(dpid, neighbor)
                    
                    # Check if network is still connected
                    if nx.is_connected(self.topology):
                        self.logger.info(f"  ✅ Network still connected")
                    else:
                        components = nx.number_connected_components(self.topology)
                        self.logger.error(f"  ⚠️  Network PARTITIONED into {components} parts!")
                    
                    # Clear all flows to force recalculation
                    self.clear_all_flows()
                break

    def clear_all_flows(self):
        """Clear flows on all switches"""
        self.logger.info("  🔄 Clearing all flows for rerouting...")
        
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
        
        self.logger.info("  ✅ Flows cleared - next packet will trigger new paths")