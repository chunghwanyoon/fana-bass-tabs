"""Demucs로 베이스 스템 추출."""

import subprocess
import sys
from pathlib import Path

from api.config import settings


def extract_bass(audio_path: Path, out_dir: Path) -> Path:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "demucs",
            "--two-stems=bass",
            "-n",
            settings.demucs_model,
            "-o",
            str(out_dir),
            str(audio_path),
        ],
        check=True,
    )
    bass_path = out_dir / settings.demucs_model / audio_path.stem / "bass.wav"
    if not bass_path.exists():
        raise RuntimeError(f"Demucs 출력 파일을 찾을 수 없음: {bass_path}")
    return bass_path
