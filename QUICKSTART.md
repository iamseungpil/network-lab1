# 🚀 SDN Lab - Quick Start Guide (Windows + Docker)

## 1분 안에 시작하기!

### 📋 최소 요구사항
- Windows 10/11
- Docker Desktop 설치됨
- 8GB RAM 이상
- 10GB 디스크 공간

### 🎯 가장 빠른 시작 방법

#### 옵션 1: 메뉴 방식 (가장 쉬움)
```cmd
sdn_lab_menu.bat
```
메뉴에서 숫자를 선택하여 실행

#### 옵션 2: PowerShell 직접 실행
```powershell
# 1단계: 시작
.\start_sdn_docker.ps1 start

# 2단계: 데모 실행
.\start_sdn_docker.ps1 run ring
```

#### 옵션 3: Docker Compose
```bash
# 시작
docker-compose up -d

# 컨테이너 접속
docker exec -it sdn-lab bash

# 컨테이너 내부에서 데모 실행
cd /opt/sdn-lab
./start_sdn_demo.sh ring
```

### 🧪 테스트 명령어 (Mininet CLI)

데모가 실행되면 다음 명령어를 입력해보세요:

```bash
# 1. 기본 연결 테스트
h1 ping -c 3 h4

# 2. 링크 실패 시뮬레이션
link s1 s2 down

# 3. 재라우팅 확인
h1 ping -c 3 h4

# 4. 링크 복구
link s1 s2 up

# 5. 전체 테스트
pingall

# 6. 종료
exit
```

### 📊 무엇을 확인해야 하나요?

컨트롤러 로그에서 다음을 확인하세요:
- `🔌 [OPENFLOW] Switch connected` - 스위치 연결
- `🔗 [LINK UP]` - 링크 발견
- `🛤️ DIJKSTRA PATH` - 경로 계산
- `🔴 [PORT EVENT]` - 링크 다운 감지
- `✅ Connectivity maintained` - 재라우팅 성공

### 🛑 종료 방법

```powershell
# PowerShell
.\start_sdn_docker.ps1 stop

# 또는 Docker Compose
docker-compose down
```

### ❓ 문제가 있나요?

1. **Docker가 실행되지 않음**
   → Docker Desktop을 시작하세요

2. **Permission denied**
   → PowerShell을 관리자 권한으로 실행

3. **포트 충돌**
   → 6633, 6653 포트가 사용 중인지 확인

### 📚 더 알아보기
- [상세 가이드](README_DOCKER_WINDOWS.md)
- [기술 문서](SDN_LAB_COMPREHENSIVE_GUIDE.md)

---
**💡 팁**: 처음이라면 `sdn_lab_menu.bat`로 시작하는 것을 추천합니다!
