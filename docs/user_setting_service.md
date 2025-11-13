# UserSettingService 用户设置服务

## 简介

UserSettingService 是一个用于管理用户个性化设置的服务类。它提供了完整的 CRUD 操作接口，支持存储和检索各种类型的用户配置信息，如界面偏好、快捷键设置等。

## 功能特性

1. **创建用户设置** - 为用户创建新的配置项
2. **获取用户设置** - 获取用户的特定配置项或所有配置项
3. **更新用户设置** - 修改现有用户配置
4. **删除用户设置** - 移除不需要的配置项
5. **JSON 数据支持** - 自动处理复杂数据结构的序列化和反序列化
6. **完善的错误处理** - 提供详细的日志记录和异常处理机制

## 数据库结构

```sql
CREATE TABLE user_settings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(255) NOT NULL,
    setting_key VARCHAR(255) NOT NULL,
    setting_value JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_setting (user_id, setting_key),
    INDEX idx_user_id (user_id)
);
```

## API 接口说明

### 1. 初始化服务

```python
from src.core.services.user_setting_service import UserSettingService

user_setting_service = UserSettingService()
```

### 2. 创建用户设置

```python
setting_id = user_setting_service.create_user_setting({
    "user_id": "user123",
    "setting_key": "ui_preferences",
    "setting_value": {
        "theme": "dark",
        "language": "zh-CN",
        "font_size": 14
    }
})
```

**参数说明:**
- `user_id`: 用户唯一标识符
- `setting_key`: 设置项的键名
- `setting_value`: 设置项的值（可以是任何可JSON序列化的数据）

**返回值:**
- 成功时返回设置项的ID（整数）
- 失败时返回0

### 3. 获取用户特定设置

```python
setting = user_setting_service.get_user_setting("user123", "ui_preferences")
```

**参数说明:**
- `user_id`: 用户唯一标识符
- `setting_key`: 设置项的键名

**返回值:**
- 成功时返回包含设置信息的字典：
  ```python
  {
      "id": 1,
      "user_id": "user123",
      "setting_key": "ui_preferences",
      "setting_value": {"theme": "dark", "language": "zh-CN", "font_size": 14},
      "created_at": datetime.datetime(2023, 1, 1, 12, 0, 0),
      "updated_at": datetime.datetime(2023, 1, 1, 12, 0, 0)
  }
  ```
- 未找到时返回 `None`

### 4. 获取用户所有设置

```python
settings = user_setting_service.get_user_settings("user123")
```

**参数说明:**
- `user_id`: 用户唯一标识符

**返回值:**
- 成功时返回包含所有设置信息的列表
- 失败时返回空列表

### 5. 更新用户设置

```python
success = user_setting_service.update_user_setting(
    "user123", 
    "ui_preferences", 
    {"theme": "light", "font_size": 16}
)
```

**参数说明:**
- `user_id`: 用户唯一标识符
- `setting_key`: 设置项的键名
- `setting_value`: 新的设置值

**返回值:**
- 成功时返回 `True`
- 失败时返回 `False`

### 6. 删除用户设置

```python
deleted = user_setting_service.delete_user_setting("user123", "ui_preferences")
```

**参数说明:**
- `user_id`: 用户唯一标识符
- `setting_key`: 设置项的键名

**返回值:**
- 成功时返回 `True`
- 失败时返回 `False`

## 使用示例

完整的使用示例请参考 [user_setting_service_example.py](../examples/user_setting_service_example.py)

## 错误处理

UserSettingService 包含完善的错误处理机制：

1. **参数验证** - 对所有输入参数进行验证
2. **异常捕获** - 捕获并记录所有数据库和JSON处理异常
3. **日志记录** - 使用Python标准日志模块记录操作日志
4. **优雅降级** - 在出现错误时返回安全的默认值而不是抛出异常

## 测试

UserSettingService 包含全面的测试用例，涵盖以下场景：

1. 基本的CRUD操作
2. 边界条件处理（如查询不存在的设置）
3. 空值和特殊字符处理
4. 多设置项并发操作

运行测试：
```bash
python test/test_user_setting_service.py
```