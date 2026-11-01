import struct

from l3.fields import Field
from l3.native import dump_reader, race_start, read_trace


def _ram(words):
    ram = bytearray(0x600000)
    for a, v in words.items():
        struct.pack_into("<I", ram, a, v)
    return bytes(ram)


def test_race_start_from_dump():
    ram = _ram({0x4a28a8: 0x500000, 0x500084: 0x510000, 0x51000c: 0x520000, 0x520008: 3498})
    frame = Field("frame", 0x8, "u32", chain=(0x4a28a8, 0x84, 0xc))
    assert race_start(dump_reader(ram), frame, end_frame=7950) == 4452


def test_read_trace_splits_records(tmp_path):
    fields = [Field("frame", 0x100, "u32"), Field("x", 0x200, "f32", count=2)]
    p = tmp_path / "t.bin"
    p.write_bytes(struct.pack("<IIff", 10, 5, 1.0, 2.0) + struct.pack("<IIff", 11, 6, 1.5, 2.0))
    rows = read_trace(p, fields)
    assert [r["frame"] for r in rows] == [[5], [6]]
    assert rows[1]["x"] == [1.5, 2.0] and rows[1]["_sample_frame"] == 11
