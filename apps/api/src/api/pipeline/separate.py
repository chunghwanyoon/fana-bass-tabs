"""Demucs로 베이스 스템 추출."""

import subprocess
import sys
from pathlib import Path

from api.config import settings


class SeparateError(Exception):
    pass


def extract_bass(audio_path: Path, out_dir: Path) -> Path:
    cmd = [
        sys.executable,
        "-m",
        "demucs",
        "--two-stems=bass",
        "-n",
        settings.demucs_model,
        "-o",
        str(out_dir),
        str(audio_path),
    ]

    # check=True 대신 capture_output 으로 stderr 받아 진단 가능하게
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Demucs 에러 메시지의 마지막 일부만 (스택 길어서 잘라냄)
        stderr_tail = (result.stderr or "")[-2000:].strip()
        stdout_tail = (result.stdout or "")[-500:].strip()
        raise SeparateError(
            f"Demucs 실패 (exit {result.returncode}).\n"
            f"stderr: {stderr_tail}\n"
            f"stdout: {stdout_tail}"
        )

    bass_path = out_dir / settings.demucs_model / audio_path.stem / "bass.wav"
    if not bass_path.exists():
        raise SeparateError(
            f"Demucs 출력 파일을 찾을 수 없음: {bass_path}\n"
            f"실행은 성공 (exit 0) 했으나 예상 경로에 파일 없음. "
            f"stdout: {(result.stdout or '')[-500:]}"
        )
    return bass_path
