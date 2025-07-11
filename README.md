# SDN Lab1: Mininet + RYU

## 프로젝트 개요
Software Defined Network (SDN) 실습을 위한 Docker 기반 프로젝트입니다.

### 목표
- RYU 컨트롤러와 Mininet을 사용한 SDN 모델 구축
- 10개 스위치와 2개 컨트롤러로 구성된 네트워크
- REST API를 통한 플로우 규칙 관리
- 간단한 CLI 인터페이스 제공

### 주요 기능
- ✅ 10개 스위치 트리 토폴로지
- ✅ Primary/Secondary 컨트롤러 구성
- ✅ L2 Learning Switch 기능
- ✅ REST API 기반 플로우 관리
- ✅ 실시간 네트워크 모니터링
- ✅ Docker 컨테이너 기반 격리

## 프로젝트 구조
```
starmooc-lab1/
├── README.md                    # 프로젝트 개요
├── docs/                       # 상세 문서
│   ├── setup-guide.md          # 설치 가이드
│   └── network-topology.md     # 네트워크 구조
├── docker/                     # Docker 설정
│   ├── cli/                    # CLI 컨테이너
│   ├── controller/             # RYU 컨트롤러 컨테이너
│   ├── mininet/               # Mininet 컨테이너
│   └── compose/               # Docker Compose 설정
├── scripts/                    # 실행 스크립트
├── mininet/                    # Mininet 토폴로지 코드
├── ryu-controllers/            # RYU 컨트롤러 애플리케이션
├── cli/                        # CLI 인터페이스
├── config/                     # 설정 파일
└── tests/                      # 테스트 코드
```

## 빠른 시작

### 1. 환경 설치
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

### 4. 환경 종료
```bash
./stop-sdn.sh
```

## 네트워크 구조

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│     CLI     │     │ Controller 1 │     │ Controller 2 │
│  (명령어)    │────▶│   (Primary)  │     │  (Secondary) │
└─────────────┘     └──────┬───────┘     └──────┬───────┘
     REST API              │ OpenFlow           │ OpenFlow
                          ▼                    ▼
                    ┌─────────────────────────────┐
                    │      Mininet Network        │
                    │    (10 Switches + 20 Hosts) │
                    └─────────────────────────────┘
```

## 주요 명령어

### CLI 명령어
- `status`: 네트워크 상태 확인
- `list-flows`: 플로우 테이블 조회
- `add-flow`: 플로우 규칙 추가
- `monitor`: 실시간 모니터링

### REST API
- `GET /flows`: 플로우 테이블 조회
- `POST /flows`: 플로우 규칙 추가

## 액세스 정보
- **Primary Controller**: http://localhost:8080
- **Secondary Controller**: http://localhost:8081
- **Mininet Monitor**: http://localhost:8082

## 문서
- [설치 가이드](docs/setup-guide.md)
- [네트워크 토폴로지](docs/network-topology.md)

## 과제 요구사항 충족
- ✅ 10개 스위치 네트워크 구성
- ✅ 2개 컨트롤러 (Primary/Secondary)
- ✅ 플로우 규칙 설정 CLI 인터페이스
- ✅ 설치 및 실행 스크립트
- ✅ 상세 설정 문서