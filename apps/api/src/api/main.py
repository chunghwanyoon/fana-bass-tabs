import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from arq.jobs import Job, JobStatus
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.config import settings
from api.pipeline import probe
from api.schemas import (
    JobAccepted,
    JobStatusResponse,
    TranscribeRequest,
    TranscribeResult,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    app.state.arq = pool
    try:
        yield
    finally:
        await pool.close()


app = FastAPI(title="Fana Bass Tabs API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/files", StaticFiles(directory=str(settings.storage_dir)), name="files")


def _arq(request: Request) -> ArqRedis:
    return request.app.state.arq


def _new_job() -> tuple[str, Path]:
    job_id = uuid.uuid4().hex[:12]
    job_dir = settings.storage_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_id, job_dir


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/transcribe/url", response_model=JobAccepted)
async def transcribe_url(req: TranscribeRequest, request: Request) -> JobAccepted:
    # 다운로드 받기 전에 메타데이터 (길이 + 제목) 추출
    try:
        meta = probe.get_url_metadata(str(req.source_url))
    except probe.DurationError as e:
        raise HTTPException(400, str(e)) from e
    _check_duration(meta["duration"])

    job_id, _ = _new_job()
    pool = _arq(request)
    await pool.enqueue_job(
        "run_transcribe",
        job_id=job_id,
        audio_path=None,
        url=str(req.source_url),
        title=meta["title"],
        transcriber=req.transcriber or settings.transcriber,
        tuning=req.tuning or settings.bass_tuning,
        time_signature=req.time_signature or settings.time_signature,
        _job_id=job_id,
    )
    return JobAccepted(job_id=job_id)


@app.post("/transcribe/file", response_model=JobAccepted)
async def transcribe_file(
    request: Request, file: UploadFile = File(...)
) -> JobAccepted:
    if not file.filename:
        raise HTTPException(400, "filename required")
    job_id, job_dir = _new_job()
    audio_path = job_dir / file.filename
    audio_path.write_bytes(await file.read())

    # 저장 후 길이 검증. 실패 시 파일 삭제하고 에러
    try:
        duration = probe.get_file_duration(audio_path)
    except probe.DurationError as e:
        audio_path.unlink(missing_ok=True)
        raise HTTPException(400, str(e)) from e
    try:
        _check_duration(duration)
    except HTTPException:
        audio_path.unlink(missing_ok=True)
        raise

    pool = _arq(request)
    # 파일 업로드는 multipart/form-data 라 박자 옵션은 query string 으로 받음
    ts = request.query_params.get("time_signature") or settings.time_signature
    await pool.enqueue_job(
        "run_transcribe",
        job_id=job_id,
        audio_path=str(audio_path),
        url=None,
        title=Path(file.filename).stem,
        transcriber=settings.transcriber,
        tuning=settings.bass_tuning,
        time_signature=ts,
        _job_id=job_id,
    )
    return JobAccepted(job_id=job_id)


def _check_duration(duration: float) -> None:
    if duration > settings.max_duration_sec:
        raise HTTPException(
            400,
            f"오디오 길이 {probe.format_duration(duration)} 가 제한 "
            f"{probe.format_duration(settings.max_duration_sec)} 를 초과합니다. "
            "더 짧은 음원으로 시도해주세요.",
        )


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str, request: Request) -> JobStatusResponse:
    pool = _arq(request)
    job = Job(job_id, pool)
    info = await job.info()

    raw_stage = await pool.get(f"job_stage:{job_id}")
    stage = raw_stage.decode() if isinstance(raw_stage, bytes) else raw_stage

    raw_progress = await pool.get(f"job_progress:{job_id}")
    progress: int | None = None
    if raw_progress is not None:
        try:
            progress = int(
                raw_progress.decode() if isinstance(raw_progress, bytes) else raw_progress
            )
        except (ValueError, AttributeError):
            progress = None

    if info is None:
        return JobStatusResponse(
            job_id=job_id, status="not_found", stage=stage, stage_progress=progress
        )

    status = await job.status()

    if status == JobStatus.complete:
        try:
            result_data = await job.result(timeout=0)
        except Exception as e:
            return JobStatusResponse(
                job_id=job_id, status="failed", stage=stage,
                stage_progress=progress, error=str(e)
            )
        return JobStatusResponse(
            job_id=job_id,
            status="complete",
            stage=stage,
            stage_progress=progress,
            result=TranscribeResult(**result_data),
        )

    if status == JobStatus.in_progress:
        return JobStatusResponse(
            job_id=job_id, status="running", stage=stage, stage_progress=progress
        )

    return JobStatusResponse(
        job_id=job_id, status="queued", stage=stage, stage_progress=progress
    )
