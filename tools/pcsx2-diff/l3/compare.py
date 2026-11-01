"""Find the first frame where native and PCSX2 game state differ beyond each field's tolerance."""
from dataclasses import dataclass


@dataclass
class Divergence:
    frame: int
    fields: dict  # name -> (native values, pcsx2 values)


def _differs(f, a, b):
    if len(a) != len(b):
        return True
    if f.type == "f32":
        return any(abs(x - y) > f.tol for x, y in zip(a, b))
    return a != b


def first_divergence(native, pcsx2, fields):
    """Samples are matched by the game's own `frame` field; frames missing on one side are skipped."""
    theirs = {s["frame"][0]: s for s in pcsx2}
    for mine in sorted(native, key=lambda s: s["frame"][0]):
        other = theirs.get(mine["frame"][0])
        if other is None:
            continue
        bad = {f.name: (mine[f.name], other[f.name]) for f in fields
               if f.name != "frame" and _differs(f, mine[f.name], other[f.name])}
        if bad:
            return Divergence(mine["frame"][0], bad)
    return None
