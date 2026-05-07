from typing import Literal

from pydantic import BaseModel, HttpUrl

# 자주 쓰이는 박자 7종. 자동 추정 대신 사용자 선택을 받음 (디폴트 4/4)
TimeSignatureLiteral = Literal["4/4", "3/4", "6/8", "2/4", "5/4", "7/8", "12/8"]


class TranscribeRequest(BaseModel):
    source_url: HttpUrl
    transcriber: Literal["basic_pitch", "crepe"] | None = None
    tuning: Literal["4string", "5string"] | None = None
    time_signature: TimeSignatureLiteral | None = None


class Note(BaseModel):
    pitch: int          # MIDI 노트 번호
    start: float        # 초
    duration: float     # 초
    velocity: int = 80


class TabNote(BaseModel):
    string: int         # 1 = 가장 가는 줄 (G)
    fret: int
    start: float
    duration: float
    pitch: int


class TranscribeResult(BaseModel):
    job_id: str
    notes: list[Note]
    tab: list[TabNote]
    musicxml_url: str
    midi_url: str
    tuning: str
    transcriber: str
    bpm: float
    title: str = ""
    time_signature: str = "4/4"


class JobAccepted(BaseModel):
    job_id: str
    status: Literal["queued"] = "queued"


JobStatusLiteral = Literal[
    "queued", "running", "complete", "failed", "not_found"
]


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatusLiteral
    stage: str | None = None
    stage_progress: int | None = None
    result: TranscribeResult | None = None
    error: str | None = None
