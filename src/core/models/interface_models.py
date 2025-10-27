from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
import json

@dataclass
class ApiTemplate:
    """接口模板数据模型"""

    id: Optional[int] = None
    project_id: int = 0
    folder_id: Optional[int] = None
    name: str = ""
    method: str = "GET"
    url_path: str = ""
    headers: Dict[str, Any] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    body: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    timeout: int = 30
    retry_enabled: bool = False
    retry_count: int = 3
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApiTemplate':
        """从字典创建对象"""
        # 处理JSON字段
        headers = data.get('headers', {})
        if isinstance(headers, str):
            try:
                headers = json.loads(headers) if headers else {}
            except json.JSONDecodeError:
                headers = {}

        params = data.get('params', {})
        if isinstance(params, str):
            try:
                params = json.loads(params) if params else {}
            except json.JSONDecodeError:
                params = {}

        body = data.get('body', {})
        if isinstance(body, str):
            try:
                body = json.loads(body) if body else {}
            except json.JSONDecodeError:
                body = {}

        # 处理时间字段
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = None

        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                updated_at = None

        return cls(
            id=data.get('id'),
            project_id=data.get('project_id', 0),
            folder_id=data.get('folder_id'),
            name=data.get('name', ''),
            method=data.get('method', 'GET'),
            url_path=data.get('url_path', ''),
            headers=headers,
            params=params,
            body=body,
            description=data.get('description', ''),
            timeout=data.get('timeout', 30),
            retry_enabled=bool(data.get('retry_enabled', False)),
            retry_count=data.get('retry_count', 3),
            created_at=created_at,
            updated_at=updated_at
        )

    def to_dict(self, for_db: bool = False) -> Dict[str, Any]:
        """转换为字典

        Args:
            for_db: 如果为True，则转换为数据库存储格式（JSON字段转为字符串）
        """
        result = {
            'id': self.id,
            'project_id': self.project_id,
            'folder_id': self.folder_id,
            'name': self.name,
            'method': self.method,
            'url_path': self.url_path,
            'headers': self.headers,
            'params': self.params,
            'body': self.body,
            'description': self.description,
            'timeout': self.timeout,
            'retry_enabled': self.retry_enabled,
            'retry_count': self.retry_count,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

        if for_db:
            # 将JSON字段转换为字符串
            for field in ['headers', 'params', 'body']:
                if result[field]:
                    result[field] = json.dumps(result[field], ensure_ascii=False)
                else:
                    result[field] = '{}'

        return result

    def validate(self) -> tuple[bool, str]:
        """验证数据有效性

        Returns:
            (是否有效, 错误消息)
        """
        if not self.name.strip():
            return False, "接口名称不能为空"

        if not self.url_path.strip():
            return False, "URL路径不能为空"

        if self.method.upper() not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
            return False, f"不支持的HTTP方法: {self.method}"

        if self.timeout <= 0:
            return False, "超时时间必须大于0"

        if self.retry_enabled and (self.retry_count <= 0 or self.retry_count > 10):
            return False, "重试次数必须在1-10之间"

        # 验证URL路径格式
        if not self.url_path.startswith('/'):
            return False, "URL路径必须以/开头"

        # 验证JSON字段
        try:
            json.dumps(self.headers)
            json.dumps(self.params)
            json.dumps(self.body)
        except (TypeError, ValueError) as e:
            return False, f"JSON格式错误: {str(e)}"

        return True, ""

    def get_full_url(self, base_url: str = "") -> str:
        """获取完整URL

        Args:
            base_url: 基础URL，如 http://api.example.com

        Returns:
            完整URL
        """
        if base_url:
            # 移除base_url末尾的/和url_path开头的/，避免双斜杠
            base_url = base_url.rstrip('/')
            url_path = self.url_path.lstrip('/')
            return f"{base_url}/{url_path}"
        else:
            return self.url_path

    def clone(self) -> 'ApiTemplate':
        """创建副本"""
        return ApiTemplate(
            id=None,  # 新副本没有ID
            project_id=self.project_id,
            folder_id=self.folder_id,
            name=f"{self.name}_副本",
            method=self.method,
            url_path=self.url_path,
            headers=self.headers.copy(),
            params=self.params.copy(),
            body=self.body.copy(),
            description=self.description,
            timeout=self.timeout,
            retry_enabled=self.retry_enabled,
            retry_count=self.retry_count,
            created_at=None,
            updated_at=None
        )

    def __str__(self) -> str:
        return f"ApiTemplate(id={self.id}, name='{self.name}', method='{self.method}', url='{self.url_path}')"

    def __repr__(self) -> str:
        return self.__str__()


@dataclass
class ApiFolder:
    """接口文件夹数据模型"""

    id: Optional[int] = None
    project_id: int = 0
    parent_id: Optional[int] = None
    name: str = ""
    description: str = ""
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    children: List['ApiFolder'] = field(default_factory=list)  # 子文件夹
    templates: List[ApiTemplate] = field(default_factory=list)  # 包含的接口模板

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApiFolder':
        """从字典创建对象"""
        # 处理时间字段
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = None

        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                updated_at = None

        return cls(
            id=data.get('id'),
            project_id=data.get('project_id', 0),
            parent_id=data.get('parent_id'),
            name=data.get('name', ''),
            description=data.get('description', ''),
            sort_order=data.get('sort_order', 0),
            created_at=created_at,
            updated_at=updated_at,
            children=[],
            templates=[]
        )

    def to_dict(self, for_db: bool = False) -> Dict[str, Any]:
        """转换为字典

        Args:
            for_db: 如果为True，则转换为数据库存储格式
        """
        result = {
            'id': self.id,
            'project_id': self.project_id,
            'parent_id': self.parent_id,
            'name': self.name,
            'description': self.description,
            'sort_order': self.sort_order,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

        if not for_db:
            # 添加嵌套数据
            result['children'] = [child.to_dict() for child in self.children]
            result['templates'] = [template.to_dict() for template in self.templates]
            result['template_count'] = len(self.templates)
            result['child_folder_count'] = len(self.children)

        return result

    def validate(self) -> tuple[bool, str]:
        """验证数据有效性

        Returns:
            (是否有效, 错误消息)
        """
        if not self.name.strip():
            return False, "文件夹名称不能为空"

        if len(self.name) > 100:
            return False, "文件夹名称不能超过100个字符"

        if self.sort_order < 0:
            return False, "排序顺序不能为负数"

        return True, ""

    def add_child(self, child_folder: 'ApiFolder') -> None:
        """添加子文件夹"""
        self.children.append(child_folder)

    def add_template(self, template: ApiTemplate) -> None:
        """添加接口模板"""
        self.templates.append(template)

    def get_all_templates(self) -> List[ApiTemplate]:
        """获取文件夹及其所有子文件夹中的所有接口模板"""
        all_templates = self.templates.copy()
        for child in self.children:
            all_templates.extend(child.get_all_templates())
        return all_templates

    def get_all_children(self) -> List['ApiFolder']:
        """获取所有子文件夹（包括嵌套子文件夹）"""
        all_children = self.children.copy()
        for child in self.children:
            all_children.extend(child.get_all_children())
        return all_children

    def find_template_by_id(self, template_id: int) -> Optional[ApiTemplate]:
        """根据ID查找接口模板"""
        for template in self.templates:
            if template.id == template_id:
                return template
        for child in self.children:
            found = child.find_template_by_id(template_id)
            if found:
                return found
        return None

    def find_folder_by_id(self, folder_id: int) -> Optional['ApiFolder']:
        """根据ID查找文件夹"""
        if self.id == folder_id:
            return self
        for child in self.children:
            found = child.find_folder_by_id(folder_id)
            if found:
                return found
        return None

    def get_path(self, folder_map: Dict[int, 'ApiFolder'] = None) -> str:
        """获取文件夹路径"""
        if folder_map is None:
            return self.name

        path_parts = [self.name]
        current = self

        while current.parent_id and current.parent_id in folder_map:
            current = folder_map[current.parent_id]
            path_parts.insert(0, current.name)

        return '/'.join(path_parts)

    def __str__(self) -> str:
        return f"ApiFolder(id={self.id}, name='{self.name}', project_id={self.project_id})"

    def __repr__(self) -> str:
        return self.__str__()


class ApiTemplateManager:
    """接口模板管理器"""

    def __init__(self):
        self.folders: List[ApiFolder] = []
        self.templates: List[ApiTemplate] = []
        self.folder_map: Dict[int, ApiFolder] = {}  # ID到文件夹的映射

    def build_tree(self, folders_data: List[Dict], templates_data: List[Dict]) -> List[ApiFolder]:
        """构建文件夹树结构

        Args:
            folders_data: 文件夹数据列表
            templates_data: 接口模板数据列表

        Returns:
            根文件夹列表
        """
        # 清空现有数据
        self.folders.clear()
        self.templates.clear()
        self.folder_map.clear()

        # 创建文件夹对象
        for folder_data in folders_data:
            folder = ApiFolder.from_dict(folder_data)
            self.folders.append(folder)
            self.folder_map[folder.id] = folder

        # 构建文件夹树
        root_folders = []
        for folder in self.folders:
            if folder.parent_id is None:
                root_folders.append(folder)
            else:
                parent = self.folder_map.get(folder.parent_id)
                if parent:
                    parent.add_child(folder)

        # 添加接口模板到对应文件夹
        for template_data in templates_data:
            template = ApiTemplate.from_dict(template_data)
            self.templates.append(template)

            folder_id = template.folder_id
            if folder_id and folder_id in self.folder_map:
                self.folder_map[folder_id].add_template(template)

        return root_folders

    def find_template(self, template_id: int) -> Optional[ApiTemplate]:
        """根据ID查找接口模板"""
        for template in self.templates:
            if template.id == template_id:
                return template
        return None

    def find_folder(self, folder_id: int) -> Optional[ApiFolder]:
        """根据ID查找文件夹"""
        return self.folder_map.get(folder_id)

    def get_templates_by_project(self, project_id: int) -> List[ApiTemplate]:
        """根据项目ID获取所有接口模板"""
        return [t for t in self.templates if t.project_id == project_id]

    def get_folders_by_project(self, project_id: int) -> List[ApiFolder]:
        """根据项目ID获取所有文件夹"""
        return [f for f in self.folders if f.project_id == project_id]

    def add_template(self, template: ApiTemplate) -> None:
        """添加接口模板"""
        self.templates.append(template)

        # 如果有关联文件夹，添加到文件夹中
        if template.folder_id and template.folder_id in self.folder_map:
            self.folder_map[template.folder_id].add_template(template)

    def add_folder(self, folder: ApiFolder) -> None:
        """添加文件夹"""
        self.folders.append(folder)
        self.folder_map[folder.id] = folder

        # 如果有父文件夹，添加到父文件夹的子列表中
        if folder.parent_id and folder.parent_id in self.folder_map:
            self.folder_map[folder.parent_id].add_child(folder)

    def remove_template(self, template_id: int) -> bool:
        """移除接口模板"""
        template = self.find_template(template_id)
        if template:
            self.templates.remove(template)

            # 从文件夹中移除
            if template.folder_id and template.folder_id in self.folder_map:
                folder = self.folder_map[template.folder_id]
                folder.templates = [t for t in folder.templates if t.id != template_id]

            return True
        return False

    def remove_folder(self, folder_id: int) -> bool:
        """移除文件夹"""
        folder = self.find_folder(folder_id)
        if folder:
            # 先移除所有子文件夹和模板
            for child in folder.get_all_children():
                self.folders.remove(child)
                self.folder_map.pop(child.id, None)

            for template in folder.get_all_templates():
                self.templates.remove(template)

            # 从父文件夹中移除
            if folder.parent_id and folder.parent_id in self.folder_map:
                parent = self.folder_map[folder.parent_id]
                parent.children = [c for c in parent.children if c.id != folder_id]

            # 移除文件夹本身
            self.folders.remove(folder)
            self.folder_map.pop(folder_id, None)

            return True
        return False


@dataclass
class GlobalTool:
    """全局工具数据模型"""

    id: Optional[int] = None
    name: str = ""
    tool_type: str = ""  # sql, random, python, timer, http, custom
    description: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_by: str = "admin"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GlobalTool':
        """从字典创建对象"""
        # 处理JSON字段
        config = data.get('config', {})
        if isinstance(config, str):
            try:
                config = json.loads(config) if config else {}
            except json.JSONDecodeError:
                config = {}

        # 处理时间字段
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = None

        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                updated_at = None

        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            tool_type=data.get('tool_type', ''),
            description=data.get('description', ''),
            config=config,
            enabled=bool(data.get('enabled', True)),
            created_by=data.get('created_by', 'admin'),
            created_at=created_at,
            updated_at=updated_at
        )

    def to_dict(self, for_db: bool = False) -> Dict[str, Any]:
        """转换为字典

        Args:
            for_db: 如果为True，则转换为数据库存储格式（JSON字段转为字符串）
        """
        result = {
            'id': self.id,
            'name': self.name,
            'tool_type': self.tool_type,
            'description': self.description,
            'config': self.config,
            'enabled': self.enabled,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

        if for_db:
            # 将JSON字段转换为字符串
            if result['config']:
                result['config'] = json.dumps(result['config'], ensure_ascii=False)
            else:
                result['config'] = '{}'

        return result

    def validate(self) -> tuple[bool, str]:
        """验证数据有效性

        Returns:
            (是否有效, 错误消息)
        """
        if not self.name.strip():
            return False, "工具名称不能为空"

        if self.tool_type not in ['sql', 'random', 'python', 'timer', 'http', 'custom']:
            return False, f"不支持的工具类型: {self.tool_type}"

        if len(self.name) > 100:
            return False, "工具名称不能超过100个字符"

        if len(self.description) > 500:
            return False, "工具描述不能超过500个字符"

        # 验证配置字段
        try:
            json.dumps(self.config)
        except (TypeError, ValueError) as e:
            return False, f"配置格式错误: {str(e)}"

        return True, ""

    def get_tool_type_display(self) -> str:
        """获取工具类型显示名称"""
        type_map = {
            'sql': 'SQL查询工具',
            'random': '随机数生成器',
            'python': 'Python脚本执行器',
            'timer': '等待定时器',
            'http': 'HTTP请求工具',
            'custom': '自定义工具'
        }
        return type_map.get(self.tool_type, self.tool_type)

    def clone(self) -> 'GlobalTool':
        """创建副本"""
        return GlobalTool(
            id=None,  # 新副本没有ID
            name=f"{self.name}_副本",
            tool_type=self.tool_type,
            description=self.description,
            config=self.config.copy(),
            enabled=self.enabled,
            created_by=self.created_by,
            created_at=None,
            updated_at=None
        )

    def __str__(self) -> str:
        return f"GlobalTool(id={self.id}, name='{self.name}', type='{self.tool_type}')"

    def __repr__(self) -> str:
        return self.__str__()


@dataclass
class TestReport:
    """测试报告数据模型"""

    id: Optional[int] = None
    scheduler_id: Optional[int] = None
    case_id: int = 0
    report_name: str = ""
    status: str = "running"  # success, failure, error, running
    total_steps: int = 0
    passed_steps: int = 0
    failed_steps: int = 0
    error_steps: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    log_path: str = ""
    created_at: Optional[datetime] = None

    # 关联数据（非数据库字段）
    case_name: str = ""
    scheduler_name: str = ""
    steps: List['TestStepResult'] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestReport':
        """从字典创建对象"""
        # 处理时间字段
        start_time = data.get('start_time')
        if isinstance(start_time, str):
            try:
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                start_time = None

        end_time = data.get('end_time')
        if isinstance(end_time, str):
            try:
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                end_time = None

        created_at = data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = None

        # 处理步骤数据
        steps_data = data.get('steps', [])
        steps = [TestStepResult.from_dict(step_data) for step_data in steps_data]

        return cls(
            id=data.get('id'),
            scheduler_id=data.get('scheduler_id'),
            case_id=data.get('case_id', 0),
            report_name=data.get('report_name', ''),
            status=data.get('status', 'running'),
            total_steps=data.get('total_steps', 0),
            passed_steps=data.get('passed_steps', 0),
            failed_steps=data.get('failed_steps', 0),
            error_steps=data.get('error_steps', 0),
            start_time=start_time,
            end_time=end_time,
            duration=data.get('duration', 0.0),
            log_path=data.get('log_path', ''),
            created_at=created_at,
            case_name=data.get('case_name', ''),
            scheduler_name=data.get('scheduler_name', ''),
            steps=steps
        )

    def to_dict(self, for_db: bool = False) -> Dict[str, Any]:
        """转换为字典

        Args:
            for_db: 如果为True，则转换为数据库存储格式
        """
        result = {
            'id': self.id,
            'scheduler_id': self.scheduler_id,
            'case_id': self.case_id,
            'report_name': self.report_name,
            'status': self.status,
            'total_steps': self.total_steps,
            'passed_steps': self.passed_steps,
            'failed_steps': self.failed_steps,
            'error_steps': self.error_steps,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'log_path': self.log_path,
            'created_at': self.created_at
        }

        if not for_db:
            # 添加关联数据
            result['case_name'] = self.case_name
            result['scheduler_name'] = self.scheduler_name
            result['steps'] = [step.to_dict() for step in self.steps]

        return result

    def validate(self) -> tuple[bool, str]:
        """验证数据有效性"""
        if not self.report_name.strip():
            return False, "报告名称不能为空"

        if self.status not in ['success', 'failure', 'error', 'running']:
            return False, f"无效的状态: {self.status}"

        if self.total_steps < 0:
            return False, "总步骤数不能为负数"

        if self.passed_steps < 0 or self.failed_steps < 0 or self.error_steps < 0:
            return False, "步骤统计数不能为负数"

        if self.total_steps != (self.passed_steps + self.failed_steps + self.error_steps):
            return False, "步骤统计数不匹配"

        if self.duration < 0:
            return False, "执行时长不能为负数"

        return True, ""

    def get_status_display(self) -> str:
        """获取状态显示名称"""
        status_map = {
            'success': '成功',
            'failure': '失败',
            'error': '错误',
            'running': '执行中'
        }
        return status_map.get(self.status, self.status)

    def get_success_rate(self) -> float:
        """计算通过率"""
        if self.total_steps == 0:
            return 0.0
        return (self.passed_steps / self.total_steps) * 100

    def is_completed(self) -> bool:
        """检查是否已完成"""
        return self.status in ['success', 'failure', 'error']

    def get_execution_time(self) -> str:
        """获取执行时间字符串"""
        if self.start_time and self.end_time:
            return f"{self.start_time.strftime('%Y-%m-%d %H:%M:%S')} - {self.end_time.strftime('%H:%M:%S')}"
        elif self.start_time:
            return f"{self.start_time.strftime('%Y-%m-%d %H:%M:%S')} - 进行中"
        else:
            return "未开始"

    def add_step_result(self, step_result: 'TestStepResult'):
        """添加步骤结果"""
        self.steps.append(step_result)
        # 更新统计信息
        self._update_stats()

    def _update_stats(self):
        """更新统计信息"""
        self.total_steps = len(self.steps)
        self.passed_steps = len([s for s in self.steps if s.status == 'success'])
        self.failed_steps = len([s for s in self.steps if s.status == 'failure'])
        self.error_steps = len([s for s in self.steps if s.status == 'error'])

        # 更新总体状态
        if self.error_steps > 0:
            self.status = 'error'
        elif self.failed_steps > 0:
            self.status = 'failure'
        elif self.passed_steps == self.total_steps:
            self.status = 'success'
        else:
            self.status = 'running'

    def __str__(self) -> str:
        return f"TestReport(id={self.id}, name='{self.report_name}', status='{self.status}')"

    def __repr__(self) -> str:
        return self.__str__()


@dataclass
class TestStepResult:
    """测试步骤结果数据模型"""

    id: Optional[int] = None
    report_id: int = 0
    step_id: int = 0
    step_order: int = 0
    status: str = "skipped"  # success, failure, error, skipped
    request_data: Dict[str, Any] = field(default_factory=dict)
    response_data: Dict[str, Any] = field(default_factory=dict)
    assertions_result: Dict[str, Any] = field(default_factory=dict)
    variables_snapshot: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    created_at: Optional[datetime] = None

    # 关联数据（非数据库字段）
    api_name: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestStepResult':
        """从字典创建对象"""
        # 处理JSON字段
        request_data = data.get('request_data', {})
        if isinstance(request_data, str):
            try:
                request_data = json.loads(request_data) if request_data else {}
            except json.JSONDecodeError:
                request_data = {}

        response_data = data.get('response_data', {})
        if isinstance(response_data, str):
            try:
                response_data = json.loads(response_data) if response_data else {}
            except json.JSONDecodeError:
                response_data = {}

        assertions_result = data.get('assertions_result', {})
        if isinstance(assertions_result, str):
            try:
                assertions_result = json.loads(assertions_result) if assertions_result else {}
            except json.JSONDecodeError:
                assertions_result = {}

        variables_snapshot = data.get('variables_snapshot', {})
        if isinstance(variables_snapshot, str):
            try:
                variables_snapshot = json.loads(variables_snapshot) if variables_snapshot else {}
            except json.JSONDecodeError:
                variables_snapshot = {}

        # 处理时间字段
        start_time = data.get('start_time')
        if isinstance(start_time, str):
            try:
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                start_time = None

        end_time = data.get('end_time')
        if isinstance(end_time, str):
            try:
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                end_time = None

        created_at = data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = None

        return cls(
            id=data.get('id'),
            report_id=data.get('report_id', 0),
            step_id=data.get('step_id', 0),
            step_order=data.get('step_order', 0),
            status=data.get('status', 'skipped'),
            request_data=request_data,
            response_data=response_data,
            assertions_result=assertions_result,
            variables_snapshot=variables_snapshot,
            error_message=data.get('error_message', ''),
            start_time=start_time,
            end_time=end_time,
            duration=data.get('duration', 0.0),
            created_at=created_at,
            api_name=data.get('api_name', '')
        )

    def to_dict(self, for_db: bool = False) -> Dict[str, Any]:
        """转换为字典

        Args:
            for_db: 如果为True，则转换为数据库存储格式（JSON字段转为字符串）
        """
        result = {
            'id': self.id,
            'report_id': self.report_id,
            'step_id': self.step_id,
            'step_order': self.step_order,
            'status': self.status,
            'request_data': self.request_data,
            'response_data': self.response_data,
            'assertions_result': self.assertions_result,
            'variables_snapshot': self.variables_snapshot,
            'error_message': self.error_message,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'created_at': self.created_at
        }

        if for_db:
            # 将JSON字段转换为字符串
            json_fields = ['request_data', 'response_data', 'assertions_result', 'variables_snapshot']
            for field in json_fields:
                if result[field]:
                    result[field] = json.dumps(result[field], ensure_ascii=False)
                else:
                    result[field] = '{}'

        if not for_db:
            # 添加关联数据
            result['api_name'] = self.api_name

        return result

    def validate(self) -> tuple[bool, str]:
        """验证数据有效性"""
        if self.status not in ['success', 'failure', 'error', 'skipped']:
            return False, f"无效的状态: {self.status}"

        if self.duration < 0:
            return False, "执行时长不能为负数"

        if self.step_order < 0:
            return False, "步骤顺序不能为负数"

        # 验证JSON字段
        try:
            json.dumps(self.request_data)
            json.dumps(self.response_data)
            json.dumps(self.assertions_result)
            json.dumps(self.variables_snapshot)
        except (TypeError, ValueError) as e:
            return False, f"JSON格式错误: {str(e)}"

        return True, ""

    def get_status_display(self) -> str:
        """获取状态显示名称"""
        status_map = {
            'success': '成功',
            'failure': '失败',
            'error': '错误',
            'skipped': '跳过'
        }
        return status_map.get(self.status, self.status)

    def is_completed(self) -> bool:
        """检查是否已完成"""
        return self.status in ['success', 'failure', 'error']

    def get_execution_time(self) -> str:
        """获取执行时间字符串"""
        if self.start_time and self.end_time:
            return f"{self.start_time.strftime('%H:%M:%S')} - {self.end_time.strftime('%H:%M:%S')}"
        elif self.start_time:
            return f"{self.start_time.strftime('%H:%M:%S')} - 进行中"
        else:
            return "未开始"

    def set_success(self, response_data: Dict[str, Any] = None, assertions_result: Dict[str, Any] = None):
        """设置为成功状态"""
        self.status = 'success'
        self.end_time = datetime.now()
        if response_data:
            self.response_data = response_data
        if assertions_result:
            self.assertions_result = assertions_result
        self._calculate_duration()

    def set_failure(self, error_message: str = "", assertions_result: Dict[str, Any] = None):
        """设置为失败状态"""
        self.status = 'failure'
        self.end_time = datetime.now()
        self.error_message = error_message
        if assertions_result:
            self.assertions_result = assertions_result
        self._calculate_duration()

    def set_error(self, error_message: str = ""):
        """设置为错误状态"""
        self.status = 'error'
        self.end_time = datetime.now()
        self.error_message = error_message
        self._calculate_duration()

    def set_skipped(self, reason: str = ""):
        """设置为跳过状态"""
        self.status = 'skipped'
        self.end_time = datetime.now()
        self.error_message = reason
        self._calculate_duration()

    def _calculate_duration(self):
        """计算执行时长"""
        if self.start_time and self.end_time:
            self.duration = (self.end_time - self.start_time).total_seconds()

    def __str__(self) -> str:
        return f"TestStepResult(id={self.id}, step={self.step_order}, status='{self.status}')"

    def __repr__(self) -> str:
        return self.__str__()


@dataclass
class TestScheduler:
    """测试调度数据模型"""

    id: Optional[int] = None
    name: str = ""
    description: str = ""
    cron_expression: str = ""
    enabled: bool = True
    case_ids: List[int] = field(default_factory=list)
    notify_emails: List[str] = field(default_factory=list)
    notify_wechat: Dict[str, Any] = field(default_factory=dict)
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_by: str = "admin"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 关联数据（非数据库字段）
    cases: List['TestCase'] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestScheduler':
        """从字典创建对象"""
        # 处理JSON字段
        case_ids = data.get('case_ids', [])
        if isinstance(case_ids, str):
            try:
                case_ids = json.loads(case_ids) if case_ids else []
            except json.JSONDecodeError:
                case_ids = []

        notify_emails = data.get('notify_emails', [])
        if isinstance(notify_emails, str):
            try:
                notify_emails = json.loads(notify_emails) if notify_emails else []
            except json.JSONDecodeError:
                notify_emails = []

        notify_wechat = data.get('notify_wechat', {})
        if isinstance(notify_wechat, str):
            try:
                notify_wechat = json.loads(notify_wechat) if notify_wechat else {}
            except json.JSONDecodeError:
                notify_wechat = {}

        # 处理时间字段
        last_run_at = data.get('last_run_at')
        if isinstance(last_run_at, str):
            try:
                last_run_at = datetime.fromisoformat(last_run_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                last_run_at = None

        next_run_at = data.get('next_run_at')
        if isinstance(next_run_at, str):
            try:
                next_run_at = datetime.fromisoformat(next_run_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                next_run_at = None

        created_at = data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = None

        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                updated_at = None

        # 处理关联数据
        cases_data = data.get('cases', [])
        cases = [TestCase.from_dict(case_data) for case_data in cases_data]

        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            description=data.get('description', ''),
            cron_expression=data.get('cron_expression', ''),
            enabled=bool(data.get('enabled', True)),
            case_ids=case_ids,
            notify_emails=notify_emails,
            notify_wechat=notify_wechat,
            last_run_at=last_run_at,
            next_run_at=next_run_at,
            created_by=data.get('created_by', 'admin'),
            created_at=created_at,
            updated_at=updated_at,
            cases=cases
        )

    def to_dict(self, for_db: bool = False) -> Dict[str, Any]:
        """转换为字典

        Args:
            for_db: 如果为True，则转换为数据库存储格式（JSON字段转为字符串）
        """
        result = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'cron_expression': self.cron_expression,
            'enabled': self.enabled,
            'case_ids': self.case_ids,
            'notify_emails': self.notify_emails,
            'notify_wechat': self.notify_wechat,
            'last_run_at': self.last_run_at,
            'next_run_at': self.next_run_at,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

        if for_db:
            # 将JSON字段转换为字符串
            json_fields = ['case_ids', 'notify_emails', 'notify_wechat']
            for field in json_fields:
                if result[field]:
                    result[field] = json.dumps(result[field], ensure_ascii=False)
                else:
                    result[field] = '[]' if field in ['case_ids', 'notify_emails'] else '{}'

        if not for_db:
            # 添加关联数据
            result['cases'] = [case.to_dict() for case in self.cases]
            result['case_count'] = len(self.case_ids)

        return result

    def validate(self) -> tuple[bool, str]:
        """验证数据有效性"""
        if not self.name.strip():
            return False, "调度名称不能为空"

        if not self.cron_expression.strip():
            return False, "Cron表达式不能为空"

        if len(self.name) > 100:
            return False, "调度名称不能超过100个字符"

        if not self.case_ids:
            return False, "至少需要选择一个测试用例"

        # 验证JSON字段
        try:
            json.dumps(self.notify_wechat)
        except (TypeError, ValueError) as e:
            return False, f"微信通知配置格式错误: {str(e)}"

        return True, ""

    def add_case(self, case_id: int):
        """添加测试用例"""
        if case_id not in self.case_ids:
            self.case_ids.append(case_id)

    def remove_case(self, case_id: int):
        """移除测试用例"""
        if case_id in self.case_ids:
            self.case_ids.remove(case_id)

    def get_case_count(self) -> int:
        """获取用例数量"""
        return len(self.case_ids)

    def is_active(self) -> bool:
        """检查是否活跃（已启用且有下次执行时间）"""
        return self.enabled and self.next_run_at is not None

    def should_run_now(self) -> bool:
        """检查是否应该立即执行"""
        if not self.enabled or not self.next_run_at:
            return False
        return self.next_run_at <= datetime.now()

    def __str__(self) -> str:
        return f"TestScheduler(id={self.id}, name='{self.name}', enabled={self.enabled})"

    def __repr__(self) -> str:
        return self.__str__()


@dataclass
class TestCase:
    """测试用例数据模型"""

    id: Optional[int] = None
    project_id: int = 0
    folder_id: Optional[int] = None
    name: str = ""
    description: str = ""
    environment_id: Optional[int] = None
    global_vars: Dict[str, Any] = field(default_factory=dict)
    created_by: str = "admin"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 关联数据（非数据库字段）
    steps: List['TestCaseStep'] = field(default_factory=list)
    environment_name: str = ""
    project_name: str = ""
    folder_name: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCase':
        """从字典创建对象"""
        # 处理JSON字段
        global_vars = data.get('global_vars', {})
        if isinstance(global_vars, str):
            try:
                global_vars = json.loads(global_vars) if global_vars else {}
            except json.JSONDecodeError:
                global_vars = {}

        # 处理时间字段
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = None

        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                updated_at = None

        # 处理步骤数据
        steps_data = data.get('steps', [])
        steps = [TestCaseStep.from_dict(step_data) for step_data in steps_data]

        return cls(
            id=data.get('id'),
            project_id=data.get('project_id', 0),
            folder_id=data.get('folder_id'),
            name=data.get('name', ''),
            description=data.get('description', ''),
            environment_id=data.get('environment_id'),
            global_vars=global_vars,
            created_by=data.get('created_by', 'admin'),
            created_at=created_at,
            updated_at=updated_at,
            steps=steps,
            environment_name=data.get('environment_name', ''),
            project_name=data.get('project_name', ''),
            folder_name=data.get('folder_name', '')
        )

    def to_dict(self, for_db: bool = False) -> Dict[str, Any]:
        """转换为字典

        Args:
            for_db: 如果为True，则转换为数据库存储格式（JSON字段转为字符串）
        """
        result = {
            'id': self.id,
            'project_id': self.project_id,
            'folder_id': self.folder_id,
            'name': self.name,
            'description': self.description,
            'environment_id': self.environment_id,
            'global_vars': self.global_vars,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

        if for_db:
            # 将JSON字段转换为字符串
            if result['global_vars']:
                result['global_vars'] = json.dumps(result['global_vars'], ensure_ascii=False)
            else:
                result['global_vars'] = '{}'

        if not for_db:
            # 添加关联数据
            result['steps'] = [step.to_dict() for step in self.steps]
            result['environment_name'] = self.environment_name
            result['project_name'] = self.project_name
            result['folder_name'] = self.folder_name
            result['step_count'] = len(self.steps)

        return result

    def validate(self) -> tuple[bool, str]:
        """验证数据有效性"""
        if not self.name.strip():
            return False, "用例名称不能为空"

        if len(self.name) > 100:
            return False, "用例名称不能超过100个字符"

        if len(self.description) > 500:
            return False, "用例描述不能超过500个字符"

        # 验证JSON字段
        try:
            json.dumps(self.global_vars)
        except (TypeError, ValueError) as e:
            return False, f"全局变量格式错误: {str(e)}"

        return True, ""

    def add_step(self, step: 'TestCaseStep'):
        """添加测试步骤"""
        step.step_order = len(self.steps)
        self.steps.append(step)

    def remove_step(self, step_id: int):
        """移除测试步骤"""
        self.steps = [step for step in self.steps if step.id != step_id]
        # 重新排序
        for i, step in enumerate(self.steps):
            step.step_order = i

    def get_step_count(self) -> int:
        """获取步骤数量"""
        return len(self.steps)

    def get_enabled_steps(self) -> List['TestCaseStep']:
        """获取启用的步骤"""
        return [step for step in self.steps if step.enabled]

    def move_step(self, from_index: int, to_index: int):
        """移动步骤位置"""
        if 0 <= from_index < len(self.steps) and 0 <= to_index < len(self.steps):
            step = self.steps.pop(from_index)
            self.steps.insert(to_index, step)
            # 重新排序
            for i, step in enumerate(self.steps):
                step.step_order = i

    def clone(self) -> 'TestCase':
        """创建副本"""
        return TestCase(
            id=None,  # 新副本没有ID
            project_id=self.project_id,
            folder_id=self.folder_id,
            name=f"{self.name}_副本",
            description=self.description,
            environment_id=self.environment_id,
            global_vars=self.global_vars.copy(),
            created_by=self.created_by,
            created_at=None,
            updated_at=None,
            steps=[step.clone() for step in self.steps]
        )

    def __str__(self) -> str:
        return f"TestCase(id={self.id}, name='{self.name}', steps={len(self.steps)})"

    def __repr__(self) -> str:
        return self.__str__()


@dataclass
class TestCaseStep:
    """测试用例步骤数据模型"""

    id: Optional[int] = None
    case_id: int = 0
    api_template_id: Optional[int] = None
    step_order: int = 0
    name: str = ""
    enabled: bool = True
    pre_processing: Dict[str, Any] = field(default_factory=dict)
    post_processing: Dict[str, Any] = field(default_factory=dict)
    assertions: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 关联数据（非数据库字段）
    api_name: str = ""
    api_method: str = ""
    api_url_path: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCaseStep':
        """从字典创建对象"""
        # 处理JSON字段
        pre_processing = data.get('pre_processing', {})
        if isinstance(pre_processing, str):
            try:
                pre_processing = json.loads(pre_processing) if pre_processing else {}
            except json.JSONDecodeError:
                pre_processing = {}

        post_processing = data.get('post_processing', {})
        if isinstance(post_processing, str):
            try:
                post_processing = json.loads(post_processing) if post_processing else {}
            except json.JSONDecodeError:
                post_processing = {}

        assertions = data.get('assertions', {})
        if isinstance(assertions, str):
            try:
                assertions = json.loads(assertions) if assertions else {}
            except json.JSONDecodeError:
                assertions = {}

        variables = data.get('variables', {})
        if isinstance(variables, str):
            try:
                variables = json.loads(variables) if variables else {}
            except json.JSONDecodeError:
                variables = {}

        # 处理时间字段
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = None

        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                updated_at = None

        return cls(
            id=data.get('id'),
            case_id=data.get('case_id', 0),
            api_template_id=data.get('api_template_id'),
            step_order=data.get('step_order', 0),
            name=data.get('name', ''),
            enabled=bool(data.get('enabled', True)),
            pre_processing=pre_processing,
            post_processing=post_processing,
            assertions=assertions,
            variables=variables,
            created_at=created_at,
            updated_at=updated_at,
            api_name=data.get('api_name', ''),
            api_method=data.get('api_method', ''),
            api_url_path=data.get('api_url_path', '')
        )

    def to_dict(self, for_db: bool = False) -> Dict[str, Any]:
        """转换为字典

        Args:
            for_db: 如果为True，则转换为数据库存储格式（JSON字段转为字符串）
        """
        result = {
            'id': self.id,
            'case_id': self.case_id,
            'api_template_id': self.api_template_id,
            'step_order': self.step_order,
            'name': self.name,
            'enabled': self.enabled,
            'pre_processing': self.pre_processing,
            'post_processing': self.post_processing,
            'assertions': self.assertions,
            'variables': self.variables,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

        if for_db:
            # 将JSON字段转换为字符串
            json_fields = ['pre_processing', 'post_processing', 'assertions', 'variables']
            for field in json_fields:
                if result[field]:
                    result[field] = json.dumps(result[field], ensure_ascii=False)
                else:
                    result[field] = '{}'

        if not for_db:
            # 添加关联数据
            result['api_name'] = self.api_name
            result['api_method'] = self.api_method
            result['api_url_path'] = self.api_url_path

        return result

    def validate(self) -> tuple[bool, str]:
        """验证数据有效性"""
        if self.step_order < 0:
            return False, "步骤顺序不能为负数"

        if len(self.name) > 100:
            return False, "步骤名称不能超过100个字符"

        # 验证JSON字段
        try:
            json.dumps(self.pre_processing)
            json.dumps(self.post_processing)
            json.dumps(self.assertions)
            json.dumps(self.variables)
        except (TypeError, ValueError) as e:
            return False, f"JSON格式错误: {str(e)}"

        return True, ""

    def get_display_name(self) -> str:
        """获取显示名称"""
        if self.name:
            return self.name
        elif self.api_name:
            return self.api_name
        else:
            return f"步骤 {self.step_order + 1}"

    def has_pre_processing(self) -> bool:
        """检查是否有前置处理"""
        return bool(self.pre_processing)

    def has_post_processing(self) -> bool:
        """检查是否有后置处理"""
        return bool(self.post_processing)

    def has_assertions(self) -> bool:
        """检查是否有断言"""
        return bool(self.assertions)

    def clone(self) -> 'TestCaseStep':
        """创建副本"""
        return TestCaseStep(
            id=None,  # 新副本没有ID
            case_id=self.case_id,
            api_template_id=self.api_template_id,
            step_order=self.step_order,
            name=self.name,
            enabled=self.enabled,
            pre_processing=self.pre_processing.copy(),
            post_processing=self.post_processing.copy(),
            assertions=self.assertions.copy(),
            variables=self.variables.copy(),
            created_at=None,
            updated_at=None
        )

    def __str__(self) -> str:
        return f"TestCaseStep(id={self.id}, order={self.step_order}, name='{self.get_display_name()}')"

    def __repr__(self) -> str:
        return self.__str__()