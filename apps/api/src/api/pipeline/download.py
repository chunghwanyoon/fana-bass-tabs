import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import yt_dlp

ProgressCb = Callable[[int], Awaitable[None]]


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
    if "t" in qs:
        new_qs["t"] = qs["t"][0]
    return urlunparse(parsed._replace(query=urlencode(new_qs)))


def yt_dlp_opts(extra: dict | None = None) -> dict:
    """download / probe 가 공통으로 쓰는 yt-dlp 옵션."""
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "mweb", "web", "android"],
            }
        },
    }
    if extra:
        opts.update(extra)
    return opts


async def from_url(
    url: str, out_dir: Path, on_progress: ProgressCb | None = None
) -> Path:
    """YouTube/SoundCloud 등에서 오디오를 받아 wav로 저장.

    on_progress 가 주어지면 다운로드 진행률 (0-100) 을 비동기 콜백으로 전달.
    """
    cleaned = clean_url(url)
    out_template = str(out_dir / "source.%(ext)s")

    # 별도 스레드의 yt-dlp 가 sync hook 으로 갱신할 진행률 박스
    pct_box = [0]

    def hook(d: dict) -> None:
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            done = d.get("downloaded_bytes")
            if total and done:
                pct_box[0] = min(99, int(done / total * 100))
        elif d.get("status") == "finished":
            pct_box[0] = 100

    opts = yt_dlp_opts(
        {
            "format": "bestaudio/best",
            "outtmpl": out_template,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "192",
                }
            ],
            "progress_hooks": [hook],
        }
    )

    def _run() -> None:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([cleaned])

    task = asyncio.create_task(asyncio.to_thread(_run))
    if on_progress is not None:
        last = -1
        while not task.done():
            cur = pct_box[0]
            if cur != last:
                await on_progress(cur)
                last = cur
            await asyncio.sleep(0.3)
    await task  # 예외 전파
    return out_dir / "source.wav"
