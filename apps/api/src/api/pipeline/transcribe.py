"""오디오 → MIDI 트랜스크립션 (Basic Pitch / CREPE 토글 가능)."""

from pathlib import Path

import pretty_midi

from api.schemas import Note


def to_midi(audio_path: Path, out_dir: Path, backend: str) -> Path:
    if backend == "basic_pitch":
        return _basic_pitch(audio_path, out_dir)
    if backend == "crepe":
        return _crepe(audio_path, out_dir)
    raise ValueError(f"Unknown transcriber: {backend}")


def _basic_pitch(audio_path: Path, out_dir: Path) -> Path:
    from basic_pitch import ICASSP_2022_MODEL_PATH
    from basic_pitch.inference import predict_and_save

    predict_and_save(
        [str(audio_path)],
        str(out_dir),
        save_midi=True,
        sonify_midi=False,
        save_model_outputs=False,
        save_notes=False,
        model_or_model_path=ICASSP_2022_MODEL_PATH,
    )
    midi_path = out_dir / f"{audio_path.stem}_basic_pitch.mid"
    if not midi_path.exists():
        raise RuntimeError(f"Basic Pitch 출력 파일을 찾을 수 없음: {midi_path}")
    return midi_path


def _crepe(audio_path: Path, out_dir: Path) -> Path:
    """단성부 피치 트래킹 → 동일 음 프레임 그룹핑 → MIDI 저장."""
    import crepe
    import librosa
    import numpy as np

    audio, sr = librosa.load(str(audio_path), sr=16000, mono=True)
    times, frequency, confidence, _ = crepe.predict(
        audio, sr, viterbi=True, step_size=10, verbose=0
    )
    valid = confidence > 0.5
    if not valid.any():
        raise RuntimeError("CREPE에서 신뢰할 수 있는 피치를 찾지 못함")

    midi_pitches = np.where(
        valid, np.round(librosa.hz_to_midi(np.maximum(frequency, 1e-6))), -1
    ).astype(int)
    notes = _frames_to_notes(midi_pitches, times)

    pm = pretty_midi.PrettyMIDI()
    bass = pretty_midi.Instrument(program=33)  # Electric Bass (finger)
    for n in notes:
        bass.notes.append(
            pretty_midi.Note(
                velocity=80, pitch=n.pitch, start=n.start, end=n.start + n.duration
            )
        )
    pm.instruments.append(bass)

    midi_path = out_dir / f"{audio_path.stem}_crepe.mid"
    pm.write(str(midi_path))
    return midi_path


def _frames_to_notes(midi_pitches, times) -> list[Note]:
    notes: list[Note] = []
    if len(midi_pitches) == 0:
        return notes
    current = int(midi_pitches[0])
    start_idx = 0
    min_dur = 0.05  # 50ms 미만은 노이즈로 간주

    def flush(pitch: int, s_idx: int, e_idx: int) -> None:
        if pitch < 0:
            return
        s_t = float(times[s_idx])
        e_t = float(times[e_idx])
        if e_t - s_t >= min_dur:
            notes.append(Note(pitch=pitch, start=s_t, duration=e_t - s_t))

    for i in range(1, len(midi_pitches)):
        if int(midi_pitches[i]) != current:
            flush(current, start_idx, i)
            current = int(midi_pitches[i])
            start_idx = i
    flush(current, start_idx, len(midi_pitches) - 1)
    return notes


def load_notes(midi_path: Path) -> list[Note]:
    pm = pretty_midi.PrettyMIDI(str(midi_path))
    notes: list[Note] = []
    for inst in pm.instruments:
        for n in inst.notes:
            notes.append(
                Note(
                    pitch=int(n.pitch),
                    start=float(n.start),
                    duration=float(n.end - n.start),
                    velocity=int(n.velocity),
                )
            )
    notes.sort(key=lambda n: n.start)
    return clean_notes(notes)


def clean_notes(
    notes: list[Note],
    min_dur: float = 0.06,        # 60ms 미만은 노이즈로 간주
    merge_gap: float = 0.03,      # 30ms 이내 같은 음은 병합
) -> list[Note]:
    """글리치/스푸리어스 노트 제거 + 인접 동일 피치 병합.

    Basic Pitch 가 폴리포닉 가정으로 동작해서 단성부 베이스에서도 한 음을
    여러 짧은 노트로 쪼개는 경향이 있음. 합쳐서 가독성 향상.
    """
    if not notes:
        return notes
    notes = sorted(notes, key=lambda n: n.start)

    merged: list[Note] = []
    for n in notes:
        if merged and merged[-1].pitch == n.pitch:
            prev = merged[-1]
            gap = n.start - (prev.start + prev.duration)
            if gap < merge_gap:
                merged[-1] = Note(
                    pitch=prev.pitch,
                    start=prev.start,
                    duration=(n.start + n.duration) - prev.start,
                    velocity=max(prev.velocity, n.velocity),
                )
                continue
        merged.append(n)

    return [n for n in merged if n.duration >= min_dur]
