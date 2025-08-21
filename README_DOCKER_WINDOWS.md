# SDN Lab - Docker Windows Guide

## 🐳 Docker를 사용한 Windows 실행 가이드

이 가이드는 Windows 환경에서 Docker를 사용하여 SDN (Software-Defined Networking) 데모를 실행하는 방법을 설명합니다.

### 📋 사전 요구사항

1. **Docker Desktop for Windows** 설치
   - [Docker Desktop 다운로드](https://www.docker.com/products/docker-desktop/)
   - WSL2 백엔드 활성화 권장

2. **Git Bash 또는 PowerShell** (Windows Terminal 권장)

### 🚀 빠른 시작

#### PowerShell 사용 (권장)

```powershell
# 1. SDN Lab 시작 (컨테이너 빌드 및 실행)
.\start_sdn_docker.ps1 start

# 2. 데모 실행 (ring 토폴로지)
.\start_sdn_docker.ps1 run ring

# 3. 컨테이너 접속
.\start_sdn_docker.ps1 connect

# 4. 컨트롤러 로그 확인
.\start_sdn_docker.ps1 logs

# 5. 종료
.\start_sdn_docker.ps1 stop
```

#### Git Bash 사용

```bash
# 1. SDN Lab 시작
./start_sdn_docker.sh start

# 2. 데모 실행
./start_sdn_docker.sh run ring

# 3. 컨테이너 접속
./start_sdn_docker.sh connect

# 4. 종료
./start_sdn_docker.sh stop
```

#### Docker Compose 사용

```bash
# 시작
docker-compose up -d

# 접속
docker exec -it sdn-lab bash

# 종료
docker-compose down
```

### 📖 상세 사용법

#### 1. 컨테이너 시작 및 초기화

```powershell
.\start_sdn_docker.ps1 start
```

이 명령은 다음 작업을 수행합니다:
- Docker 이미지 빌드 (Ubuntu 22.04 기반)
- systemd를 포함한 privileged 컨테이너 시작
- Open vSwitch 서비스 시작
- Mininet 환경 초기화

#### 2. SDN 데모 실행

세 가지 토폴로지를 선택할 수 있습니다:

```powershell
# Diamond 토폴로지 (4개 스위치)
.\start_sdn_docker.ps1 run diamond

# Ring 토폴로지 (10개 스위치)
.\start_sdn_docker.ps1 run ring

# Graph 토폴로지 (복잡한 구조)
.\start_sdn_docker.ps1 run graph
```

#### 3. Mininet CLI에서 테스트

데모가 시작되면 Mininet CLI가 표시됩니다:

```bash
# 기본 연결 테스트
mininet> h1 ping h4

# 링크 실패 시뮬레이션
mininet> link s1 s2 down
mininet> h1 ping h4  # 대체 경로로 재라우팅

# 링크 복구
mininet> link s1 s2 up

# 전체 연결 테스트
mininet> pingall

# 종료
mininet> exit
```

#### 4. 컨트롤러 로그 모니터링

별도 터미널에서 실시간 로그 확인:

```powershell
.\start_sdn_docker.ps1 logs
```

로그에서 확인할 수 있는 내용:
- 🔌 OpenFlow 스위치 연결
- 🔗 LLDP 토폴로지 발견
- 📦 패킷 처리 과정
- 🛤️ Dijkstra 경로 계산
- 💥 링크 실패 감지
- ✅ 자동 재라우팅

### 🔧 문제 해결

#### Docker Desktop이 시작되지 않는 경우

1. WSL2 설치 확인:
```powershell
wsl --install
wsl --set-default-version 2
```

2. Hyper-V 활성화 확인:
```powershell
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
```

#### 컨테이너가 시작되지 않는 경우

```powershell
# 기존 컨테이너 정리
docker stop sdn-lab
docker rm sdn-lab

# 이미지 재빌드
.\start_sdn_docker.ps1 rebuild

# 다시 시작
.\start_sdn_docker.ps1 start
```

#### Permission denied 오류

PowerShell을 관리자 권한으로 실행하거나, Docker Desktop 설정에서 드라이브 공유를 활성화하세요.

### 📂 프로젝트 구조

```
network-lab1/
├── Dockerfile                 # Docker 이미지 정의
├── docker-compose.yml        # Docker Compose 설정
├── start_sdn_docker.sh       # Bash 실행 스크립트
├── start_sdn_docker.ps1      # PowerShell 실행 스크립트
├── ryu-controller/
│   ├── main_controller.py    # 기본 컨트롤러
│   └── main_controller_stp.py # STP 포함 컨트롤러
└── mininet/
    ├── ring_topology.py      # 10-스위치 링
    ├── diamond_topology.py   # 4-스위치 다이아몬드
    └── graph_topology.py     # 복잡한 그래프
```

### 🎯 주요 기능

1. **Dijkstra 최단 경로 라우팅**: NetworkX를 사용한 동적 경로 계산
2. **자동 토폴로지 발견**: LLDP를 통한 네트워크 구조 자동 감지
3. **링크 실패 대응**: 실시간 링크 상태 감지 및 재라우팅
4. **STP 루프 방지**: 링 토폴로지에서 브로드캐스트 스톰 방지

### 📊 성능 메트릭

| 메트릭 | 값 | 설명 |
|--------|-----|------|
| LLDP 간격 | 5초 | 토폴로지 갱신 주기 |
| 경로 계산 | <1ms | 10-스위치 토폴로지 |
| 재라우팅 시간 | ~3초 | 감지 + 재계산 |
| Flow 타임아웃 | 30초 | 변경사항 적응 |

### 🐛 디버깅 팁

1. **컨테이너 내부 접속**:
```powershell
.\start_sdn_docker.ps1 connect
```

2. **Open vSwitch 상태 확인**:
```bash
ovs-vsctl show
ovs-dpctl dump-flows
```

3. **Mininet 정리**:
```bash
mn -c
```

4. **컨트롤러 재시작**:
```bash
pkill -f ryu-manager
ryu-manager --observe-links ryu-controller/main_controller_stp.py
```

### 📚 추가 문서

- [SDN_LAB_COMPREHENSIVE_GUIDE.md](SDN_LAB_COMPREHENSIVE_GUIDE.md) - 기술 상세 가이드
- [Original README.md](README.md) - 원본 Ubuntu 가이드

### ⚠️ 주의사항

- Docker Desktop이 실행 중이어야 합니다
- 첫 실행 시 이미지 빌드에 5-10분 소요될 수 있습니다
- `--privileged` 옵션이 필요하므로 신뢰할 수 있는 환경에서만 실행하세요
- Windows Defender 방화벽이 포트 6633, 6653을 차단하지 않도록 확인하세요

### 🤝 기여

문제를 발견하거나 개선 사항이 있으면 이슈를 등록해주세요!
