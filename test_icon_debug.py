import os
import sys

# 添加src目录到路径，模拟应用程序的导入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 模拟interface_step_card.py中的get_icon方法
class MockInterfaceStepCard:
    def __init__(self):
        pass
    
    def get_icon(self, icon_name):
        """获取图标"""
        try:
            # 使用相对路径访问图标资源
            # 模拟当前文件路径：d:\workspace\TestTool\src\ui\interface_auto\components\interface_step_card.py
            current_file_path = r"d:\workspace\TestTool\src\ui\interface_auto\components\interface_step_card.py"
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(current_file_path)))))
            icon_path = os.path.join(base_dir, "resources", "icons", icon_name)
            
            print(f"当前文件路径: {current_file_path}")
            print(f"base_dir: {base_dir}")
            print(f"图标路径: {icon_path}")
            print(f"路径是否存在: {os.path.exists(icon_path)}")
            
            if os.path.exists(icon_path):
                print(f"图标文件大小: {os.path.getsize(icon_path)} bytes")
                return f"图标加载成功: {icon_path}"
            else:
                return f"图标文件不存在: {icon_path}"
        except Exception as e:
            return f"错误: {str(e)}"

# 测试所有图标
mock_card = MockInterfaceStepCard()

print("=== 测试所有图标文件 ===")
icon_files = ["copy.png", "edit.png", "delete.png"]

for icon_file in icon_files:
    print(f"\n测试图标: {icon_file}")
    result = mock_card.get_icon(icon_file)
    print(result)

# 检查实际的图标目录内容
print("\n=== 检查图标目录内容 ===")
icon_dir = r"d:\workspace\TestTool\src\resources\icons"
if os.path.exists(icon_dir):
    files = os.listdir(icon_dir)
    print(f"图标目录中的文件: {files}")
else:
    print(f"图标目录不存在: {icon_dir}")