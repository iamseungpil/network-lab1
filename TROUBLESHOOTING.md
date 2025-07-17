# 🚨 Docker Build Error 해결 가이드

## 문제 원인
Docker 빌드 중 발생한 에러는 Windows와 Linux 간의 줄바꿈 문자 차이 때문입니다.
- Windows: CRLF (`\r\n`)
- Linux/Docker: LF (`\n`)

## 🔧 해결 방법

### 방법 1: 자동 수정 스크립트 사용 (권장)
```bash
# 줄바꿈 문제 해결 및 실행 권한 부여
./fix-line-endings.sh

# Docker 이미지 빌드
docker build -t sdn-lab-image .

# 자동 실행
./run-all.sh
```

### 방법 2: 수동 해결
```bash
# dos2unix가 있는 경우
dos2unix docker-scripts/*.sh
dos2unix *.sh

# 또는 sed 사용
find . -name "*.sh" -type f -exec sed -i 's/\r$//' {} \;

# 실행 권한 부여
chmod +x *.sh
chmod +x docker-scripts/*.sh
```

### 방법 3: Git 설정으로 자동 해결
```bash
# Git이 자동으로 줄바꿈을 처리하도록 설정
git config --global core.autocrlf input
```

## 📁 필수 파일 구조
```
network-lab1/
├── docker-scripts/
│   ├── docker-start-sdn.sh
│   ├── init-ovs.sh
│   └── stop-sdn.sh
├── Dockerfile
├── requirements.txt
├── run-all.sh
├── run-background.sh
├── docker-run.sh
└── fix-line-endings.sh
```

## 🔍 확인사항
1. `docker-scripts/` 폴더가 존재하는지 확인
2. 모든 `.sh` 파일이 LF 줄바꿈을 사용하는지 확인
3. Docker가 실행 중인지 확인

## 💡 추가 팁
- VS Code 사용 시 우측 하단에서 CRLF를 LF로 변경 가능
- `.gitattributes` 파일이 줄바꿈 설정을 관리함

## 🚀 빌드 성공 후
```bash
# 자동 실행
./run-all.sh

# 또는 백그라운드 실행
./run-background.sh
```

## 🐛 일반적인 문제들

### 1. Permission denied
```bash
chmod +x *.sh
chmod +x docker-scripts/*.sh
```

### 2. 포트 충돌
```bash
# 사용 중인 포트 확인
netstat -tlnp | grep -E '6700|6800'

# 또는
docker ps --filter "publish=6700"
docker ps --filter "publish=6800"
```

### 3. 컨테이너가 이미 존재함
```bash
docker stop sdn-lab
docker rm sdn-lab
```

### 4. Git Bash 경로 변환 문제

**증상**: "C:/Users/.../Git/sbin/init: no such file or directory" 에러

**해결 방법**:
```bash
# 이미 스크립트에 포함되어 있음
export MSYS_NO_PATHCONV=1

# 또는 수동으로 실행 시
MSYS_NO_PATHCONV=1 docker run ...
```

**대체 방법**:
- WSL2 사용
- Docker Desktop의 터미널 사용
- CMD에서 Git Bash로 스크립트 실행: `bash ./run-all.sh`

### 5. SDN 스크립트를 찾을 수 없음

**증상**: "SDN start script not found!" 에러

**해결 방법**:
```bash
# 1. 컨테이너 상태 확인
./test-container.sh

# 2. 컨테이너 재빌드
./rebuild.sh

# 3. 다시 실행
./run-all.sh
```

**수동 해결**:
```bash
# 컨테이너 접속
docker exec -it sdn-lab bash

# 스크립트 확인
ls -la /docker-start-sdn.sh
ls -la /network-lab/

# 직접 실행
/docker-start-sdn.sh
# 또는
cd /network-lab && ./start_sdn.sh
```

### 6. 상세 로그 확인
```bash
# Docker 빌드 로그
docker build --no-cache --progress=plain -t sdn-lab-image .

# 컨테이너 로그
docker logs sdn-lab

# 컨트롤러 로그
docker exec -it sdn-lab tail -f /tmp/sdn.log
```
