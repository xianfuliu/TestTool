import sys
import traceback


def excepthook(exc_type, exc_value, exc_traceback):
    """全局异常处理"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    print("未捕获的异常:", exc_type.__name__)
    print("异常信息:", exc_value)

    # 打印堆栈跟踪
    traceback.print_exception(exc_type, exc_value, exc_traceback)

    # 尝试显示错误对话框
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance()
        if app:
            error_msg = f"发生未处理的异常:\n\n{exc_type.__name__}: {exc_value}"
            QMessageBox.critical(None, "未处理的异常", error_msg)
    except:
        pass

    sys.exit(1)
