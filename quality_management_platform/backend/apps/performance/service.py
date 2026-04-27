from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .jmeter_jmx_builder import artifact_directory, build_jmx_from_suite_ir, validate_jmx_file
from .jmeter_runner import DEFAULT_RUN_TIMEOUT_SECONDS, run_jmeter_plan
from .runtime import JMETER_BIN, JMETER_EXECUTABLE, JMETER_ROOT, PERFORMANCE_ARTIFACT_ROOT, PROJECT_ROOT
from .suite_compiler import compile_suite_to_load_ir


def _detect_jmeter_version() -> str:
    match = re.search(r"apache-jmeter-(\d+\.\d+(?:\.\d+)?)", JMETER_ROOT.name)
    return match.group(1) if match else ""


def _read_java_runtime() -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError, OSError) as exc:
        return {
            "available": False,
            "message": str(exc),
            "raw": "",
        }
    output = (completed.stderr or completed.stdout or "").strip()
    first_line = output.splitlines()[0] if output else ""
    return {
        "available": completed.returncode == 0,
        "message": first_line,
        "raw": output,
    }


def get_runtime_info() -> dict[str, Any]:
    java_runtime = _read_java_runtime()
    readme_path = JMETER_ROOT / "README.md"
    return {
        "project_root": str(PROJECT_ROOT),
        "jmeter_home": str(JMETER_ROOT),
        "jmeter_bin": str(JMETER_BIN),
        "jmeter_executable": str(JMETER_EXECUTABLE),
        "jmeter_version": _detect_jmeter_version(),
        "installed": JMETER_ROOT.exists() and JMETER_EXECUTABLE.exists(),
        "readme_exists": readme_path.exists(),
        "java": java_runtime,
        "ready": JMETER_ROOT.exists() and JMETER_EXECUTABLE.exists() and bool(java_runtime.get("available")),
    }


def compile_suite_jmx_artifacts(
    suite_id: int,
    *,
    environment_id: int | None = None,
    load_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = get_runtime_info()
    if not runtime.get("ready"):
        raise ValueError("JMeter 或 Java 环境未就绪")

    suite_ir = compile_suite_to_load_ir(
        suite_id,
        environment_id=environment_id,
        load_profile=load_profile,
    )
    output_dir = artifact_directory(PERFORMANCE_ARTIFACT_ROOT, suite_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    suite_ir_path = output_dir / "suite-load-ir.json"
    suite_ir_path.write_text(json.dumps(suite_ir, ensure_ascii=False, indent=2), encoding="utf-8")
    jmx_artifacts = build_jmx_from_suite_ir(suite_ir, output_dir)
    validation = validate_jmx_file(Path(jmx_artifacts["jmx_path"]))
    return {
        "suite": suite_ir.get("suite"),
        "load_profile": suite_ir.get("load_profile"),
        "warnings": suite_ir.get("warnings") or [],
        "artifact_dir": str(output_dir),
        "suite_ir_path": str(suite_ir_path),
        "jmx_path": jmx_artifacts.get("jmx_path"),
        "csv_files": jmx_artifacts.get("csv_files") or [],
        "hooks_asset": jmx_artifacts.get("hooks_asset") or {},
        "validation": validation,
    }


def run_suite_jmx_artifacts(
    suite_id: int,
    *,
    environment_id: int | None = None,
    load_profile: dict[str, Any] | None = None,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    compiled = compile_suite_jmx_artifacts(
        suite_id,
        environment_id=environment_id,
        load_profile=load_profile,
    )
    validation = compiled.get("validation") or {}
    if not validation.get("passed"):
        raise ValueError("生成的 JMX 未通过 JMeter 结构校验，无法执行")

    artifact_dir = Path(str(compiled.get("artifact_dir") or ""))
    execution = run_jmeter_plan(
        Path(str(compiled.get("jmx_path") or "")),
        result_jtl_path=artifact_dir / "results.jtl",
        jmeter_log_path=artifact_dir / "jmeter.log",
        console_log_path=artifact_dir / "jmeter.console.log",
        timeout_seconds=int(timeout_seconds or DEFAULT_RUN_TIMEOUT_SECONDS),
    )
    return {
        **compiled,
        "execution": execution,
    }
