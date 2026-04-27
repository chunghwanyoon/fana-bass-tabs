# HF Spaces (Docker) 용 Dockerfile.
# build context = repo root. apps/api/* 경로가 그대로 동작.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces 는 비루트 사용자 (UID 1000) 권장
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    STORAGE_DIR=/home/user/data

WORKDIR /home/user/app

# pyproject + 소스 복사 (deps 변경 없을 때 캐시 활용)
COPY --chown=user apps/api/pyproject.toml ./
COPY --chown=user apps/api/src ./src

RUN pip install --no-cache-dir --user -e .[ml]

# Demucs/CREPE 가중치 사전 베이크 → 첫 요청 콜드스타트 단축
# (Basic Pitch 는 패키지 번들이라 별도 다운로드 없음)
RUN python -c "from demucs.pretrained import get_model; get_model('htdemucs')" \
    || echo "WARN: Demucs 모델 사전 다운로드 실패 (런타임 재시도)"
RUN python -c "import numpy as np, crepe; crepe.predict(np.zeros(16000, dtype=np.float32), 16000, viterbi=False, step_size=100, verbose=0)" \
    || echo "WARN: CREPE 모델 사전 다운로드 실패 (런타임 재시도)"

RUN mkdir -p /home/user/data

COPY --chown=user apps/api/start.sh /home/user/start.sh

EXPOSE 8000
CMD ["bash", "/home/user/start.sh"]
