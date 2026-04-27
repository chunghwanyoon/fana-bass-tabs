"""베이스 프렛보드 모델 + 음 → 프렛 위치 매핑."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Tuning:
    name: str
    strings: tuple[int, ...]  # 개방현 MIDI 노트, 인덱스 0 = 1번 줄 (가장 가는 줄)
    fret_count: int = 24


# 4현 표준: G2(43) D2(38) A1(33) E1(28)
TUNING_4 = Tuning(name="4string", strings=(43, 38, 33, 28))

# 5현 표준 (Low B): G2(43) D2(38) A1(33) E1(28) B0(23)
TUNING_5 = Tuning(name="5string", strings=(43, 38, 33, 28, 23))


def get_tuning(name: str) -> Tuning:
    if name == "4string":
        return TUNING_4
    if name == "5string":
        return TUNING_5
    raise ValueError(f"Unknown tuning: {name}")


def positions_for_pitch(pitch: int, tuning: Tuning) -> list[tuple[int, int]]:
    """이 음을 낼 수 있는 모든 (string_1based, fret) 후보."""
    out: list[tuple[int, int]] = []
    for i, open_pitch in enumerate(tuning.strings):
        fret = pitch - open_pitch
        if 0 <= fret <= tuning.fret_count:
            out.append((i + 1, fret))
    return out


def choose_positions(
    pitches: list[int], tuning: Tuning
) -> list[tuple[int, int] | None]:
    """직전 위치에서 손 이동 비용을 최소화하는 단순 휴리스틱.

    범위를 벗어나는 음은 None.
    """
    chosen: list[tuple[int, int] | None] = []
    prev: tuple[int, int] | None = None
    for p in pitches:
        candidates = positions_for_pitch(p, tuning)
        if not candidates:
            chosen.append(None)
            continue
        if prev is None:
            best = min(candidates, key=lambda sf: (sf[1], abs(sf[0] - 2)))
        else:
            ps, pf = prev
            best = min(
                candidates,
                key=lambda sf: (
                    abs(sf[0] - ps) * 2 + abs(sf[1] - pf),
                    sf[1],
                ),
            )
        chosen.append(best)
        prev = best
    return chosen
