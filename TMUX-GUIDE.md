# SDN Lab tmux 사용 가이드

## 개선된 tmux 기반 실행

기존 screen 대신 tmux를 사용하여 더 안정적이고 interactive한 환경을 제공합니다.

### 🚀 빠른 시작

```bash
# 1. 실행 권한 설정
./make-executable.sh

# 2. tmux 기반 실행 (권장)
./run-all-tmux.sh
```

### 📖 tmux 기본 조작법

#### 세션 구조
- **Window 0 (controllers)**: RYU 컨트롤러들이 실행됨
- **Window 1 (mininet)**: Mininet CLI가 실행됨 (기본 활성 윈도우)

#### 주요 단축키
| 키 조합 | 기능 |
|---------|------|
| `Ctrl+B, 0` | 컨트롤러 윈도우로 이동 |
| `Ctrl+B, 1` | Mininet 윈도우로 이동 |
| `Ctrl+B, N` | 다음 윈도우 |
| `Ctrl+B, P` | 이전 윈도우 |
| `Ctrl+B, D` | tmux 세션에서 detach (백그라운드 실행 유지) |
| `Ctrl+B, [` | 스크롤 모드 (q로 종료) |
| `Ctrl+C` | Mininet CLI에서 정상 동작 |

### 🔧 개별 컴포넌트 실행

분리된 스크립트로 개별 컴포넌트를 실행할 수 있습니다:

```bash
# 컨트롤러만 시작
./start_controllers.sh

# Mininet만 시작 (다른 터미널에서)
./start_mininet.sh
```

### 📊 네트워크 테스트

Mininet CLI에서 사용할 수 있는 주요 명령어:

```bash
# 모든 호스트 간 연결 테스트
mininet> pingall

# 크로스 컨트롤러 통신 테스트
mininet> h1 ping h11

# 네트워크 정보 확인
mininet> dump
mininet> links

# 특정 호스트 간 통신
mininet> h1 ping h20
```

### 🔄 세션 재연결

tmux 세션이 detach되었거나 연결이 끊어진 경우:

```bash
# 기존 세션에 재연결
docker exec -it sdn-lab tmux attach-session -t sdn-lab

# 또는 스크립트로 재실행
./run-all-tmux.sh
```

### 🏗️ 컨트롤러 구조

- **Primary Controller** (포트 6700): 스위치 s1-s5 관리
- **Secondary Controller** (포트 6800): 스위치 s6-s10 관리
- **게이트웨이 기반 크로스 컨트롤러 통신** 지원

### 🐛 문제 해결

#### tmux 세션 상태 확인
```bash
# 컨테이너 내부에서 세션 목록 확인
docker exec sdn-lab tmux list-sessions

# 특정 윈도우 상태 확인
docker exec sdn-lab tmux list-windows -t sdn-lab
```

#### 세션 강제 종료
```bash
# 특정 세션 종료
docker exec sdn-lab tmux kill-session -t sdn-lab

# 모든 tmux 세션 종료
docker exec sdn-lab tmux kill-server
```

#### 컨트롤러 상태 확인
```bash
# 컨트롤러 프로세스 확인
docker exec sdn-lab ps aux | grep ryu-manager

# 포트 확인
docker exec sdn-lab netstat -tlnp | grep -E "6700|6800"
```

### ⚡ 성능 최적화

tmux는 screen보다 다음과 같은 장점이 있습니다:

- ✅ 더 안정적인 세션 관리
- ✅ 향상된 터미널 호환성
- ✅ 더 나은 키보드 단축키 지원
- ✅ 윈도우 분할 및 관리 기능
- ✅ 세션 지속성 개선

### 📝 추가 팁

1. **윈도우 간 이동**: `Ctrl+B` 후 윈도우 번호 (0, 1)를 누르면 빠르게 이동
2. **로그 확인**: 컨트롤러 윈도우에서 실시간으로 RYU 로그 확인 가능
3. **세션 유지**: `Ctrl+B, D`로 detach하면 컨테이너가 계속 실행됨
4. **멀티태스킹**: 여러 터미널에서 동시에 같은 tmux 세션에 접속 가능

### 🚨 주의사항

- Mininet CLI에서 `exit` 입력 시 전체 네트워크가 종료됩니다
- 컨트롤러 윈도우에서 프로세스 종료 시 네트워크 연결이 끊어집니다
- tmux 세션 종료 전에 항상 Mininet을 정상 종료해주세요
