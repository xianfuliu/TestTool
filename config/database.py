import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime
import json
from typing import Dict, Any, List, Optional
import sys
import os

# 添加项目根目录到Python路径，以便能够导入settings模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class JSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理datetime对象"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class Database:
    """数据库连接管理类"""

    def __init__(self):
        from config.settings import DATABASE_CONFIG
        self.config = DATABASE_CONFIG
        self._connection_pool = []
        self._max_pool_size = 5

    def get_connection(self):
        """获取数据库连接（带重连机制）"""
        try:
            conn = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset='utf8mb4',
                cursorclass=DictCursor,
                connect_timeout=30,  # 连接超时30秒
                read_timeout=60,     # 读取超时60秒
                write_timeout=60,    # 写入超时60秒
                autocommit=False     # 关闭自动提交，手动控制事务
            )
            
            # 测试连接是否有效
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            return conn
        except pymysql.Error as e:
            print(f"数据库连接失败: {e}")
            # 等待1秒后重试
            import time
            time.sleep(1)
            
            # 重试连接
            return pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset='utf8mb4',
                cursorclass=DictCursor,
                connect_timeout=30,
                read_timeout=60,
                write_timeout=60,
                autocommit=False
            )

    def init_database(self):
        """初始化数据库表结构"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 按依赖顺序创建表
                    for table_name, create_sql in DB_TABLES.items():
                        try:
                            cursor.execute(create_sql)
                            print(f"表 {table_name} 创建成功")
                        except Exception as e:
                            print(f"创建表 {table_name} 失败: {e}")
                    conn.commit()
                    print("数据库初始化完成")
        except Exception as e:
            print(f"数据库初始化失败: {e}")
            raise e


# 完整的数据库表结构定义
DB_TABLES = {
    'business_groups': '''
        CREATE TABLE IF NOT EXISTS business_groups (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_name (name),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'projects': '''
        CREATE TABLE IF NOT EXISTS projects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            group_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES business_groups(id) ON DELETE CASCADE,
            UNIQUE KEY uk_group_project (group_id, name),
            INDEX idx_group_id (group_id),
            INDEX idx_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'environments': '''
        CREATE TABLE IF NOT EXISTS environments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            base_url VARCHAR(255) NOT NULL,
            description TEXT,
            headers JSON,
            variables JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'api_templates': '''
        CREATE TABLE IF NOT EXISTS api_templates (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT NOT NULL,
            folder_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            method VARCHAR(10) NOT NULL,
            url_path VARCHAR(500) NOT NULL,
            headers JSON,
            params JSON,
            body JSON,
            description TEXT,
            sort_order INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            INDEX idx_project_id (project_id),
            INDEX idx_name (name),
            INDEX idx_method (method),
            INDEX idx_sort_order (sort_order)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'test_cases': '''
        CREATE TABLE IF NOT EXISTS test_cases (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT NOT NULL,
            folder_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            environment_id INT,
            global_vars JSON,
            sort_order INT DEFAULT 0,
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (environment_id) REFERENCES environments(id) ON DELETE SET NULL,
            INDEX idx_project_id (project_id),
            INDEX idx_name (name),
            INDEX idx_created_at (created_at),
            INDEX idx_sort_order (sort_order)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'test_case_steps': '''
        CREATE TABLE IF NOT EXISTS test_case_steps (
            id INT AUTO_INCREMENT PRIMARY KEY,
            case_id INT NOT NULL,
            api_template_id INT,
            step_order INT NOT NULL DEFAULT 0,
            name VARCHAR(100),
            enabled BOOLEAN DEFAULT TRUE,
            pre_processing JSON COMMENT '前置处理配置',
            post_processing JSON COMMENT '后置处理配置',
            assertions JSON COMMENT '断言配置',
            variables JSON COMMENT '步骤局部变量',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (case_id) REFERENCES test_cases(id) ON DELETE CASCADE,
            FOREIGN KEY (api_template_id) REFERENCES api_templates(id) ON DELETE SET NULL,
            UNIQUE KEY uk_case_step_order (case_id, step_order),
            INDEX idx_case_id (case_id),
            INDEX idx_api_template_id (api_template_id),
            INDEX idx_step_order (step_order)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'test_schedulers': '''
        CREATE TABLE IF NOT EXISTS test_schedulers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            cron_expression VARCHAR(50) NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            case_ids JSON COMMENT '测试用例ID列表',
            notify_emails JSON COMMENT '邮件通知列表',
            notify_wechat JSON COMMENT '微信通知配置',
            last_run_at TIMESTAMP NULL,
            next_run_at TIMESTAMP NULL,
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_name (name),
            INDEX idx_enabled (enabled),
            INDEX idx_next_run_at (next_run_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'test_reports': '''
        CREATE TABLE IF NOT EXISTS test_reports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            scheduler_id INT,
            case_id INT NOT NULL,
            report_name VARCHAR(200) NOT NULL,
            status ENUM('success', 'failure', 'error', 'running') DEFAULT 'running',
            total_steps INT DEFAULT 0,
            passed_steps INT DEFAULT 0,
            failed_steps INT DEFAULT 0,
            error_steps INT DEFAULT 0,
            start_time TIMESTAMP NULL,
            end_time TIMESTAMP NULL,
            duration FLOAT DEFAULT 0 COMMENT '执行时长(秒)',
            log_path VARCHAR(500) COMMENT '日志文件路径',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scheduler_id) REFERENCES test_schedulers(id) ON DELETE SET NULL,
            FOREIGN KEY (case_id) REFERENCES test_cases(id) ON DELETE CASCADE,
            INDEX idx_scheduler_id (scheduler_id),
            INDEX idx_case_id (case_id),
            INDEX idx_status (status),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'test_step_results': '''
        CREATE TABLE IF NOT EXISTS test_step_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            report_id INT NOT NULL,
            step_id INT NOT NULL,
            step_order INT NOT NULL,
            status ENUM('success', 'failure', 'error', 'skipped') DEFAULT 'skipped',
            request_data JSON COMMENT '请求数据',
            response_data JSON COMMENT '响应数据',
            assertions_result JSON COMMENT '断言结果',
            variables_snapshot JSON COMMENT '变量快照',
            error_message TEXT,
            start_time TIMESTAMP NULL,
            end_time TIMESTAMP NULL,
            duration FLOAT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (report_id) REFERENCES test_reports(id) ON DELETE CASCADE,
            INDEX idx_report_id (report_id),
            INDEX idx_step_id (step_id),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'global_tools': '''
        CREATE TABLE IF NOT EXISTS global_tools (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            tool_type ENUM('sql', 'random', 'python', 'timer', 'http', 'custom') NOT NULL,
            description TEXT,
            config JSON NOT NULL COMMENT '工具配置',
            enabled BOOLEAN DEFAULT TRUE,
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_name (name),
            INDEX idx_tool_type (tool_type),
            INDEX idx_enabled (enabled)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'global_variables': '''
        CREATE TABLE IF NOT EXISTS global_variables (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT NOT NULL DEFAULT 0,
            name VARCHAR(100) NOT NULL,
            value TEXT,
            variable_type ENUM('string', 'number', 'boolean', 'json') DEFAULT 'string',
            description TEXT,
            created_by VARCHAR(50) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_project_name (project_id, name),
            INDEX idx_project_id (project_id),
            INDEX idx_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'api_folders': '''
        CREATE TABLE IF NOT EXISTS api_folders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT NOT NULL,
            parent_id INT DEFAULT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            sort_order INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES api_folders(id) ON DELETE CASCADE,
            INDEX idx_project_id (project_id),
            INDEX idx_parent_id (parent_id),
            INDEX idx_sort_order (sort_order)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'case_folders': '''
        CREATE TABLE IF NOT EXISTS case_folders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT NOT NULL,
            parent_id INT DEFAULT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            sort_order INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES case_folders(id) ON DELETE CASCADE,
            INDEX idx_project_id (project_id),
            INDEX idx_parent_id (parent_id),
            INDEX idx_sort_order (sort_order)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ''',

    'user_settings': '''
        CREATE TABLE IF NOT EXISTS user_settings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            setting_key VARCHAR(100) NOT NULL,
            setting_value JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_user_setting (user_id, setting_key),
            INDEX idx_user_id (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    '''
}

# 初始化数据
INITIAL_DATA = {
    'environments': [
        {
            'name': '开发环境',
            'base_url': 'http://dev.example.com',
            'description': '开发测试环境',
            'headers': {'Content-Type': 'application/json'},
            'variables': {}
        },
        {
            'name': '测试环境',
            'base_url': 'http://test.example.com',
            'description': '测试环境',
            'headers': {'Content-Type': 'application/json'},
            'variables': {}
        },
        {
            'name': '生产环境',
            'base_url': 'https://api.example.com',
            'description': '生产环境',
            'headers': {'Content-Type': 'application/json'},
            'variables': {}
        }
    ],

    'global_tools': [
        {
            'name': 'SQL查询工具',
            'tool_type': 'sql',
            'description': '执行SQL查询并返回结果',
            'config': {
                'database_type': 'mysql',
                'connection_params': {},
                'result_type': 'single'  # single, multiple, count
            },
            'enabled': True
        },
        {
            'name': '随机数生成器',
            'tool_type': 'random',
            'description': '生成指定范围的随机数',
            'config': {
                'min_value': 1,
                'max_value': 100,
                'type': 'integer'  # integer, float, string
            },
            'enabled': True
        },
        {
            'name': 'Python脚本执行器',
            'tool_type': 'python',
            'description': '执行Python脚本代码',
            'config': {
                'timeout': 30,
                'allowed_modules': ['random', 'datetime', 'json', 're']
            },
            'enabled': True
        },
        {
            'name': '等待定时器',
            'tool_type': 'timer',
            'description': '等待指定时间后再执行下一步',
            'config': {
                'max_wait_time': 300  # 最大等待时间（秒）
            },
            'enabled': True
        },
        {
            'name': 'HTTP请求工具',
            'tool_type': 'http',
            'description': '发送HTTP请求',
            'config': {
                'timeout': 30,
                'max_redirects': 5
            },
            'enabled': True
        }
    ]
}


class DataModel:
    """数据模型基类"""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataModel':
        """从字典创建数据模型实例"""
        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance

    def to_dict(self) -> Dict[str, Any]:
        """将数据模型转换为字典"""
        result = {}
        for key in dir(self):
            if not key.startswith('_') and not callable(getattr(self, key)):
                value = getattr(self, key)
                # 处理特殊类型
                if isinstance(value, datetime):
                    value = value.isoformat()
                result[key] = value
        return result


class BusinessGroup(DataModel):
    """业务分组模型"""

    def __init__(self):
        self.id: Optional[int] = None
        self.name: str = ""
        self.description: str = ""
        self.created_by: str = "admin"
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None


class Project(DataModel):
    """项目模型"""

    def __init__(self):
        self.id: Optional[int] = None
        self.group_id: int = 0
        self.name: str = ""
        self.description: str = ""
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None


class Environment(DataModel):
    """环境配置模型"""

    def __init__(self):
        self.id: Optional[int] = None
        self.name: str = ""
        self.base_url: str = ""
        self.description: str = ""
        self.headers: Dict[str, Any] = {}
        self.variables: Dict[str, Any] = {}
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None


class ApiTemplate(DataModel):
    """接口模板模型"""

    def __init__(self):
        self.id: Optional[int] = None
        self.project_id: int = 0
        self.folder_id: Optional[int] = None
        self.name: str = ""
        self.method: str = "GET"
        self.url_path: str = ""
        self.headers: Dict[str, Any] = {}
        self.params: Dict[str, Any] = {}
        self.body: Dict[str, Any] = {}
        self.description: str = ""
        self.sort_order: int = 0
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None


class TestCase(DataModel):
    """测试用例模型"""

    def __init__(self):
        self.id: Optional[int] = None
        self.project_id: int = 0
        self.folder_id: Optional[int] = None
        self.name: str = ""
        self.description: str = ""
        self.environment_id: Optional[int] = None
        self.global_vars: Dict[str, Any] = {}
        self.created_by: str = "admin"
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None


class TestCaseStep(DataModel):
    """测试用例步骤模型"""

    def __init__(self):
        self.id: Optional[int] = None
        self.case_id: int = 0
        self.api_template_id: Optional[int] = None
        self.step_order: int = 0
        self.name: str = ""
        self.enabled: bool = True
        self.pre_processing: Dict[str, Any] = {}
        self.post_processing: Dict[str, Any] = {}
        self.assertions: Dict[str, Any] = {}
        self.variables: Dict[str, Any] = {}
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None


class TestScheduler(DataModel):
    """测试调度模型"""

    def __init__(self):
        self.id: Optional[int] = None
        self.name: str = ""
        self.description: str = ""
        self.cron_expression: str = ""
        self.enabled: bool = True
        self.case_ids: List[int] = []
        self.notify_emails: List[str] = []
        self.notify_wechat: Dict[str, Any] = {}
        self.last_run_at: Optional[datetime] = None
        self.next_run_at: Optional[datetime] = None
        self.created_by: str = "admin"
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None


class TestReport(DataModel):
    """测试报告模型"""

    def __init__(self):
        self.id: Optional[int] = None
        self.scheduler_id: Optional[int] = None
        self.case_id: int = 0
        self.report_name: str = ""
        self.status: str = "running"  # success, failure, error, running
        self.total_steps: int = 0
        self.passed_steps: int = 0
        self.failed_steps: int = 0
        self.error_steps: int = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.duration: float = 0.0
        self.log_path: str = ""
        self.created_at: Optional[datetime] = None


class TestStepResult(DataModel):
    """测试步骤结果模型"""

    def __init__(self):
        self.id: Optional[int] = None
        self.report_id: int = 0
        self.step_id: int = 0
        self.step_order: int = 0
        self.status: str = "skipped"  # success, failure, error, skipped
        self.request_data: Dict[str, Any] = {}
        self.response_data: Dict[str, Any] = {}
        self.assertions_result: Dict[str, Any] = {}
        self.variables_snapshot: Dict[str, Any] = {}
        self.error_message: str = ""
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.duration: float = 0.0
        self.created_at: Optional[datetime] = None


class GlobalTool(DataModel):
    """全局工具模型"""

    def __init__(self):
        self.id: Optional[int] = None
        self.name: str = ""
        self.tool_type: str = ""  # sql, random, python, timer, http, custom
        self.description: str = ""
        self.config: Dict[str, Any] = {}
        self.enabled: bool = True
        self.created_by: str = "admin"
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None


class GlobalVariable(DataModel):
    """全局变量模型"""

    def __init__(self):
        self.id: Optional[int] = None
        self.name: str = ""
        self.value: str = ""
        self.variable_type: str = "string"  # string, number, boolean, json
        self.description: str = ""
        self.created_by: str = "admin"
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None


class ApiFolder(DataModel):
    """接口文件夹模型"""

    def __init__(self):
        self.id: Optional[int] = None
        self.project_id: int = 0
        self.parent_id: Optional[int] = None
        self.name: str = ""
        self.description: str = ""
        self.sort_order: int = 0
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None


class CaseFolder(DataModel):
    """用例文件夹模型"""

    def __init__(self):
        self.id: Optional[int] = None
        self.project_id: int = 0
        self.parent_id: Optional[int] = None
        self.name: str = ""
        self.description: str = ""
        self.sort_order: int = 0
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None


class UserSetting(DataModel):
    """用户设置模型"""

    def __init__(self):
        self.id: Optional[int] = None
        self.user_id: str = ""
        self.setting_key: str = ""
        self.setting_value: Dict[str, Any] = {}
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None


def initialize_database():
    """初始化数据库"""
    db = Database()

    # 创建表结构
    db.init_database()

    # 插入初始数据
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                for table_name, data_list in INITIAL_DATA.items():
                    # 检查表是否为空
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                    count = cursor.fetchone()['count']

                    if count == 0:
                        print(f"插入初始数据到 {table_name}")
                        for data in data_list:
                            # 处理JSON字段
                            processed_data = {}
                            for key, value in data.items():
                                if isinstance(value, (dict, list)):
                                    processed_data[key] = json.dumps(value, cls=JSONEncoder)
                                else:
                                    processed_data[key] = value

                            columns = ', '.join(processed_data.keys())
                            placeholders = ', '.join(['%s'] * len(processed_data))
                            sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                            cursor.execute(sql, list(processed_data.values()))

                conn.commit()
                print("初始数据插入完成")

    except Exception as e:
        print(f"插入初始数据失败: {e}")


# 应用启动时自动初始化数据库
if __name__ == "__main__":
    initialize_database()