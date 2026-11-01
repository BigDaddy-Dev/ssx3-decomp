import pytest

from l3.fields import Field
from l3.pcsx2 import L3Error, Pcsx2Sampler


class FakePine:
    def __init__(self, gid="SLUS-20772", mem=None):
        self.gid, self.mem = gid, mem or {}

    def game_id(self):
        return self.gid

    def read(self, addr, width=4):
        return self.mem.get(addr, 0)


def test_rejects_wrong_game_id():
    with pytest.raises(L3Error, match="SLUS-20772"):
        Pcsx2Sampler(pine=FakePine("SLES-51697")).check_game()


def test_accepts_usa_disc():
    Pcsx2Sampler(pine=FakePine()).check_game()


def test_missing_socket_message(tmp_path):
    with pytest.raises(L3Error, match="PCSX2_PINE_SOCK"):
        Pcsx2Sampler(sock_path=str(tmp_path / "nope.sock"))


def test_sample_reads_fields():
    import struct
    bits = struct.unpack("<I", struct.pack("<f", 2.5))[0]
    p = FakePine(mem={0x10: 42, 0x20: bits, 0x24: bits})
    fs = [Field("score", 0x10, "u32", 0, 1), Field("pos", 0x20, "f32", 0.01, 2)]
    assert Pcsx2Sampler(pine=p).sample(fs) == {"score": [42], "pos": [2.5, 2.5]}
