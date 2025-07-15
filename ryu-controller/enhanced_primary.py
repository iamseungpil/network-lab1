#!/usr/bin/env python3
"""
Enhanced Primary Controller with Cross-Controller Support
크로스 컨트롤러 통신을 지원하는 개선된 Primary Controller
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, arp, icmp, ipv4


class EnhancedPrimaryController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(EnhancedPrimaryController, self).__init__(*args, **kwargs)
        
        # 관리할 스위치 DPID (s1-s5)
        self.managed_switches = {1, 2, 3, 4, 5}
        
        # L2 학습 테이블: {dpid: {mac: port}}
        self.mac_to_port = {}
        self.datapaths = {}
        self.global_mac_table = {}  # {mac: (dpid, port)} - 전역 MAC 테이블
        
        # 스위치 간 연결 정보 (토폴로지 맵)
        self.switch_links = {
            1: {2: 3, 3: 4},          # s1: s2(port3), s3(port4)
            2: {1: 3, 4: 4, 5: 5},    # s2: s1(port3), s4(port4), s5(port5)
            3: {1: 3, 6: 4, 7: 5},    # s3: s1(port3), s6(port4), s7(port5)
            4: {2: 3, 8: 4, 9: 5},    # s4: s2(port3), s8(port4), s9(port5)
            5: {2: 3, 10: 4}          # s5: s2(port3), s10(port4)
        }
        
        # Secondary Controller 영역의 호스트 정보 (사전 정의)
        self.secondary_hosts = {
            '00:00:00:00:00:0b': {'ip': '10.0.0.11', 'switch': 6},  # h11
            '00:00:00:00:00:0c': {'ip': '10.0.0.12', 'switch': 6},  # h12
            '00:00:00:00:00:0d': {'ip': '10.0.0.13', 'switch': 7},  # h13
            '00:00:00:00:00:0e': {'ip': '10.0.0.14', 'switch': 7},  # h14
            '00:00:00:00:00:0f': {'ip': '10.0.0.15', 'switch': 8},  # h15
            '00:00:00:00:00:10': {'ip': '10.0.0.16', 'switch': 8},  # h16
            '00:00:00:00:00:11': {'ip': '10.0.0.17', 'switch': 9},  # h17
            '00:00:00:00:00:12': {'ip': '10.0.0.18', 'switch': 9},  # h18
            '00:00:00:00:00:13': {'ip': '10.0.0.19', 'switch': 10}, # h19
            '00:00:00:00:00:14': {'ip': '10.0.0.20', 'switch': 10}  # h20
        }
        
        self.logger.info("Enhanced Primary Controller initialized - managing switches s1-s5")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """새로운 스위치가 연결될 때 호출"""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        # 관리 대상 스위치인지 확인
        if dpid not in self.managed_switches:
            self.logger.info(f"Switch s{dpid} not managed by Primary Controller")
            return

        # 스위치 등록
        self.datapaths[dpid] = datapath
        self.mac_to_port.setdefault(dpid, {})
        
        self.logger.info(f"Primary Controller: Switch s{dpid} connected successfully")

        # Table-miss flow entry 설치
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                        ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        
        self.logger.info(f"Table-miss flow installed on switch s{dpid}")

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """플로우 엔트리 추가"""
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

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """패킷이 컨트롤러로 전송될 때 호출"""
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id

        # 관리 대상 스위치가 아니면 무시
        if dpid not in self.managed_switches:
            return

        # 패킷 파싱
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # LLDP 패킷 무시
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src

        # 브로드캐스트/멀티캐스트 처리 (로그 생략)
        if dst == 'ff:ff:ff:ff:ff:ff' or dst.startswith('33:33:'):
            out_port = ofproto.OFPP_FLOOD
            actions = [parser.OFPActionOutput(out_port)]
            data = None
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data = msg.data
            out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                    in_port=in_port, actions=actions, data=data)
            datapath.send_msg(out)
            return

        # 유니캐스트 패킷만 로그 출력
        self.logger.info(f"[PRIMARY-PACKET] {src} → {dst} on s{dpid}:{in_port}")

        # MAC 주소 학습
        if src not in self.mac_to_port[dpid]:
            self.mac_to_port[dpid][src] = in_port
            self.global_mac_table[src] = (dpid, in_port)
            self.logger.info(f"[PRIMARY-LEARN] {src} learned at s{dpid}:{in_port}")

        # 목적지 MAC 주소에 따른 포워딩 결정
        if dst in self.mac_to_port[dpid]:
            # 같은 스위치 내 로컬 전달
            out_port = self.mac_to_port[dpid][dst]
            # 로컬 전달은 로그 생략
        elif dst in self.global_mac_table:
            # 다른 Primary 스위치로 전달
            target_dpid, target_port = self.global_mac_table[dst]
            out_port = self._find_next_hop(dpid, target_dpid)
            self.logger.info(f"[PRIMARY-ROUTE] s{dpid} → s{target_dpid} via port {out_port}")
        elif dst in self.secondary_hosts:
            # Secondary Controller 영역으로 전달
            out_port = self._get_gateway_port_to_secondary(dpid, dst)
            self.logger.info(f"[PRIMARY-CROSS] s{dpid} → Secondary via port {out_port} (to {dst})")
        else:
            # 알 수 없는 목적지 - 플러딩 (로그 생략)
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # 플로우 설치 (flooding이 아닌 경우에만)
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            self.add_flow(datapath, 1, match, actions, msg.buffer_id)
            self.logger.info(f"[PRIMARY-FLOW] s{dpid}: {src}→{dst} installed (port {out_port})")
            return

        # Packet Out
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    def _find_next_hop(self, current_dpid, target_dpid):
        """목표 스위치로 가는 다음 홉 찾기"""
        if current_dpid == target_dpid:
            return None
            
        # 직접 연결된 경우
        if target_dpid in self.switch_links.get(current_dpid, {}):
            return self.switch_links[current_dpid][target_dpid]
            
        # 경로 찾기 (간단한 구현)
        # s1 -> s2/s3, s2 -> s4/s5, s3 -> s6/s7, s4 -> s8/s9, s5 -> s10
        if current_dpid == 1:
            if target_dpid in [2, 4, 5]:
                return 3  # s1 -> s2
            elif target_dpid in [3, 6, 7]:
                return 4  # s1 -> s3
        elif current_dpid == 2:
            if target_dpid == 1:
                return 3  # s2 -> s1
            elif target_dpid in [4, 8, 9]:
                return 4  # s2 -> s4
            elif target_dpid in [5, 10]:
                return 5  # s2 -> s5
        elif current_dpid == 3:
            return 3  # s3 -> s1 (모든 경로는 s1을 통함)
        elif current_dpid == 4:
            return 3  # s4 -> s2
        elif current_dpid == 5:
            return 3  # s5 -> s2
            
        return None

    def _get_gateway_port_to_secondary(self, dpid, dst_mac):
        """Secondary 영역으로 가는 게이트웨이 포트 찾기"""
        dst_info = self.secondary_hosts.get(dst_mac)
        if not dst_info:
            return None
            
        target_switch = dst_info['switch']
        
        # 현재 스위치에서 Secondary 영역으로 직접 연결된 경우
        if dpid == 3:  # s3는 s6, s7로 직접 연결
            if target_switch in [6, 7]:
                return self.switch_links[3].get(target_switch)
        elif dpid == 4:  # s4는 s8, s9로 직접 연결
            if target_switch in [8, 9]:
                return self.switch_links[4].get(target_switch)
        elif dpid == 5:  # s5는 s10으로 직접 연결
            if target_switch == 10:
                return self.switch_links[5].get(target_switch)
        
        # 간접 경로 찾기
        if target_switch in [6, 7]:  # s6, s7는 s3를 통해
            return self._find_next_hop(dpid, 3)
        elif target_switch in [8, 9]:  # s8, s9는 s4를 통해
            return self._find_next_hop(dpid, 4)
        elif target_switch == 10:  # s10은 s5를 통해
            return self._find_next_hop(dpid, 5)
            
        return None

    def get_status(self):
        """컨트롤러 상태 반환"""
        return {
            'controller': 'enhanced_primary',
            'managed_switches': list(self.managed_switches),
            'connected_switches': list(self.datapaths.keys()),
            'learned_macs': {f's{dpid}': len(mac_table) 
                           for dpid, mac_table in self.mac_to_port.items()},
            'cross_controller_hosts': len(self.secondary_hosts)
        }