# Link Failure Testing Guide

## 방법 1: Mininet CLI에서 직접 명령어 실행

### OpenFlow 명령어 사용 (권장)
```bash
# 링크 끊기
mininet> sh ovs-ofctl mod-port s1 s1-eth2 down
mininet> sh ovs-ofctl mod-port s2 s2-eth3 down

# 링크 복구
mininet> sh ovs-ofctl mod-port s1 s1-eth2 up
mininet> sh ovs-ofctl mod-port s2 s2-eth3 up
```

### Mininet link 명령어 사용 (논리적 링크)
```bash
# 링크 끊기
mininet> link s1 s2 down

# 링크 복구  
mininet> link s1 s2 up
```

**주의**: `link` 명령어는 논리적 링크만 끊어서 OpenFlow 이벤트가 트리거되지 않을 수 있습니다. 
`ovs-ofctl mod-port`를 사용하면 실제 포트 상태를 변경하여 컨트롤러가 감지할 수 있습니다.

## 방법 2: Shell 스크립트 사용

### 자동 테스트 스크립트 실행
```bash
# 실행 권한 부여
chmod +x test_link_failure.sh

# 스크립트 실행
./test_link_failure.sh
```

## 방법 3: 외부 터미널에서 명령어 실행

tmux 세션이 실행 중일 때 다른 터미널에서:

```bash
# mininet 세션에 명령어 전송
tmux send-keys -t sdn_demo:0.1 "sh ovs-ofctl mod-port s1 s1-eth2 down" Enter

# 또는 직접 OVS 명령어 실행 (root 권한 필요)
sudo ovs-ofctl mod-port s1 s1-eth2 down
```

## Ring 토폴로지 (10 switches) 포트 매핑

각 스위치의 포트 구성:
- Port 1: 호스트 연결
- Port 2: 다음 스위치로 연결 (시계방향)
- Port 3: 이전 스위치에서 연결 (반시계방향)

### 주요 링크:
```
s1:2 <-> s2:3
s2:2 <-> s3:3
s3:2 <-> s4:3
s4:2 <-> s5:3
s5:2 <-> s6:3
s6:2 <-> s7:3
s7:2 <-> s8:3
s8:2 <-> s9:3
s9:2 <-> s10:3
s10:2 <-> s1:3
```

## 테스트 시나리오 예제

### 시나리오 1: 단일 링크 실패
```bash
# 정상 상태 테스트
mininet> h1 ping -c 3 h5

# s1-s2 링크 끊기
mininet> sh ovs-ofctl mod-port s1 s1-eth2 down

# 우회 경로로 통신 확인
mininet> h1 ping -c 3 h5  # 더 긴 경로로 우회

# 링크 복구
mininet> sh ovs-ofctl mod-port s1 s1-eth2 up
```

### 시나리오 2: 다중 링크 실패
```bash
# 두 개 링크 동시 끊기
mininet> sh ovs-ofctl mod-port s1 s1-eth2 down
mininet> sh ovs-ofctl mod-port s5 s5-eth2 down

# 통신 테스트
mininet> h1 ping -c 3 h6  # 여전히 가능 (다른 경로 존재)

# 링크 복구
mininet> sh ovs-ofctl mod-port s1 s1-eth2 up
mininet> sh ovs-ofctl mod-port s5 s5-eth2 up
```

## 컨트롤러 로그 확인

다른 터미널에서 컨트롤러 로그 모니터링:
```bash
# 컨트롤러 로그 실시간 확인
tmux capture-pane -t sdn_demo:0.0 -p | tail -30

# 특정 패턴 검색
tmux capture-pane -t sdn_demo:0.0 -p | grep "LINK_DOWN\|PATH CHANGE"
```

## 트러블슈팅

### 링크가 끊어지지 않을 때
1. `ovs-ofctl mod-port` 대신 `ovs-vsctl` 사용:
   ```bash
   mininet> sh ovs-vsctl set interface s1-eth2 link_state=down
   ```

2. 포트 번호 확인:
   ```bash
   mininet> sh ovs-ofctl show s1
   ```

### 컨트롤러가 감지하지 못할 때
1. LLDP 패킷 확인
2. 컨트롤러의 port_status_handler 동작 확인
3. OpenFlow 버전 확인 (1.3 이상 필요)