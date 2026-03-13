import os
import json
import sys
import tempfile
import zipfile
import shutil
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
                    self.update_available.emit(latest_version, release_notes, download_url)
                
        except URLError as e:
            self.update_error.emit(f"网络连接错误: {e}")
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
            
            # 创建批处理文件来执行更新
            batch_content = f"""
@echo off
chcp 65001 >nul
timeout /t 3 /nobreak >nul
taskkill /f /im "{os.path.basename(current_exe)}" >nul 2>&1
timeout /t 2 /nobreak >nul
copy /y "{update_file_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
            
            batch_file = os.path.join(tempfile.gettempdir(), f"{self.app_name}_update.bat")
            with open(batch_file, 'w', encoding='utf-8') as f:
                f.write(batch_content)
            
            # 执行批处理文件
            os.system(f'start "" "{batch_file}"')
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