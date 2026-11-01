"""Turn an upstream scenario input script (SSX3_INPUT) into a PCSX2 .p2m2 input recording.

Layout: docs/local/pcsx2-comparison.md (PCSX2 v2.8.2 InputRecordingFile/PadData).
"""
import struct

HEADER = struct.Struct("<B50s255s255sII?")  # 570 bytes
# libpad bit -> pressure byte index within the 18-byte pad record.
PRESSURE = {0x20: 6, 0x80: 7, 0x10: 8, 0x40: 9, 0x1000: 10, 0x2000: 11, 0x4000: 12, 0x8000: 13,
            0x400: 14, 0x800: 15, 0x100: 16, 0x200: 17}
IDLE = bytes([0xFF, 0xFF, 0x7F, 0x7F, 0x7F, 0x7F]) + bytes(12)


def _held(script, total_frames):
    held = [0] * total_frames
    for item in filter(None, script.split(",")):
        start, buttons, n = item.split(":")
        start, mask, n = int(start), int(buttons, 16), int(n)
        for f in range(start, min(start + n, total_frames)):
            held[f] |= mask
    return held


def _pad(mask):
    rec = bytearray(IDLE)
    rec[0] = ~mask & 0xFF
    rec[1] = ~(mask >> 8) & 0xFF
    for bit, idx in PRESSURE.items():
        if mask & bit:
            rec[idx] = 0xFF
    return bytes(rec)


def scenario_to_p2m2(ssx3_input, total_frames, out_path):
    with open(out_path, "wb") as f:
        f.write(HEADER.pack(1, b"PCSX2-v2.8.2", b"ssx3-port", b"SLUS-20772", total_frames, 0, False))
        for mask in _held(ssx3_input, total_frames):
            f.write(_pad(mask) + IDLE)
