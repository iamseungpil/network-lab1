# SDN 네트워크 상세 분석

## 1. 토폴로지 구조

### Ring Topology (10 스위치)
```
    s1 --- s2 --- s3 --- s4 --- s5
    |                           |
   s10                          s6
    |                           |
    s9 --- s8 --- s7 -----------
```

**특징:**
- 각 스위치마다 1개의 호스트 연결 (h1~h10)
- 호스트는 항상 포트 1에 연결
- 스위치 간 연결은 포트 2, 3 사용
- 완전한 링 구조로 각 노드에서 2개의 경로 존재

## 2. Flooding 방지 메커니즘

### 현재 구현 상태:
```python
def flood_packet(self, datapath, msg, in_port):
    # 모든 포트로 flooding (입력 포트 제외)
    for port_no in datapath.ports:
        if port_no != in_port:
            out_ports.append(port_no)
```

**문제점:** 
- ❌ **STP가 구현되지 않음** - 링 토폴로지에서 브로드캐스트 스톰 발생 가능
- ❌ **Flooding 제한 없음** - 모든 포트로 무제한 flooding

**해결 방법:**
1. STP 구현으로 루프 방지
2. 브로드캐스트 캐시로 중복 flooding 방지
3. TTL이나 시퀀스 번호로 패킷 추적

## 3. Dijkstra 라우팅 동작

### 코드 레벨 분석:

#### 3.1 패킷 수신 시 처리 흐름:
```python
@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
def packet_in_handler(self, ev):
    # 1. 소스 MAC 학습
    self.learn_host_location(dpid, src_mac, in_port)
    
    # 2. 목적지 확인
    if dst_mac in self.host_locations:
        dst_dpid, dst_port = self.host_locations[dst_mac]
        
        # 3. 같은 스위치인 경우
        if dpid == dst_dpid:
            out_port = dst_port
        
        # 4. 다른 스위치인 경우 - Dijkstra 사용
        else:
            path = self.calculate_shortest_path(dpid, dst_dpid)
            next_hop = path[1]
            out_port = self.switch_to_port[dpid].get(next_hop)
```

#### 3.2 Dijkstra 경로 계산:
```python
def calculate_shortest_path(self, src_dpid, dst_dpid):
    # NetworkX 라이브러리 사용
    path = nx.shortest_path(self.topology_graph, src_dpid, dst_dpid, weight='weight')
    
    # 로그 출력
    print(f"🛤️  DIJKSTRA PATH: {path}")
    return path
```

### Dijkstra 라우팅 확인 방법:

**1. 컨트롤러 로그에서 확인할 키워드:**
- `"🛤️  Using DIJKSTRA PATH"` - 경로 사용 시
- `"🛤️  DIJKSTRA PATH CALCULATED"` - 경로 계산 시  
- `"Next hop: s"` - 다음 홉 결정
- `"Path length:"` - 경로 길이

**2. 예시 시나리오 (h1 → h6):**
```
최단 경로 (5 홉):
- 시계방향: s1 → s2 → s3 → s4 → s5 → s6
- 반시계방향: s1 → s10 → s9 → s8 → s7 → s6
```

## 4. 링크 실패 시 재라우팅

### 동작 과정:

1. **링크 실패 감지:**
```python
@set_ev_cls(event.EventPortModify, MAIN_DISPATCHER)
def port_modify_handler(self, ev):
    if port.state == 1:  # OFPPS_LINK_DOWN
        print(f"🔴 [PORT EVENT] Port {port_no} LINK_DOWN")
```

2. **토폴로지 재계산:**
```python
def discover_topology(self):
    # 링크 제거
    self.topology_graph.remove_edge(src_dpid, dst_dpid)
    
    # 새로운 경로 계산 (다음 패킷 시)
```

3. **대체 경로 사용:**
- 링크 s1-s2가 끊어지면
- h1 → h2는 s1 → s10 → s9 → ... → s2로 우회

## 5. 실제 테스트 명령어

### Dijkstra 라우팅 확인:
```bash
# 세션 연결
tmux attach -t sdn_demo

# 하단 창에서 (Mininet CLI)
h1 ping -c 1 h6  # 반대편 호스트 (5홉)
h1 ping -c 1 h3  # 2홉 거리

# 상단 창에서 로그 확인
# "DIJKSTRA PATH" 검색
```

### 링크 실패 테스트:
```bash
# 링크 끊기
link s1 s2 down

# 재라우팅 확인
h1 ping -c 3 h2  # 우회 경로 사용

# 링크 복구
link s1 s2 up
```

## 6. 개선 필요 사항

1. **STP 구현 필요**
   - 현재 링 토폴로지에서 브로드캐스트 스톰 위험
   - IEEE 802.1D STP 알고리즘 추가 필요

2. **Flow 테이블 최적화**
   - 현재 모든 패킷이 컨트롤러로 전송
   - Proactive flow 설치로 성능 향상 가능

3. **경로 시각화**
   - 현재 경로를 명확히 보기 어려움
   - traceroute 기능 추가 권장

## 7. 핵심 로그 메시지 해석

| 로그 메시지 | 의미 |
|-----------|------|
| `📦 [PACKET #N]` | 패킷 수신 |
| `🖥️ [HOST] Learned` | 호스트 위치 학습 |
| `🛤️ Using DIJKSTRA PATH` | Dijkstra 경로 사용 |
| `📡 Broadcast/Multicast` | 브로드캐스트 flooding |
| `🔴 [PORT EVENT] LINK_DOWN` | 링크 다운 감지 |
| `✅ Packet forwarded` | 패킷 전달 완료 |

## 결론

- **링 구조**: ✅ 정상 (10개 스위치, 각 1개 호스트)
- **Dijkstra 라우팅**: ✅ 동작 (NetworkX shortest_path 사용)
- **재라우팅**: ✅ 동작 (링크 실패 시 대체 경로)
- **Flooding 방지**: ❌ 미구현 (STP 없음, 브로드캐스트 스톰 위험)