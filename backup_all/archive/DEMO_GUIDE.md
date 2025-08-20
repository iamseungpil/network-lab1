# 🎯 SDN Dual Controller Demo Guide

## 📺 Demo 실행 방법 (3가지)

### 1. **Visual Demo - 한 화면에서 모든 것 보기 (추천!)**
```bash
./cleanup_network.sh
./demo_visual.sh attach  # 자동으로 tmux 연결
```

**화면 구성:**
```
┌─────────────────┬─────────────────┐
│ Primary Ctrl    │ Secondary Ctrl  │
│ (s1-s5)         │ (s6-s10)        │
│ Dijkstra logs   │ Dijkstra logs   │
├─────────────────┴─────────────────┤
│         Test Output                │
│         (8개 테스트 실시간)         │
└────────────────────────────────────┘
```

### 2. **기본 Demo - 전체 테스트**
```bash
./cleanup_network.sh
./demo_all.sh auto        # 자동 실행

# 테스트 후 로그 확인
tmux attach -t dual_controllers:0  # Primary controller
tmux attach -t dual_controllers:1  # Secondary controller
```

### 3. **Visual Mode with demo_all.sh**
```bash
./cleanup_network.sh
./demo_all.sh visual      # Split-pane 모드

# 자동으로 연결
tmux attach -t dual_controllers
```

## 🔍 tmux 사용법

### 세션 연결/해제
```bash
# 연결
tmux attach -t sdn_visual      # visual demo
tmux attach -t dual_controllers # 일반 demo

# 해제 (세션 유지)
Ctrl+b, d

# 세션 종료
tmux kill-session -t sdn_visual
```

### Pane 네비게이션
- **Pane 이동**: `Ctrl+b` → 화살표 키
- **Pane 확대**: `Ctrl+b` → `z` (토글)
- **스크롤**: `Ctrl+b` → `[` → 화살표/PgUp/PgDn → `q`로 종료

## 📊 실시간으로 보는 내용

### Primary Controller (왼쪽 상단)
```
[PRIMARY][DIJKSTRA] Computing path from s1 to s3
[PRIMARY][DIJKSTRA] ✓ OPTIMAL PATH: s1 -> s3 (cost=1)
[PRIMARY][LINK-DOWN] s1 port 4 failed
[PRIMARY][TOPOLOGY] Removed link s1-s3
```

### Secondary Controller (오른쪽 상단)
```
[SECONDARY][DIJKSTRA] Computing path from s6 to s10
[SECONDARY][DIJKSTRA] ✓ OPTIMAL PATH: s6 -> s10 (cost=2)
[SECONDARY][LINK-DOWN] s6 port 3 failed
```

### Test Output (하단)
```
[TEST 1] Testing intra-domain connectivity h1 -> h5
✓ Primary domain routing works (s1→s3)

[TEST 3] Breaking primary domain link s1 <-> s3
✓ Link s1-s3 is now DOWN

[TEST 4] Testing primary domain rerouting
✓ PRIMARY DOMAIN REROUTING SUCCESS!
```

## 🎬 Demo 시나리오

1. **정상 라우팅** - 최적 경로 계산
2. **링크 장애** - s1-s3 링크 끊김
3. **자동 재라우팅** - s1→s2→s4→s3 우회
4. **Cross-domain 장애** - s3-s6 끊김
5. **대체 게이트웨이** - s4→s8 경로 사용
6. **링크 복구** - 최적 경로 복원

## 🔧 문제 해결

### Controllers not running
```bash
./cleanup_network.sh
netstat -ln | grep -E "6633|6634"
```

### tmux session 오류
```bash
tmux kill-server  # 모든 세션 종료
./cleanup_network.sh
```

### Mininet 오류
```bash
sudo mn -c
./cleanup_network.sh
```

## 💡 Tips

1. **Dijkstra 로그만 보기**
```bash
./demo_dijkstra.sh auto
```

2. **수동 테스트**
```bash
# Demo 실행 후 Mininet CLI에서
mininet> h1 ping h5
mininet> net.configLinkStatus("s1", "s3", "down")
mininet> h1 ping h5  # 우회 경로 확인
```

3. **로그 필터링**
```bash
# Primary controller의 Dijkstra 로그만
tmux capture-pane -t sdn_visual:0 -p | grep DIJKSTRA
```

## 📈 성능 지표

- **링크 장애 감지**: ~1초
- **경로 재계산**: ~100ms
- **플로우 재설정**: ~2초
- **전체 복구 시간**: ~3초

## 🚀 Quick Start

가장 빠르게 확인하는 방법:
```bash
./demo_visual.sh attach
```

이 명령 하나로:
- ✅ 네트워크 정리
- ✅ 컨트롤러 시작
- ✅ Split-pane 생성
- ✅ 테스트 실행
- ✅ 실시간 모니터링