"""Demucs로 베이스 스템 추출."""

import asyncio
import re
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

from api.config import settings

ProgressCb = Callable[[int], Awaitable[None]]


class SeparateError(Exception):
    pass


# Demucs/tqdm stderr 의 "  42%|████▏     | ..." 패턴
_PCT_PATTERN = re.compile(rb"(\d+)%\|")


async def extract_bass(
    audio_path: Path, out_dir: Path, on_progress: ProgressCb | None = None
) -> Path:
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

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stderr_buf = bytearray()
    last_pct = -1
    while True:
        chunk = await proc.stderr.read(512) if proc.stderr else b""
        if not chunk:
            break
        stderr_buf.extend(chunk)
        # 각 chunk 안의 마지막 % 매치만 사용 (tqdm 이 \r 로 같은 줄을 여러 번 갱신)
        matches = _PCT_PATTERN.findall(chunk)
        if matches and on_progress is not None:
            pct = int(matches[-1])
            if pct != last_pct:
                await on_progress(pct)
                last_pct = pct

    rc = await proc.wait()
    stdout_data = await proc.stdout.read() if proc.stdout else b""

    if rc != 0:
        stderr_tail = bytes(stderr_buf)[-2000:].decode("utf-8", errors="replace").strip()
        stdout_tail = stdout_data[-500:].decode("utf-8", errors="replace").strip()
        raise SeparateError(
            f"Demucs 실패 (exit {rc}).\n"
            f"stderr: {stderr_tail}\n"
            f"stdout: {stdout_tail}"
        )

    bass_path = out_dir / settings.demucs_model / audio_path.stem / "bass.wav"
    if not bass_path.exists():
        raise SeparateError(
            f"Demucs 출력 파일을 찾을 수 없음: {bass_path}\n"
            f"실행은 성공 (exit 0) 했으나 예상 경로에 파일 없음. "
            f"stdout: {stdout_data[-500:].decode('utf-8', errors='replace')}"
        )
    return bass_path
