from __future__ import annotations

import csv
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import Any

from .runtime import JMETER_EXECUTABLE


DEFAULT_RUN_TIMEOUT_SECONDS = 600
MAX_ERROR_SAMPLES = 20
_JTL_BOOL_TRUE = {"true", "1", "yes", "y", "on"}
_JTL_BOOL_FALSE = {"false", "0", "no", "n", "off"}
_JTL_SAVE_SERVICE_PROPERTIES = {
    "jmeter.save.saveservice.output_format": "csv",
    "jmeter.save.saveservice.print_field_names": "true",
    "jmeter.save.saveservice.timestamp_format": "ms",
    "jmeter.save.saveservice.assertion_results": "none",
    "jmeter.save.saveservice.assertion_results_failure_message": "true",
    "jmeter.save.saveservice.data_type": "true",
    "jmeter.save.saveservice.label": "true",
    "jmeter.save.saveservice.response_code": "true",
    "jmeter.save.saveservice.response_message": "true",
    "jmeter.save.saveservice.successful": "true",
    "jmeter.save.saveservice.thread_name": "true",
    "jmeter.save.saveservice.time": "true",
    "jmeter.save.saveservice.latency": "true",
    "jmeter.save.saveservice.connect_time": "true",
    "jmeter.save.saveservice.bytes": "true",
    "jmeter.save.saveservice.sent_bytes": "true",
    "jmeter.save.saveservice.url": "true",
    "jmeter.save.saveservice.thread_counts": "true",
    "jmeter.save.saveservice.idle_time": "true",
    "jmeter.save.saveservice.response_data": "false",
    "jmeter.save.saveservice.response_data.on_error": "false",
    "jmeter.save.saveservice.samplerData": "false",
    "jmeter.save.saveservice.requestHeaders": "false",
    "jmeter.save.saveservice.responseHeaders": "false",
}


def _int_value(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _float_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool_value(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in _JTL_BOOL_TRUE:
        return True
    if text in _JTL_BOOL_FALSE:
        return False
    return default


def _safe_divide(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return numerator / denominator


def _round_number(value: float, digits: int = 2) -> float:
    return round(float(value or 0.0), digits)


def _histogram_percentile(histogram: Counter[int], total: int, percentile: float) -> float:
    if not histogram or total <= 0:
        return 0.0
    threshold = max(1, int(total * percentile + 0.999999))
    cumulative = 0
    for value in sorted(histogram):
        cumulative += histogram[value]
        if cumulative >= threshold:
            return float(value)
    return float(max(histogram))


def _new_label_stat() -> dict[str, Any]:
    return {
        "total_samples": 0,
        "failed_samples": 0,
        "elapsed_sum_ms": 0.0,
        "min_elapsed_ms": None,
        "max_elapsed_ms": None,
        "response_codes": Counter(),
        "elapsed_histogram": Counter(),
    }


def parse_jtl_file(jtl_path: Path) -> dict[str, Any]:
    if not jtl_path.exists():
        return {
            "available": False,
            "message": "JTL 文件不存在",
            "jtl_path": str(jtl_path),
        }

    total_samples = 0
    failed_samples = 0
    elapsed_sum_ms = 0.0
    total_bytes = 0
    min_elapsed_ms: int | None = None
    max_elapsed_ms: int | None = None
    min_timestamp_ms: int | None = None
    max_timestamp_ms: int | None = None
    elapsed_histogram: Counter[int] = Counter()
    latency_histogram: Counter[int] = Counter()
    response_codes: Counter[str] = Counter()
    label_stats: dict[str, dict[str, Any]] = {}
    error_samples: list[dict[str, Any]] = []

    with jtl_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        field_names = list(reader.fieldnames or [])
        for row in reader:
            total_samples += 1
            elapsed_ms = _int_value(row.get("elapsed"), 0)
            latency_ms = _int_value(row.get("Latency") or row.get("latency"), 0)
            timestamp_ms = _int_value(row.get("timeStamp") or row.get("timestamp"), 0)
            sample_end_ms = timestamp_ms + max(elapsed_ms, 0)
            success = _bool_value(row.get("success"), True)
            label = str(row.get("label") or "(unnamed)")
            response_code = str(row.get("responseCode") or row.get("response_code") or "")
            response_message = str(row.get("responseMessage") or row.get("response_message") or "")
            failure_message = str(row.get("failureMessage") or row.get("failure_message") or "")
            bytes_count = _int_value(row.get("bytes"), 0)

            elapsed_sum_ms += elapsed_ms
            total_bytes += max(bytes_count, 0)
            elapsed_histogram[elapsed_ms] += 1
            latency_histogram[latency_ms] += 1
            response_codes[response_code or "-"] += 1

            min_elapsed_ms = elapsed_ms if min_elapsed_ms is None else min(min_elapsed_ms, elapsed_ms)
            max_elapsed_ms = elapsed_ms if max_elapsed_ms is None else max(max_elapsed_ms, elapsed_ms)
            if timestamp_ms > 0:
                min_timestamp_ms = timestamp_ms if min_timestamp_ms is None else min(min_timestamp_ms, timestamp_ms)
                max_timestamp_ms = sample_end_ms if max_timestamp_ms is None else max(max_timestamp_ms, sample_end_ms)

            stat = label_stats.setdefault(label, _new_label_stat())
            stat["total_samples"] += 1
            stat["elapsed_sum_ms"] += elapsed_ms
            stat["elapsed_histogram"][elapsed_ms] += 1
            stat["response_codes"][response_code or "-"] += 1
            stat["min_elapsed_ms"] = elapsed_ms if stat["min_elapsed_ms"] is None else min(stat["min_elapsed_ms"], elapsed_ms)
            stat["max_elapsed_ms"] = elapsed_ms if stat["max_elapsed_ms"] is None else max(stat["max_elapsed_ms"], elapsed_ms)

            if not success:
                failed_samples += 1
                stat["failed_samples"] += 1
                if len(error_samples) < MAX_ERROR_SAMPLES:
                    error_samples.append(
                        {
                            "label": label,
                            "response_code": response_code,
                            "response_message": response_message,
                            "failure_message": failure_message,
                            "elapsed_ms": elapsed_ms,
                            "time_stamp": timestamp_ms,
                        }
                    )

    duration_seconds = _round_number(_safe_divide(max((max_timestamp_ms or 0) - (min_timestamp_ms or 0), 0), 1000.0), 3)
    throughput_per_sec = _round_number(_safe_divide(total_samples, duration_seconds) if duration_seconds > 0 else total_samples)

    labels: list[dict[str, Any]] = []
    for label, stat in label_stats.items():
        label_total = int(stat["total_samples"])
        label_failed = int(stat["failed_samples"])
        labels.append(
            {
                "label": label,
                "total_samples": label_total,
                "failed_samples": label_failed,
                "error_rate": _round_number(_safe_divide(label_failed, label_total) * 100),
                "avg_elapsed_ms": _round_number(_safe_divide(stat["elapsed_sum_ms"], label_total)),
                "min_elapsed_ms": int(stat["min_elapsed_ms"] or 0),
                "max_elapsed_ms": int(stat["max_elapsed_ms"] or 0),
                "p95_elapsed_ms": _round_number(_histogram_percentile(stat["elapsed_histogram"], label_total, 0.95)),
                "response_codes": dict(sorted(stat["response_codes"].items(), key=lambda item: (-item[1], item[0]))),
            }
        )
    labels.sort(key=lambda item: (-item["failed_samples"], item["label"]))

    return {
        "available": True,
        "message": "ok",
        "jtl_path": str(jtl_path),
        "field_names": field_names,
        "total_samples": total_samples,
        "failed_samples": failed_samples,
        "passed_samples": total_samples - failed_samples,
        "error_rate": _round_number(_safe_divide(failed_samples, total_samples) * 100),
        "duration_seconds": duration_seconds,
        "throughput_per_sec": throughput_per_sec,
        "total_bytes": total_bytes,
        "avg_elapsed_ms": _round_number(_safe_divide(elapsed_sum_ms, total_samples)),
        "min_elapsed_ms": int(min_elapsed_ms or 0),
        "max_elapsed_ms": int(max_elapsed_ms or 0),
        "p90_elapsed_ms": _round_number(_histogram_percentile(elapsed_histogram, total_samples, 0.90)),
        "p95_elapsed_ms": _round_number(_histogram_percentile(elapsed_histogram, total_samples, 0.95)),
        "p99_elapsed_ms": _round_number(_histogram_percentile(elapsed_histogram, total_samples, 0.99)),
        "p95_latency_ms": _round_number(_histogram_percentile(latency_histogram, total_samples, 0.95)),
        "response_codes": dict(sorted(response_codes.items(), key=lambda item: (-item[1], item[0]))),
        "labels": labels,
        "error_samples": error_samples,
    }


def run_jmeter_plan(
    jmx_path: Path,
    *,
    result_jtl_path: Path,
    jmeter_log_path: Path,
    console_log_path: Path | None = None,
    timeout_seconds: int = DEFAULT_RUN_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if not JMETER_EXECUTABLE.exists():
        raise ValueError("JMeter 可执行文件不存在")
    if not jmx_path.exists():
        raise ValueError("JMX 文件不存在")

    command = [
        str(JMETER_EXECUTABLE),
        "-n",
        "-t",
        str(jmx_path),
        "-l",
        str(result_jtl_path),
        "-j",
        str(jmeter_log_path),
        "-Jsummariser.name=summary",
    ]
    command.extend(f"-J{key}={value}" for key, value in _JTL_SAVE_SERVICE_PROPERTIES.items())

    started_at = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=max(1, int(timeout_seconds or DEFAULT_RUN_TIMEOUT_SECONDS)),
            check=False,
        )
        timed_out = False
        stdout_text = completed.stdout or ""
        stderr_text = completed.stderr or ""
        return_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout_text = exc.stdout or ""
        stderr_text = exc.stderr or ""
        return_code = -1

    duration_ms = _round_number((time.perf_counter() - started_at) * 1000)
    console_output = "\n".join(part.strip() for part in [stdout_text, stderr_text] if part and part.strip())
    if console_log_path is not None:
        console_log_path.write_text(console_output, encoding="utf-8")

    jtl_summary = parse_jtl_file(result_jtl_path) if result_jtl_path.exists() else {
        "available": False,
        "message": "JMeter 未生成 JTL 结果文件",
        "jtl_path": str(result_jtl_path),
    }
    summary_available = bool(jtl_summary.get("available"))
    total_samples = int(jtl_summary.get("total_samples") or 0) if summary_available else 0
    sample_failures = int(jtl_summary.get("failed_samples") or 0) if summary_available else 0
    passed = (not timed_out) and return_code == 0 and summary_available and total_samples > 0 and sample_failures == 0

    return {
        "passed": passed,
        "timed_out": timed_out,
        "return_code": return_code,
        "duration_ms": duration_ms,
        "command": command,
        "jmx_path": str(jmx_path),
        "result_jtl_path": str(result_jtl_path),
        "jmeter_log_path": str(jmeter_log_path),
        "console_log_path": str(console_log_path) if console_log_path is not None else "",
        "console_output": console_output,
        "summary": jtl_summary,
    }
