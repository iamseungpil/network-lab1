# SDN Multi-Controller Lab with Docker

Gateway-based 크로스 컨트롤러 통신을 지원하는 다중 컨트롤러 SDN 환경입니다.

## 🚀 빠른 시작 가이드 (Docker)

### 필수 요구사항
- Docker Desktop (Windows/Mac) 또는 Docker Engine (Linux)
- Git
- 8GB 이상의 RAM
- 20GB 이상의 디스크 공간

### 실행 방법

#### 🔥 초보자 버전 (간단!)

```bash
# 1. 프로젝트 클론
git clone <repository-url>
cd network-lab1

# 2. 실행 권한 설정
./make-executable.sh

# 3. 한 번에 모든 것 실행!
./run-simple.sh

# 4. screen 세션 조작법
# - 세션에서 나가기: Ctrl+A, D
# - 재연결: ./run-simple.sh
```

#### 🔧 고급 사용자 버전 (tmux)

```bash
# tmux 기반 다중 윈도우 실행
./run.sh

# tmux 세션 조작법
# - 컨트롤러 윈도우: Ctrl+B, 0
# - Mininet 윈도우: Ctrl+B, 1
# - 세션에서 나가기: Ctrl+B, D
# - 재연결: ./connect.sh
```

### 추가 스크립트

```bash
# 개별 컴포넌트 실행
./start_controllers.sh    # 컨트롤러만 시작
./start_mininet.sh        # Mininet만 시작

# 유틸리티
./rebuild.sh              # 컨테이너 재빌드
./fix-line-endings.sh     # Windows 호환성
```

## 📺 tmux 세션 사용법

SDN Lab은 tmux 세션에서 실행됩니다:

### 주요 단축키
- `Ctrl+B, 0`: 컨트롤러 윈도우로 이동
- `Ctrl+B, 1`: Mininet 윈도우로 이동
- `Ctrl+B, D`: tmux 세션에서 detach (백그라운드 유지)
- `Ctrl+B, [`: 스크롤 모드 (`q`로 종료)

상세한 tmux 사용법은 `TMUX-GUIDE.md`를 참조하세요.

- **재연결하기**: `./connect.sh` 실행
- **컨테이너 bash 접속**: `docker exec -it sdn-lab bash`

## 🧪 테스트 시나리오

### 1. 기본 연결성 테스트

```bash
# Mininet CLI에서 (자동으로 연결됨)
mininet> net          # 네트워크 토폴로지 확인
mininet> nodes        # 노드 목록 확인
mininet> links        # 링크 상태 확인
mininet> dump         # 모든 노드 정보

# 같은 컨트롤러 내 통신 테스트
mininet> h1 ping -c 3 h2    # Primary 내부 (s1)
mininet> h11 ping -c 3 h12  # Secondary 내부 (s6)
```

### 2. 크로스 컨트롤러 통신 테스트

```bash
# h1(Primary) ↔ h11(Secondary) 통신
mininet> h1 arp -s 10.0.0.11 00:00:00:00:00:0b
mininet> h11 arp -s 10.0.0.1 00:00:00:00:00:01
mininet> h1 ping -c 5 h11
mininet> h11 ping -c 5 h1
```

### 3. Flow 테이블 확인

```bash
# OpenFlow 룰 확인
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s1
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s3  # 게이트웨이
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s6
```

## 📊 네트워크 구성

```
                    s1 (Primary)
                   /         \
                 s2           s3
                / \          /  \
              s4   s5      s6   s7  ← 컨트롤러 경계
             / \    |       (Secondary)
           s8   s9  s10         

컨트롤러 할당:
- Primary Controller (포트 6700): s1, s2, s3, s4, s5
- Secondary Controller (포트 6800): s6, s7, s8, s9, s10
```

### 호스트 정보

| 호스트 | IP 주소 | MAC 주소 | 스위치 | 컨트롤러 |
|--------|---------|----------|--------|----------|
| h1-h2 | 10.0.0.1-2 | 00:00:00:00:00:01-02 | s1 | Primary |
| h3-h4 | 10.0.0.3-4 | 00:00:00:00:00:03-04 | s2 | Primary |
| h5-h6 | 10.0.0.5-6 | 00:00:00:00:00:05-06 | s3 | Primary |
| h7-h8 | 10.0.0.7-8 | 00:00:00:00:00:07-08 | s4 | Primary |
| h9-h10 | 10.0.0.9-10 | 00:00:00:00:00:09-0a | s5 | Primary |
| h11-h12 | 10.0.0.11-12 | 00:00:00:00:00:0b-0c | s6 | Secondary |
| h13-h14 | 10.0.0.13-14 | 00:00:00:00:00:0d-0e | s7 | Secondary |
| h15-h16 | 10.0.0.15-16 | 00:00:00:00:00:0f-10 | s8 | Secondary |
| h17-h18 | 10.0.0.17-18 | 00:00:00:00:00:11-12 | s9 | Secondary |
| h19-h20 | 10.0.0.19-20 | 00:00:00:00:00:13-14 | s10 | Secondary |

## 🛠️ 문제 해결

### Docker 관련

```bash
# 컨테이너 상태 확인
docker ps -a

# 컨테이너 로그 확인
docker logs sdn-lab

# 수동으로 컨테이너 정리
docker stop sdn-lab
docker rm sdn-lab

# 이미지 재빌드 (문제 해결 시)
docker rmi sdn-lab-image
./run-all.sh
```

### SDN Lab 관련

```bash
# 컨테이너 내부로 들어가기
docker exec -it sdn-lab bash

# OVS 상태 확인
ovs-vsctl show

# 서비스 상태 확인
systemctl status sdn-lab

# 로그 확인
journalctl -u sdn-lab -n 100

# 수동으로 SDN 환경 시작
cd /network-lab
./start_sdn.sh
```

## 🧩 고급 사용법

### 다중 테스트 시나리오

```bash
# 시나리오 1: 전체 연결성
mininet> pingall

# 시나리오 2: 특정 경로 테스트
mininet> h1 traceroute h11

# 시나리오 3: 대역폭 테스트
mininet> iperf h1 h11

# 시나리오 4: 패킷 캡처
mininet> h1 tcpdump -i h1-eth0 -w capture.pcap &
mininet> h2 ping -c 10 h1
```

### OpenFlow 디버깅

```bash
# Flow 통계 실시간 모니터링
mininet> sh watch ovs-ofctl -O OpenFlow13 dump-flows s1

# 포트 통계 확인
mininet> sh ovs-ofctl -O OpenFlow13 dump-ports s1

# 그룹 테이블 확인
mininet> sh ovs-ofctl -O OpenFlow13 dump-groups s1
```

## 📝 학습 목표

1. **Multi-Controller SDN**: 분산 컨트롤러 아키텍처 이해
2. **Gateway-based Routing**: 게이트웨이 기반 크로스 컨트롤러 통신
3. **MAC Address Domain**: MAC 주소 기반 도메인 라우팅
4. **OpenFlow 1.3**: 플로우 룰 설치 및 관리
5. **Docker Networking**: 컨테이너 기반 SDN 환경 구축

## 🔧 환경 초기화

```bash
# 모든 것을 정리하고 다시 시작
docker stop sdn-lab && docker rm sdn-lab
docker rmi sdn-lab-image
./run.sh
```

## 📚 추가 자료

- [RYU SDN Framework](https://ryu-sdn.org/)
- [OpenFlow 1.3 Specification](https://opennetworking.org/software-defined-standards/specifications/)
- [Mininet Documentation](http://mininet.org/)

## 라이선스

교육 목적으로 자유롭게 사용 가능합니다.
