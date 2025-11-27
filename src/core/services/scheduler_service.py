import sys
import os
import time
import logging
import signal
import traceback
import threading
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.database import Database
from src.utils.interface_utils.cron_parser import CronParser
from src.core.services.test_case_service import TestCaseService
from src.core.services.test_report_service import TestReportService
from src.utils.interface_utils.execute_test_case import ExecuteTestCase
from src.utils.interface_utils.report_generator import HTMLReportGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scheduler_service.log', encoding='utf-8', mode='w')
    ]
)

logger = logging.getLogger("UnifiedSchedulerService")


class UnifiedSchedulerService:
    """统一调度服务"""
    
    def __init__(self):
        self.running = False
        self.check_interval = 5  # 检查间隔（秒）
        
        # 服务状态
        self.start_time = None
        self.execution_count = 0
        self.error_count = 0
        
        # 线程池
        self.thread_pool = []
        self.max_threads = 5
        
        # 正在执行的调度
        self.active_schedulers: Dict[int, threading.Thread] = {}
        
        # 初始化服务组件
        self._initialize_services()
    
    def _initialize_services(self):
        """初始化必要的服务组件"""
        try:
            # 创建数据库连接实例
            self.db = Database()
            self.cron_parser = CronParser()
            self.test_case_service = TestCaseService()
            self.test_report_service = TestReportService()
            
            # 初始化测试执行和报告生成工具
            self.execute_test_case = ExecuteTestCase()
            self.report_generator = HTMLReportGenerator()
            
            logger.info("服务组件初始化成功")
            
        except Exception as e:
            logger.error(f"服务组件初始化失败: {str(e)}")
            raise
    
    def start_service(self):
        """启动服务"""
        if self.running:
            logger.warning("服务已在运行中")
            return False
            
        try:
            # 尝试获取分布式锁
            if not self._acquire_distributed_lock():
                logger.warning("检测到已有调度服务实例在运行，当前实例将作为只读客户端运行")
                self.running = False
                return False
            
            self.running = True
            self.start_time = datetime.now()
            self.execution_count = 0
            self.error_count = 0
            
            logger.info(f"统一调度服务已启动，检查间隔: {self.check_interval}秒")
            logger.info(f"服务启动时间: {self.start_time}")
            logger.info("当前实例持有调度锁")
            
            return True
            
        except Exception as e:
            logger.error(f"启动服务失败: {str(e)}")
            self.running = False
            # 释放锁
            self._release_distributed_lock()
            return False
    
    def stop_service(self):
        """停止服务"""
        if not self.running:
            return
            
        self.running = False
        
        # 停止所有正在执行的调度
        for scheduler_id, thread in self.active_schedulers.items():
            if thread and thread.is_alive():
                logger.info(f"停止调度 {scheduler_id} 的执行线程")
        
        # 等待所有线程完成
        logger.info("等待所有执行线程完成...")
        for thread in self.thread_pool:
            if thread.is_alive():
                thread.join(timeout=10)
        
        service_duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        # 释放分布式锁（确保在服务停止时释放）
        try:
            self._release_distributed_lock()
            logger.info("分布式锁释放完成")
        except Exception as e:
            logger.error(f"释放分布式锁失败: {str(e)}")
            # 即使释放失败也要继续停止流程
        
        logger.info(f"统一调度服务已停止")
        logger.info(f"服务运行时长: {service_duration:.2f}秒")
        logger.info(f"检查次数: {self.execution_count}, 错误次数: {self.error_count}")
    
    def run_service_loop(self):
        """运行服务主循环"""
        logger.info("服务主循环开始运行")
        
        # 等待到整分钟（00秒）再开始运行
        current_time = datetime.now()
        current_second = current_time.second
        wait_seconds = 60 - current_second if current_second > 0 else 0
        
        if wait_seconds > 0:
            logger.info(f"当前时间: {current_time}, 等待 {wait_seconds} 秒到整分钟再开始运行...")
            
            # 精确等待到整分钟
            for i in range(wait_seconds):
                if not self.running:
                    logger.info("服务在等待期间被停止")
                    return
                
                # 计算剩余等待时间
                remaining = wait_seconds - i - 1
                if remaining > 0:
                    # 精确等待1秒
                    time.sleep(1)
                    
                    # 每10秒或最后5秒显示倒计时
                    if (i + 1) % 10 == 0 or remaining <= 5:
                        logger.info(f"等待倒计时: {remaining}秒")
                else:
                    # 最后1秒，精确等待到整秒
                    current_microsecond = datetime.now().microsecond
                    if current_microsecond > 0:
                        # 等待到整秒
                        time.sleep((1000000 - current_microsecond) / 1000000.0)
                    break
        
        # 在等待期间也检查续期（测试用）
        if wait_seconds > 30:  # 如果等待时间超过30秒，在等待期间检查续期
            logger.info("长时间等待期间检查续期逻辑...")
            # 模拟续期检查（此时last_lock_renewal还未初始化，使用服务启动时间作为参考）
            current_time = datetime.now()
            time_since_start = (current_time - self.start_time).total_seconds()
            logger.info(f"等待期间续期检查 - 服务启动时间: {time_since_start:.0f}秒, 需要: 120秒")
        
        # 记录整分钟启动时间
        start_time = datetime.now()
        logger.info(f"整分钟启动时间: {start_time}")
        
        iteration = 0
        last_lock_renewal = datetime.now()
        
        while self.running:
            iteration += 1
            
            try:
                logger.info(f"=== 第 {iteration} 次检查 ===")
                
                # 清理已完成的线程
                self._cleanup_threads()
                
                # 检查并执行调度
                self._check_and_execute_schedulers()
                
                # 记录执行统计
                self.execution_count += 1
                
                # 记录状态
                uptime = (datetime.now() - self.start_time).total_seconds()
                logger.info(f"服务持续运行中 - 检查次数: {self.execution_count}, 错误次数: {self.error_count}, 运行时长: {uptime:.0f}秒")
                
                # 定期续期分布式锁（测试用：每2分钟续期一次）
                current_time = datetime.now()
                time_since_last_renewal = (current_time - last_lock_renewal).total_seconds()
                
                # 调试日志：记录续期检查情况（每30秒记录一次）
                if iteration % 6 == 0:  # 每30秒记录一次（6次循环 * 5秒 = 30秒）
                    logger.info(f"续期检查 - 循环次数: {iteration}, 距离上次续期: {time_since_last_renewal:.0f}秒, 需要: 120秒")
                
                if time_since_last_renewal >= 120:  # 测试用：2分钟
                    logger.info(f"触发分布式锁续期 - 距离上次续期: {time_since_last_renewal:.0f}秒")
                    if self._renew_distributed_lock():
                        logger.info("分布式锁续期成功")
                        last_lock_renewal = current_time
                    else:
                        logger.error("分布式锁续期失败，服务将停止")
                        self.running = False
                        break
                
                # 等待下一次检查
                logger.info(f"等待 {self.check_interval} 秒后再次检查...")
                
                # 分段等待，便于及时响应停止信号
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                self.error_count += 1
                logger.error(f"第 {iteration} 次检查异常 (错误#{self.error_count}): {str(e)}")
                logger.debug(f"异常详情: {traceback.format_exc()}")
                
                # 错误后短暂等待再继续
                if self.running:
                    time.sleep(5)
        
        logger.info("服务主循环正常退出")
    
    def _cleanup_threads(self):
        """清理已完成的线程"""
        active_threads = []
        for thread in self.thread_pool:
            if thread.is_alive():
                active_threads.append(thread)
            else:
                logger.debug(f"清理已完成线程: {thread.name}")
        
        self.thread_pool = active_threads
        
        # 清理已完成的调度记录
        completed_schedulers = []
        for scheduler_id, thread in self.active_schedulers.items():
            if not thread.is_alive():
                completed_schedulers.append(scheduler_id)
        
        for scheduler_id in completed_schedulers:
            del self.active_schedulers[scheduler_id]
        
        if len(self.thread_pool) > 0:
            logger.info(f"当前活跃线程数: {len(self.thread_pool)}, 活跃调度数: {len(self.active_schedulers)}")
    
    def _check_and_execute_schedulers(self):
        """检查并执行符合条件的调度"""
        try:
            # 获取所有启用的调度
            schedulers = self._get_all_schedulers()
            enabled_schedulers = [s for s in schedulers if s.get('enabled', False)]
            
            current_time = datetime.now()
            
            logger.info(f"检查时间: {current_time}, 启用的调度数量: {len(enabled_schedulers)}")
            
            execution_count = 0
            
            for scheduler in enabled_schedulers:
                scheduler_id = scheduler['id']
                scheduler_name = scheduler['name']
                cron_expression = scheduler.get('cron_expression', '')
                
                if not cron_expression:
                    logger.warning(f"调度 {scheduler_name} (ID: {scheduler_id}) 没有Cron表达式，跳过")
                    continue
                
                # 检查调度是否正在执行
                if scheduler_id in self.active_schedulers:
                    thread = self.active_schedulers[scheduler_id]
                    if thread and thread.is_alive():
                        logger.warning(f"调度 {scheduler_name} (ID: {scheduler_id}) 正在执行中，跳过本次执行")
                        continue
                
                # 计算下次执行时间
                next_run = self.cron_parser.get_next_run(cron_expression)
                
                logger.info(f"调度 {scheduler_name} - Cron: {cron_expression}, 下次执行: {next_run}")
                
                # 如果下次执行时间早于当前时间，说明需要执行
                # 添加时间窗口容错（5秒），避免错过精确执行时间
                time_window = timedelta(seconds=5)
                if next_run and (next_run <= current_time or 
                               (next_run - current_time <= time_window and next_run >= current_time - time_window)):
                    logger.info(f"调度 {scheduler_name} (ID: {scheduler_id}) 需要执行")
                    
                    # 检查线程池容量
                    if len(self.thread_pool) >= self.max_threads:
                        logger.warning(f"线程池已满，跳过调度 {scheduler_name}")
                        continue
                    
                    # 创建执行线程
                    thread = threading.Thread(
                        target=self._execute_scheduler_thread,
                        args=(scheduler,),
                        name=f"Scheduler-{scheduler_id}"
                    )
                    thread.daemon = True
                    thread.start()
                    
                    self.thread_pool.append(thread)
                    self.active_schedulers[scheduler_id] = thread
                    execution_count += 1
                    
                    logger.info(f"调度 {scheduler_name} 执行线程已启动")
                
            if execution_count > 0:
                logger.info(f"本次检查启动了 {execution_count} 个调度执行线程")
            else:
                logger.info("本次检查没有需要执行的调度")
        
        except Exception as e:
            logger.error(f"检查调度失败: {str(e)}")
            raise
    
    def _execute_scheduler_thread(self, scheduler_data):
        """执行单个调度的线程函数"""
        try:
            scheduler_id = scheduler_data['id']
            scheduler_name = scheduler_data['name']
            
            logger.info(f"开始执行调度: {scheduler_name} (ID: {scheduler_id})")
            
            # 获取调度中配置的测试用例ID列表
            case_ids = scheduler_data.get('case_ids', [])
            if not case_ids:
                logger.warning(f"调度 '{scheduler_name}' 中没有配置测试用例")
                return
            
            logger.info(f"调度 {scheduler_name} 包含 {len(case_ids)} 个测试用例")
            
            # 执行测试用例
            success_count = 0
            total_count = len(case_ids)
            
            # 记录执行开始时间
            execution_start_time = datetime.now()
            
            # 存储每个用例的执行结果
            case_results = []
            
            for i, case_id in enumerate(case_ids):
                try:
                    # 获取测试用例数据
                    case_data = self.test_case_service.get_case_with_steps(case_id)
                    if not case_data:
                        logger.warning(f"测试用例ID {case_id} 不存在，跳过执行")
                        continue
                    
                    case_name = case_data.get('name', '未知用例')
                    logger.info(f"执行测试用例 [{i+1}/{total_count}]: {case_name} (ID: {case_id})")
                    
                    # 使用ExecuteTestCase工具类执行测试用例并生成测试报告
                    execution_result = self.execute_test_case.execute_test_case_unified(
                        case_data, 
                        generate_report=True, 
                        scheduler_id=scheduler_id
                    )
                    
                    if execution_result.get('success'):
                        success_count += 1
                        logger.info(f"测试用例 {case_name} (ID: {case_id}) 执行成功")
                        case_results.append({
                            'case_id': case_id,
                            'case_name': case_name,
                            'success': True,
                            'execution_time': datetime.now()
                        })
                    else:
                        logger.warning(f"测试用例 {case_name} (ID: {case_id}) 执行失败")
                        case_results.append({
                            'case_id': case_id,
                            'case_name': case_name,
                            'success': False,
                            'execution_time': datetime.now()
                        })
                    
                except Exception as e:
                    logger.error(f"执行测试用例ID {case_id} 失败: {str(e)}")
                    case_results.append({
                        'case_id': case_id,
                        'case_name': '未知用例',
                        'success': False,
                        'error': str(e),
                        'execution_time': datetime.now()
                    })
            
            # 记录执行结束时间
            execution_end_time = datetime.now()
            execution_duration = (execution_end_time - execution_start_time).total_seconds()
            
            logger.info(f"调度 {scheduler_name} 执行完成 - 成功: {success_count}/{total_count}, 耗时: {execution_duration:.2f}秒")
            
            # 更新调度执行时间
            try:
                self._update_last_run(scheduler_id)
                self._update_next_run(scheduler_id)
                logger.info(f"调度 {scheduler_name} 执行时间已更新")
            except Exception as e:
                logger.error(f"更新调度执行时间失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"执行调度失败: {str(e)}")
    
    def execute_scheduler(self, scheduler_id):
        """执行指定ID的调度（公共方法，用于UI调用）"""
        try:
            # 获取调度数据
            schedulers = self._get_all_schedulers()
            scheduler_data = None
            for scheduler in schedulers:
                if scheduler['id'] == scheduler_id:
                    scheduler_data = scheduler
                    break
            
            if not scheduler_data:
                error_msg = f"调度ID {scheduler_id} 不存在"
                logger.error(error_msg)
                return False
            
            # 检查调度是否启用
            if not scheduler_data.get('enabled', False):
                error_msg = f"调度 '{scheduler_data['name']}' 未启用，无法执行"
                logger.warning(error_msg)
                return False
            
            # 检查调度是否正在执行
            if scheduler_id in self.active_schedulers:
                thread = self.active_schedulers[scheduler_id]
                if thread and thread.is_alive():
                    logger.warning(f"调度 '{scheduler_data['name']}' 正在执行中，跳过本次执行")
                    return False
            
            # 创建执行线程
            thread = threading.Thread(
                target=self._execute_scheduler_thread,
                args=(scheduler_data,),
                name=f"Manual-Scheduler-{scheduler_id}"
            )
            thread.daemon = True
            thread.start()
            
            self.thread_pool.append(thread)
            self.active_schedulers[scheduler_id] = thread
            
            logger.info(f"手动执行调度 '{scheduler_data['name']}' 已启动")
            return True
            
        except Exception as e:
            error_msg = f"执行调度ID {scheduler_id} 失败: {str(e)}"
            logger.error(error_msg)
            return False
    
    def get_all_schedulers(self):
        """获取所有调度（公共方法，用于UI调用）"""
        return self._get_all_schedulers()

    def get_schedulers_by_project(self, project_id):
        """根据项目ID获取调度任务列表
        
        Args:
            project_id: 项目ID，如果为None或空字符串则返回所有调度任务
            
        Returns:
            List[Dict]: 调度任务列表
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    if project_id:
                        # 按项目筛选
                        cursor.execute("""
                            SELECT id, name, description, cron_expression, enabled, 
                                   case_ids, notify_emails, notify_wechat, 
                                   last_run_at, next_run_at, created_by, created_at, updated_at, project_id
                            FROM test_schedulers 
                            WHERE project_id = %s
                            ORDER BY created_at DESC
                        """, (project_id,))
                    else:
                        # 返回所有调度任务
                        cursor.execute("""
                            SELECT id, name, description, cron_expression, enabled, 
                                   case_ids, notify_emails, notify_wechat, 
                                   last_run_at, next_run_at, created_by, created_at, updated_at, project_id
                            FROM test_schedulers 
                            ORDER BY created_at DESC
                        """)
                    
                    schedulers = cursor.fetchall()
                    
                    # 处理JSON字段
                    for scheduler in schedulers:
                        for field in ['case_ids', 'notify_emails', 'notify_wechat']:
                            if scheduler.get(field):
                                scheduler[field] = json.loads(scheduler[field])
                            else:
                                scheduler[field] = []
                    
                    return schedulers
        except Exception as e:
            logger.error(f"获取项目调度列表失败: {e}")
            return []

    def get_scheduler_by_id(self, scheduler_id):
        """根据ID获取调度（公共方法，用于UI调用）"""
        try:
            schedulers = self._get_all_schedulers()
            for scheduler in schedulers:
                if scheduler['id'] == scheduler_id:
                    return scheduler
            return None
        except Exception as e:
            logger.error(f"获取调度ID {scheduler_id} 失败: {e}")
            return None

    def check_scheduler_name_exists(self, name: str, exclude_scheduler_id: int = None) -> bool:
        """检查调度名称是否已存在
        
        Args:
            name: 调度名称
            exclude_scheduler_id: 排除的调度ID（用于编辑时检查）
            
        Returns:
            bool: 如果名称已存在返回True，否则返回False
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    if exclude_scheduler_id:
                        cursor.execute("""
                            SELECT COUNT(*) as count FROM test_schedulers 
                            WHERE name = %s AND id != %s
                        """, (name, exclude_scheduler_id))
                    else:
                        cursor.execute("""
                            SELECT COUNT(*) as count FROM test_schedulers 
                            WHERE name = %s
                        """, (name,))
                    
                    result = cursor.fetchone()
                    return result['count'] > 0
                    
        except Exception as e:
            logger.error(f"检查调度名称是否存在失败: {e}")
            return False

    def create_scheduler(self, scheduler_data):
        """创建新调度（公共方法，用于UI调用）"""
        try:
            # 检查调度名称是否已存在
            name = scheduler_data.get('name', '')
            if self.check_scheduler_name_exists(name):
                logger.warning(f"调度名称 '{name}' 已存在，创建失败")
                return False
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 构建插入SQL
                    sql = """
                        INSERT INTO test_schedulers 
                        (name, description, cron_expression, enabled, case_ids, 
                         notify_emails, notify_wechat, created_by, created_at, updated_at, project_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s)
                    """
                    
                    # 准备参数
                    params = (
                        name,
                        scheduler_data.get('description', ''),
                        scheduler_data.get('cron_expression', ''),
                        scheduler_data.get('enabled', False),
                        json.dumps(scheduler_data.get('case_ids', [])),
                        json.dumps(scheduler_data.get('notify_emails', [])),
                        json.dumps(scheduler_data.get('notify_wechat', [])),
                        scheduler_data.get('created_by', 'system'),
                        scheduler_data.get('project_id')
                    )
                    
                    cursor.execute(sql, params)
                    conn.commit()
                    
                    logger.info(f"创建调度成功: {name}")
                    return True
                    
        except Exception as e:
            logger.error(f"创建调度失败: {e}")
            return False

    def update_scheduler_status(self, scheduler_id, enabled):
        """更新调度状态（公共方法，用于UI调用）"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE test_schedulers 
                        SET enabled = %s, updated_at = NOW() 
                        WHERE id = %s
                    """, (enabled, scheduler_id))
                    conn.commit()
                    
                    status_text = "启用" if enabled else "禁用"
                    logger.info(f"调度ID {scheduler_id} 状态已更新为: {status_text}")
                    return True
                    
        except Exception as e:
            logger.error(f"更新调度状态失败: {e}")
            return False

    def delete_scheduler(self, scheduler_id):
        """删除调度（公共方法，用于UI调用）"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM test_schedulers 
                        WHERE id = %s
                    """, (scheduler_id,))
                    conn.commit()
                    
                    logger.info(f"删除调度ID {scheduler_id} 成功")
                    return True
                    
        except Exception as e:
            logger.error(f"删除调度失败: {e}")
            return False

    def update_scheduler(self, scheduler_id, scheduler_data):
        """更新调度（公共方法，用于UI调用）"""
        try:
            # 检查调度名称是否已存在（排除当前调度）
            name = scheduler_data.get('name', '')
            if self.check_scheduler_name_exists(name, scheduler_id):
                logger.warning(f"调度名称 '{name}' 已存在，更新失败")
                return False
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 构建更新SQL
                    sql = """
                        UPDATE test_schedulers 
                        SET name = %s, description = %s, cron_expression = %s, 
                            enabled = %s, case_ids = %s, notify_emails = %s, 
                            notify_wechat = %s, project_id = %s, updated_at = NOW()
                        WHERE id = %s
                    """
                    
                    # 准备参数
                    params = (
                        name,
                        scheduler_data.get('description', ''),
                        scheduler_data.get('cron_expression', ''),
                        scheduler_data.get('enabled', False),
                        json.dumps(scheduler_data.get('case_ids', [])),
                        json.dumps(scheduler_data.get('notify_emails', [])),
                        json.dumps(scheduler_data.get('notify_wechat', [])),
                        scheduler_data.get('project_id'),
                        scheduler_id
                    )
                    
                    cursor.execute(sql, params)
                    conn.commit()
                    
                    logger.info(f"更新调度ID {scheduler_id} 成功")
                    return True
                    
        except Exception as e:
            logger.error(f"更新调度失败: {e}")
            return False

    def update_last_run(self, scheduler_id):
        """更新上次执行时间（公共方法，用于UI调用）"""
        try:
            self._update_last_run(scheduler_id)
            logger.info(f"更新调度ID {scheduler_id} 上次执行时间成功")
            return True
        except Exception as e:
            logger.error(f"更新上次执行时间失败: {e}")
            return False

    def _get_all_schedulers(self):
        """获取所有调度"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, name, description, cron_expression, enabled, 
                               case_ids, notify_emails, notify_wechat, 
                               last_run_at, next_run_at, created_by, created_at, updated_at, project_id
                        FROM test_schedulers 
                        ORDER BY created_at DESC
                    """)
                    schedulers = cursor.fetchall()
                    
                    # 处理JSON字段
                    for scheduler in schedulers:
                        for field in ['case_ids', 'notify_emails', 'notify_wechat']:
                            if scheduler.get(field):
                                scheduler[field] = json.loads(scheduler[field])
                            else:
                                scheduler[field] = []
                    
                    return schedulers
        except Exception as e:
            logger.error(f"获取调度列表失败: {e}")
            return []

    def _update_last_run(self, scheduler_id):
        """更新上次执行时间"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE test_schedulers 
                        SET last_run_at = NOW() 
                        WHERE id = %s
                    """, (scheduler_id,))
                    conn.commit()
        except Exception as e:
            logger.error(f"更新上次执行时间失败: {e}")
            raise

    def _acquire_distributed_lock(self):
        """获取分布式锁，确保同一时间只有一个实例执行调度"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 尝试获取锁，锁的有效期为服务运行期间（设置为1小时）
                    lock_timeout = 3600  # 1小时
                    
                    # 使用固定的实例标识（基于主机名和进程ID）
                    import socket
                    import os
                    instance_id = f"{socket.gethostname()}_{os.getpid()}"
                    
                    # 先清理过期的锁（在事务之外执行）
                    cursor.execute("""
                        DELETE FROM distributed_locks 
                        WHERE expires_at < NOW()
                    """)
                    conn.commit()
                    
                    # 使用数据库的FOR UPDATE锁来确保原子性
                    conn.autocommit = False
                    
                    try:
                        # 使用SELECT FOR UPDATE锁定表，防止并发插入
                        cursor.execute("""
                            SELECT instance_id FROM distributed_locks 
                            WHERE lock_key = %s AND expires_at > NOW()
                            FOR UPDATE
                        """, ('scheduler_execution_lock',))
                        
                        existing_lock = cursor.fetchone()
                        
                        if existing_lock:
                            # 已经有其他实例持有锁
                            logger.debug(f"检测到已有调度服务实例在运行，实例ID: {existing_lock['instance_id']}")
                            conn.rollback()
                            return False
                        
                        # 尝试插入新锁记录
                        cursor.execute("""
                            INSERT INTO distributed_locks (lock_key, instance_id, expires_at) 
                            VALUES (%s, %s, NOW() + INTERVAL %s SECOND)
                        """, ('scheduler_execution_lock', instance_id, lock_timeout))
                        
                        conn.commit()
                        logger.info("成功获取分布式锁")
                        return True
                        
                    except Exception as e:
                        conn.rollback()
                        # 插入失败说明锁已被其他实例持有（可能是并发冲突）
                        logger.debug(f"获取分布式锁失败（锁已被其他实例持有）: {e}")
                        return False
                    finally:
                        conn.autocommit = True
                        
        except Exception as e:
            logger.error(f"获取分布式锁时发生异常: {e}")
            return False
    
    def _renew_distributed_lock(self):
        """续期分布式锁"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 使用与获取锁时相同的实例标识
                    import socket
                    import os
                    instance_id = f"{socket.gethostname()}_{os.getpid()}"
                    
                    # 续期锁，延长1小时有效期
                    lock_timeout = 3600  # 1小时
                    
                    cursor.execute("""
                        UPDATE distributed_locks 
                        SET expires_at = NOW() + INTERVAL %s SECOND
                        WHERE lock_key = %s AND instance_id = %s
                    """, (lock_timeout, 'scheduler_execution_lock', instance_id))
                    
                    if cursor.rowcount > 0:
                        conn.commit()
                        logger.debug("分布式锁续期成功")
                        return True
                    else:
                        logger.warning("分布式锁续期失败：锁记录不存在")
                        return False
                        
        except Exception as e:
            logger.error(f"续期分布式锁失败: {e}")
            return False

    def _release_distributed_lock(self):
        """释放分布式锁"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 使用与获取锁时相同的实例标识
                    import socket
                    import os
                    instance_id = f"{socket.gethostname()}_{os.getpid()}"
                    
                    cursor.execute("""
                        DELETE FROM distributed_locks 
                        WHERE lock_key = %s AND instance_id = %s
                    """, ('scheduler_execution_lock', instance_id))
                    conn.commit()
                    logger.info("分布式锁已释放")
        except Exception as e:
            logger.error(f"释放分布式锁失败: {e}")
    
    def _update_next_run(self, scheduler_id):
        """更新下次执行时间"""
        try:
            # 获取调度信息
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT cron_expression FROM test_schedulers WHERE id = %s
                    """, (scheduler_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        cron_expression = result['cron_expression']
                        next_run = self.cron_parser.get_next_run(cron_expression)
                        
                        if next_run:
                            cursor.execute("""
                                UPDATE test_schedulers 
                                SET next_run_at = %s 
                                WHERE id = %s
                            """, (next_run, scheduler_id))
                            conn.commit()
        except Exception as e:
            logger.error(f"更新下次执行时间失败: {e}")
            raise


def signal_handler(signum, frame, service):
    """信号处理函数"""
    logger.info("收到停止信号，正在停止调度服务...")
    service.stop_service()


def main():
    """主函数"""
    service = None
    service_started = False
    
    try:
        # 创建调度服务实例
        service = UnifiedSchedulerService()
        
        # 注册信号处理
        def handle_signal(signum, frame):
            signal_handler(signum, frame, service)
            
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
        
        logger.info("正在启动统一调度服务...")
        
        # 启动服务
        if service.start_service():
            service_started = True
            logger.info("统一调度服务启动成功，按 Ctrl+C 停止服务")
            
            # 运行服务循环
            service.run_service_loop()
            
            logger.info("服务正常停止")
        else:
            logger.error("服务启动失败")
            return 1
            
    except KeyboardInterrupt:
        logger.info("用户中断，正在停止调度服务...")
    except Exception as e:
        logger.error(f"调度服务异常: {str(e)}")
        logger.debug(f"异常详情: {traceback.format_exc()}")
        return 1
    finally:
        # 只有在服务成功启动后才调用stop_service
        if service and service_started:
            service.stop_service()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())