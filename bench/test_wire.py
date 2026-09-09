import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_compat
import wire


class WireTests(unittest.TestCase):
    def test_encodes_all_uart_messages_to_hand_checked_bytes(self):
        cases = [
            ({"type": "motor", "seq": 42, "left": 400, "right": -250}, "7e0101052a900106ff6e86"),
            ({"type": "estop", "assert": True}, "7e0102010104bf"),
            ({"type": "estop", "assert": False}, "7e0102010025af"),
            ({"type": "heartbeat_to_shrike", "seq": 48879}, "7e010302efbe7808"),
            ({"type": "sensor", "ultrasonic_echo_us": 12345, "estop_line": True, "flags": 165}, "7e018104393001a56c9d"),
            ({"type": "heartbeat_to_pi", "seq": 1}, "7e01820201005cd6"),
        ]
        for message, expected in cases:
            with self.subTest(message=message):
                self.assertEqual(wire.encode(message).hex(), expected)

    def test_decoder_reports_offsets_errors_and_incomplete_tail(self):
        good = wire.encode({"type": "estop", "assert": True})
        bad = bytearray(wire.encode({"type": "motor", "seq": 1, "left": 2, "right": 3}))
        bad[-1] ^= 1
        tail = wire.encode({"type": "heartbeat_to_pi", "seq": 9})[:-1]
        records = wire.decode(b"xx" + bytes(bad) + good + tail)
        self.assertEqual(records[0], {"offset": 2, "end": 13, "error": "bad_crc"})
        self.assertEqual(records[1]["offset"], 13)
        self.assertEqual(records[1]["message"], {"type": "estop", "assert": True})
        self.assertEqual(records[2], {"offset": 20, "end": 27, "error": "incomplete"})

    def test_sync_byte_inside_payload_is_not_resynchronised(self):
        frame = wire.encode({"type": "motor", "seq": 0x7E, "left": 0x7E, "right": 0x7E00})
        self.assertEqual(wire.decode(frame)[0]["message"], {"type": "motor", "seq": 126, "left": 126, "right": 32256})

    def test_known_type_bad_length_consumes_then_resynchronises(self):
        malformed = bytes.fromhex("7e0101020000")
        crc = wire.crc16(malformed[1:]).to_bytes(2, "little")
        good = wire.encode({"type": "heartbeat_to_pi", "seq": 2})
        records = wire.decode(malformed + crc + good)
        self.assertEqual(records[0]["error"], "bad_length")
        self.assertEqual(records[1]["message"]["seq"], 2)

    def test_header_errors_resynchronise_like_the_rust_decoder(self):
        good = wire.encode({"type": "estop", "assert": False})
        unknown_body = bytes.fromhex("01400199")
        unknown = b"\x7e" + unknown_body + wire.crc16(unknown_body).to_bytes(2, "little")
        cases = [
            (b"\x7e\x02" + good, "bad_version", 2),
            (bytes((0x7E, 1, 1, 17)) + good, "bad_length", 4),
            (unknown + good, "unknown_type", len(unknown)),
        ]
        for stream, error, end in cases:
            with self.subTest(error=error):
                records = wire.decode(stream)
                self.assertEqual(records[0], {"offset": 0, "end": end, "error": error})
                self.assertEqual(records[1]["message"], {"type": "estop", "assert": False})

    def test_strict_validation_rejects_bool_as_number_and_out_of_range(self):
        invalid = [
            {"type": "motor", "seq": True, "left": 0, "right": 0},
            {"type": "motor", "seq": 0, "left": 32768, "right": 0},
            {"type": "estop", "assert": 1},
            {"type": "sensor", "ultrasonic_echo_us": -1, "estop_line": False, "flags": 0},
        ]
        for message in invalid:
            with self.subTest(message=message), self.assertRaises((TypeError, ValueError)):
                wire.encode(message)

    def test_fpga_encoder_matches_axiomos_golden_and_enforces_envelope(self):
        self.assertEqual(wire.encode_fpga(0x2A, 400, -250).hex(), "7e0101062a900106ff00cc47")
        for args in [(0, 801, 0, 0), (0, 0, -801, 0), (0, 0, 0, 1), (True, 0, 0, 0)]:
            with self.subTest(args=args), self.assertRaises((TypeError, ValueError)):
                wire.encode_fpga(*args)

    def test_vectors_label_synthetic_and_freshness_dependent_traffic(self):
        vectors = wire.vectors()
        self.assertEqual(vectors["classification"], "synthetic")
        self.assertEqual(vectors["fpga_golden"]["hex"], "7e0101062a900106ff00cc47")
        self.assertEqual(vectors["traffic"]["duplicate"]["classification"], "protocol-valid; freshness-dependent")
        self.assertEqual(vectors["traffic"]["reordered"]["classification"], "protocol-valid; freshness-dependent")

    def test_cli_encodes_and_decodes(self):
        script = Path(wire.__file__)
        encoded = subprocess.run(
            [sys.executable, script, "encode", '{"type":"estop","assert":true}'],
            text=True, capture_output=True, check=True,
        )
        self.assertEqual(encoded.stdout.strip(), "7e0102010104bf")
        with tempfile.NamedTemporaryFile() as capture:
            capture.write(bytes.fromhex(encoded.stdout.strip()))
            capture.flush()
            decoded = subprocess.run([sys.executable, script, "decode", capture.name], text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(decoded.stdout)[0]["offset"], 0)

    def test_compat_executes_codec_from_pinned_axiomos_commit(self):
        repo = __import__("os").environ.get("AXIOMOS_REPO")
        if not repo:
            self.skipTest("set AXIOMOS_REPO to run committed-codec integration")
        script = Path(__file__).with_name("check_compat.py")
        result = subprocess.run(
            [sys.executable, script, "--repo", repo],
            text=True, capture_output=True, check=True,
        )
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "compatible")
        self.assertEqual(report["scope"], "wire compatibility only; runtime safety not tested")
        self.assertEqual(len(report["resolved_commit"]), 40)
        self.assertEqual(len(report["source_sha256"]), 64)
        self.assertTrue(report["rustc_version"].startswith("rustc "))

    def test_compat_rejects_changed_python_decoded_motor_semantics(self):
        stream = wire.encode({"type": "motor", "seq": 1, "left": 123, "right": -456}).hex()
        rust_results = [[f"Ok@11:{stream}"]]
        changed = [{"offset": 0, "end": 11,
                    "message": {"type": "motor", "seq": 1, "left": 124, "right": -456}}]
        with patch.object(wire, "decode", return_value=changed):
            self.assertFalse(check_compat.decodes_match([stream], rust_results))


if __name__ == "__main__":
    unittest.main()
