from pathlib import Path

import yt_dlp


def from_url(url: str, out_dir: Path) -> Path:
    """YouTube/SoundCloud 등에서 오디오를 받아 wav로 저장."""
    out_template = str(out_dir / "source.%(ext)s")
    opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    return out_dir / "source.wav"
