# SDN Network Lab - Docker Environment

이 프로젝트는 Mininet과 RYU 컨트롤러를 사용하는 SDN 네트워크 실험 환경입니다.

## 🐳 Docker 환경 구성

### 사전 요구사항
- Docker가 설치되어 있어야 합니다
- Linux/Mac 또는 WSL2/Git Bash 환경

> 💡 **Git Bash 사용 시**: 모든 스크립트에 `MSYS_NO_PATHCONV=1`이 포함되어 있어 경로 변환 문제가 자동 해결됩니다.

### 🔧 초기 설정

Docker 빌드 전에 줄바꿈 문제를 해결하고 실행 권한을 부여합니다:

```bash
# 줄바꿈 수정 및 실행 권한 부여
./fix-line-endings.sh

# 또는 실행 권한만 부여
chmod +x *.sh
chmod +x docker-scripts/*.sh
```

### 빠른 시작 (자동 실행)

#### 통합 실행 스크립트 사용 (권장)
```bash
./run-all.sh
```

이 스크립트는 Docker 컨테이너를 생성하고 SDN 실험을 자동으로 시작합니다.

#### 백그라운드 실행
```bash
./run-background.sh
```

### 수동 실행 방법

#### 1. 컨테이너만 생성
```bash
./docker-run.sh
```

#### 2. 컨테이너 접속 후 수동 실행
```bash
# 컨테이너 접속
docker exec -it sdn-lab bash

# 실험 환경 시작
cd /network-lab
./docker-start-sdn.sh
```

## 🏗️ 네트워크 구조

### 토폴로지
- **스위치**: 10개 (s1-s10)
- **호스트**: 20개 (h1-h20)
- **컨트롤러**: 2개
  - Primary Controller (포트 6700): s1-s5 관리
  - Secondary Controller (포트 6800): s6-s10 관리

### 스위치 연결 구조 (트리 토폴로지)
```
        s1
       /  \
      s2   s3
     / \   / \
    s4 s5 s6 s7
   / \    |
  s8 s9  s10
```

## 🎯 실행 모드

### 인터랙티브 모드 (기본)
```bash
./run-all.sh
```

### 백그라운드 실행 모드
```bash
# 백그라운드로 시작
./run-background.sh

# 또는 컨테이너 내부에서
./docker-start-sdn.sh --background

# Mininet CLI 접속
docker exec -it sdn-lab screen -r mininet

# Screen 세션에서 나가기: Ctrl+A, D
```

### 실시간 로그 확인
```bash
# 컨트롤러 로그 확인
docker exec -it sdn-lab tail -f /tmp/sdn.log

# 컨트롤러 프로세스 확인
docker exec sdn-lab ps aux | grep ryu-manager
```

### 환경 중지
```bash
# 컨테이너 내부에서
/stop-sdn.sh

# 또는 호스트에서
docker exec sdn-lab /stop-sdn.sh
```

## 🧪 실험 방법

### 기본 연결성 테스트
```bash
mininet> pingall
```

### 특정 호스트 간 통신 테스트
```bash
mininet> h1 ping h10
```

### 네트워크 정보 확인
```bash
mininet> dump
mininet> links
mininet> net
```

### ARP 테이블 설정 (크로스 컨트롤러 통신)
```bash
mininet> h1 arp -s 10.0.0.11 00:00:00:00:00:0b
```

## 🛠️ 문제 해결

### 줄바꿈 문제
```bash
# dos2unix가 있는 경우
dos2unix docker-scripts/*.sh

# sed 사용
sed -i 's/\r$//' docker-scripts/*.sh
```

### 컨테이너 로그 확인
```bash
docker logs sdn-lab
```

### OVS 상태 확인 (컨테이너 내부)
```bash
ovs-vsctl show
ovs-ofctl dump-flows s1
```

### 컨테이너 재시작
```bash
docker stop sdn-lab
docker start sdn-lab
docker exec -it sdn-lab bash
```

## 📝 주의사항

1. **Privileged 모드**: 이 컨테이너는 네트워크 네임스페이스 생성을 위해 privileged 모드로 실행됩니다.
2. **systemd**: Mininet이 정상 작동하려면 systemd가 필요하므로 `/sbin/init`으로 시작합니다.
3. **포트**: 6700, 6800 포트가 호스트에서 사용 가능해야 합니다.

## 🔧 개발 환경

- Ubuntu 22.04 베이스 이미지
- Python 3.10
- Mininet 2.3.0
- RYU 4.34
- Open vSwitch

## 📚 추가 리소스

- [Mininet Documentation](http://mininet.org/)
- [RYU SDN Framework](https://ryu-sdn.org/)
- [OpenFlow Specification](https://www.opennetworking.org/software-defined-standards/specifications/)
