FROM python:3.10-slim

# 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
RUN pip install requests click tabulate

# 작업 디렉토리 설정
WORKDIR /app

# CLI 시작 스크립트
COPY start-cli.sh /app/
RUN chmod +x /app/start-cli.sh

CMD ["/app/start-cli.sh"]