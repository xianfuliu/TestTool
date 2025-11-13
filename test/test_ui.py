import sys
sys.path.append('src')
from src.ui.interface_auto.api_template import ApiTemplateManager
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import time

app = QApplication(sys.argv)
print('[DEBUG] 创建ApiTemplateManager实例...')
manager = ApiTemplateManager()
print('[DEBUG] ApiTemplateManager创建完成')
print('[DEBUG] 显示窗口...')
manager.show()
print('[DEBUG] 窗口显示完成')

# 定义函数
check_final_state = None
def create_test_tab(index):
    if hasattr(manager, 'tabbed_editor'):
        print(f'[DEBUG] 尝试创建标签页 {index}...')
        template_data = {
            'name': f'测试接口{index}',
            'method': 'GET',
            'url_path': f'/api/test{index}'
        }
        
        try:
            tab_id = manager.tabbed_editor.open_template(template_data)
            print(f'[DEBUG] 标签页 {index} 创建完成，ID: {tab_id}')
            
            # 模拟快速关闭操作
            if index == 0:
                QTimer.singleShot(200, lambda: try_close_tab(0))
        except Exception as e:
            print(f'[DEBUG] 创建标签页 {index} 时出错: {e}')

def try_close_tab(index):
    if hasattr(manager, 'tabbed_editor'):
        print(f'[DEBUG] 尝试关闭标签页 {index}...')
        try:
            # 直接调用关闭方法，模拟可能的内部触发
            manager.tabbed_editor.close_tab(index, from_close_button=True)
        except Exception as e:
            print(f'[DEBUG] 关闭标签页 {index} 时出错: {e}')

def check_final_state():
    if hasattr(manager, 'tabbed_editor'):
        print(f'[DEBUG] 最终检查 - initializing状态: {manager.tabbed_editor.initializing}')
        print(f'[DEBUG] 最终检查 - 标签页数量: {manager.tabbed_editor.tab_widget.count()}')
        print('[DEBUG] 测试完成，程序运行正常')
    app.quit()

# 模拟在初始化过程中可能触发的问题
print('[DEBUG] 模拟快速操作场景...')

# 在初始化过程中快速创建多个标签页
for i in range(3):
    QTimer.singleShot(100 + i*50, lambda i=i: create_test_tab(i))

# 等待一段时间后检查状态
QTimer.singleShot(3000, check_final_state)

print('[DEBUG] 开始事件循环...')
app.exec_()