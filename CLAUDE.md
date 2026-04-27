# Fana Bass Tabs — LLM 작업 가이드

> 이 프로젝트는 **사용자가 직접 코딩하지 않고 LLM 에이전트가 모든 작업을 수행**하는 방식으로 진행됩니다. 새 세션이 시작될 때 이 문서를 먼저 읽고 컨텍스트를 파악하세요.

## 1. 프로젝트 목표

YouTube/SoundCloud 링크 또는 음원 파일을 입력받아, 곡의 **베이스 기타 파트**를 추출해 두 가지 결과물을 생성합니다:

1. **악보 스코어** — 베이스 클레프 표준 기보 (MusicXML)
2. **베이스 타브** — 프렛 위치 기반 타브 기보

베이스 외 다른 파트는 다루지 않습니다.

## 2. 절대 바꾸지 말아야 할 결정 (변경하려면 사용자에게 먼저 확인)

- **모노레포 구조**: `apps/api` (Python) + `apps/web` (TypeScript) 한 저장소
- **백엔드 언어는 Python**: 트랜스크립션 ML 라이브러리 (Demucs, Basic Pitch, CREPE) 가 Python 전용. Kotlin/Node 로 옮기지 말 것
- **잡 큐는 arq (Redis)**: ML 처리는 동기로 두지 말 것 (요청당 수십 초 ~ 수 분)
- **베이스 5현 기본 지원**: 사용자가 5현 베이스를 사용. 4현/5현 모두 지원. 드롭 D 는 불필요
- **MusicXML 을 스코어 교환 포맷으로 사용**: 프론트의 OpenSheetMusicDisplay 가 이걸 받음
- **타브는 VexFlow 로 직접 렌더**: OSMD 의 타브 지원이 불완전해서 분리됨

## 3. 아키텍처

```
┌─────────────────┐  HTTP  ┌──────────────┐  enqueue  ┌─────────┐
│ apps/web        │───────▶│ apps/api     │──────────▶│  Redis  │
│ Vite+React+TS   │  poll  │ FastAPI      │           │  (arq)  │
│ OSMD + VexFlow  │◀──────│              │           └────┬────┘
└─────────────────┘        └──────────────┘                │
                                  ▲                         │ pop job
                                  │ static files            ▼
                                  │              ┌──────────────────┐
                                  └──────────────│ apps/api         │
                                                 │ arq worker       │
                                                 │  └ yt-dlp        │
                                                 │  └ Demucs        │
                                                 │  └ Basic Pitch / │
                                                 │    CREPE         │
                                                 │  └ music21       │
                                                 └──────────────────┘
                                                          │
                                                          ▼
                                                   storage/<job_id>/
                                                   ├ source.wav
                                                   ├ htdemucs/.../bass.wav
                                                   ├ *.mid
                                                   └ score.musicxml
```

**파이프라인 단계** (`apps/api/src/api/worker.py:run_transcribe`):

1. `downloading` — yt-dlp 로 오디오 받기 (URL 입력시) / 파일 입력은 스킵
2. `separating` — Demucs `--two-stems=bass` 로 베이스 스템 추출
3. `transcribing` — Basic Pitch 또는 CREPE 로 오디오 → MIDI
4. `scoring` — librosa beat tracker 로 BPM 추정 → music21 로 MusicXML 생성, 프렛 위치 휴리스틱으로 타브 JSON 생성
5. `complete`

각 단계는 Redis 키 `job_stage:<job_id>` 에 기록되어 프론트엔드가 폴링으로 표시.

## 4. 디렉토리 맵

```
fana-bass-tabs/
├── CLAUDE.md                      # 이 문서
├── README.md                      # 짧은 외부용 요약
├── docker-compose.yml             # Redis 서비스
├── pnpm-workspace.yaml            # JS 워크스페이스 정의
├── package.json                   # 루트 스크립트 (dev:web 등)
├── .gitignore
│
├── apps/api/                      # Python 백엔드
│   ├── pyproject.toml             # 의존성 (ml, dev 는 optional)
│   ├── .env.example               # 환경변수 템플릿
│   └── src/api/
│       ├── main.py                # FastAPI 앱 + 엔드포인트
│       ├── worker.py              # arq 워커 (run_transcribe, WorkerSettings)
│       ├── config.py              # pydantic-settings
│       ├── schemas.py             # API I/O 모델 (Pydantic)
│       └── pipeline/
│           ├── download.py        # yt-dlp 래퍼
│           ├── separate.py        # Demucs subprocess 호출
│           ├── transcribe.py      # Basic Pitch / CREPE 백엔드
│           ├── tempo.py           # librosa BPM 추정
│           ├── score.py           # music21 MusicXML 생성
│           ├── tab.py             # 노트 → TabNote 변환
│           └── fretboard.py       # 4현/5현 튜닝 + 위치 선택 휴리스틱
│
└── apps/web/                      # TypeScript 프론트
    ├── package.json
    ├── vite.config.ts             # /api → :8000 프록시
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx                # 메인 화면 (URL/파일 입력 + 결과 표시)
        ├── api.ts                 # fetch 래퍼 + 폴링 헬퍼
        ├── types.ts               # 백엔드 스키마와 동기화된 타입
        ├── index.css
        └── components/
            ├── ScoreView.tsx      # OpenSheetMusicDisplay 래퍼
            └── TabView.tsx        # VexFlow TabStave 렌더 (BPM 기반 가변 음표)
```

## 5. 셋업 런북 (제로 → 실행)

전제: Python 3.11+, Node.js 20+, pnpm, ffmpeg, Docker (또는 로컬 Redis)

```bash
# Redis (둘 중 하나)
docker compose up -d redis
# 또는
brew install redis && brew services start redis

# 백엔드
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -e .         # 가벼운 deps
pip install -e .[ml]     # 무거운 ML deps (PyTorch, TensorFlow 등 — 시간 걸림)
cp .env.example .env

# 프론트엔드
cd ../../apps/web && pnpm install
```

## 6. 개발 시 동시에 실행해야 하는 프로세스 3개

각각 별도 터미널:

```bash
# 1) Redis (이미 docker compose up 했으면 스킵)

# 2) API 서버
cd apps/api && source .venv/bin/activate
uvicorn api.main:app --reload --app-dir src --port 8000

# 3) arq 워커 (실제 트랜스크립션은 여기서 실행됨)
cd apps/api && source .venv/bin/activate
arq api.worker.WorkerSettings

# 4) 프론트엔드
cd apps/web && pnpm dev    # http://localhost:5173
```

워커 없이 API만 띄우면 잡이 큐에만 쌓이고 처리되지 않음.

## 7. 주요 환경변수 (`apps/api/.env`)

| 키 | 기본값 | 설명 |
|---|---|---|
| `STORAGE_DIR` | `./storage` | 작업 산출물 저장 디렉토리 |
| `DEMUCS_MODEL` | `htdemucs` | `htdemucs` / `htdemucs_ft` / `mdx_extra` |
| `TRANSCRIBER` | `basic_pitch` | `basic_pitch` / `crepe` |
| `BASS_TUNING` | `5string` | `4string` / `5string` |
| `REDIS_URL` | `redis://localhost:6379` | arq 가 사용할 Redis |

## 8. API 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/health` | 헬스체크 |
| POST | `/transcribe/url` | `{source_url, transcriber?, tuning?}` → `{job_id, status}` |
| POST | `/transcribe/file` | `multipart/form-data` (file) → `{job_id, status}` |
| GET | `/jobs/{job_id}` | 잡 상태 폴링. 완료 시 `result` 포함 |
| GET | `/files/{job_id}/{filename}` | 산출물 정적 서빙 (MusicXML, MIDI 등) |

응답 스키마는 `apps/api/src/api/schemas.py` 가 단일 진실의 원천. 프론트의 `apps/web/src/types.ts` 는 이걸 손으로 동기화해야 함 (자동 생성 안 함).

## 9. 코드 컨벤션

### Python
- 타입 힌트 필수, `from __future__ import annotations` 사용 안 함 (Python 3.11+ 이라 불필요)
- ruff 로 린트 (`pyproject.toml [tool.ruff]`)
- Pydantic v2 (`model_dump()` 등)
- 외부 IO 는 가능하면 async, 무거운 ML 은 동기여도 OK (워커 안에서 실행되므로)

### TypeScript
- strict 모드, `noUnusedLocals/Parameters` true
- React 함수형 컴포넌트만, hooks 는 useEffect/useState 위주
- 백엔드 응답 타입은 `types.ts` 에 손으로 정의 (스키마 변경 시 양쪽 같이 수정)

### 공통
- 주석은 *왜* 필요한 경우에만, *무엇* 은 코드 자체로 표현
- 한국어 주석 OK, 식별자는 영어
- LLM 친화 원칙: 함수가 길어지면 분리, 매직넘버는 상수로

## 10. 아키텍처 결정 (왜 이렇게 했는가)

| 결정 | 이유 |
|---|---|
| Python 백엔드 | Demucs/Basic Pitch/CREPE 모두 Python 전용 ML 라이브러리. JVM/Node 포팅이 빈약함 |
| arq (Celery 아님) | FastAPI 와 async-native, 의존성은 Redis 만, 가벼움. Celery 는 사이드 프로젝트엔 과함 |
| 큐 워커 분리 | Demucs 가 곡당 수십 초~수 분. HTTP 요청 동기 처리 시 타임아웃 + 동시 요청 처리 불가 |
| Basic Pitch + CREPE 둘 다 | Basic Pitch 는 다성부용, 베이스 같은 단성부에선 노이즈가 낄 수 있음. CREPE 는 단성부 전용. 비교 후 기본값 결정 예정 |
| music21 + MusicXML | 음악 표기의 표준 포맷. OSMD 가 받아 렌더 |
| VexFlow 별도 사용 (타브) | OSMD 의 타브 지원이 부분적. VexFlow 의 TabStave 로 직접 렌더가 더 안정적 |
| `[ml]` extras 분리 | PyTorch/TensorFlow 가 무거움. 가벼운 작업 (린트, 타입체크) 시 ML 설치 안 해도 됨 |
| 프렛 위치 자체 구현 | 적절한 OSS 가 없음. "직전 위치 거리 최소화 + 낮은 프렛 선호" 휴리스틱. `apps/api/src/api/pipeline/fretboard.py:choose_positions` |

## 11. 배포 (Hugging Face Spaces + Vercel + Upstash)

### 구성
- **Frontend (Vercel)**: Vite 정적 빌드. Root Directory = `apps/web`. 환경변수 `VITE_API_BASE_URL` 로 백엔드 URL 주입. 카드 불필요
- **Backend (HF Spaces, Docker SDK)**: 단일 Docker 컨테이너에 uvicorn (포그라운드) + arq 워커 (백그라운드). `apps/api/start.sh` 가 두 프로세스 동시 실행. 카드 불필요, 무료 16GB RAM / 2 vCPU
- **Redis (Upstash)**: 무료 티어. `REDIS_URL` 을 HF Space Secrets 에 등록 (`rediss://...`). 카드 불필요

### 핵심 결정
- **HF Spaces 선택 이유**: 카드 등록 불필요 (사용자 명시 요구사항). 16GB RAM 으로 Demucs OOM 위험 거의 없음. Docker SDK 라 로컬/프로덕션 동일 이미지
- **api 와 worker 가 같은 컨테이너**: HF Spaces 가 단일 컨테이너 모델이라 자연스럽게 합쳐짐. `apps/api/start.sh` 가 백그라운드 워커 + 포그라운드 API 동시 실행
- **비루트 사용자 (UID 1000)**: HF Spaces 보안 권장사항. Dockerfile 에 `USER user` 명시
- **저장소는 ephemeral**: HF Spaces 무료 티어는 영속 디스크 없음 (paid 부가 옵션). Space 가 sleep/restart 되면 산출물 사라짐. **데모용으로 OK** — 새 요청은 정상 처리됨. 영속화가 필요해지면 HF Persistent Storage ($5/월) 또는 결과를 응답에 인라인 (base64 MusicXML/MIDI)
- **공개 URL**: 무료 Space 는 항상 public. 호기심 트래픽 가능성 있음. 진짜 막으려면 백엔드에 토큰 인증 추가 (현재는 없음)
- **48시간 sleep**: 미사용 시 자동 sleep, 첫 요청에 ~30초 wake-up. 이후는 즉시 응답

### 배포 파일
- `Dockerfile` (repo 루트) — HF Spaces 가 root 의 Dockerfile 을 자동 인식. Python 3.11-slim + ffmpeg + ML deps + 모델 사전 베이크. 비루트 사용자
- `apps/api/start.sh` — arq 워커 백그라운드 + uvicorn 포그라운드. 워킹 디렉토리는 `/home/user/app`
- `.dockerignore` — `apps/web`, `storage`, `__pycache__`, `.git` 등 제외
- `README.md` 의 YAML frontmatter — HF Spaces 메타데이터 (`title`, `sdk: docker`, `app_port: 8000`)
- `apps/web/.env.example` — `VITE_API_BASE_URL` 문서화

### 첫 배포 런북 (사용자 작업)

1. **GitHub 푸시**: 새 repo 생성 → `git remote add origin ... && git push -u origin main`

2. **Upstash Redis**: upstash.com 가입 (GitHub 로그인 가능, 카드 불필요) → Database 생성 (region: AP-Southeast-1 Singapore 또는 AP-Northeast-1 Tokyo) → "Endpoint" 의 `rediss://default:<password>@<host>:6379` URL 복사

3. **HF Space 생성 + 배포**:
   - huggingface.co 가입 (카드 불필요)
   - "New Space" 클릭 → Settings:
     - Space name: 임의 (예: `fana-bass-tabs`). 최종 URL: `https://<owner>-<space-name>.hf.space`
     - License: 선택 (mit 등)
     - SDK: **Docker** (Blank template)
     - Hardware: CPU basic (free)
     - Visibility: Public (free)
   - 생성 후 Space 페이지 → Settings → "Repository secrets" → New secret:
     - Name: `REDIS_URL`
     - Value: 2단계의 `rediss://...` URL
   - 로컬에서 HF Space 를 두번째 remote 로 추가하고 push:
     ```bash
     # HF 계정에 SSH 키 등록 후 (또는 HTTPS + access token 사용):
     git remote add huggingface git@hf.co:spaces/<owner>/<space-name>.git
     git push huggingface main
     ```
     - HTTPS 방식: `git remote add huggingface https://huggingface.co/spaces/<owner>/<space-name>` 후 push 시 username + Access Token 입력
   - Space 페이지에서 "Building" → "Running" 으로 상태 변화 확인 (첫 빌드 10-20분)
   - 백엔드 URL: `https://<owner>-<space-name>.hf.space`. `/health` 로 확인

4. **Vercel 프론트엔드**:
   - vercel.com 가입 → Add New Project → GitHub repo import
   - Root Directory: `apps/web`
   - Framework Preset: Vite
   - Environment Variables: `VITE_API_BASE_URL=https://<owner>-<space-name>.hf.space`
   - Deploy

### 자주 발생하는 문제
- **HF Space 빌드 실패**: Space 페이지의 "Logs" 탭 확인. 흔한 원인: ML deps 다운로드 네트워크 지연 (재시도). pip install 메모리 부족이면 Hardware 를 잠시 더 큰 것으로 (현재는 Free 만 사용)
- **HF Space 권한 오류**: Dockerfile 의 `USER user` 누락 또는 `--chown=user` 미적용 시 빌드/런타임 권한 실패. 현재 Dockerfile 은 모두 적용됨
- **Vercel build 실패 (pnpm workspace)**: Vercel 의 Root Directory 가 `apps/web` 인지 확인. Build Command 자동 검출 안 되면 `pnpm install --frozen-lockfile=false && pnpm build` 로 명시
- **CORS 오류**: 백엔드 `main.py` 의 CORS 미들웨어 `allow_origins=["*"]` 가 이미 허용. 막히면 Vercel 도메인 명시
- **Sleep 후 첫 요청 timeout**: 48시간 미사용 후 wake-up 에 ~30초. 프론트 폴링이 timeout 되면 retry 로직 추가 또는 사용자에게 안내 메시지
- **저장된 파일이 사라짐**: Space restart 시 ephemeral 디스크 초기화. 의도된 동작. 영속화 필요해지면 §11 핵심 결정 참조

## 12. 알려진 한계 / 다음에 해야 할 일

작업 우선순위 순:

1. **두 트랜스크라이버 비교 평가** — 같은 입력에 대해 Basic Pitch vs CREPE 결과를 비교. 베이스에 더 정확한 쪽이 기본값. 평가 스크립트 + 샘플 데이터 필요
2. **테스트** — 백엔드/프론트 모두 테스트 부재. 최소한 `fretboard.choose_positions`, `tempo.estimate_bpm`, `secondsToVexflow` 같은 순수 함수부터 단위 테스트
3. **프렛 위치 알고리즘 개선** — 현재는 단순 그리디. 가능하면 동적 계획법으로 전체 시퀀스 비용 최소화. 코드/오픈 포지션 가중치도 추가 고려
4. **노트 그루핑** — 트랜스크립션 결과가 매우 짧은 노트들 (글리치) 로 잘게 쪼개질 수 있음. `transcribe.load_notes` 출력에 후처리 (짧은 노트 병합/제거) 필요할 수 있음
5. **MusicXML 측면에서 박자/마디** — 현재 `score.notes_to_musicxml` 가 `s.write` 의 자동 마디화에 의존. 박자 기호 명시, 비트 정렬 개선 여지 있음
6. **BPM 추정 정확도** — `tempo.estimate_bpm` 이 첫 60초만 사용. 곡 전체로 평균/중앙값 내거나, 사용자가 수동 보정할 수 있는 UI 추가 고려
7. **에러 처리** — 워커 실패 시 사용자 메시지가 빈약 (스택트레이스 그대로 노출됨). 예외별 사용자 친화 메시지 매핑
8. **저장 정책** — 현재 산출물이 영원히 디스크에 남음. arq 의 `keep_result` 만 1시간이고 파일은 영구. 잡 만료 시 청소 크론 필요
9. **인증** — 현재 없음. 외부 공개시 필요
10. **모델 프리페치** — 첫 요청에서 Demucs/CREPE 모델을 다운로드 (~150MB). 워커 startup 훅에서 미리 로드하면 사용자 첫 요청 지연 감소
11. **TabView 정확도** — VexFlow `Voice.Mode.SOFT` 로 박자 검증을 끔. 마디 안에서 노트가 꽉 채우지 않아도 그대로 그림. 마디 정렬과 쉼표 삽입 개선 필요

## 13. LLM 작업 시 주의사항

### 하지 말 것
- ML 의존성을 require 로 옮기지 말 것 (`[project.optional-dependencies].ml` 그대로). CI 가 무거워짐
- 동기 처리로 되돌리지 말 것. 큐 거치는 게 정답
- `score.py` 와 `pipeline/tempo.py` 의 이름 충돌 주의 — `from music21 import tempo` 하지 말고 `from music21.tempo import MetronomeMark` 로 명시 임포트
- API 응답 스키마 바꿀 때 `apps/web/src/types.ts` 도 같이 수정
- `apps/api/src/api/main.py` 와 `apps/api/src/api/worker.py` 는 같은 `pipeline` 모듈을 임포트 — 큐 재구성하더라도 import cycle 만들지 말 것
- 사용자가 명시 요청 안 한 라이브러리 추가하지 말 것 (이미 PyTorch/TF 만으로도 무거움)

### 작업할 때
- 새 엔드포인트 추가 시: `schemas.py` → `main.py` (또는 `worker.py`) → `apps/web/src/types.ts` → `apps/web/src/api.ts` 순서로 동기화
- 파이프라인 단계 추가/수정 시 `worker.py:run_transcribe` 의 `stage()` 호출과 프론트 `App.tsx:stageLabel()` 도 같이 업데이트
- 새 환경변수는 `.env.example`, `config.py`, `CLAUDE.md` 의 표 세 곳 모두 업데이트
- 의미 있는 단위마다 커밋. 커밋 메시지는 한국어 OK

### 사용자에 대해
- 사용자는 5현 베이스 사용자. 베이스 기타 도메인 지식 보유
- 한국어 응답 선호 (`~/.claude/CLAUDE.md` 에서 글로벌 지정)
- "알아서 해" 라고 하면 합리적 가정 + 진행. 막히는 부분만 짧게 질문
