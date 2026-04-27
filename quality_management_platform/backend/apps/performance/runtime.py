from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"
JMETER_ROOT = PROJECT_ROOT / "tools" / "jmeter" / "apache-jmeter-5.6.3"
JMETER_BIN = JMETER_ROOT / "bin"
JMETER_EXECUTABLE = JMETER_BIN / "jmeter.bat"
PERFORMANCE_ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "performance"
PYTHON_EXECUTABLE = Path(sys.executable)
