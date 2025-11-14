import os

# 模拟修复后的get_icon方法路径构建
def get_icon_path(icon_name):
    # 模拟当前文件路径：d:\workspace\TestTool\src\ui\interface_auto\components\interface_step_card.py
    current_file_path = r"d:\workspace\TestTool\src\ui\interface_auto\components\interface_step_card.py"
    
    # 计算base_dir：向上4级目录
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(current_file_path)))))
    
    # 构建图标路径（修复后）
    icon_path = os.path.join(base_dir, "resources", "icons", icon_name)
    
    return icon_path

# 测试路径构建
icon_path = get_icon_path("copy.png")
print(f"修复后构建的图标路径: {icon_path}")
print(f"路径是否存在: {os.path.exists(icon_path)}")

# 检查路径的每一部分
current_file_path = r"d:\workspace\TestTool\src\ui\interface_auto\components\interface_step_card.py"
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(current_file_path)))))
print(f"base_dir: {base_dir}")
print(f"base_dir是否存在: {os.path.exists(base_dir)}")

# 检查resources目录
resources_dir = os.path.join(base_dir, "resources")
print(f"resources_dir: {resources_dir}")
print(f"resources_dir是否存在: {os.path.exists(resources_dir)}")

# 检查icons目录
icons_dir = os.path.join(resources_dir, "icons")
print(f"icons_dir: {icons_dir}")
print(f"icons_dir是否存在: {os.path.exists(icons_dir)}")

# 检查copy.png文件
copy_path = os.path.join(icons_dir, "copy.png")
print(f"copy.png路径: {copy_path}")
print(f"copy.png是否存在: {os.path.exists(copy_path)}")