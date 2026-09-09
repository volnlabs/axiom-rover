#!/usr/bin/env python3
"""Execute the committed AxiomOS Rust codec against rover wire fixtures."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import wire

DEFAULT_COMMIT = "4f5aa9037832b9ee27145c5ffc87f4c3ca707e18"
SOURCES = ["lib.rs", "motor.rs", "ring.rs", "session.rs", "watchdog.rs"]
DRIVER = r'''
extern crate shrike_link;
use shrike_link::{encode, Decoder, Msg, MAX_FRAME};

fn hex(bytes: &[u8]) -> String { bytes.iter().map(|b| format!("{b:02x}")).collect() }
fn unhex(s: &str) -> Vec<u8> {
    (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i+2], 16).unwrap()).collect()
}
fn main() {
    let messages = [
        Msg::MotorSetpoint { seq: 42, left: 400, right: -250 },
        Msg::Estop { assert: true }, Msg::Estop { assert: false },
        Msg::HeartbeatToShrike { seq: 48879 },
        Msg::Sensor { ultrasonic_echo_us: 12345, estop_line: true, flags: 165 },
        Msg::HeartbeatToPi { seq: 1 },
    ];
    for msg in messages {
        let mut out = [0u8; MAX_FRAME]; let n = encode(&msg, &mut out).unwrap();
        println!("ENC {}", hex(&out[..n]));
    }
    for arg in std::env::args().skip(1) {
        let mut decoder = Decoder::new(); let mut results = Vec::new();
        for (index, byte) in unhex(&arg).into_iter().enumerate() {
            if let Some(result) = decoder.push(byte) {
                results.push(match result {
                    Ok(msg) => {
                        let mut out = [0u8; MAX_FRAME]; let n = encode(&msg, &mut out).unwrap();
                        format!("Ok@{}:{}", index + 1, hex(&out[..n]))
                    },
                    Err(e) => format!("{e:?}@{}", index + 1),
                });
            }
        }
        println!("DEC {}", results.join("|"));
    }
}
'''


def run(command, **kwargs):
    return subprocess.run(command, text=True, capture_output=True, check=True, **kwargs).stdout.strip()


ERROR_NAMES = {
    "bad_crc": "BadCrc", "bad_version": "BadVersion", "bad_length": "BadLen",
    "unknown_type": "UnknownType",
}


def python_decode_results(streams):
    results = []
    for stream in streams:
        events = []
        for record in wire.decode(bytes.fromhex(stream)):
            if record.get("error") == "incomplete":
                continue
            if "message" in record:
                events.append(f"Ok@{record['end']}:{wire.encode(record['message']).hex()}")
            else:
                events.append(f"{ERROR_NAMES[record['error']]}@{record['end']}")
        results.append(events)
    return results


def decodes_match(streams, rust_results):
    return python_decode_results(streams) == rust_results


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--commit", default=DEFAULT_COMMIT)
    args = parser.parse_args(argv)
    resolved = run(["git", "-C", str(args.repo), "rev-parse", f"{args.commit}^{{commit}}"])
    cache = Path(__file__).resolve().parents[1] / ".cache"
    cache.mkdir(exist_ok=True)
    digest = hashlib.sha256()
    with tempfile.TemporaryDirectory(prefix="wire-compat-", dir=cache) as directory:
        temp = Path(directory)
        for name in SOURCES:
            data = subprocess.run(
                ["git", "-C", str(args.repo), "show", f"{resolved}:kernel/crates/shrike_link/src/{name}"],
                capture_output=True, check=True,
            ).stdout
            digest.update(name.encode() + b"\0" + data)
            (temp / name).write_bytes(data)
        (temp / "driver.rs").write_text(DRIVER)
        run(["rustc", "--edition=2021", "--crate-name", "shrike_link", "--crate-type", "rlib",
             str(temp / "lib.rs"), "-o", str(temp / "libshrike_link.rlib")])
        run(["rustc", "--edition=2021", str(temp / "driver.rs"), "--extern",
             f"shrike_link={temp / 'libshrike_link.rlib'}", "-o", str(temp / "driver")])

        uart = [entry["hex"] for entry in wire.vectors()["uart"]]
        good = uart[2]
        unknown_body = bytes.fromhex("01400199")
        unknown = (b"\x7e" + unknown_body + wire.crc16(unknown_body).to_bytes(2, "little")).hex()
        bad_crc = wire.vectors()["bad_crc"]["hex"] + good
        sync_payload = wire.encode({"type": "motor", "seq": 0x7E, "left": 0x7E, "right": 0x7E00}).hex()
        truncated = uart[0][:-2]
        streams = uart + [bad_crc, "7e02" + good, "7e010111" + good,
                          truncated, unknown + good, sync_payload]
        output = run([str(temp / "driver"), *streams]).splitlines()

    rust_vectors = [line[4:] for line in output if line.startswith("ENC ")]
    rust_decodes = [line[4:].split("|") if line[4:] else []
                    for line in output if line.startswith("DEC")]
    python_decodes = python_decode_results(streams)
    if rust_vectors != uart or not decodes_match(streams, rust_decodes):
        raise SystemExit(json.dumps({"status": "incompatible", "rust_vectors": rust_vectors,
                                     "python_vectors": uart, "rust_decodes": rust_decodes,
                                     "python_decodes": python_decodes}, indent=2))
    report = {
        "status": "compatible",
        "scope": "wire compatibility only; runtime safety not tested",
        "resolved_commit": resolved,
        "source_sha256": digest.hexdigest(),
        "rustc_version": run(["rustc", "--version"]),
        "uart_vectors_checked": len(uart),
        "decode_streams_checked": len(streams),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
