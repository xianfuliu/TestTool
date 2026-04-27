from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote, unquote
from typing import Any

NULL_MARKER = "__TESTTOOL_NULL__"
BACKEND_ROOT = Path(__file__).resolve().parents[2]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_platform.settings")
try:  # pragma: no cover - bootstrap guard
    import django

    django.setup()
except Exception:
    pass


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _json_safe(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        return str(value)


def _load_module(module_file: Path):
    spec = importlib.util.spec_from_file_location("testtool_generated_hooks", module_file)
    if spec is None or spec.loader is None:
        raise ValueError(f"unable to load hook module: {module_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_variables_file(path: Path) -> dict[str, Any]:
    variables: dict[str, Any] = {}
    if not path.exists():
        return variables
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line:
            continue
        key, separator, value = raw_line.partition("\t")
        if not separator:
            continue
        variables[str(key)] = unquote(value)
    return variables


def _variable_changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    all_keys = set(before.keys()) | set(after.keys())
    for key in sorted(all_keys):
        before_value = before.get(key)
        after_value = after.get(key)
        if before_value == after_value:
            continue
        changes[str(key)] = _json_safe(after_value)
    return changes


def _execute_functions(module, function_names: list[str], context: dict[str, Any]) -> dict[str, Any]:
    working_context = {
        "variables": {str(key): value for key, value in _as_dict(context.get("variables")).items()},
        "source_data": context.get("source_data"),
    }
    original_variables = dict(working_context["variables"])
    results: list[dict[str, Any]] = []

    for function_name in function_names:
        hook_function = getattr(module, function_name, None)
        if hook_function is None or not callable(hook_function):
            raise ValueError(f"hook function not found: {function_name}")
        result = _as_dict(hook_function(working_context))
        results.append(_json_safe(result))
        current_variables = _as_dict(result.get("current_variables"))
        if current_variables:
            working_context["variables"] = {str(key): value for key, value in current_variables.items()}
        elif isinstance(result.get("variable_changes"), dict):
            working_context["variables"].update(_as_dict(result.get("variable_changes")))
        if "source_data" in result:
            working_context["source_data"] = result.get("source_data")
        if str(result.get("status") or "success") != "success":
            break

    status = "success"
    message = "ok"
    if results and str(results[-1].get("status") or "success") != "success":
        status = "failed"
        message = str(results[-1].get("message") or "hook failed")

    return {
        "status": status,
        "message": message,
        "functions": function_names,
        "results": results,
        "variable_changes": _variable_changes(original_variables, working_context["variables"]),
        "current_variables": _json_safe(working_context["variables"]),
        "source_data": _json_safe(working_context.get("source_data")),
    }


def _stringify_variable_value(value: Any) -> str:
    if value is None:
        return NULL_MARKER
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _write_flat_result(path: Path, result: dict[str, Any]) -> None:
    lines = [
        f"status\t{quote(str(result.get('status') or 'failed'))}",
        f"message\t{quote(str(result.get('message') or ''))}",
    ]
    for key, value in _as_dict(result.get("variable_changes")).items():
        lines.append(f"variable\t{key}\t{quote(_stringify_variable_value(value))}")
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute generated performance hooks")
    parser.add_argument("--module-file", required=True)
    parser.add_argument("--functions", required=True, help="Comma separated hook function names")
    parser.add_argument("--context-file")
    parser.add_argument("--result-file")
    parser.add_argument("--variables-file")
    parser.add_argument("--result-flat-file")
    args = parser.parse_args(argv)

    module_file = Path(args.module_file).resolve()
    context_file = Path(args.context_file).resolve() if args.context_file else None
    result_file = Path(args.result_file).resolve() if args.result_file else None
    variables_file = Path(args.variables_file).resolve() if args.variables_file else None
    result_flat_file = Path(args.result_flat_file).resolve() if args.result_flat_file else None
    function_names = [item.strip() for item in str(args.functions).split(",") if item.strip()]
    if not function_names:
        raise ValueError("no hook functions provided")

    module = _load_module(module_file)
    if variables_file is not None:
        context = {"variables": _load_variables_file(variables_file)}
    elif context_file is not None and context_file.exists():
        context = json.loads(context_file.read_text(encoding="utf-8"))
    else:
        context = {}
    result = _execute_functions(module, function_names, _as_dict(context))
    if result_file is not None:
        result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if result_flat_file is not None:
        _write_flat_result(result_flat_file, result)
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
