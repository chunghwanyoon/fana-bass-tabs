"""arq 워커. 트랜스크립션 잡을 백그라운드에서 처리.

실행: `arq api.worker.WorkerSettings`
"""

from pathlib import Path
from typing import Any

from arq.connections import RedisSettings

from api.config import settings
from api.pipeline import (
    download,
    fretboard,
    score,
    separate,
    tab,
    tempo,
    transcribe,
)


async def run_transcribe(
    ctx: dict[str, Any],
    job_id: str,
    audio_path: str | None,
    url: str | None,
    transcriber: str,
    tuning: str,
) -> dict[str, Any]:
    redis = ctx["redis"]
    job_dir = settings.storage_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    async def stage(name: str) -> None:
        await redis.set(f"job_stage:{job_id}", name, ex=3600)

    if url is not None:
        await stage("downloading")
        path = download.from_url(url, job_dir)
    else:
        assert audio_path is not None
        path = Path(audio_path)

    await stage("separating")
    bass_path = separate.extract_bass(path, job_dir)

    await stage("transcribing")
    midi_path = transcribe.to_midi(bass_path, job_dir, backend=transcriber)
    notes = transcribe.load_notes(midi_path)

    await stage("scoring")
    bpm = tempo.estimate_bpm(bass_path)
    tuning_spec = fretboard.get_tuning(tuning)
    tab_notes = tab.notes_to_tab(notes, tuning_spec)
    musicxml_path = score.notes_to_musicxml(notes, job_dir, bpm=bpm)

    await stage("complete")
    return {
        "job_id": job_id,
        "notes": [n.model_dump() for n in notes],
        "tab": [t.model_dump() for t in tab_notes],
        "musicxml_url": f"/files/{job_id}/{musicxml_path.name}",
        "midi_url": f"/files/{job_id}/{midi_path.name}",
        "tuning": tuning,
        "transcriber": transcriber,
        "bpm": bpm,
    }


class WorkerSettings:
    functions = [run_transcribe]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    job_timeout = 1800     # 30분 (긴 곡 + 첫 모델 다운로드 여유)
    max_jobs = 1           # ML 무거우므로 동시 1개만
    keep_result = 3600     # 결과 1시간 보관
