FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# pyproject + 소스만 먼저 복사 (deps 변경 없을 때 캐시 활용)
COPY apps/api/pyproject.toml ./
COPY apps/api/src ./src

RUN pip install --no-cache-dir -e .[ml]

# Demucs/CREPE 모델 가중치를 이미지에 미리 베이크 → 첫 요청 콜드스타트 단축
# (Basic Pitch 는 패키지에 번들되어 있어 별도 다운로드 없음)
RUN python -c "from demucs.pretrained import get_model; get_model('htdemucs')" \
    || echo "WARN: Demucs 모델 사전 다운로드 실패 (런타임에 재시도)"
RUN python -c "import numpy as np, crepe; crepe.predict(np.zeros(16000, dtype=np.float32), 16000, viterbi=False, step_size=100, verbose=0)" \
    || echo "WARN: CREPE 모델 사전 다운로드 실패 (런타임에 재시도)"

ENV STORAGE_DIR=/data
RUN mkdir -p /data

COPY apps/api/start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

EXPOSE 8000
CMD ["/usr/local/bin/start.sh"]
