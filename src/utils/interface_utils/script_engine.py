import subprocess
import sys
import tempfile
import os
from typing import Dict, Any


class ScriptEngine:
    """脚本执行引擎"""

    def execute_script(self, script: str, variables: Dict[str, Any], timeout: int = 30) -> Any:
        """执行Python脚本"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            # 写入变量
            for key, value in variables.items():
                f.write(f"{key} = {repr(value)}\n")

            # 写入脚本
            f.write(script)

            temp_file = f.name

        try:
            # 执行脚本
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                # 解析输出
                output_lines = result.stdout.strip().split('\n')
                if output_lines:
                    # 最后一行作为返回值
                    return output_lines[-1]
                else:
                    return None
            else:
                raise Exception(f"脚本执行错误: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise Exception("脚本执行超时")
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)