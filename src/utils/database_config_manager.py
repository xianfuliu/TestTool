#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库配置管理工具

功能说明：
1. 提供数据库配置的增删改查功能
2. 支持数据库连接测试
3. 管理默认数据库配置
4. 提供数据库配置的导入导出功能
"""

import pymysql
from pymysql.cursors import DictCursor
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from config.database import Database


class DatabaseConfigManager:
    """数据库配置管理类"""

    def __init__(self):
        self.db = Database()

    def get_all_configs(self) -> List[Dict[str, Any]]:
        """获取所有数据库配置"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, name, host, port, user, database_name, charset, 
                               description, is_default, enabled, created_at, updated_at
                        FROM database_configs 
                        WHERE enabled = TRUE
                        ORDER BY is_default DESC, name ASC
                    """
                    )
                    return cursor.fetchall()
        except Exception as e:
            print(f"获取数据库配置失败: {e}")
            return []

    def get_config_by_id(self, config_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取数据库配置"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, name, host, port, user, password, database_name, charset, 
                               description, is_default, enabled, created_at, updated_at
                        FROM database_configs 
                        WHERE id = %s
                    """,
                        (config_id,),
                    )
                    return cursor.fetchone()
        except Exception as e:
            print(f"获取数据库配置失败: {e}")
            return None

    def get_default_config(self) -> Optional[Dict[str, Any]]:
        """获取默认数据库配置"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, name, host, port, user, password, database_name, charset, 
                               description, is_default, enabled
                        FROM database_configs 
                        WHERE is_default = TRUE AND enabled = TRUE
                        LIMIT 1
                    """
                    )
                    return cursor.fetchone()
        except Exception as e:
            print(f"获取默认数据库配置失败: {e}")
            return None

    def add_config(self, config_data: Dict[str, Any]) -> bool:
        """添加数据库配置"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 如果设置为默认配置，先取消其他配置的默认状态
                    if config_data.get("is_default"):
                        cursor.execute(
                            "UPDATE database_configs SET is_default = FALSE WHERE is_default = TRUE"
                        )

                    sql = """
                        INSERT INTO database_configs 
                        (name, host, port, user, password, database_name, charset, description, is_default, enabled)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """

                    cursor.execute(
                        sql,
                        (
                            config_data["name"],
                            config_data["host"],
                            config_data["port"],
                            config_data["user"],
                            config_data["password"],
                            config_data["database_name"],
                            config_data.get("charset", "utf8mb4"),
                            config_data.get("description", ""),
                            config_data.get("is_default", False),
                            config_data.get("enabled", True),
                        ),
                    )

                    conn.commit()
                    return True
        except Exception as e:
            print(f"添加数据库配置失败: {e}")
            return False

    def update_config(self, config_id: int, config_data: Dict[str, Any]) -> bool:
        """更新数据库配置"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 如果设置为默认配置，先取消其他配置的默认状态
                    if config_data.get("is_default"):
                        cursor.execute(
                            "UPDATE database_configs SET is_default = FALSE WHERE is_default = TRUE AND id != %s",
                            (config_id,),
                        )

                    sql = """
                        UPDATE database_configs 
                        SET name = %s, host = %s, port = %s, user = %s, password = %s, 
                            database_name = %s, charset = %s, description = %s, 
                            is_default = %s, enabled = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """

                    cursor.execute(
                        sql,
                        (
                            config_data["name"],
                            config_data["host"],
                            config_data["port"],
                            config_data["user"],
                            config_data["password"],
                            config_data["database_name"],
                            config_data.get("charset", "utf8mb4"),
                            config_data.get("description", ""),
                            config_data.get("is_default", False),
                            config_data.get("enabled", True),
                            config_id,
                        ),
                    )

                    conn.commit()
                    return True
        except Exception as e:
            print(f"更新数据库配置失败: {e}")
            return False

    def delete_config(self, config_id: int) -> bool:
        """删除数据库配置"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查是否为默认配置，如果是则不能删除
                    cursor.execute(
                        "SELECT is_default FROM database_configs WHERE id = %s",
                        (config_id,),
                    )
                    config = cursor.fetchone()

                    if config and config.get("is_default"):
                        print("不能删除默认数据库配置")
                        return False

                    cursor.execute(
                        "DELETE FROM database_configs WHERE id = %s", (config_id,)
                    )
                    conn.commit()
                    return True
        except Exception as e:
            print(f"删除数据库配置失败: {e}")
            return False

    def test_connection(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """测试数据库连接"""
        result = {"success": False, "message": "", "details": {}}

        try:
            # 测试连接
            conn = pymysql.connect(
                host=config_data["host"],
                port=config_data["port"],
                user=config_data["user"],
                password=config_data["password"],
                database=config_data["database_name"],
                charset=config_data.get("charset", "utf8mb4"),
                cursorclass=DictCursor,
                connect_timeout=10,
                read_timeout=10,
                write_timeout=10,
            )

            with conn.cursor() as cursor:
                # 测试基本连接
                cursor.execute("SELECT 1")

                # 获取数据库版本信息
                cursor.execute("SELECT VERSION() as version")
                version_info = cursor.fetchone()

                # 获取数据库字符集信息
                cursor.execute("SHOW VARIABLES LIKE 'character_set_%'")
                charset_info = cursor.fetchall()

                # 获取数据库大小
                cursor.execute(
                    f"SELECT SUM(data_length + index_length) as size FROM information_schema.tables WHERE table_schema = '{config_data['database_name']}'"
                )
                db_size = cursor.fetchone()

                result["success"] = True
                result["message"] = "数据库连接测试成功"
                result["details"] = {
                    "version": version_info.get("version") if version_info else "未知",
                    "database_size": db_size.get("size") if db_size else 0,
                    "character_sets": {
                        item["Variable_name"]: item["Value"] for item in charset_info
                    },
                }

            conn.close()

        except pymysql.Error as e:
            result["success"] = False
            result["message"] = f"数据库连接失败: {e}"
            result["details"] = {"error_code": e.args[0], "error_message": str(e)}

        return result

    def set_default_config(self, config_id: int) -> bool:
        """设置默认数据库配置"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 先取消所有配置的默认状态
                    cursor.execute("UPDATE database_configs SET is_default = FALSE")

                    # 设置指定配置为默认
                    cursor.execute(
                        "UPDATE database_configs SET is_default = TRUE WHERE id = %s",
                        (config_id,),
                    )

                    conn.commit()
                    return True
        except Exception as e:
            print(f"设置默认配置失败: {e}")
            return False

    def export_configs(self) -> str:
        """导出所有数据库配置为JSON格式"""
        configs = self.get_all_configs()

        # 移除密码字段，确保安全
        for config in configs:
            if "password" in config:
                config["password"] = "***"

        return json.dumps(configs, ensure_ascii=False, indent=2, default=str)

    def import_configs(self, json_data: str) -> bool:
        """从JSON导入数据库配置"""
        try:
            configs = json.loads(json_data)

            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    for config in configs:
                        # 检查配置是否已存在
                        cursor.execute(
                            "SELECT id FROM database_configs WHERE name = %s",
                            (config["name"],),
                        )
                        existing_config = cursor.fetchone()

                        if existing_config:
                            # 更新现有配置
                            self.update_config(existing_config["id"], config)
                        else:
                            # 添加新配置
                            self.add_config(config)

                    conn.commit()
                    return True
        except Exception as e:
            print(f"导入数据库配置失败: {e}")
            return False


def test_database_connection(config: Dict[str, Any]) -> Dict[str, Any]:
    """测试数据库连接的静态方法"""
    manager = DatabaseConfigManager()
    return manager.test_connection(config)


def get_default_database_config() -> Optional[Dict[str, Any]]:
    """获取默认数据库配置的静态方法"""
    manager = DatabaseConfigManager()
    return manager.get_default_config()


if __name__ == "__main__":
    # 测试代码
    manager = DatabaseConfigManager()

    # 获取所有配置
    configs = manager.get_all_configs()
    print("所有数据库配置:")
    for config in configs:
        print(
            f"  - {config['name']}: {config['host']}:{config['port']}/{config['database_name']}"
        )

    # 获取默认配置
    default_config = manager.get_default_config()
    if default_config:
        print(f"\n默认配置: {default_config['name']}")

    # 测试连接
    if default_config:
        test_result = manager.test_connection(default_config)
        print(f"\n连接测试结果: {test_result['message']}")
