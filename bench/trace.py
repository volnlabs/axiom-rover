#!/usr/bin/env python3
"""Validate a RevB bench logic capture against its predeclared cases."""

import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path


SIGNALS = (
    "estop_n", "fault_n", "pwm_l", "pwm_r", "l_in1", "l_in2",
    "r_in3", "r_in4", "drv_ain1", "drv_ain2", "drv_bin1",
    "drv_bin2", "nsleep",
)
STARTUP_LOW = ("pwm_l", "pwm_r", "l_in1", "l_in2", "r_in3", "r_in4", "drv_ain1", "drv_ain2", "drv_bin1", "drv_bin2")
OFF_SIGNALS = ("pwm_l", "pwm_r", "drv_ain1", "drv_ain2", "drv_bin1", "drv_bin2")


def _finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _failure(source_hash, evidence_kind, errors, checked=()):
    limitation = (
        "Synthetic evidence does not establish physical hardware behavior."
        if evidence_kind == "synthetic"
        else "Digital samples cannot establish sub-sample analog timing or motor behavior."
    )
    return {
        "passed": False,
        "source_sha256": source_hash,
        "checked_case_ids": list(checked),
        "evidence_kind": evidence_kind,
        "limitation": limitation + (
            " Event times are externally annotated and need raw UART/SPI/reset capture corroboration."
            " This report does not authenticate metadata, identify the stimulus or ack owner, or measure requested PWM duty."
        ),
        "errors": errors,
    }


def _load_manifest(data):
    value = json.loads(data.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("manifest must be a JSON object")
    evidence = value.get("evidence")
    limits = value.get("limits")
    startup = value.get("startup")
    cases = value.get("off_intervals")
    if value.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    if not isinstance(evidence, dict) or evidence.get("kind") not in ("physical", "synthetic"):
        raise ValueError("evidence.kind must be physical or synthetic")
    required = ("hardware_revision", "software_ids", "instruments", "power_state")
    if any(not evidence.get(name) for name in required):
        raise ValueError("evidence metadata is incomplete")
    if evidence.get("limits_declared_before_evaluation") is not True:
        raise ValueError("limits must be declared before evaluation")
    if not isinstance(evidence["software_ids"], dict) or not isinstance(evidence["instruments"], list):
        raise ValueError("software_ids must be an object and instruments a list")
    for instrument in evidence["instruments"]:
        if not isinstance(instrument, dict) or any(
            name not in instrument for name in ("name", "calibration", "time_resolution_us", "timing_uncertainty_us")
        ):
            raise ValueError("each instrument needs name, calibration, time_resolution_us, and timing_uncertainty_us")
        if any(not isinstance(instrument[name], str) or not instrument[name] for name in ("name", "calibration")):
            raise ValueError("instrument name and calibration must be nonempty strings")
        for field in ("time_resolution_us", "timing_uncertainty_us"):
            number = instrument[field]
            if not _finite_number(number) or number < 0:
                raise ValueError(f"instrument {field} must be finite and nonnegative")
        if instrument["time_resolution_us"] == 0:
            raise ValueError("instrument time_resolution_us must be positive")
    if not isinstance(limits, dict):
        raise ValueError("limits must be an object")
    for name in ("digital_tolerance_us", "min_direction_mask_us", "min_wakeup_us", "max_sample_gap_us"):
        number = limits.get(name)
        if not _finite_number(number) or number < 0:
            raise ValueError(f"limits.{name} must be finite and nonnegative")
    if limits["max_sample_gap_us"] == 0:
        raise ValueError("limits.max_sample_gap_us must be positive")
    if evidence["power_state"] != "motor_disconnected":
        raise ValueError("phase1 power_state must be motor_disconnected")
    if evidence["kind"] == "physical":
        ids = evidence["software_ids"]
        exact = {"host_commit", "rp2040_commit", "rp2040_sha256", "fpga_commit", "fpga_sha256", "timing_manifest_sha256"}
        if set(ids) != exact or any(not isinstance(ids[name], str) or not ids[name] for name in exact):
            raise ValueError("physical evidence requires the exact nonempty software_ids fields")
        for name in ("rp2040_sha256", "fpga_sha256", "timing_manifest_sha256"):
            if len(ids[name]) != 64 or any(char not in "0123456789abcdefABCDEF" for char in ids[name]):
                raise ValueError(f"physical evidence {name} must be a 64-digit hex hash")
        if limits["min_wakeup_us"] < 1000:
            raise ValueError("physical evidence min_wakeup_us must be at least 1000")
    if not isinstance(startup, dict) or not _finite_number(startup.get("observe_until_us")) or startup["observe_until_us"] < 0:
        raise ValueError("startup.observe_until_us is required")
    if not isinstance(cases, list):
        raise ValueError("off_intervals must be a list")
    ids = set()
    for case in cases:
        expected_fields = {"id", "event_us", "stop_deadline_us", "observe_until_us", "max_pre_event_drive_gap_us"}
        if not isinstance(case, dict) or set(case) != expected_fields:
            raise ValueError("each off interval needs exactly id, event_us, stop_deadline_us, observe_until_us, max_pre_event_drive_gap_us")
        case_id = case["id"]
        times = [case[name] for name in ("event_us", "stop_deadline_us", "observe_until_us")]
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise ValueError("case IDs must be unique nonempty strings")
        if any(not _finite_number(t) for t in times) or not times[0] <= times[1] <= times[2]:
            raise ValueError(f"case {case_id}: require finite event <= stop deadline <= observe until")
        if not _finite_number(case["max_pre_event_drive_gap_us"]) or case["max_pre_event_drive_gap_us"] <= 0:
            raise ValueError(f"case {case_id}: max_pre_event_drive_gap_us must be finite and positive")
        ids.add(case_id)
    return value


def _load_rows(data):
    with io.StringIO(data.decode("utf-8"), newline="") as stream:
        reader = csv.DictReader(stream)
        expected = {"time_us", *SIGNALS}
        if reader.fieldnames is None or set(reader.fieldnames) != expected or len(reader.fieldnames) != len(expected):
            raise ValueError("CSV columns must be exactly time_us and the required signals")
        rows = []
        previous = None
        for line, raw in enumerate(reader, 2):
            if None in raw or any(value is None for value in raw.values()):
                raise ValueError(f"line {line}: row does not match the CSV header")
            try:
                when = float(raw["time_us"])
            except (TypeError, ValueError):
                raise ValueError(f"line {line}: invalid time_us") from None
            if not math.isfinite(when) or previous is not None and when <= previous:
                raise ValueError(f"line {line}: time_us must be finite and strictly increasing")
            row = {"time_us": when}
            for signal in SIGNALS:
                if raw[signal] not in ("0", "1"):
                    raise ValueError(f"line {line}: {signal} must be exactly 0 or 1")
                row[signal] = int(raw[signal])
            rows.append(row)
            previous = when
    if not rows:
        raise ValueError("capture has no samples")
    return rows


def _edge_times(rows, expected):
    values = [expected(row) for row in rows]
    return [rows[i]["time_us"] for i in range(1, len(rows)) if values[i] != values[i - 1]]


def _check_follow(rows, output, expected, tolerance, errors):
    edges = _edge_times(rows, expected)
    for row in rows:
        if row[output] != expected(row) and not any(0 <= row["time_us"] - edge <= tolerance for edge in edges):
            errors.append(f"{output} mismatch at {row['time_us']} us outside {tolerance} us tolerance")


def evaluate(manifest_path, csv_path):
    source_hash = manifest_hash = ""
    evidence_kind = "unknown"
    try:
        source = Path(csv_path).read_bytes()
        manifest_source = Path(manifest_path).read_bytes()
        source_hash = hashlib.sha256(source).hexdigest()
        manifest_hash = hashlib.sha256(manifest_source).hexdigest()
        manifest = _load_manifest(manifest_source)
        evidence_kind = manifest["evidence"]["kind"]
        rows = _load_rows(source)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        report = _failure(source_hash, evidence_kind, [str(error)])
        report["manifest_sha256"] = manifest_hash
        report["checker_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        return report

    errors = []
    physical_margin = 0
    if evidence_kind == "physical":
        physical_margin = 2 * max(
            item["time_resolution_us"] + item["timing_uncertainty_us"]
            for item in manifest["evidence"]["instruments"]
        )
    tolerance = manifest["limits"]["digital_tolerance_us"]
    maximum_gap = manifest["limits"]["max_sample_gap_us"]
    for previous, current in zip(rows, rows[1:]):
        if current["time_us"] - previous["time_us"] > maximum_gap:
            errors.append(f"sample gap ending at {current['time_us']} us exceeds {maximum_gap} us")
    _check_follow(rows, "nsleep", lambda row: row["estop_n"], tolerance, errors)
    for output, direction, pwm in (
        ("drv_ain1", "l_in1", "pwm_l"), ("drv_ain2", "l_in2", "pwm_l"),
        ("drv_bin1", "r_in3", "pwm_r"), ("drv_bin2", "r_in4", "pwm_r"),
    ):
        _check_follow(rows, output, lambda row, d=direction, p=pwm: row[d] & row[p], tolerance, errors)

    minimum = manifest["limits"]["min_direction_mask_us"] + physical_margin
    for directions, pwm in (("l_in1 l_in2".split(), "pwm_l"), ("r_in3 r_in4".split(), "pwm_r")):
        low_since = rows[0]["time_us"] if not rows[0][pwm] else None
        last_direction_change = None
        for index, row in enumerate(rows):
            if index and rows[index - 1][pwm] and not row[pwm]:
                low_since = row["time_us"]
            if index and any(row[name] != rows[index - 1][name] for name in directions):
                last_direction_change = row["time_us"]
                if rows[index - 1][pwm] or row[pwm]:
                    errors.append(f"{pwm} was not low on both samples around direction change at {row['time_us']} us")
                elif low_since is None or row["time_us"] - low_since < minimum:
                    errors.append(f"{pwm} mask before direction change at {row['time_us']} us was shorter than {minimum} us")
            if index and not rows[index - 1][pwm] and row[pwm]:
                if last_direction_change is not None and row["time_us"] - last_direction_change < minimum:
                    errors.append(f"direction did not settle for {minimum} us before {pwm} rose at {row['time_us']} us")
                low_since = None

    awake_since = rows[0]["time_us"] if rows[0]["nsleep"] else None
    for index, row in enumerate(rows):
        if index and rows[index - 1]["nsleep"] and not row["nsleep"]:
            awake_since = None
        if index and not rows[index - 1]["nsleep"] and row["nsleep"]:
            awake_since = row["time_us"]
            if row["pwm_l"] or row["pwm_r"]:
                errors.append(f"nSLEEP rose while PWM was high at {row['time_us']} us")
        for pwm in ("pwm_l", "pwm_r"):
            if index and not rows[index - 1][pwm] and row[pwm]:
                required = manifest["limits"]["min_wakeup_us"] + physical_margin
                if awake_since is None or row["time_us"] - awake_since < required:
                    errors.append(f"{pwm} rose before the declared nSLEEP wakeup interval at {row['time_us']} us")

    startup_end = manifest["startup"]["observe_until_us"]
    if rows[0]["time_us"] > 0 or rows[-1]["time_us"] < startup_end:
        errors.append("capture does not cover the startup window from 0 us")
    elif any(row[name] for row in rows if row["time_us"] <= startup_end for name in STARTUP_LOW):
        errors.append("startup outputs are not default-low")

    checked = []
    case_reports = []
    for case in manifest["off_intervals"]:
        case_id = case["id"]
        checked.append(case_id)
        event, deadline, hold_end = case["event_us"], case["stop_deadline_us"], case["observe_until_us"]
        if rows[0]["time_us"] > event or rows[-1]["time_us"] < hold_end + physical_margin:
            errors.append(f"case {case_id}: capture does not cover event, deadline, and hold window")
            continue
        before = [row for row in rows if row["time_us"] < event]
        latest = before[-1] if before else None
        earliest_drive = event - case["max_pre_event_drive_gap_us"]
        recent = []
        for row in before:
            if row["time_us"] < earliest_drive:
                continue
            if row["pwm_l"] and (row["drv_ain1"] or row["drv_ain2"]):
                recent.append((row["time_us"], ("l_in1", "l_in2")))
            if row["pwm_r"] and (row["drv_bin1"] or row["drv_bin2"]):
                recent.append((row["time_us"], ("r_in3", "r_in4")))
        observed_gap = event - max((item[0] for item in recent), default=event)
        if not recent:
            errors.append(f"case {case_id}: no recent drive-high sample before event")
            observed_gap = None
        elif latest is None or not latest["nsleep"] or not any(any(latest[name] for name in directions) for _, directions in recent):
            errors.append(f"case {case_id}: pre-event direction or nSLEEP was not enabled for the driven channel")
        case_reports.append({"id": case_id, "observed_pre_event_drive_gap_us": observed_gap})
        deadline_candidates = [i for i, row in enumerate(rows) if row["time_us"] <= deadline - physical_margin]
        if not deadline_candidates:
            errors.append(f"case {case_id}: no sample proves stop before deadline with timing margin")
            continue
        deadline_index = max(deadline_candidates)
        hold_index = min(i for i, row in enumerate(rows) if row["time_us"] >= hold_end + physical_margin)
        if any(rows[i][name] for i in range(deadline_index, hold_index + 1) for name in OFF_SIGNALS):
            errors.append(f"case {case_id}: gates or driver inputs were not off by deadline and held off")

    report = _failure(source_hash, evidence_kind, errors, checked)
    report["passed"] = not errors
    report["manifest_sha256"] = manifest_hash
    report["checker_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report["declared_limits"] = manifest["limits"]
    report["hardware_revision"] = manifest["evidence"]["hardware_revision"]
    report["power_state"] = manifest["evidence"]["power_state"]
    report["physical_timing_margin_us"] = physical_margin
    report["startup_checked"] = True
    report["cases"] = case_reports
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    aliases_input = args.output.exists() and any(os.path.samefile(args.output, source) for source in (args.manifest, args.csv))
    if args.output.resolve() in (args.manifest.resolve(), args.csv.resolve()) or aliases_input:
        parser.error("--output must differ from both input paths")
    try:
        report = evaluate(args.manifest, args.csv)
    except OSError as error:
        report = _failure("", "unknown", [str(error)])
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
