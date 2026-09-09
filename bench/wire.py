#!/usr/bin/env python3
"""Independent AxiomOS/Shrike wire fixtures; never drives serial hardware."""

import argparse
import binascii
import json
import struct
from pathlib import Path

SYNC = 0x7E
VERSION = 1
MAX_PAYLOAD = 16
TYPES = {
    "motor": (0x01, "<Bhh"),
    "estop": (0x02, "<?"),
    "heartbeat_to_shrike": (0x03, "<H"),
    "sensor": (0x81, "<H?B"),
    "heartbeat_to_pi": (0x82, "<H"),
}
BY_TYPE = {value[0]: (name, value[1]) for name, value in TYPES.items()}


def crc16(data):
    return binascii.crc_hqx(data, 0xFFFF)


def _integer(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if not low <= value <= high:
        raise ValueError(f"{name} must be in {low}..={high}")
    return value


def _boolean(value, name):
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be boolean")
    return value


def encode(message):
    if not isinstance(message, dict) or message.get("type") not in TYPES:
        raise ValueError("unknown message type")
    name = message["type"]
    ty, _ = TYPES[name]
    if name == "motor":
        values = (_integer(message["seq"], "seq", 0, 255),
                  _integer(message["left"], "left", -32768, 32767),
                  _integer(message["right"], "right", -32768, 32767))
    elif name == "estop":
        values = (_boolean(message["assert"], "assert"),)
    elif name.startswith("heartbeat"):
        values = (_integer(message["seq"], "seq", 0, 65535),)
    else:
        values = (_integer(message["ultrasonic_echo_us"], "ultrasonic_echo_us", 0, 65535),
                  _boolean(message["estop_line"], "estop_line"),
                  _integer(message["flags"], "flags", 0, 255))
    payload = struct.pack(TYPES[name][1], *values)
    body = bytes((VERSION, ty, len(payload))) + payload
    return bytes((SYNC,)) + body + crc16(body).to_bytes(2, "little")


def _message(ty, payload):
    name, fmt = BY_TYPE[ty]
    values = struct.unpack(fmt, payload)
    if name == "motor":
        return {"type": name, "seq": values[0], "left": values[1], "right": values[2]}
    if name == "estop":
        return {"type": name, "assert": bool(values[0])}
    if name.startswith("heartbeat"):
        return {"type": name, "seq": values[0]}
    return {"type": name, "ultrasonic_echo_us": values[0], "estop_line": bool(values[1]), "flags": values[2]}


def decode(data):
    records = []
    offset = 0
    while offset < len(data):
        try:
            start = data.index(SYNC, offset)
        except ValueError:
            break
        if len(data) - start < 2:
            records.append({"offset": start, "end": len(data), "error": "incomplete"})
            break
        if data[start + 1] != VERSION:
            records.append({"offset": start, "end": start + 2, "error": "bad_version"})
            offset = start + 2
            continue
        if len(data) - start < 4:
            records.append({"offset": start, "end": len(data), "error": "incomplete"})
            break
        version, ty, length = data[start + 1:start + 4]
        end = start + 6 + length
        if length > MAX_PAYLOAD:
            records.append({"offset": start, "end": start + 4, "error": "bad_length"})
            offset = start + 4
            continue
        if end > len(data):
            records.append({"offset": start, "end": len(data), "error": "incomplete"})
            break
        frame = data[start:end]
        if crc16(frame[1:-2]) != int.from_bytes(frame[-2:], "little"):
            error = "bad_crc"
        elif ty not in BY_TYPE:
            error = "unknown_type"
        elif length != struct.calcsize(BY_TYPE[ty][1]):
            error = "bad_length"
        else:
            records.append({"offset": start, "end": end, "message": _message(ty, frame[4:-2])})
            offset = end
            continue
        records.append({"offset": start, "end": end, "error": error})
        offset = end
    return records


def encode_fpga(seq, left, right, flags=0):
    seq = _integer(seq, "seq", 0, 255)
    left = _integer(left, "left", -800, 800)
    right = _integer(right, "right", -800, 800)
    flags = _integer(flags, "flags", 0, 0)
    body = struct.pack("<BBBBBhhB", SYNC, VERSION, 1, 6, seq, left, right, flags)
    return body + crc16(body[1:]).to_bytes(2, "little")


def vectors():
    messages = [
        {"type": "motor", "seq": 42, "left": 400, "right": -250},
        {"type": "estop", "assert": True}, {"type": "estop", "assert": False},
        {"type": "heartbeat_to_shrike", "seq": 48879},
        {"type": "sensor", "ultrasonic_echo_us": 12345, "estop_line": True, "flags": 165},
        {"type": "heartbeat_to_pi", "seq": 1},
    ]
    encoded = [{"message": msg, "hex": encode(msg).hex()} for msg in messages]
    bad = bytearray(bytes.fromhex(encoded[0]["hex"])); bad[-1] ^= 1
    motor = encoded[0]["hex"]
    return {
        "classification": "synthetic", "uart": encoded,
        "bad_crc": {"hex": bad.hex(), "classification": "synthetic invalid"},
        "truncated": {"hex": motor[:-2], "classification": "synthetic invalid"},
        "traffic": {
            "duplicate": {"hex": motor + motor, "classification": "protocol-valid; freshness-dependent"},
            "reordered": {"hex": encode({"type": "motor", "seq": 44, "left": 0, "right": 0}).hex() + motor,
                          "classification": "protocol-valid; freshness-dependent"},
        },
        "fpga_golden": {"hex": encode_fpga(0x2A, 400, -250).hex(), "classification": "synthetic protocol fixture"},
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    enc = commands.add_parser("encode"); enc.add_argument("json")
    dec = commands.add_parser("decode"); dec.add_argument("file", type=Path)
    commands.add_parser("vectors")
    args = parser.parse_args(argv)
    if args.command == "encode":
        print(encode(json.loads(args.json)).hex())
    elif args.command == "decode":
        print(json.dumps(decode(args.file.read_bytes()), indent=2))
    else:
        print(json.dumps(vectors(), indent=2))


if __name__ == "__main__":
    main()
