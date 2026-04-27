"""librosa beat tracker로 BPM 추정."""

from pathlib import Path

import librosa
import numpy as np


def estimate_bpm(audio_path: Path, max_seconds: float = 60.0) -> float:
    """첫 max_seconds 초만 사용해 빠르게 BPM 추정. 추정 실패 시 120 fallback."""
    y, sr = librosa.load(str(audio_path), sr=22050, mono=True, duration=max_seconds)
    if y.size == 0:
        return 120.0
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])
    if not np.isfinite(bpm) or bpm <= 0:
        return 120.0
    return bpm
