import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SIGNALS = (
    "estop_n", "fault_n", "pwm_l", "pwm_r", "l_in1", "l_in2",
    "r_in3", "r_in4", "drv_ain1", "drv_ain2", "drv_bin1",
    "drv_bin2", "nsleep",
)


class TraceCheckerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def manifest(self, **changes):
        value = {
            "schema_version": 1,
            "evidence": {
                "kind": "synthetic",
                "hardware_revision": "RevB",
                "software_ids": {"rover": "deadbeef", "axiomos": "cafebabe"},
                "instruments": [{
                    "name": "logic-export",
                    "calibration": "synthetic fixture",
                    "time_resolution_us": 1,
                    "timing_uncertainty_us": 1,
                }],
                "power_state": "motor_disconnected",
                "limits_declared_before_evaluation": True,
            },
            "limits": {
                "digital_tolerance_us": 2,
                "min_direction_mask_us": 5,
                "min_wakeup_us": 5,
                "max_sample_gap_us": 12,
            },
            "startup": {"observe_until_us": 0},
            "off_intervals": [{
                "id": "physical-estop",
                "event_us": 20,
                "stop_deadline_us": 25,
                "observe_until_us": 35,
                "max_pre_event_drive_gap_us": 5,
            }],
        }
        value.update(changes)
        path = self.root / "case.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def trace(self, rows, fieldnames=("time_us",) + SIGNALS):
        path = self.root / "capture.csv"
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return path

    @staticmethod
    def row(time_us, **changes):
        row = {name: 0 for name in SIGNALS}
        row.update(time_us=time_us, estop_n=1, fault_n=1)
        row.update(changes)
        return row

    def valid_rows(self):
        return [
            self.row(0, nsleep=1),
            self.row(5, l_in1=1, nsleep=1),
            self.row(10, pwm_l=1, l_in1=1, drv_ain1=1, nsleep=1),
            self.row(18, pwm_l=1, l_in1=1, drv_ain1=1, nsleep=1),
            self.row(20, estop_n=0, pwm_l=0, l_in1=1, drv_ain1=1, nsleep=1),
            self.row(22, estop_n=0, l_in1=1),
            self.row(25, estop_n=0), self.row(35, estop_n=0),
        ]

    def evaluate(self, rows=None, manifest=None, fieldnames=("time_us",) + SIGNALS):
        from bench.trace import evaluate
        return evaluate(manifest or self.manifest(), self.trace(rows or self.valid_rows(), fieldnames))

    def test_valid_capture_allows_declared_propagation(self):
        report = self.evaluate()
        self.assertTrue(report["passed"])
        self.assertEqual(["physical-estop"], report["checked_case_ids"])
        self.assertEqual("synthetic", report["evidence_kind"])
        self.assertIn("does not establish physical", report["limitation"])
        self.assertIn("externally annotated", report["limitation"])

    def test_rejects_missing_signal_nonfinite_time_and_nonbinary_value(self):
        variants = [
            (self.valid_rows(), ("time_us",) + SIGNALS[:-1]),
            ([self.row(0), self.row("nan")], ("time_us",) + SIGNALS),
            ([self.row(0), self.row(5, pwm_l=2)], ("time_us",) + SIGNALS),
        ]
        for rows, fields in variants:
            with self.subTest(fields=fields, last=rows[-1]):
                self.assertFalse(self.evaluate(rows, fieldnames=fields)["passed"])

    def test_rejects_wiring_mismatch_outside_tolerance(self):
        rows = self.valid_rows()
        rows[3]["time_us"] = 17
        rows[3]["drv_ain1"] = 0
        self.assertFalse(self.evaluate(rows)["passed"])

    def test_rejects_late_stop(self):
        rows = self.valid_rows()
        rows[6].update(pwm_l=1, drv_ain1=1, l_in1=1)
        self.assertFalse(self.evaluate(rows)["passed"])

    def test_rejects_stuck_pwm_during_hold(self):
        rows = self.valid_rows()
        rows[-1]["pwm_l"] = 1
        self.assertFalse(self.evaluate(rows)["passed"])

    def test_rejects_direction_transition_while_pwm_active(self):
        rows = self.valid_rows()
        rows.insert(4, self.row(19, pwm_l=1, l_in2=1, drv_ain2=1, nsleep=1))
        self.assertFalse(self.evaluate(rows)["passed"])

    def test_rejects_direction_transition_before_minimum_mask_elapsed(self):
        rows = self.valid_rows()
        rows[5].update(l_in1=0, l_in2=1)
        self.assertFalse(self.evaluate(rows)["passed"])

    def test_rejects_pwm_restart_before_direction_settles(self):
        rows = self.valid_rows()
        rows[6].update(l_in1=1, pwm_l=1, drv_ain1=1)
        self.assertFalse(self.evaluate(rows)["passed"])

    def test_software_stop_may_hold_nsleep_high(self):
        rows = self.valid_rows()
        for row in rows:
            row["estop_n"] = row["nsleep"] = 1
        self.assertTrue(self.evaluate(rows)["passed"])

    def test_rejects_sample_gaps_above_declared_limit(self):
        manifest = json.loads(self.manifest().read_text(encoding="utf-8"))
        manifest["limits"]["max_sample_gap_us"] = 5
        self.assertFalse(self.evaluate(manifest=self.manifest(**manifest))["passed"])

    def test_rejects_all_zero_nonstartup_capture(self):
        rows = [self.row(t, estop_n=0, fault_n=0) for t in (0, 5, 20, 25, 35)]
        self.assertFalse(self.evaluate(rows)["passed"])

    def test_rejects_truncated_hold_window(self):
        self.assertFalse(self.evaluate(self.valid_rows()[:-1])["passed"])

    def test_rejects_non_low_startup(self):
        rows = self.valid_rows()
        rows[0]["l_in1"] = 1
        self.assertFalse(self.evaluate(rows)["passed"])

    def test_rejects_invalid_or_posthoc_manifest(self):
        manifest = json.loads(self.manifest().read_text(encoding="utf-8"))
        manifest["evidence"]["limits_declared_before_evaluation"] = False
        manifest["off_intervals"][0]["stop_deadline_us"] = 19
        self.assertFalse(self.evaluate(manifest=self.manifest(**manifest))["passed"])

    def test_rejects_physical_evidence_with_weak_identity_or_wakeup_limit(self):
        manifest = json.loads(self.manifest().read_text(encoding="utf-8"))
        manifest["evidence"]["kind"] = "physical"
        manifest["limits"]["min_wakeup_us"] = 999
        self.assertFalse(self.evaluate(manifest=self.manifest(**manifest))["passed"])

    def test_rejects_unlabelled_instrument(self):
        manifest = json.loads(self.manifest().read_text(encoding="utf-8"))
        manifest["evidence"]["instruments"][0]["name"] = None
        self.assertFalse(self.evaluate(manifest=self.manifest(**manifest))["passed"])

    def test_startup_only_all_off_capture_passes_without_stop_claims(self):
        manifest = json.loads(self.manifest().read_text(encoding="utf-8"))
        manifest["off_intervals"] = []
        rows = [self.row(0, nsleep=1), self.row(5, nsleep=1)]
        report = self.evaluate(rows, self.manifest(**manifest))
        self.assertTrue(report["passed"])
        self.assertTrue(report["startup_checked"])
        self.assertEqual([], report["checked_case_ids"])

    def test_rejects_extra_csv_row_field(self):
        manifest = self.manifest()
        capture = self.trace(self.valid_rows())
        lines = capture.read_text(encoding="utf-8").splitlines()
        lines[1] += ",1"
        capture.write_text("\n".join(lines) + "\n", encoding="utf-8")
        from bench.trace import evaluate
        self.assertFalse(evaluate(manifest, capture)["passed"])

    def test_physical_uncertainty_requires_stop_before_the_measured_deadline(self):
        manifest = json.loads(self.manifest().read_text(encoding="utf-8"))
        manifest["evidence"].update(kind="physical", software_ids={
            "host_commit": "host", "rp2040_commit": "rp", "fpga_commit": "fpga",
            "rp2040_sha256": "1" * 64, "fpga_sha256": "2" * 64,
            "timing_manifest_sha256": "3" * 64,
        })
        manifest["limits"].update(min_wakeup_us=1000, max_sample_gap_us=1200)
        manifest["off_intervals"] = [{
            "id": "software-stop", "event_us": 2000,
            "stop_deadline_us": 2010, "observe_until_us": 2020,
            "max_pre_event_drive_gap_us": 10,
        }]
        rows = [
            self.row(0, nsleep=1), self.row(10, l_in1=1, nsleep=1),
            self.row(1014, pwm_l=1, l_in1=1, drv_ain1=1, nsleep=1),
            self.row(1999, pwm_l=1, l_in1=1, drv_ain1=1, nsleep=1),
            self.row(2010, l_in1=1, nsleep=1), self.row(2024, l_in1=1, nsleep=1),
        ]
        report = self.evaluate(rows, self.manifest(**manifest))
        self.assertFalse(report["passed"])
        self.assertEqual(4, report["physical_timing_margin_us"])

    def test_nsleep_fall_resets_wakeup_for_each_motor(self):
        manifest = json.loads(self.manifest().read_text(encoding="utf-8"))
        manifest["limits"].update(min_wakeup_us=5, max_sample_gap_us=10)
        manifest["off_intervals"][0].update(event_us=30, stop_deadline_us=32, observe_until_us=35)
        rows = [
            self.row(0, nsleep=1), self.row(5, l_in1=1, r_in3=1, nsleep=1),
            self.row(10, pwm_l=1, l_in1=1, r_in3=1, drv_ain1=1, nsleep=1),
            self.row(15, estop_n=0, pwm_l=1, l_in1=1, r_in3=1, drv_ain1=1),
            self.row(20, pwm_l=1, l_in1=1, r_in3=1, drv_ain1=1, nsleep=1),
            self.row(21, pwm_l=1, pwm_r=1, l_in1=1, r_in3=1, drv_ain1=1, drv_bin1=1, nsleep=1),
            self.row(30, l_in1=1, r_in3=1, nsleep=1), self.row(35, l_in1=1, r_in3=1, nsleep=1),
        ]
        self.assertFalse(self.evaluate(rows, self.manifest(**manifest))["passed"])

    def test_rejects_nsleep_rise_while_pwm_is_already_high(self):
        manifest = json.loads(self.manifest().read_text(encoding="utf-8"))
        manifest["limits"].update(min_direction_mask_us=1, min_wakeup_us=1000, max_sample_gap_us=1001)
        manifest["off_intervals"] = []
        rows = [
            self.row(0, nsleep=1), self.row(1, l_in1=1, nsleep=1),
            self.row(1001, pwm_l=1, l_in1=1, drv_ain1=1, nsleep=1),
            self.row(1100, estop_n=0, pwm_l=1, l_in1=1, drv_ain1=1),
            self.row(1200, pwm_l=1, l_in1=1, drv_ain1=1, nsleep=1),
            self.row(2200, l_in1=1, nsleep=1),
        ]
        self.assertFalse(self.evaluate(rows, self.manifest(**manifest))["passed"])

    def test_rejects_stale_historical_drive_before_event(self):
        rows = self.valid_rows()
        rows[3].update(time_us=11, pwm_l=0, drv_ain1=0)
        report = self.evaluate(rows)
        self.assertFalse(report["passed"])
        self.assertTrue(any("recent drive" in error for error in report["errors"]))

    def test_recent_pwm_pulse_can_precede_low_phase_at_event(self):
        rows = self.valid_rows()
        rows.insert(4, self.row(19, l_in1=1, nsleep=1))
        report = self.evaluate(rows)
        self.assertTrue(report["passed"])
        self.assertEqual(2, report["cases"][0]["observed_pre_event_drive_gap_us"])

    def test_rejects_direction_cleared_after_recent_drive(self):
        rows = self.valid_rows()
        rows.insert(4, self.row(19, nsleep=1))
        report = self.evaluate(rows)
        self.assertFalse(report["passed"])
        self.assertTrue(any("pre-event direction" in error for error in report["errors"]))

    def test_cli_writes_report_with_source_hash_without_modifying_inputs(self):
        manifest = self.manifest()
        capture = self.trace(self.valid_rows())
        before = (manifest.read_bytes(), capture.read_bytes())
        output = self.root / "report.json"
        run = subprocess.run(
            [sys.executable, "bench/trace.py", str(manifest), str(capture), "--output", str(output)],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
        )
        self.assertEqual(0, run.returncode, run.stderr)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertRegex(report["source_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(report["manifest_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(report["checker_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(before, (manifest.read_bytes(), capture.read_bytes()))

    def test_cli_refuses_to_overwrite_an_input(self):
        manifest = self.manifest()
        capture = self.trace(self.valid_rows())
        before = capture.read_bytes()
        run = subprocess.run(
            [sys.executable, "bench/trace.py", str(manifest), str(capture), "--output", str(capture)],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
        )
        self.assertNotEqual(0, run.returncode)
        self.assertEqual(before, capture.read_bytes())

    def test_cli_refuses_hardlinked_input_aliases(self):
        for source_name in ("manifest", "capture"):
            with self.subTest(source=source_name):
                manifest = self.manifest()
                capture = self.trace(self.valid_rows())
                source = manifest if source_name == "manifest" else capture
                before = source.read_bytes()
                output = self.root / "alias"
                if output.exists():
                    output.unlink()
                os.link(source, output)
                run = subprocess.run(
                    [sys.executable, "bench/trace.py", str(manifest), str(capture), "--output", str(output)],
                    cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
                )
                self.assertNotEqual(0, run.returncode)
                self.assertEqual(before, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
