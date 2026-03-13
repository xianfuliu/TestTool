import os
import json
import sys
import tempfile
import zipfile
import shutil
import time
import subprocess
from urllib.request import urlopen, Request
from urllib.error import URLError
import threading
from PyQt5.QtCore import QObject, pyqtSignal, QThread


class UpdateManager(QObject):
    """自动更新管理器"""
    
    # 信号定义
    update_available = pyqtSignal(str, str, str)  # 新版本号, 更新说明, 下载链接
    download_progress = pyqtSignal(int)  # 下载进度百分比
    download_complete = pyqtSignal(str)  # 下载完成的文件路径
    update_error = pyqtSignal(str)  # 错误信息
    
    def __init__(self, current_version, app_name="TestTool"):
        super().__init__()
        self.current_version = current_version
        self.app_name = app_name
        self.github_repo = "xianfuliu/TestTool"  # 需要替换为实际的GitHub仓库
        self.update_url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"
        
    def check_for_updates(self):
        """检查是否有新版本可用"""
        thread = threading.Thread(target=self._check_updates_thread)
        thread.daemon = True
        thread.start()
    
    def _check_updates_thread(self):
        """在后台线程中检查更新"""
        try:
            import socket
            socket.setdefaulttimeout(10)  # 设置全局超时
            
            request = Request(self.update_url)
            request.add_header('User-Agent', 'TestTool-Updater')
            request.add_header('Accept', 'application/vnd.github.v3+json')
            
            # 添加更详细的错误处理
            try:
                with urlopen(request, timeout=10) as response:
                    if response.getcode() != 200:
                        self.update_error.emit(f"GitHub API错误: HTTP {response.getcode()}")
                        return
                    
                    data = json.loads(response.read().decode())
                    
                    # 检查必要的字段
                    if 'tag_name' not in data:
                        self.update_error.emit("GitHub API返回数据格式错误")
                        return
                    
                    latest_version = data['tag_name'].lstrip('v')
                    release_notes = data.get('body', '暂无更新说明')
                    
                    # 查找exe文件的下载链接
                    download_url = None
                    for asset in data.get('assets', []):
                        if asset['name'].endswith('.exe'):
                            download_url = asset['browser_download_url']
                            break
                    
                    if download_url and self._is_newer_version(latest_version, self.current_version):
                        self.update_available.emit(latest_version, release_notes, download_url)
                    else:
                        # 没有新版本时也发送信号
                        self.update_error.emit("当前已是最新版本")
                        
            except URLError as e:
                if hasattr(e, 'reason'):
                    self.update_error.emit(f"网络连接错误: {e.reason}")
                elif hasattr(e, 'code'):
                    self.update_error.emit(f"HTTP错误: {e.code}")
                else:
                    self.update_error.emit(f"网络错误: {e}")
                    
        except Exception as e:
            self.update_error.emit(f"检查更新失败: {e}")
    
    def _is_newer_version(self, latest, current):
        """比较版本号，判断是否有新版本"""
        def parse_version(version):
            return tuple(map(int, version.split('.')))
        
        try:
            return parse_version(latest) > parse_version(current)
        except:
            return False
    
    def download_update(self, download_url):
        """下载更新文件"""
        thread = threading.Thread(target=self._download_thread, args=(download_url,))
        thread.daemon = True
        thread.start()
    
    def _download_thread(self, download_url):
        """在后台线程中下载更新"""
        try:
            temp_dir = tempfile.gettempdir()
            download_path = os.path.join(temp_dir, f"{self.app_name}_update.exe")
            
            request = Request(download_url)
            request.add_header('User-Agent', 'TestTool-Updater')
            
            with urlopen(request) as response:
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                with open(download_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            self.download_progress.emit(progress)
            
            self.download_complete.emit(download_path)
            
        except Exception as e:
            self.update_error.emit(f"下载更新失败: {e}")
    
    def install_update(self, update_file_path):
        """安装更新"""
        try:
            # 获取当前可执行文件路径
            current_exe = sys.executable
            current_dir = os.path.dirname(current_exe)
            exe_name = os.path.basename(current_exe)
            
            # 创建更可靠的批处理文件
            batch_content = f"""
@echo off
chcp 65001 >nul
echo 正在安装更新...

:: 等待3秒确保程序完全启动
timeout /t 3 /nobreak >nul

:: 强制终止当前程序进程
taskkill /f /im "{exe_name}" >nul 2>&1

:: 等待进程完全退出
timeout /t 2 /nobreak >nul

:: 再次检查并终止（确保进程已关闭）
tasklist /fi "imagename eq {exe_name}" | find "{exe_name}" >nul
if %errorlevel% == 0 (
    echo 检测到进程仍在运行，再次终止...
    taskkill /f /im "{exe_name}" >nul 2>&1
    timeout /t 1 /nobreak >nul
)

:: 复制新版本文件
echo 正在替换文件...
copy /y "{update_file_path}" "{current_exe}" >nul

:: 检查复制是否成功
if exist "{current_exe}" (
    echo 更新安装成功！
    echo 正在启动新版本...
    start "" /d "{current_dir}" "{exe_name}"
    echo 启动命令已执行
) else (
    echo 错误：文件替换失败！
    pause
)

:: 删除临时文件
del "{update_file_path}" >nul 2>&1

:: 删除批处理文件自身
del "%~f0" >nul 2>&1
"""
            
            batch_file = os.path.join(tempfile.gettempdir(), f"{self.app_name}_update_{int(time.time())}.bat")
            
            with open(batch_file, 'w', encoding='utf-8') as f:
                f.write(batch_content)
            
            # 执行批处理文件（使用最小化窗口）
            subprocess.Popen([batch_file], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            # 立即退出当前程序
            sys.exit(0)
            
        except Exception as e:
            self.update_error.emit(f"安装更新失败: {e}")


class UpdateChecker(QThread):
    """更新检查线程"""
    
    update_found = pyqtSignal(str, str, str)
    check_failed = pyqtSignal(str)
    
    def __init__(self, current_version, github_repo):
        super().__init__()
        self.current_version = current_version
        self.github_repo = github_repo
        self.update_url = f"https://api.github.com/repos/{github_repo}/releases/latest"
    
    def run(self):
        try:
            request = Request(self.update_url)
            request.add_header('User-Agent', 'TestTool-Updater')
            
            with urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode())
                
                latest_version = data['tag_name'].lstrip('v')
                release_notes = data['body']
                
                # 查找exe文件的下载链接
                download_url = None
                for asset in data.get('assets', []):
                    if asset['name'].endswith('.exe'):
                        download_url = asset['browser_download_url']
                        break
                
                if download_url and self._is_newer_version(latest_version, self.current_version):
                    self.update_found.emit(latest_version, release_notes, download_url)
                
        except Exception as e:
            self.check_failed.emit(str(e))
    
    def _is_newer_version(self, latest, current):
        """比较版本号"""
        def parse_version(version):
            return tuple(map(int, version.split('.')))
        
        try:
            return parse_version(latest) > parse_version(current)
        except:
            return False