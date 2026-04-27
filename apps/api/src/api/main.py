import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.config import settings
from api.pipeline import download, fretboard, score, separate, tab, transcribe
from api.schemas import TranscribeRequest, TranscribeResult

app = FastAPI(title="Fana Bass Tabs API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/files", StaticFiles(directory=str(settings.storage_dir)), name="files")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/transcribe/url", response_model=TranscribeResult)
def transcribe_url(req: TranscribeRequest) -> TranscribeResult:
    job_id, job_dir = _new_job()
    audio_path = download.from_url(str(req.source_url), job_dir)
    return _run_pipeline(
        job_id=job_id,
        job_dir=job_dir,
        audio_path=audio_path,
        transcriber=req.transcriber or settings.transcriber,
        tuning=req.tuning or settings.bass_tuning,
    )


@app.post("/transcribe/file", response_model=TranscribeResult)
def transcribe_file(file: UploadFile = File(...)) -> TranscribeResult:
    if not file.filename:
        raise HTTPException(400, "filename required")
    job_id, job_dir = _new_job()
    audio_path = job_dir / file.filename
    audio_path.write_bytes(file.file.read())
    return _run_pipeline(
        job_id=job_id,
        job_dir=job_dir,
        audio_path=audio_path,
        transcriber=settings.transcriber,
        tuning=settings.bass_tuning,
    )


def _new_job() -> tuple[str, Path]:
    job_id = uuid.uuid4().hex[:12]
    job_dir = settings.storage_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_id, job_dir


def _run_pipeline(
    job_id: str,
    job_dir: Path,
    audio_path: Path,
    transcriber: str,
    tuning: str,
) -> TranscribeResult:
    bass_path = separate.extract_bass(audio_path, job_dir)
    midi_path = transcribe.to_midi(bass_path, job_dir, backend=transcriber)
    notes = transcribe.load_notes(midi_path)
    tuning_spec = fretboard.get_tuning(tuning)
    tab_notes = tab.notes_to_tab(notes, tuning_spec)
    musicxml_path = score.notes_to_musicxml(notes, job_dir)

    midi_url = f"/files/{job_id}/{midi_path.name}"
    musicxml_url = f"/files/{job_id}/{musicxml_path.name}"
    return TranscribeResult(
        job_id=job_id,
        notes=notes,
        tab=tab_notes,
        musicxml_url=musicxml_url,
        midi_url=midi_url,
        tuning=tuning,
        transcriber=transcriber,
    )
