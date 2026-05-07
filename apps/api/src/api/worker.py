"""arq 워커. 트랜스크립션 잡을 백그라운드에서 처리.

실행: `arq api.worker.WorkerSettings`
"""

import json
import logging
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
from api.schemas import Note, TabNote

logger = logging.getLogger("api.worker")


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

    async def set_stage(name: str) -> None:
        await redis.set(f"job_stage:{job_id}", name, ex=3600)
        # 새 단계 진입 시 진행률 초기화
        await redis.set(f"job_progress:{job_id}", "0", ex=3600)

    async def set_progress(pct: int) -> None:
        await redis.set(f"job_progress:{job_id}", str(int(pct)), ex=3600)

    if url is not None:
        await set_stage("downloading")
        path = await download.from_url(url, job_dir, on_progress=set_progress)
    else:
        assert audio_path is not None
        path = Path(audio_path)

    await set_stage("separating")
    bass_path = await separate.extract_bass(path, job_dir, on_progress=set_progress)

    await set_stage("transcribing")
    midi_path = transcribe.to_midi(bass_path, job_dir, backend=transcriber)
    notes = transcribe.load_notes(midi_path)

    await set_stage("scoring")
    bpm = tempo.estimate_bpm(bass_path)
    tuning_spec = fretboard.get_tuning(tuning)
    tab_notes = tab.notes_to_tab(notes, tuning_spec)
    musicxml_path = score.notes_to_musicxml(notes, job_dir, bpm=bpm)

    await set_stage("complete")
    await set_progress(100)

    result = {
        "job_id": str(job_id),
        "notes": [_note_to_dict(n) for n in notes],
        "tab": [_tab_to_dict(t) for t in tab_notes],
        "musicxml_url": f"/files/{job_id}/{musicxml_path.name}",
        "midi_url": f"/files/{job_id}/{midi_path.name}",
        "tuning": str(tuning),
        "transcriber": str(transcriber),
        "bpm": float(bpm),
    }

    # 마지막 보루: JSON round-trip 으로 모든 값을 강제로 JSON-호환 (=msgpack-호환) 으로
    try:
        return json.loads(json.dumps(result, default=_json_fallback))
    except Exception:
        logger.exception("[run_transcribe] JSON 직렬화 실패. result keys=%s", list(result.keys()))
        raise


def _note_to_dict(n: Note) -> dict[str, int | float]:
    return {
        "pitch": int(n.pitch),
        "start": float(n.start),
        "duration": float(n.duration),
        "velocity": int(n.velocity),
    }


def _tab_to_dict(t: TabNote) -> dict[str, int | float]:
    return {
        "string": int(t.string),
        "fret": int(t.fret),
        "start": float(t.start),
        "duration": float(t.duration),
        "pitch": int(t.pitch),
    }


def _json_fallback(obj: Any) -> Any:
    """numpy 등 JSON 이 모르는 타입을 Python 네이티브로 변환."""
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            pass
    if hasattr(obj, "tolist"):
        try:
            return obj.tolist()
        except Exception:
            pass
    return str(obj)


class WorkerSettings:
    functions = [run_transcribe]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    job_timeout = 1800
    max_jobs = 1
    keep_result = 3600
