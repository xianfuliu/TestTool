from __future__ import annotations

from apps.common.http import api_view

from .service import compile_suite_jmx_artifacts, get_runtime_info, run_suite_jmx_artifacts


@api_view
def bootstrap(_request, payload=None):
    return {
        "runtime": get_runtime_info(),
        "capabilities": {
            "jmx_compile": True,
            "jmeter_run": True,
            "report_parse": True,
        },
    }


@api_view
def compile_suite_jmx(_request, suite_id: int, payload=None):
    request_payload = payload or {}
    return compile_suite_jmx_artifacts(
        suite_id,
        environment_id=request_payload.get("environment_id"),
        load_profile=request_payload.get("load_profile"),
    )


@api_view
def run_suite_jmx(_request, suite_id: int, payload=None):
    request_payload = payload or {}
    return run_suite_jmx_artifacts(
        suite_id,
        environment_id=request_payload.get("environment_id"),
        load_profile=request_payload.get("load_profile"),
        timeout_seconds=request_payload.get("timeout_seconds"),
    )
