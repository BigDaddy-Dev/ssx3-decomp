import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_staged import check  # noqa: E402

MB = 1_048_576


def test_blocks_iso():
    assert check([("A", "SSX 3 (USA).iso", 10, False)])


def test_blocks_generated():
    assert check([("A", "generated/ee/shard00.rs", 10, False)])


def test_blocks_rename_into_generated():
    assert check([("R100", "generated/vu/x.rs", 10, False)])


def test_blocks_large_binary():
    assert check([("A", "docs/x.png", MB + 1, True)])


def test_allows_large_text():
    assert check([("M", "crates/ssx3-game/src/big.rs", 2 * MB, False)]) == []


def test_allows_path_with_spaces():
    assert check([("A", "docs/local/a b.md", 10, False)]) == []


def test_deletions_allowed():
    assert check([("D", "generated/x", 0, False)]) == []


def test_blocks_ram_dump():
    assert check([("A", "out/ram-race.bin", 10, True)])


def test_blocks_gs_dump():
    assert check([("A", "dumps/frame.gs", 10, True)])
