from __future__ import annotations

from typing import Any, TypedDict


CASE_IR_SCHEMA_VERSION = 1


class CompiledCaseStepIR(TypedDict, total=False):
    id: int | None
    step_id: str
    step_order: int
    name: str
    enabled: bool
    api_template_id: int | None
    request: dict[str, Any]
    pre_tools: list[dict[str, Any]]
    assert_tools: list[dict[str, Any]]
    post_tools: list[dict[str, Any]]
    extractors: list[dict[str, Any]]
    validators: list[dict[str, Any]]
    variables: dict[str, Any]
    flags: dict[str, Any]


class CompiledCaseIR(TypedDict, total=False):
    schema_version: int
    case: dict[str, Any]
    runtime: dict[str, Any]
    global_request_config: dict[str, Any]
    variables: dict[str, Any]
    steps: list[CompiledCaseStepIR]
    outputs: list[dict[str, Any]]


def empty_case_ir() -> CompiledCaseIR:
    return {
        "schema_version": CASE_IR_SCHEMA_VERSION,
        "case": {},
        "runtime": {},
        "global_request_config": {},
        "variables": {},
        "steps": [],
        "outputs": [],
    }
