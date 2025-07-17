# 🚀 SDN Lab - Shell Scripts Only

이 프로젝트는 shell 스크립트만을 사용하여 Docker 기반 SDN 실험 환경을 구성합니다.

## 📋 스크립트 목록

### 메인 스크립트
- `run-all.sh` - Docker 컨테이너 생성 및 SDN 실험 자동 시작 (권장)
- `run-gitbash.sh` - Git Bash 호환 버전
- `run-background.sh` - 백그라운드 모드로 실행
- `docker-run.sh` - 컨테이너만 생성 (수동 실행용)

### 유틸리티 스크립트
- `fix-line-endings.sh` - 줄바꾸기 문제 해결 및 실행 권한 부여
- `make-executable.sh` - 모든 스크립트에 실행 권한 부여
- `rebuild.sh` - 컨테이너 전체 재빌드
- `test-container.sh` - 컨테이너 설정 테스트
- `debug-container.sh` - 컨테이너 문제 디버그

### Docker 내부 스크립트 (`docker-scripts/`)
- `docker-start-sdn.sh` - SDN 환경 시작
- `init-ovs.sh` - Open vSwitch 초기화
- `stop-sdn.sh` - SDN 환경 중지

## 🏃 빠른 시작

```bash
# 1. 초기 설정 (처음 한 번만)
./fix-line-endings.sh

# 2. 자동 실행
./run-all.sh
```

## 🔧 문제 해결

```bash
# 컨테이너 재빌드가 필요한 경우
./rebuild.sh
./run-all.sh

# Git Bash에서 문제가 있는 경우
./run-gitbash.sh

# 컨테이너 상태 확인
./test-container.sh
```

## 📖 자세한 문서
- [QUICK-START.md](QUICK-START.md) - 빠른 시작 가이드
- [README-Docker.md](README-Docker.md) - Docker 환경 상세 문서
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - 문제 해결 가이드

## 📝 참고
- Windows 전용 스크립트들은 `old-windows-scripts/` 폴더로 이동되었습니다
- 모든 작업은 shell 스크립트로만 수행됩니다
- Git Bash, WSL2, Linux, Mac에서 사용 가능합니다
- Git Bash 사용 시 경로 변환 문제는 자동 해결됩니다 (`MSYS_NO_PATHCONV=1`)
