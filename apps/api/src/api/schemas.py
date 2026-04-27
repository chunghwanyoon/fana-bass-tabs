from typing import Literal

from pydantic import BaseModel, HttpUrl


class TranscribeRequest(BaseModel):
    source_url: HttpUrl
    transcriber: Literal["basic_pitch", "crepe"] | None = None
    tuning: Literal["4string", "5string"] | None = None


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
