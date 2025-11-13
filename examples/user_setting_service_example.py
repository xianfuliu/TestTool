#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UserSettingService 使用示例
演示如何在实际项目中使用用户设置服务
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.services.user_setting_service import UserSettingService


def main():
    """主函数 - 演示UserSettingService的使用"""
    # 创建服务实例
    user_setting_service = UserSettingService()
    
    # 用户ID（在实际应用中，这可能来自登录用户）
    user_id = "example_user_123"
    
    print("=== UserSettingService 使用示例 ===\n")
    
    # 1. 保存用户的UI偏好设置
    print("1. 保存用户的UI偏好设置...")
    ui_preferences = {
        "theme": "dark",
        "language": "zh-CN",
        "font_size": 14,
        "auto_save": True,
        "sidebar_collapsed": False
    }
    
    setting_id = user_setting_service.create_user_setting({
        "user_id": user_id,
        "setting_key": "ui_preferences",
        "setting_value": ui_preferences
    })
    
    if setting_id:
        print(f"   UI偏好设置保存成功，设置ID: {setting_id}")
    else:
        print("   UI偏好设置保存失败")
        return
    
    # 2. 保存用户的快捷键设置
    print("\n2. 保存用户的快捷键设置...")
    key_bindings = {
        "save": "Ctrl+S",
        "undo": "Ctrl+Z",
        "redo": "Ctrl+Y",
        "run_test": "F5"
    }
    
    setting_id = user_setting_service.create_user_setting({
        "user_id": user_id,
        "setting_key": "key_bindings",
        "setting_value": key_bindings
    })
    
    if setting_id:
        print(f"   快捷键设置保存成功，设置ID: {setting_id}")
    else:
        print("   快捷键设置保存失败")
    
    # 3. 获取用户的特定设置
    print("\n3. 获取用户的UI偏好设置...")
    ui_setting = user_setting_service.get_user_setting(user_id, "ui_preferences")
    if ui_setting:
        print(f"   成功获取UI偏好设置: {ui_setting['setting_value']}")
    else:
        print("   未找到UI偏好设置")
    
    # 4. 获取用户的所有设置
    print("\n4. 获取用户的所有设置...")
    all_settings = user_setting_service.get_user_settings(user_id)
    print(f"   用户共有 {len(all_settings)} 个设置:")
    for setting in all_settings:
        print(f"   - {setting['setting_key']}: {setting['setting_value']}")
    
    # 5. 更新用户的设置
    print("\n5. 更新用户的UI偏好设置...")
    updated_ui_preferences = ui_preferences.copy()
    updated_ui_preferences["theme"] = "light"
    updated_ui_preferences["font_size"] = 16
    
    success = user_setting_service.update_user_setting(
        user_id, 
        "ui_preferences", 
        updated_ui_preferences
    )
    
    if success:
        print("   UI偏好设置更新成功")
        # 验证更新
        updated_setting = user_setting_service.get_user_setting(user_id, "ui_preferences")
        if updated_setting:
            print(f"   更新后的设置: {updated_setting['setting_value']}")
    else:
        print("   UI偏好设置更新失败")
    
    # 6. 删除用户的设置
    print("\n6. 删除用户的快捷键设置...")
    deleted = user_setting_service.delete_user_setting(user_id, "key_bindings")
    if deleted:
        print("   快捷键设置删除成功")
    else:
        print("   快捷键设置删除失败")
    
    # 7. 最终检查
    print("\n7. 最终检查 - 获取用户剩余的所有设置...")
    remaining_settings = user_setting_service.get_user_settings(user_id)
    print(f"   用户剩余 {len(remaining_settings)} 个设置:")
    for setting in remaining_settings:
        print(f"   - {setting['setting_key']}: {setting['setting_value']}")
    
    print("\n=== 示例结束 ===")


if __name__ == "__main__":
    main()