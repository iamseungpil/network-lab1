# SDN Lab1 설치 및 설정 가이드

## 시스템 요구사항
- Ubuntu 20.04 LTS 이상
- Docker 및 Docker Compose
- 최소 4GB RAM, 20GB 디스크 공간

## 설치 과정

### 1. 기본 환경 설치
```bash
cd starmooc-lab1/scripts
./install-all.sh
```

### 2. SDN 환경 시작
```bash
./start-sdn.sh
```

### 3. CLI 접속
```bash
docker exec -it sdn-cli python3 /app/cli/flow_cli.py interactive
```

## 네트워크 구조

### 토폴로지
- **스위치**: 10개 (s1 ~ s10)
- **호스트**: 20개 (h1 ~ h20, 각 스위치당 2개)
- **컨트롤러**: 2개 (Primary, Secondary)

### 연결 구조 (트리 토폴로지)
```
        s1 (Root)
       /  \
      s2   s3
     / |   | \
    s4 s5  s6 s7
   /| |      
  s8 s9 s10  
```

### 호스트 배치
- s1: h1, h2
- s2: h3, h4
- s3: h5, h6
- ... (각 스위치당 2개 호스트)

## 컨트롤러 구성

### Primary Controller (controller1)
- **포트**: 6633 (OpenFlow), 8080 (REST API)
- **역할**: 메인 컨트롤러, 플로우 관리
- **기능**: L2 스위칭, REST API 제공

### Secondary Controller (controller2)
- **포트**: 6634 (OpenFlow), 8081 (REST API)
- **역할**: 백업 컨트롤러
- **기능**: 장애 시 Primary 대체

## CLI 명령어

### 기본 명령어
```bash
# 네트워크 상태 확인
python3 flow_cli.py status

# 플로우 테이블 조회
python3 flow_cli.py list-flows

# 플로우 추가
python3 flow_cli.py add-flow --dpid 1 --output 2 --in-port 1

# 컨트롤러 전환
python3 flow_cli.py switch-controller --controller secondary

# 실시간 모니터링
python3 flow_cli.py monitor

# 대화형 모드
python3 flow_cli.py interactive
```

## 테스트 시나리오

### 1. 기본 연결 테스트
```bash
# Mininet CLI에서
mininet> pingall
```

### 2. 플로우 추가 테스트
```bash
# CLI에서 플로우 추가
add-flow --dpid 1 --in-port 1 --eth-dst aa:aa:aa:aa:aa:aa --output 2
```

### 3. 컨트롤러 장애 테스트
```bash
# Primary 컨트롤러 중지
docker stop sdn-controller1

# Secondary 컨트롤러로 자동 전환 확인
```

## 문제 해결

### 컨테이너 로그 확인
```bash
docker logs sdn-controller1
docker logs sdn-controller2
docker logs sdn-mininet
```

### 네트워크 재시작
```bash
./stop-sdn.sh
./start-sdn.sh
```

### 포트 충돌 해결
```bash
# 사용 중인 포트 확인
netstat -tlnp | grep :8080

# 프로세스 종료
sudo kill -9 <PID>
```