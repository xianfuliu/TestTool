import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.services.user_setting_service import UserSettingService

def test_user_setting_service():
    """测试UserSettingService功能"""
    service = UserSettingService()
    
    # 测试数据
    user_id = "test_user_001"
    setting_key = "ui_preferences"
    setting_value = {
        "theme": "dark",
        "language": "zh-CN",
        "auto_save": True,
        "font_size": 14
    }
    
    # 创建用户设置
    print("创建用户设置...")
    setting_id = service.create_user_setting({
        "user_id": user_id,
        "setting_key": setting_key,
        "setting_value": setting_value
    })
    
    if setting_id > 0:
        print(f"用户设置创建成功，ID: {setting_id}")
    else:
        print("用户设置创建失败")
        return
    
    # 获取用户设置
    print("\n获取用户设置...")
    setting = service.get_user_setting(user_id, setting_key)
    if setting:
        print(f"获取到用户设置: {setting}")
    else:
        print("未找到用户设置")
        return
    
    # 更新用户设置
    print("\n更新用户设置...")
    updated_value = setting_value.copy()
    updated_value["theme"] = "light"
    updated_value["font_size"] = 16
    
    success = service.update_user_setting(user_id, setting_key, updated_value)
    if success:
        print("用户设置更新成功")
    else:
        print("用户设置更新失败")
        return
    
    # 再次获取用户设置以验证更新
    print("\n验证更新后的用户设置...")
    updated_setting = service.get_user_setting(user_id, setting_key)
    if updated_setting and updated_setting.get("setting_value", {}).get("theme") == "light":
        print(f"用户设置更新验证成功: {updated_setting['setting_value']}")
    else:
        print("用户设置更新验证失败")
    
    # 获取用户所有设置
    print("\n获取用户所有设置...")
    all_settings = service.get_user_settings(user_id)
    print(f"用户设置总数: {len(all_settings)}")
    
    # 删除用户设置
    print("\n删除用户设置...")
    deleted = service.delete_user_setting(user_id, setting_key)
    if deleted:
        print("用户设置删除成功")
    else:
        print("用户设置删除失败")

def test_edge_cases():
    """测试边界情况"""
    service = UserSettingService()
    
    # 测试不存在的用户设置
    print("\n=== 测试边界情况 ===")
    print("获取不存在的用户设置...")
    setting = service.get_user_setting("non_existent_user", "non_existent_key")
    if setting is None:
        print("正确处理了不存在的用户设置")
    else:
        print("错误：应该返回None")
    
    # 测试空值处理
    print("\n创建包含空值的用户设置...")
    empty_setting_id = service.create_user_setting({
        "user_id": "test_user_002",
        "setting_key": "empty_setting",
        "setting_value": {}
    })
    
    if empty_setting_id > 0:
        print("空值设置创建成功")
        # 获取空值设置
        empty_setting = service.get_user_setting("test_user_002", "empty_setting")
        if empty_setting and empty_setting.get("setting_value") == {}:
            print("空值设置获取正确")
        else:
            print("空值设置获取错误")
        
        # 删除空值设置
        service.delete_user_setting("test_user_002", "empty_setting")
    else:
        print("空值设置创建失败")

def test_multiple_settings():
    """测试多个用户设置"""
    service = UserSettingService()
    
    user_id = "multi_test_user"
    
    # 创建多个设置
    print("\n=== 测试多个用户设置 ===")
    settings_data = [
        {"setting_key": "theme", "setting_value": {"mode": "dark", "color": "blue"}},
        {"setting_key": "layout", "setting_value": {"sidebar": True, "toolbar": False}},
        {"setting_key": "preferences", "setting_value": {"notifications": True, "auto_backup": False}}
    ]
    
    created_ids = []
    for data in settings_data:
        setting_id = service.create_user_setting({
            "user_id": user_id,
            "setting_key": data["setting_key"],
            "setting_value": data["setting_value"]
        })
        if setting_id > 0:
            created_ids.append(setting_id)
            print(f"设置 {data['setting_key']} 创建成功")
        else:
            print(f"设置 {data['setting_key']} 创建失败")
    
    # 获取所有设置
    all_settings = service.get_user_settings(user_id)
    print(f"用户 {user_id} 的设置总数: {len(all_settings)}")
    
    # 验证设置数量
    if len(all_settings) == len(settings_data):
        print("设置数量正确")
    else:
        print("设置数量不正确")
    
    # 清理测试数据
    print("清理测试数据...")
    for data in settings_data:
        service.delete_user_setting(user_id, data["setting_key"])
    print("测试数据清理完成")

if __name__ == "__main__":
    test_user_setting_service()
    test_edge_cases()
    test_multiple_settings()
    print("\n所有测试完成！")