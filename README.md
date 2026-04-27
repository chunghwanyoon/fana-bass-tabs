---
title: Fana Bass Tabs API
sdk: docker
app_port: 8000
pinned: false
short_description: 베이스 기타 자동 트랜스크립션 (오디오 → 악보 + 타브)
---

# Fana Bass Tabs

YouTube/SoundCloud 링크나 음원 파일에서 베이스 기타 파트의 **악보 (MusicXML) 와 타브** 를 자동 생성합니다.

> 위 YAML frontmatter 는 Hugging Face Spaces (Docker SDK) 가 읽는 메타데이터입니다. GitHub 에서는 보이지 않지만 HF Spaces 페이지의 제목/포트 설정에 사용됩니다.

## 스택

- **Backend**: Python 3.11 / FastAPI / arq (Redis 큐) / Demucs / Basic Pitch / CREPE / music21
- **Frontend**: TypeScript / Vite / React / OpenSheetMusicDisplay / VexFlow
- **배포**: Hugging Face Spaces (백엔드) + Vercel (프론트) + Upstash (Redis)

## 빠른 시작

자세한 셋업/실행/배포 가이드는 [CLAUDE.md](./CLAUDE.md) 참고.

```bash
# 1. Redis (로컬 개발용, 배포에는 Upstash 사용)
docker compose up -d redis

# 2. 백엔드
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e .[ml]
cp .env.example .env

# 3. 프론트엔드
cd ../../apps/web && pnpm install

# 4. 서비스 3개 (각각 별도 터미널)
uvicorn api.main:app --reload --app-dir src --port 8000   # apps/api 에서
arq api.worker.WorkerSettings                             # apps/api 에서
pnpm dev                                                  # apps/web 에서
```

## LLM-driven development

이 프로젝트는 사용자가 직접 코딩하지 않고 LLM 에이전트가 모든 작업을 수행합니다. 새 세션이 시작되면 **반드시 [CLAUDE.md](./CLAUDE.md) 를 먼저 읽으세요** — 아키텍처 결정, 컨벤션, 알려진 한계, 다음에 해야 할 일이 정리되어 있습니다.
