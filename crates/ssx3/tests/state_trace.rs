//! SSX3_STATE_TRACE: per-frame samples of guest RAM ranges from the headless runner
//! (tools/pcsx2-diff). Needs `generated/` and the game data, so it is ignored by default:
//! `cargo test --profile game -p ssx3 --test state_trace -- --ignored`.

use std::process::Command;

#[test]
#[ignore]
fn scenarios_trace_matches_ram_dump() {
    let dir = std::env::temp_dir().join(format!("ssx3-trace-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let trace = dir.join("trace.bin");
    let ram = dir.join("ram.bin");
    let status = Command::new(env!("CARGO_BIN_EXE_ssx3-headless"))
        .arg("600")
        .current_dir(env!("CARGO_MANIFEST_DIR").to_owned() + "/../..")
        .env("SSX3_EVENT", "BRA2")
        .env("SSX3_RAM_DUMP", &ram)
        .env("SSX3_STATE_TRACE", &trace)
        .env("SSX3_STATE_RANGES", "0x100000+256,0x4a0000+8")
        .env("SSX3_STATE_EVERY", "600")
        .status()
        .unwrap();
    assert!(status.success());
    let t = std::fs::read(&trace).expect("trace file written");
    let r = std::fs::read(&ram).unwrap();
    assert_eq!(t.len(), 4 + 256 + 8, "one record at frame 600");
    assert_eq!(u32::from_le_bytes(t[0..4].try_into().unwrap()), 600);
    assert_eq!(&t[4..260], &r[0x100000..0x100100]);
    assert_eq!(&t[260..268], &r[0x4a0000..0x4a0008]);
}

#[test]
#[ignore]
fn no_trace_without_env() {
    let dir = std::env::temp_dir().join(format!("ssx3-notrace-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let status = Command::new(env!("CARGO_BIN_EXE_ssx3-headless"))
        .arg("5")
        .current_dir(env!("CARGO_MANIFEST_DIR").to_owned() + "/../..")
        .env("SSX3_STATE_RANGES", "0x100000+4")
        .env_remove("SSX3_STATE_TRACE")
        .status()
        .unwrap();
    assert!(status.success());
    assert!(std::fs::read_dir(&dir).unwrap().next().is_none());
}
