"""Sample game-state fields from a running PCSX2 over PINE (upstream tools/pine.py)."""
import os
import socket
import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # tools/
from pine import OP_READ, Pine  # noqa: E402

GAME_ID = "SLUS-20772"


class L3Error(RuntimeError):
    pass


def default_sock():
    base = os.environ.get("XDG_RUNTIME_DIR") or os.environ.get("TMPDIR") or tempfile.gettempdir()
    return os.path.join(base, "pcsx2.sock")


class Pcsx2Sampler:
    def __init__(self, sock_path=None, pine=None):
        if pine is not None:
            self.pine = pine
            return
        path = sock_path or os.environ.get("PCSX2_PINE_SOCK") or default_sock()
        if not os.path.exists(path):
            raise L3Error(f"no PINE socket at {path}: start PCSX2 with PINE on, or set PCSX2_PINE_SOCK")
        p = Pine.__new__(Pine)
        p.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            p.s.connect(path)
        except OSError as e:
            raise L3Error(f"cannot connect to PINE at {path} ({e}); check PCSX2_PINE_SOCK") from None
        self.pine = p

    def check_game(self):
        gid = self.pine.game_id().strip()
        if gid != GAME_ID:
            raise L3Error(f"PCSX2 is running {gid or 'nothing'}, expected {GAME_ID} (SSX 3 USA)")

    def _words(self, fields):
        for f in fields:
            width = {"u8": 1, "u16": 2, "u32": 4, "f32": 4}[f.type]
            for i in range(f.count):
                yield f, f.addr + i * width, width

    def sample(self, fields):
        words = list(self._words(fields))
        if isinstance(self.pine, Pine):  # one batch, so every value comes from the same moment
            raw = self.pine.batch([struct.pack("<BI", OP_READ[w], a) for _, a, w in words])
            vals, off = [], 0
            for _, _, w in words:
                vals.append(int.from_bytes(raw[off:off + w], "little"))
                off += w
        else:
            vals = [self.pine.read(a, w) for _, a, w in words]
        out = {f.name: [] for f in fields}
        for (f, _, _), v in zip(words, vals):
            out[f.name].append(struct.unpack("<f", struct.pack("<I", v))[0] if f.type == "f32" else v)
        return out
