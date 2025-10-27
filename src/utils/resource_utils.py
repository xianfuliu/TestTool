import sys
import os

def resource_path(relative_path):
    """获取资源的绝对路径。用于PyInstaller打包后找到资源文件"""
    try:
        # 如果是打包后的环境
        base_path = sys._MEIPASS
    except AttributeError:
        # 如果是开发环境
        base_path = os.path.abspath("")

    # 规范化路径，确保使用正确的路径分隔符
    normalized_path = os.path.normpath(os.path.join(base_path, relative_path))

    # 如果找不到文件，尝试其他可能的位置
    if not os.path.exists(normalized_path):
        # 尝试在当前目录下查找
        alt_path = os.path.normpath(os.path.join(os.path.abspath(""), relative_path))
        if os.path.exists(alt_path):
            return alt_path

        # 尝试在resources目录下查找
        filename = os.path.basename(relative_path)
        alt_path = os.path.normpath(os.path.join(os.path.abspath(""), "resources", filename))
        if os.path.exists(alt_path):
            return alt_path

        # 尝试在_base_path/resources下查找
        alt_path = os.path.normpath(os.path.join(base_path, "resources", filename))
        if os.path.exists(alt_path):
            return alt_path

        # 尝试在config目录下查找
        filename = os.path.basename(relative_path)
        alt_path = os.path.normpath(os.path.join(os.path.abspath("."), "config", filename))
        if os.path.exists(alt_path):
            return alt_path

        # 尝试在_base_path/config下查找
        alt_path = os.path.normpath(os.path.join(base_path, "config", filename))
        if os.path.exists(alt_path):
            return alt_path

    return normalized_path