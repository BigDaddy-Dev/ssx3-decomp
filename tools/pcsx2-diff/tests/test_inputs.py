import struct

from l3.inputs import scenario_to_p2m2

HEADER = 570


def frame(data, f, port=0):
    off = HEADER + f * 36 + port * 18
    return data[off:off + 18]


def test_scenario_to_p2m2_header_and_frame0(tmp_path):
    out = tmp_path / "s.p2m2"
    scenario_to_p2m2("0:0008:2", 10, out)
    d = out.read_bytes()
    assert len(d) == HEADER + 10 * 36
    assert d[0] == 1
    assert d[51:51 + 9] == b"ssx3-port"
    assert d[306:306 + 10] == b"SLUS-20772"
    assert struct.unpack_from("<II?", d, 561) == (10, 0, False)
    f0 = frame(d, 0)
    assert f0[0] == 0xFF & ~0x08 and f0[1] == 0xFF          # Start held, active low
    assert f0[2:6] == bytes([0x7F] * 4)                       # sticks neutral
    assert f0[6:] == bytes(12)                                # no pressure (Start has none)
    assert frame(d, 0, port=1)[0:2] == b"\xff\xff"            # port 1 idle


def test_press_spans_frames(tmp_path):
    out = tmp_path / "s.p2m2"
    scenario_to_p2m2("100:4000:8", 120, out)
    d = out.read_bytes()
    for f in (99, 108):
        assert frame(d, f)[1] == 0xFF
    for f in range(100, 108):
        fr = frame(d, f)
        assert fr[1] == 0xFF & ~0x40 and fr[12] == 0xFF       # Cross bit and Cross pressure


def test_overlapping_presses_combine(tmp_path):
    out = tmp_path / "s.p2m2"
    scenario_to_p2m2("0:2020:4,2:0400:4", 8, out)             # Circle+Right, then L1 overlapping
    fr = frame(out.read_bytes(), 3)
    assert fr[0] == 0xFF & ~0x20 and fr[1] == 0xFF & ~(0x20 | 0x04)
    assert fr[6] == 0xFF and fr[11] == 0xFF and fr[14] == 0xFF


def test_press_past_end_is_clipped(tmp_path):
    out = tmp_path / "s.p2m2"
    scenario_to_p2m2("8:4000:8", 10, out)
    assert len(out.read_bytes()) == HEADER + 10 * 36
