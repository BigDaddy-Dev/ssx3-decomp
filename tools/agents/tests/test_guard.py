import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from guard import check_diff  # noqa: E402

MOD = "crates/ssx3-game/src/oc7.rs"


def test_allows_only_module():
    assert check_diff([("M", MOD)], MOD) == []
    assert check_diff([("A", MOD)], MOD) == []


def test_rejects_second_file():
    assert check_diff([("M", MOD), ("M", "crates/ssx3-game/src/oc8.rs")], MOD)


def test_rejects_overrides_txt():
    assert check_diff([("M", MOD), ("M", "overrides.txt")], MOD)


def test_rejects_lib_rs():
    assert check_diff([("M", MOD), ("M", "crates/ssx3-game/src/lib.rs")], MOD)


def test_rejects_cargo_toml():
    assert check_diff([("M", MOD), ("M", "crates/ssx3-game/Cargo.toml")], MOD)


def test_rejects_generated():
    assert check_diff([("M", "generated/ee/shard03/src/lib.rs")], MOD)


def test_rejects_rename():
    assert check_diff([("R100", MOD)], MOD)


def test_rejects_deleting_module():
    assert check_diff([("D", MOD)], MOD)


def test_rejects_empty_diff():
    out = check_diff([], MOD)
    assert out and "no change" in out[0]
