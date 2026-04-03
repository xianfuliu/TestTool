#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
卡片工具服务类

功能说明：
1. 提供工具文件夹的增删改查功能
2. 提供工具卡片的增删改查功能
3. 支持从JSON配置迁移到数据库
4. 管理卡片执行和参数映射
"""

from config.database import Database
from typing import Dict, Any, List, Optional
import json
import os


class ToolCardsService:
    """卡片工具服务类"""

    def __init__(self):
        self.db = Database()
        self.database_available = self._check_database_connection()

    def _check_database_connection(self) -> bool:
        """检查数据库连接是否可用"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                print("[DEBUG] 数据库连接检查成功")
                return True
        except Exception as e:
            print(f"[ERROR] 数据库连接检查失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """获取所有项目"""
        if not self.database_available:
            return []

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, description, business_group_id,
                               created_by, created_at, updated_at
                        FROM projects
                        ORDER BY id ASC
                    """)
                    return cursor.fetchall()
        except Exception as e:
            print(f"获取项目列表失败: {e}")
            return []

    def get_all_folders(self) -> List[Dict[str, Any]]:
        """获取所有工具文件夹"""
        if not self.database_available:
            return []

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, description, parent_id, sort_order, is_default,
                               created_by, created_at, updated_at
                        FROM tool_card_folders
                        ORDER BY parent_id IS NULL DESC, created_at ASC, id ASC
                    """)
                    folders = cursor.fetchall()
                    
                    # 返回扁平列表，UI层会自己构建树形结构
                    return folders
        except Exception as e:
            print(f"获取工具文件夹失败: {e}")
            return []

    def get_folder_by_id(self, folder_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取文件夹信息"""
        if not self.database_available:
            return None

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, description, parent_id, sort_order, is_default,
                               created_by, created_at, updated_at
                        FROM tool_card_folders
                        WHERE id = %s
                    """, (folder_id,))
                    return cursor.fetchone()
        except Exception as e:
            print(f"获取文件夹失败: {e}")
            return None

    def get_cards_by_folder(self, folder_id: int) -> List[Dict[str, Any]]:
        """根据文件夹ID获取工具卡片"""
        if not self.database_available:
            return []

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, folder_id, name, description, card_type, 
                               config, mappings, sort_order, enabled,
                               created_by, created_at, updated_at
                        FROM tool_card_items
                        WHERE folder_id = %s AND enabled = TRUE
                        ORDER BY sort_order ASC, id ASC
                    """, (folder_id,))
                    cards = cursor.fetchall()
                    
                    # 解析JSON字段
                    for card in cards:
                        if card.get('config'):
                            card['config'] = json.loads(card['config'])
                        if card.get('mappings'):
                            card['mappings'] = json.loads(card['mappings'])
                    
                    return cards
        except Exception as e:
            print(f"获取工具卡片失败: {e}")
            return []

    def get_subfolders_by_parent(self, parent_folder_id: int) -> List[Dict[str, Any]]:
        """根据父文件夹ID获取所有子文件夹"""
        if not self.database_available:
            return []

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, description, parent_id, sort_order, is_default,
                               created_by, created_at, updated_at
                        FROM tool_card_folders
                        WHERE parent_id = %s
                        ORDER BY created_at ASC, id ASC
                    """, (parent_folder_id,))
                    return cursor.fetchall()
        except Exception as e:
            print(f"获取子文件夹失败: {e}")
            return []

    def get_card_by_id(self, card_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取工具卡片"""
        if not self.database_available:
            return None

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, folder_id, name, description, card_type, 
                               config, mappings, sort_order, enabled,
                               created_by, created_at, updated_at
                        FROM tool_card_items
                        WHERE id = %s
                    """, (card_id,))
                    card = cursor.fetchone()
                    
                    if card:
                        # 解析JSON字段
                        if card.get('config'):
                            card['config'] = json.loads(card['config'])
                        if card.get('mappings'):
                            card['mappings'] = json.loads(card['mappings'])
                    
                    return card
        except Exception as e:
            print(f"获取工具卡片失败: {e}")
            return None

    def create_folder(self, folder_data: Dict[str, Any]) -> Optional[int]:
        """创建工具文件夹"""
        if not self.database_available:
            return None

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO tool_card_folders (name, description, parent_id, sort_order, is_default, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        folder_data.get('name'),
                        folder_data.get('description', ''),
                        folder_data.get('parent_id'),
                        folder_data.get('sort_order', 0),
                        folder_data.get('is_default', False),
                        folder_data.get('created_by', 'admin')
                    ))
                    folder_id = cursor.lastrowid
                    conn.commit()
                    return folder_id
        except Exception as e:
            print(f"创建工具文件夹失败: {e}")
            return None

    def update_folder(self, folder_id: int, folder_data: Dict[str, Any]) -> bool:
        """更新工具文件夹"""
        if not self.database_available:
            return False

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 先检查文件夹是否存在
                    cursor.execute("SELECT id FROM tool_card_folders WHERE id = %s", (folder_id,))
                    existing_folder = cursor.fetchone()
                    
                    if not existing_folder:
                        print(f"[ERROR] 文件夹ID {folder_id} 不存在，无法更新")
                        return False
                    
                    cursor.execute("""
                        UPDATE tool_card_folders 
                        SET name = %s, description = %s, parent_id = %s, 
                            sort_order = %s, is_default = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (
                        folder_data.get('name'),
                        folder_data.get('description', ''),
                        folder_data.get('parent_id'),
                        folder_data.get('sort_order', 0),
                        folder_data.get('is_default', False),
                        folder_id
                    ))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"更新工具文件夹失败: {e}")
            return False

    def create_card(self, card_data: Dict[str, Any]) -> Optional[int]:
        """创建工具卡片"""
        if not self.database_available:
            return None

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO tool_card_items (folder_id, name, description, card_type, 
                                              config, mappings, sort_order, enabled, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        card_data.get('folder_id'),
                        card_data.get('name'),
                        card_data.get('description', ''),
                        card_data.get('card_type', 'sql'),
                        json.dumps(card_data.get('config', {}), ensure_ascii=False),
                        json.dumps(card_data.get('mappings', {}), ensure_ascii=False),
                        card_data.get('sort_order', 0),
                        card_data.get('enabled', True),
                        card_data.get('created_by', 'admin')
                    ))
                    card_id = cursor.lastrowid
                    conn.commit()
                    return card_id
        except Exception as e:
            print(f"创建工具卡片失败: {e}")
            return None

    def update_card(self, card_id: int, card_data: Dict[str, Any]) -> bool:
        """更新工具卡片"""
        if not self.database_available:
            print(f"[ERROR] 数据库不可用，无法更新卡片 {card_id}")
            return False

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 先检查卡片是否存在
                    cursor.execute("SELECT id FROM tool_card_items WHERE id = %s", (card_id,))
                    existing_card = cursor.fetchone()
                    
                    if not existing_card:
                        print(f"[ERROR] 卡片ID {card_id} 不存在，无法更新")
                        return False
                    
                    # 执行更新操作
                    cursor.execute("""
                        UPDATE tool_card_items
                        SET name = %s, description = %s, card_type = %s,
                            config = %s, mappings = %s, sort_order = %s, enabled = %s
                        WHERE id = %s
                    """, (
                        card_data.get('name'),
                        card_data.get('description', ''),
                        card_data.get('card_type', 'sql'),
                        json.dumps(card_data.get('config', {}), ensure_ascii=False),
                        json.dumps(card_data.get('mappings', {}), ensure_ascii=False),
                        card_data.get('sort_order', 0),
                        card_data.get('enabled', True),
                        card_id
                    ))
                    conn.commit()
                    
                    affected_rows = cursor.rowcount
                    print(f"[DEBUG] 更新卡片 {card_id}，影响行数: {affected_rows}")
                    
                    # 修改逻辑：数据无变化也应该视为成功
                    # 如果卡片存在且UPDATE执行成功（无异常），就返回True
                    # 影响行数为0表示数据没有变化，这也是成功的
                    return True
        except Exception as e:
            print(f"[ERROR] 更新工具卡片失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def delete_card(self, card_id: int) -> bool:
        """删除工具卡片"""
        if not self.database_available:
            return False

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM tool_card_items WHERE id = %s", (card_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"删除工具卡片失败: {e}")
            return False

    def delete_folder(self, folder_id: int) -> bool:
        """删除工具文件夹（包含级联删除子文件夹）"""
        if not self.database_available:
            return False

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 先递归删除所有子文件夹
                    self._delete_subfolders_recursive(conn, folder_id)
                    
                    # 然后删除当前文件夹
                    cursor.execute("DELETE FROM tool_card_folders WHERE id = %s", (folder_id,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"删除工具文件夹失败: {e}")
            return False

    def _delete_subfolders_recursive(self, conn, folder_id: int):
        """递归删除子文件夹"""
        try:
            with conn.cursor() as cursor:
                # 获取所有子文件夹
                cursor.execute("SELECT id FROM tool_card_folders WHERE parent_id = %s", (folder_id,))
                subfolders = cursor.fetchall()
                
                # 递归删除每个子文件夹
                for subfolder in subfolders:
                    subfolder_id = subfolder['id']
                    self._delete_subfolders_recursive(conn, subfolder_id)
                    
                    # 删除子文件夹
                    cursor.execute("DELETE FROM tool_card_folders WHERE id = %s", (subfolder_id,))
        except Exception as e:
            print(f"递归删除子文件夹失败: {e}")
            raise

    def initialize_default_data(self) -> bool:
        """初始化默认数据"""
        if not self.database_available:
            return False

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 创建默认文件夹
                    cursor.execute("""
                        INSERT INTO tool_card_folders (name, description, parent_id, sort_order, is_default, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        "默认工具",
                        "系统默认工具文件夹",
                        None,
                        0,
                        True,
                        'admin'
                    ))
                    
                    conn.commit()
                    print("默认数据初始化完成")
                    return True
        except Exception as e:
            print(f"默认数据初始化失败: {e}")
            return False

    def _build_folder_tree(self, folders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """构建文件夹树形结构"""
        folder_map = {}
        root_folders = []

        # 创建文件夹映射
        for folder in folders:
            folder_id = folder['id']
            folder_map[folder_id] = folder
            folder['cards'] = []  # 初始化卡片列表

        # 构建树形结构
        for folder in folders:
            parent_id = folder.get('parent_id')
            if parent_id and parent_id in folder_map:
                parent_folder = folder_map[parent_id]
                if 'children' not in parent_folder:
                    parent_folder['children'] = []
                parent_folder['children'].append(folder)
            else:
                root_folders.append(folder)

        return root_folders




# 提供全局函数方便使用
def get_tool_cards_service():
    """获取卡片工具服务实例"""
    return ToolCardsService()


def initialize_tool_cards_data():
    """初始化工具卡片数据"""
    service = ToolCardsService()
    return service.initialize_default_data()