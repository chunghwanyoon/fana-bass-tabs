from api.pipeline.fretboard import Tuning, choose_positions
from api.schemas import Note, TabNote


def notes_to_tab(notes: list[Note], tuning: Tuning) -> list[TabNote]:
    pitches = [n.pitch for n in notes]
    positions = choose_positions(pitches, tuning)
    out: list[TabNote] = []
    for note, pos in zip(notes, positions, strict=True):
        if pos is None:
            continue  # 베이스 음역대 밖
        s, f = pos
        out.append(
            TabNote(
                string=s,
                fret=f,
                start=note.start,
                duration=note.duration,
                pitch=note.pitch,
            )
        )
    return out
