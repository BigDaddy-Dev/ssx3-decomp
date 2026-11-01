"""Game-state fields compared between the native build and PCSX2 (fields.toml)."""
import struct
import tomllib
from dataclasses import dataclass

FMT = {"u8": "B", "u16": "H", "u32": "I", "f32": "f"}
SIZE = {"u8": 1, "u16": 2, "u32": 4, "f32": 4}


@dataclass(frozen=True)
class Field:
    name: str
    addr: int
    type: str
    tol: float = 0.0
    count: int = 1

    @property
    def size(self):
        return SIZE[self.type] * self.count


def load_fields(path):
    with open(path, "rb") as f:
        rows = tomllib.load(f)["field"]
    return [Field(r["name"], r["addr"], r["type"], float(r.get("tol", 0)), r.get("count", 1)) for r in rows]


def ranges(fields):
    """The SSX3_STATE_RANGES value for these fields (the native trace hook)."""
    return ",".join(f"{f.addr:#x}+{f.size}" for f in fields)


def decode(record, fields):
    """One native trace record: u32 sample frame, then each field's bytes in order."""
    need = 4 + sum(f.size for f in fields)
    if len(record) < need:
        raise ValueError(f"trace record is {len(record)} bytes, fields need {need}")
    out = {"_sample_frame": struct.unpack_from("<I", record)[0]}
    off = 4
    for f in fields:
        out[f.name] = list(struct.unpack_from(f"<{f.count}{FMT[f.type]}", record, off))
        off += f.size
    return out
