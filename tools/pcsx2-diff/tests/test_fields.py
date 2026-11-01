import struct

import pytest

from l3.fields import Field, decode, load_fields, ranges


def test_load_fields(tmp_path):
    p = tmp_path / "f.toml"
    p.write_text('[[field]]\nname = "rider_pos"\naddr = 0x4a1000\ntype = "f32"\ntol = 0.01\ncount = 3\n'
                 '[[field]]\nname = "score"\naddr = 0x4a2000\ntype = "u32"\n')
    assert load_fields(p) == [Field("rider_pos", 0x4A1000, "f32", 0.01, 3), Field("score", 0x4A2000, "u32", 0.0, 1)]


def test_ranges_format():
    fs = [Field("a", 0x4A1000, "f32", 0.01, 3), Field("b", 0x100, "u16", 0, 1)]
    assert ranges(fs) == "0x4a1000+12,0x100+2"


def test_decode_f32_array():
    fs = [Field("pos", 0x10, "f32", 0.01, 3), Field("mode", 0x20, "u8", 0, 1)]
    rec = struct.pack("<I", 600) + struct.pack("<3f", 1.5, -2.0, 3.25) + bytes([7])
    out = decode(rec, fs)
    assert out == {"_sample_frame": 600, "pos": [1.5, -2.0, 3.25], "mode": [7]}


def test_decode_short_record_raises():
    with pytest.raises(ValueError):
        decode(struct.pack("<I", 1) + b"\0", [Field("x", 0, "u32", 0, 1)])
