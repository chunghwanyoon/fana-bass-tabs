from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import yt_dlp


def clean_url(url: str) -> str:
    """YouTube URL 에서 playlist/radio 파라미터 제거.

    `?v=VIDEO&list=RDxxx&start_radio=1` 처럼 라디오 믹스 파라미터가 붙어 있으면
    yt-dlp 가 단일 영상이 아닌 playlist (`youtube:tab` extractor) 로 처리하다
    실패하기 쉬움. v 파라미터만 남겨서 단순 영상 URL 로 정제.
    """
    parsed = urlparse(url)
    if "youtube.com" not in parsed.netloc and "youtu.be" not in parsed.netloc:
        return url
    if "/watch" not in parsed.path:
        return url
    qs = parse_qs(parsed.query)
    if "v" not in qs:
        return url
    new_qs = {"v": qs["v"][0]}
    if "t" in qs:  # 시작 시간은 보존
        new_qs["t"] = qs["t"][0]
    return urlunparse(parsed._replace(query=urlencode(new_qs)))


def yt_dlp_opts(extra: dict | None = None) -> dict:
    """download / probe 가 공통으로 쓰는 yt-dlp 옵션."""
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,           # 항상 단일 영상으로 처리
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
        # YouTube 봇 차단 우회: 데이터센터 IP 에서도 통과 가능성 높은 클라이언트들
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "mweb", "web", "android"],
            }
        },
    }
    if extra:
        opts.update(extra)
    return opts


def from_url(url: str, out_dir: Path) -> Path:
    """YouTube/SoundCloud 등에서 오디오를 받아 wav로 저장."""
    url = clean_url(url)
    out_template = str(out_dir / "source.%(ext)s")
    opts = yt_dlp_opts({
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
    })
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    return out_dir / "source.wav"
