from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QLabel, QHBoxLayout, QWidget, QApplication
from PyQt5.QtGui import QPixmap
import os


class Toast:
    """Toast提示工具类 - 完全兼容QMessageBox方法签名"""

    # 预定义样式和图标 - 统一使用黑底白字
    STYLES = {
        'warning': {
            'background': 'rgba(0, 0, 0, 0.85)',
            'border': '1px solid #555',
            'icon': 'warning.png'
        },
        'critical': {
            'background': 'rgba(0, 0, 0, 0.85)',
            'border': '1px solid #555',
            'icon': 'error.png'
        },
        'success': {
            'background': 'rgba(0, 0, 0, 0.85)',
            'border': '1px solid #555',
            'icon': 'success.png'
        },
        'information': {
            'background': 'rgba(0, 0, 0, 0.85)',
            'border': '1px solid #555',
            'icon': 'info.png'
        }
    }

    @staticmethod
    def get_icon_path(icon_name):
        """获取图标文件的完整路径"""
        # 获取当前文件的绝对路径
        current_file_path = os.path.abspath(__file__)

        # 方法1: 从当前文件向上查找，直到找到包含 'src' 目录的文件夹
        current_dir = os.path.dirname(current_file_path)
        while current_dir and not os.path.exists(os.path.join(current_dir, 'src')):
            parent_dir = os.path.dirname(current_dir)
            if parent_dir == current_dir:  # 已经到达根目录
                break
            current_dir = parent_dir

        # 构建图标路径
        icon_path = os.path.join(current_dir, 'src', 'resources', 'icons', icon_name)

        # 如果找不到，尝试其他可能的路径
        if not os.path.exists(icon_path):
            # 方法2: 假设当前工作目录是项目根目录
            icon_path = os.path.join(os.getcwd(), 'src', 'resources', 'icons', icon_name)

        if not os.path.exists(icon_path):
            # 方法3: 直接使用相对路径
            icon_path = os.path.join('src', 'resources', 'icons', icon_name)

        if not os.path.exists(icon_path):
            # 方法4: 尝试绝对路径
            icon_path = "D:/workspace/TestTool/src/resources/icons/" + icon_name

        if not os.path.exists(icon_path):
            print(f"警告: 找不到图标文件 {icon_name}")
            return None
        return icon_path

    @staticmethod
    def show_message(parent, message, message_type='information', duration=2000):
        """显示Toast提示 - 清晰的参数名

        Args:
            parent: 父窗口
            message: 提示消息
            message_type: 消息类型
            duration: 显示时长(毫秒)
        """
        # 参数验证
        if not isinstance(duration, int):
            duration = 2000

        if message_type not in Toast.STYLES:
            message_type = 'information'

        style = Toast.STYLES[message_type]

        # 创建Toast容器
        # 如果parent为None，使用主窗口作为parent
        if parent is None:
            # 先获取主窗口
            main_window_temp = None
            for widget in QApplication.topLevelWidgets():
                if widget.isWindow() and widget.windowType() == Qt.Window:
                    main_window_temp = widget
                    break
            parent = main_window_temp if main_window_temp else QApplication.desktop()
        
        toast = QWidget(parent)
        toast.setObjectName("toast")
        
        # 设置窗口标志 - 确保Toast位于最上层且不会被覆盖
        toast.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        toast.setAttribute(Qt.WA_ShowWithoutActivating)

        # 创建背景容器，用于实现圆角效果
        background_widget = QWidget(toast)
        background_widget.setObjectName("background_widget")
        
        # 设置布局
        layout = QHBoxLayout(background_widget)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)

        # 添加图标（如果存在）
        icon_path = Toast.get_icon_path(style['icon'])
        if icon_path and os.path.exists(icon_path):
            try:
                icon_label = QLabel()
                pixmap = QPixmap(icon_path)

                if not pixmap.isNull():
                    # 调整图标大小（20x20像素）
                    scaled_pixmap = pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    icon_label.setPixmap(scaled_pixmap)
                    icon_label.setStyleSheet("background-color: transparent;")  # 确保图标背景透明
                    layout.addWidget(icon_label)
                else:
                    print(f"无法加载图标: {icon_path}")
                    # 创建备用图标
                    backup_pixmap = QPixmap(20, 20)
                    backup_pixmap.fill(Qt.red)  # 红色方块作为备用
                    icon_label.setPixmap(backup_pixmap)
                    layout.addWidget(icon_label)
            except Exception as e:
                print(f"加载图标时出错: {e}")
        else:
            print(f"图标路径无效: {icon_path}")
            # 即使没有图标，也创建一个空标签占位，保持布局一致
            empty_label = QLabel()
            empty_label.setFixedSize(20, 20)
            layout.addWidget(empty_label)

        # 添加文本
        text_label = QLabel(message)
        text_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold; background: transparent;")
        layout.addWidget(text_label)

        # 设置背景容器的样式 - 实现黑色圆角背景
        background_widget.setStyleSheet(f"""
            QWidget#background_widget {{
                background-color: {style['background']};
                border-radius: 10px;
                border: {style['border']};
            }}
            QLabel {{
                color: white;
                font-size: 18px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
        """)
        
        # 设置背景容器的大小和位置
        background_widget.adjustSize()
        toast.resize(background_widget.size())
        
        # 设置Toast为透明，让背景容器显示圆角效果
        toast.setAttribute(Qt.WA_TranslucentBackground)
        toast.setStyleSheet("background: transparent;")

        # 调整大小并居中
        toast.adjustSize()

        # 获取应用程序的主窗口，而不是使用传递的parent
        main_window = None
        
        # 方法1: 使用activeWindow获取当前活动窗口
        main_window = QApplication.activeWindow()
        
        # 方法2: 如果activeWindow为None，遍历所有顶层窗口
        if main_window is None:
            for widget in QApplication.topLevelWidgets():
                if widget.isWindow() and widget.windowType() == Qt.Window and widget.isVisible():
                    main_window = widget
                    break
        
        # 计算Toast位置
        if main_window is not None and hasattr(main_window, 'geometry'):
            # 使用主窗口的几何信息计算位置
            main_rect = main_window.geometry()
            toast_x = main_rect.x() + (main_rect.width() // 2) - (toast.width() // 2)
            toast_y = main_rect.y() + (main_rect.height() // 2) - (toast.height() // 2)
            
        else:
            # 如果找不到主窗口，使用桌面中央位置
            desktop = QApplication.desktop()
            screen_rect = desktop.availableGeometry()
            toast_x = screen_rect.x() + (screen_rect.width() // 2) - (toast.width() // 2)
            toast_y = screen_rect.y() + (screen_rect.height() // 2) - (toast.height() // 2)
        
        # 在主窗口中央显示Toast
        toast.move(toast_x, toast_y)

        # 显示Toast
        toast.show()
        toast.raise_()

        # 设置自动隐藏
        # 设置定时器
        QTimer.singleShot(duration, toast.hide)
        QTimer.singleShot(duration + 100, toast.deleteLater)

        return toast

    @staticmethod
    def information(parent, title, message, buttons=None, defaultButton=None):
        """信息提示 - 兼容QMessageBox"""
        # 注意：第二个参数是title，但我们显示的是message
        return Toast.show_message(parent, message, 'success')

    @staticmethod
    def warning(parent, title, message, buttons=None, defaultButton=None):
        """警告提示 - 兼容QMessageBox"""
        return Toast.show_message(parent, message, 'warning')

    @staticmethod
    def critical(parent, title, message, buttons=None, defaultButton=None):
        """错误提示 - 兼容QMessageBox"""
        return Toast.show_message(parent, message, 'critical')

    # 推荐使用的新方法（避免混淆）
    @staticmethod
    def info(parent, message, duration=2000):
        """信息提示 - 推荐使用"""
        return Toast.show_message(parent, message, 'information', duration)

    @staticmethod
    def warn(parent, message, duration=2000):
        """警告提示 - 推荐使用"""
        return Toast.show_message(parent, message, 'warning', duration)

    @staticmethod
    def error(parent, message, duration=2000):
        """错误提示 - 推荐使用"""
        return Toast.show_message(parent, message, 'critical', duration)

    @staticmethod
    def success(parent, message, duration=2000):
        """成功提示 - 推荐使用"""
        return Toast.show_message(parent, message, 'success', duration)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget


    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setup_ui()

        def setup_ui(self):
            self.setWindowTitle("Toast测试 - 调试图标问题")
            self.setGeometry(100, 100, 500, 400)

            central_widget = QWidget()
            self.setCentralWidget(central_widget)

            layout = QVBoxLayout()

            # 测试各种Toast类型
            btn_info = QPushButton("信息提示")
            btn_info.clicked.connect(lambda: Toast.information(self, "信息", "这是一个信息提示"))
            layout.addWidget(btn_info)

            btn_warning = QPushButton("警告提示")
            btn_warning.clicked.connect(lambda: Toast.warning(self, "警告", "这是一个警告提示"))
            layout.addWidget(btn_warning)

            btn_critical = QPushButton("错误提示")
            btn_critical.clicked.connect(lambda: Toast.critical(self, "错误", "这是一个错误提示"))
            layout.addWidget(btn_critical)

            btn_success = QPushButton("成功提示")
            btn_success.clicked.connect(lambda: Toast.success(self, "操作成功完成！"))
            layout.addWidget(btn_success)

            central_widget.setLayout(layout)


    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())
