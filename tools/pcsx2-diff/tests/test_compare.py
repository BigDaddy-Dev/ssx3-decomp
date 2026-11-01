from l3.compare import Divergence, first_divergence
from l3.fields import Field

FS = [Field("frame", 0, "u32", 0, 1), Field("score", 4, "u32", 0, 1), Field("pos", 8, "f32", 0.01, 1)]


def s(frame, score=0, pos=1.0):
    return {"frame": [frame], "score": [score], "pos": [pos]}


def test_first_divergence_none_within_tol():
    assert first_divergence([s(1, pos=1.0)], [s(1, pos=1.005)], FS) is None


def test_first_divergence_reports_earliest():
    nat = [s(1), s(2, score=5), s(3, score=9)]
    pcs = [s(1), s(2, score=6), s(3, score=8)]
    assert first_divergence(nat, pcs, FS) == Divergence(2, {"score": ([5], [6])})


def test_int_exact_float_tol():
    d = first_divergence([s(1, score=1, pos=1.0)], [s(1, score=1, pos=1.02)], FS)
    assert d == Divergence(1, {"pos": ([1.0], [1.02])})


def test_missing_frames_skipped():
    nat = [s(1), s(2, score=99), s(3)]
    pcs = [s(1), s(3)]
    assert first_divergence(nat, pcs, FS) is None
