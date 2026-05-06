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
        # YouTube 봇 차단 우회: 데이터센터 IP 에서도 통과 가능성 높은 모바일 클라이언트
        # 들을 우선 시도. 실패 시 다른 클라이언트로 자동 재시도
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "mweb", "web", "android"],
            }
        },
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    return out_dir / "source.wav"
