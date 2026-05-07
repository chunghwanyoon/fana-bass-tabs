"""오디오 길이 검증. URL 은 yt-dlp metadata, 파일은 librosa 사용."""

from pathlib import Path

import librosa
import yt_dlp

from api.pipeline.download import clean_url, yt_dlp_opts


class DurationError(Exception):
    """다운로드 받기 전에 거절되는 길이 검증 실패 또는 메타데이터 실패."""


_BOT_HINTS = (
    "confirm you're not a bot",
    "Sign in to confirm",
    "cookies",
)

_NETWORK_HINTS = (
    "UNEXPECTED_EOF_WHILE_READING",
    "Unable to download API page",
    "Connection reset",
    "timed out",
    "SSLError",
)


def get_url_duration(url: str) -> float:
    """yt-dlp 메타데이터만 추출 (다운로드 X). 길이 (초) 반환."""
    cleaned = clean_url(url)
    opts = yt_dlp_opts({"skip_download": True, "extract_flat": False})
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(cleaned, download=False)
    except yt_dlp.DownloadError as e:
        msg = str(e)
        if any(h in msg for h in _BOT_HINTS):
            raise DurationError(
                "YouTube 가 봇 차단 모드를 활성화했습니다. "
                "다른 영상으로 시도하거나, 음악 파일을 직접 업로드해주세요. "
                "(이 문제는 데이터센터 IP 에서 자주 발생합니다)"
            ) from e
        if any(h in msg for h in _NETWORK_HINTS):
            raise DurationError(
                "YouTube 와의 연결이 일시적으로 실패했습니다. "
                "잠시 후 다시 시도하거나, 음악 파일을 직접 업로드해주세요."
            ) from e
        raise DurationError(f"URL 메타데이터 추출 실패: {msg}") from e
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
