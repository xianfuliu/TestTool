import json
import requests
from PyQt5.QtCore import QThread, pyqtSignal


class ApiWorker(QThread):
    """API 请求工作线程"""
    finished = pyqtSignal(dict)  # 响应数据
    error = pyqtSignal(str)  # 错误信息

    def __init__(self, url, method, headers, body, encrypt_url=None, decrypt_url=None):
        super().__init__()
        self.url = url
        self.method = method
        self.headers = headers
        self.body = body
        self.encrypt_url = encrypt_url
        self.decrypt_url = decrypt_url

    def run(self):
        try:
            request_body = self.body
            encrypted_data = None
            response_data = None
            final_response = None

            # 如果需要加密，先调用加密接口
            if self.encrypt_url and self.encrypt_url.strip():
                try:
                    encrypt_response = requests.post(
                        self.encrypt_url,
                        data=json.dumps(request_body),
                        headers=self.headers,
                        timeout=30
                    )
                    if encrypt_response.status_code == 200:
                        # 尝试解析加密响应
                        try:
                            encrypted_data = encrypt_response.text
                        except:
                            encrypted_data = encrypt_response.text

                        if not encrypted_data:
                            self.error.emit(f"加密接口返回数据格式错误: {encrypt_response.text}")
                            return
                    else:
                        self.error.emit(f"加密接口调用失败: {encrypt_response.status_code} - {encrypt_response.text}")
                        return
                except Exception as e:
                    self.error.emit(f"加密接口调用异常: {str(e)}")
                    return

            # 发送主请求
            try:
                if self.method.upper() == "POST":
                    if encrypted_data:
                        # 使用加密后的数据
                        response = requests.post(
                            self.url,
                            data=encrypted_data if isinstance(encrypted_data,
                                                              (dict, list)) else encrypted_data,
                            headers=self.headers,
                            timeout=30
                        )
                    else:
                        # 使用原始数据
                        response = requests.post(
                            self.url,
                            json=request_body,
                            headers=self.headers,
                            timeout=30
                        )
                else:
                    # GET 请求
                    if encrypted_data:
                        params = {"encrypted_data": encrypted_data} if isinstance(encrypted_data,
                                                                                  (dict, list)) else encrypted_data
                    else:
                        params = request_body
                    response = requests.get(
                        self.url,
                        params=params,
                        headers=self.headers,
                        timeout=30
                    )

                response_data = response.text

            except Exception as e:
                self.error.emit(f"主请求发送失败: {str(e)}")
                return

            # 如果需要解密，调用解密接口
            if self.decrypt_url and self.decrypt_url.strip() and response.status_code == 200:
                try:
                    decrypt_response = requests.post(
                        self.decrypt_url,
                        data=response_data,
                        headers=self.headers,
                        timeout=30
                    )
                    if decrypt_response.status_code == 200:
                        try:
                            decrypt_result = decrypt_response.json()
                            final_response = decrypt_result.get("decrypted_data") or decrypt_result.get(
                                "data") or decrypt_result
                        except:
                            final_response = decrypt_response.text
                    else:
                        self.error.emit(f"解密接口调用失败: {decrypt_response.status_code} - {decrypt_response.text}")
                        return
                except Exception as e:
                    self.error.emit(f"解密接口调用异常: {str(e)}")
                    return
            else:
                # 不需要解密，直接使用原始响应
                final_response = response_data

            # 构造统一格式的响应数据
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_data,  # 原始响应体
                "decrypted_body": final_response  # 解密后的响应体（如果有）
            }

            self.finished.emit(result)

        except Exception as e:
            self.error.emit(f"请求失败: {str(e)}")
