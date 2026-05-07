"""음 리스트 → MusicXML (베이스 클레프 + 박자 시그니처 + 제목 + 템포)."""

from pathlib import Path

from music21 import clef, instrument, metadata, meter, note, stream
from music21.tempo import MetronomeMark

from api.schemas import Note


def notes_to_musicxml(
    notes: list[Note],
    out_dir: Path,
    bpm: float,
    title: str = "",
    time_signature: str = "4/4",
) -> Path:
    s = stream.Score()
    s.metadata = metadata.Metadata()
    s.metadata.title = title or "Untitled"
    s.metadata.composer = "Fana Bass Tabs"

    part = stream.Part()
    part.insert(0, instrument.ElectricBass())
    part.insert(0, clef.BassClef())
    part.insert(0, meter.TimeSignature(time_signature))
    part.insert(0, MetronomeMark(number=bpm))

    qn_per_sec = bpm / 60.0
    for n in notes:
        offset_q = round(n.start * qn_per_sec * 4) / 4   # 16분음표 격자
        dur_q = max(round(n.duration * qn_per_sec * 4) / 4, 0.25)
        m21_note = note.Note(midi=n.pitch)
        m21_note.quarterLength = dur_q
        part.insert(offset_q, m21_note)

    s.append(part)
    s.makeMeasures(inPlace=True)

    out_path = out_dir / "score.musicxml"
    s.write("musicxml", fp=str(out_path))
    return out_path
