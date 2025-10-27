import requests
import time
import json
from PyQt5.QtCore import QThread, pyqtSignal


class ScheduleExecutor(QThread):
    """定时任务执行器"""
    finished = pyqtSignal(str)  # 执行完成信号
    error = pyqtSignal(str)  # 错误信号

    def __init__(self, job_id, job_group):
        super().__init__()
        self.job_id = job_id
        self.job_group = job_group
        self.base_url = "https://xj-api-test.hqrzdb.com/stage-api"
        self.token = None
        self.cookies = None

    def run(self):
        try:
            # 1. 登录
            if not self.login():
                self.error.emit("登录定时任务平台失败")
                return
            time.sleep(3)

            # 2. 执行定时任务
            if not self.execute_job():
                self.error.emit("执行定时任务失败")
                return
            time.sleep(3)

            # 3. 退出登录
            if not self.logout():
                self.error.emit("退出登录失败")
                return
            time.sleep(3)

            self.finished.emit(f"任务 {self.job_id} 执行完成")

        except Exception as e:
            self.error.emit(f"执行异常: {str(e)}")

    def login(self):
        """登录定时任务平台"""
        try:
            login_url = f"{self.base_url}/auth/login"
            login_data = {
                "username": "admin",
                "password": "admin123"
            }

            response = requests.post(
                login_url,
                json=login_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                self.token = result.get("data", {}).get("access_token")

                if self.token:
                    # 构建 cookies
                    self.cookies = f"username=admin; rememberMe=true; Admin-Expires-In=720; password=iTYNwzOPCsG75/1HmhouFVEVCDjITuKAWg42P/ZFHpKoDL1SfPx040BqNnLTT6hvq+hT7BWGVKV6tZSoJ1T6yQ==; Admin-Token={self.token}"
                    return True
            return False

        except Exception as e:
            print(f"登录失败: {str(e)}")
            return False

    def execute_job(self):
        """执行定时任务"""
        try:
            execute_url = f"{self.base_url}/schedule/job/run"
            job_data = {
                "jobId": self.job_id,
                "jobGroup": self.job_group
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
                "Cookie": self.cookies
            }

            response = requests.put(
                execute_url,
                json=job_data,
                headers=headers,
                timeout=30
            )
            return response.status_code == 200

        except Exception as e:
            print(f"执行定时任务失败: {str(e)}")
            return False

    def logout(self):
        """退出登录"""
        try:
            logout_url = f"{self.base_url}/auth/logout"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
                "Cookie": self.cookies
            }

            response = requests.delete(
                logout_url,
                headers=headers,
                timeout=30
            )
            return response.status_code == 200

        except Exception as e:
            print(f"退出登录失败: {str(e)}")
            return False
