from l3.script import (Press, format_script, gameplay_start, parse_script, per_side_script,
                       shift, split, trim_menu)

SNOW = ("1600:0008:8,2000:4000:8,3350:4000:8,3450:4000:8,3550:4000:8,4350:4000:8,4450:4000:8,"
        "4950:2080:60,5010:8000:50,5065:4000:35")


def test_parse_and_format_roundtrip():
    ps = parse_script("100:4000:8,200:2020:60")
    assert ps == [Press(100, 0x4000, 8), Press(200, 0x2020, 60)]
    assert format_script(ps) == "100:4000:8,200:2020:60"


def test_gameplay_start_is_first_circle_hold():
    assert gameplay_start(parse_script(SNOW)) == 4950


def test_gameplay_start_none_without_riding():
    assert gameplay_start(parse_script("1600:0008:8,2420:0020:30")) is None


def test_split_menu_and_race_presses():
    menu, race = split(parse_script(SNOW), 4950)
    assert [p.start for p in menu] == [1600, 2000, 3350, 3450, 3550, 4350, 4450]
    assert [p.start for p in race] == [4950, 5010, 5065]


def test_shift_race_presses_by_offset():
    race = parse_script("4950:2080:60,5010:8000:50")
    assert shift(race, -900) == [Press(4050, 0x2080, 60), Press(4110, 0x8000, 50)]
    assert shift(parse_script("10:4000:8"), -20) == []


def test_trim_menu_drops_presses_near_race_start():
    menu, _ = split(parse_script(SNOW), 4950)
    kept = trim_menu(menu, race_start=3552, margin=120)
    assert [p.start for p in kept] == [1600, 2000, 3350]     # 3450 >= 3552-120
    assert [p.start for p in trim_menu(menu, 3552, 0)] == [1600, 2000, 3350, 3450, 3550]


def test_per_side_script_lands_race_presses_on_same_race_frames():
    ps = parse_script(SNOW)
    nat = parse_script(per_side_script(ps, race_start=3552, ref_race_start=4452, margin=120))
    pcs = parse_script(per_side_script(ps, race_start=4452, ref_race_start=4452, margin=120))
    nat_race = [p.start - 3552 for p in nat if p.mask == 0x2080]
    pcs_race = [p.start - 4452 for p in pcs if p.mask == 0x2080]
    assert nat_race == pcs_race == [498]
    assert max(p.start for p in pcs if p.start < 4950) < 4452 - 120
