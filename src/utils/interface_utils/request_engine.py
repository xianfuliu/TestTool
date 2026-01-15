import requests
import json
from typing import Dict, Any
from src.utils.interface_utils.variable_manager import VariableManager


class RequestEngine:
    def __init__(self):
        self.session = requests.Session()
        self.variable_manager = VariableManager()

    def execute_request(
        self, api_data: Dict[str, Any], variables: Dict[str, Any] = None
    ):
        """执行HTTP请求"""
        try:
            # 替换变量
            url = self.variable_manager.replace_variables(api_data["url"], variables)
            headers = self.variable_manager.replace_variables_in_dict(
                api_data.get("headers", {}), variables
            )
            params = self.variable_manager.replace_variables_in_dict(
                api_data.get("params", {}), variables
            )
            body = self.variable_manager.replace_variables_in_dict(
                api_data.get("body", {}), variables
            )

            method = api_data["method"].upper()

            # 执行请求
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=body if method in ["POST", "PUT", "PATCH"] else None,
                timeout=30,
            )

            return {
                "success": True,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.json() if response.text else {},
                "text": response.text,
                "elapsed": response.elapsed.total_seconds(),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute_request_with_encryption(
        self,
        api_data: Dict[str, Any],
        encrypt_url: str,
        decrypt_url: str,
        variables: Dict[str, Any] = None,
    ):
        """执行带加解密的HTTP请求，按照正确顺序执行"""
        try:
            print("[DEBUG] 开始执行带加解密的HTTP请求")
            print(f"[DEBUG] 加密接口: {encrypt_url}")
            print(f"[DEBUG] 解密接口: {decrypt_url}")

            # 1. 替换变量，得到步骤的最新请求体
            url = self.variable_manager.replace_variables(api_data["url"], variables)
            headers = self.variable_manager.replace_variables_in_dict(
                api_data.get("headers", {}), variables
            )
            params = self.variable_manager.replace_variables_in_dict(
                api_data.get("params", {}), variables
            )
            body = self.variable_manager.replace_variables_in_dict(
                api_data.get("body", {}), variables
            )

            print("[DEBUG] 步骤1: 变量替换完成")
            print(f"[DEBUG] 替换后URL: {url}")
            print(f"[DEBUG] 替换后请求体: {body}")

            # 2. 调用加密接口，得到密文
            print("[DEBUG] 步骤2: 开始调用加密接口")
            encrypt_response = self.session.post(
                encrypt_url, json=body, headers=headers, timeout=30
            )

            if encrypt_response.status_code != 200:
                error_msg = f"加密接口调用失败: {encrypt_response.status_code} - {encrypt_response.text}"
                print(f"[DEBUG] {error_msg}")
                return {"success": False, "error": error_msg}

            encrypted_data = encrypt_response.text
            print("[DEBUG] 加密接口调用成功")
            print(f"[DEBUG] 加密后数据: {encrypted_data}")

            # 3. 使用密文请求主接口
            print("[DEBUG] 步骤3: 使用密文请求主接口")
            method = api_data["method"].upper()

            # 对于加解密场景，通常主接口也是POST请求，使用加密数据作为请求体
            response = self.session.post(
                url, data=encrypted_data, headers=headers, timeout=30
            )

            print("[DEBUG] 主接口请求完成")
            print(f"[DEBUG] 主接口状态码: {response.status_code}")

            # 4. 调用解密接口，得到明文
            print("[DEBUG] 步骤4: 调用解密接口")
            decrypt_response = self.session.post(
                decrypt_url, data=response.text, headers=headers, timeout=30
            )

            if decrypt_response.status_code != 200:
                error_msg = f"解密接口调用失败: {decrypt_response.status_code} - {decrypt_response.text}"
                print(f"[DEBUG] {error_msg}")
                return {"success": False, "error": error_msg}

            decrypted_data = decrypt_response.text
            print("[DEBUG] 解密接口调用成功")
            print(f"[DEBUG] 解密后数据: {decrypted_data}")

            # 5. 构造最终响应
            result = {
                "success": True,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": json.loads(decrypted_data) if decrypted_data else {},
                "text": response.text,  # 原始响应文本
                "decrypted_body": decrypted_data,  # 解密后的响应体
                "elapsed": response.elapsed.total_seconds(),
            }

            print("[DEBUG] 带加解密的HTTP请求执行完成")
            return result

        except Exception as e:
            error_msg = f"带加解密的请求执行异常: {str(e)}"
            print(f"[DEBUG] {error_msg}")
            import traceback

            print(f"[DEBUG] 异常堆栈: {traceback.format_exc()}")
            return {"success": False, "error": error_msg}
