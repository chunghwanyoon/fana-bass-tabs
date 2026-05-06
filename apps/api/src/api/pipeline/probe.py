"""오디오 길이 검증. URL 은 yt-dlp metadata, 파일은 librosa 사용."""

from pathlib import Path

import librosa
import yt_dlp


class DurationError(Exception):
    """다운로드 받기 전에 거절되는 길이 검증 실패."""


def get_url_duration(url: str) -> float:
    """yt-dlp 메타데이터만 추출 (다운로드 X). 길이 (초) 반환."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise DurationError(f"URL 메타데이터 추출 실패: {e}") from e

    duration = info.get("duration")
    if duration is None:
        raise DurationError("영상 길이를 확인할 수 없습니다 (라이브 스트림이거나 메타데이터 누락)")
    return float(duration)


def get_file_duration(audio_path: Path) -> float:
    """업로드된 오디오 파일의 길이 (초). librosa.get_duration 사용."""
    try:
        return float(librosa.get_duration(path=str(audio_path)))
    except Exception as e:
        raise DurationError(f"파일 길이 추출 실패: {e}") from e


def format_duration(seconds: float) -> str:
    """초 → "M분 S초" 한글 표기."""
    total = int(round(seconds))
    m, s = divmod(total, 60)
    if m == 0:
        return f"{s}초"
    return f"{m}분 {s}초"
