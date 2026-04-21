#!/usr/bin/env python
import atexit
import os
import subprocess
import sys


def _is_runserver_command(argv: list[str]) -> bool:
    return len(argv) > 1 and argv[1] == "runserver"


def _should_start_scheduler(argv: list[str]) -> bool:
    if os.environ.get("TESTTOOL_DISABLE_SCHEDULER") == "1":
        return False
    if not _is_runserver_command(argv):
        return False
    return os.environ.get("RUN_MAIN") == "true" or "--noreload" in argv


def _start_scheduler_worker() -> None:
    env = os.environ.copy()
    env["TESTTOOL_DISABLE_SCHEDULER"] = "1"
    command = [sys.executable, os.path.abspath(__file__), "run_scheduler", "--interval", "10"]
    process = subprocess.Popen(command, cwd=os.path.dirname(os.path.abspath(__file__)), env=env)

    def stop_scheduler() -> None:
        if process.poll() is None:
            process.terminate()

    atexit.register(stop_scheduler)
    print("[scheduler] worker started with interval=10s")


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_platform.settings")
    if _should_start_scheduler(sys.argv):
        _start_scheduler_worker()
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
