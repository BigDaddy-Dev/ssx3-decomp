"""Native side: read a RAM dump (SSX3_RAM_DUMP) and a state trace (SSX3_STATE_TRACE)."""
import struct

from .fields import decode, resolve


def dump_reader(ram):
    """read32(addr) over a 32 MiB EE RAM dump (KSEG addresses are masked like the bus does)."""
    def read32(a):
        return struct.unpack_from("<I", ram, a & 0x1ffffff)[0]
    return read32


def race_start(read32, frame_field, end_frame):
    """Boot frame at which the race counter was 0, from a dump taken after `end_frame` frames
    (the counter rises +1 per frame, docs/local/l3-spike.md)."""
    (f,) = resolve([frame_field], read32)
    return end_frame - read32(f.addr)


def read_trace(path, fields):
    """The trace file as decoded samples (fields must be resolved, in SSX3_STATE_RANGES order)."""
    size = 4 + sum(f.size for f in fields)
    data = open(path, "rb").read()
    return [decode(data[i:i + size], fields) for i in range(0, len(data) - size + 1, size)]
