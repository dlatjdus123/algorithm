# ==============================================================================
# Google Cloud Run 배포용 Dockerfile
# ==============================================================================
# 경량화된 공식 Python 슬림 이미지 사용
FROM python:3.11-slim

# 파이썬 출력 버퍼링 비활성화 (로그가 Cloud Run 콘솔에 실시간으로 표시되도록 설정)
ENV PYTHONUNBUFFERED=1

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사 및 설치 (캐시 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 전체 소스코드 복사
COPY . .

# Cloud Run 기본 포트 환경변수 설정 (기본값 8080)
ENV PORT=8080

# Cloud Run 프로덕션용 Gunicorn 웹 서버 실행
# - workers: 1 (Cloud Run의 컨테이너당 인스턴스 특성에 맞춰 동시성은 스레드로 처리 권장)
# - threads: 8 (I/O 및 가벼운 CPU 바운드 요청 병렬 처리)
# - timeout: 0 (Cloud Run의 요청 타임아웃 처리에 위임)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app

