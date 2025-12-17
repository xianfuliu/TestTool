import sys
import os
import time
import logging
import signal
import traceback
import threading
import json
import gc
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("警告: psutil模块未安装，资源监控功能将受限")

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.database import Database
from src.utils.interface_utils.cron_parser import CronParser
from src.core.services.test_case_service import TestCaseService
from src.core.services.test_report_service import TestReportService
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
        self.check_interval = 10  # 检查间隔缩短到0.5秒，提高任务响应及时性
        
        # 服务状态
        self.start_time = None
        self.execution_count = 0
        self.error_count = 0
        
        # 线程池 - 平台级应用优化
        self.thread_pool = []
        self.max_threads = 50  # 增加线程池容量到50，适应高并发任务
        
        # 任务队列，用于处理线程池满时的任务
        self.pending_tasks = []
        self.max_pending_tasks = 100  # 最大待处理任务数增加到100
        
        # 正在执行的调度
        self.active_schedulers: Dict[int, threading.Thread] = {}
        
        # 资源监控配置 - 平台级应用优化
        self.max_memory_mb = 2048  # 最大内存使用限制增加到2GB
        self.max_cpu_percent = 90  # 最大CPU使用率限制增加到90%
        self.memory_check_interval = 15  # 内存检查间隔缩短到15秒，提高监控频率
        self.last_memory_check = datetime.now()
        
        # 任务执行时间限制
        self.max_task_execution_time = 1800  # 单个任务最大执行时间增加到30分钟
        
        # 资源使用统计
        self.memory_usage_history = []
        self.cpu_usage_history = []
        self.max_history_size = 200  # 最大历史记录数增加到200
        
        # 任务执行监控
        self.task_start_times: Dict[int, datetime] = {}  # 任务ID -> 开始时间
        self.task_timeout_check_interval = 30  # 任务超时检查间隔缩短到30秒
        self.last_timeout_check = datetime.now()
        
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
            
            # 延迟导入测试执行工具以避免循环导入
            from src.utils.interface_utils.test_case_executor import TestCaseExecutor
            self.execute_test_case = TestCaseExecutor(execution_mode='scheduler')
            
            # 初始化报告生成工具
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
                
                # 检查资源使用情况
                self._check_resource_limits()
                
                # 检查任务超时
                self._check_task_timeouts()
                
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
                
                # 优化等待机制：使用更精确的等待，减少延迟
                # 同时保持响应停止信号的能力
                start_wait_time = time.time()
                while time.time() - start_wait_time < self.check_interval:
                    if not self.running:
                        break
                    # 每0.1秒检查一次，提高响应性
                    time.sleep(0.1)
                    
            except Exception as e:
                self.error_count += 1
                logger.error(f"第 {iteration} 次检查异常 (错误#{self.error_count}): {str(e)}")
                logger.debug(f"异常详情: {traceback.format_exc()}")
                
                # 错误后短暂等待再继续
                if self.running:
                    time.sleep(5)
        
        logger.info("服务主循环正常退出")
    
    def _check_resource_limits(self):
        """检查资源使用情况，确保在限制范围内"""
        try:
            current_time = datetime.now()
            
            # 定期检查内存使用情况
            if (current_time - self.last_memory_check).total_seconds() >= self.memory_check_interval:
                self.last_memory_check = current_time
                
                memory_usage_mb = 0
                cpu_percent = 0
                
                if PSUTIL_AVAILABLE:
                    # 获取当前进程的内存使用情况
                    process = psutil.Process(os.getpid())
                    memory_info = process.memory_info()
                    memory_usage_mb = memory_info.rss / 1024 / 1024
                    
                    # 获取CPU使用率
                    cpu_percent = process.cpu_percent(interval=0.1)
                else:
                    # 在没有psutil的情况下，使用简化的资源估算
                    # 基于线程数量和任务队列长度估算资源使用
                    memory_usage_mb = len(self.thread_pool) * 10 + len(self.pending_tasks) * 2
                    cpu_percent = min(100, len(self.thread_pool) * 5 + len(self.pending_tasks))
                
                # 记录使用历史
                self._add_to_history(self.memory_usage_history, memory_usage_mb)
                self._add_to_history(self.cpu_usage_history, cpu_percent)
                
                # 检查是否超过限制
                if memory_usage_mb > self.max_memory_mb:
                    logger.warning(f"内存使用超过限制: {memory_usage_mb:.1f}MB > {self.max_memory_mb}MB")
                    self._handle_memory_overflow()
                
                if cpu_percent > self.max_cpu_percent:
                    logger.warning(f"CPU使用率超过限制: {cpu_percent:.1f}% > {self.max_cpu_percent}%")
                    self._handle_cpu_overload()
                
                # 定期清理历史记录
                if len(self.memory_usage_history) > self.max_history_size:
                    self.memory_usage_history = self.memory_usage_history[-self.max_history_size:]
                if len(self.cpu_usage_history) > self.max_history_size:
                    self.cpu_usage_history = self.cpu_usage_history[-self.max_history_size:]
                
                # 每5分钟记录一次资源使用情况
                if current_time.minute % 5 == 0 and current_time.second < 10:
                    avg_memory = sum(self.memory_usage_history[-10:]) / min(10, len(self.memory_usage_history))
                    avg_cpu = sum(self.cpu_usage_history[-10:]) / min(10, len(self.cpu_usage_history))
                    logger.info(f"资源监控 - 内存: {avg_memory:.1f}MB, CPU: {avg_cpu:.1f}%, 活跃线程: {len(self.thread_pool)}")
        
        except Exception as e:
            logger.error(f"资源检查失败: {str(e)}")
    
    def _add_to_history(self, history: List[float], value: float):
        """添加值到历史记录"""
        history.append(value)
        if len(history) > self.max_history_size:
            history.pop(0)
    
    def _handle_memory_overflow(self):
        """处理内存溢出情况"""
        try:
            logger.warning("检测到内存使用过高，开始清理资源...")
            
            # 强制垃圾回收
            gc.collect()
            
            # 清理过长的任务队列
            if len(self.pending_tasks) > self.max_pending_tasks // 2:
                logger.warning(f"清理待处理队列，从 {len(self.pending_tasks)} 个任务中移除一半")
                self.pending_tasks = self.pending_tasks[:self.max_pending_tasks // 2]
            
            # 清理历史记录
            self.memory_usage_history = self.memory_usage_history[-self.max_history_size // 2:]
            self.cpu_usage_history = self.cpu_usage_history[-self.max_history_size // 2:]
            
            logger.info("内存清理完成")
            
        except Exception as e:
            logger.error(f"内存清理失败: {str(e)}")
    
    def _handle_cpu_overload(self):
        """处理CPU过载情况"""
        try:
            logger.warning("检测到CPU使用过高，开始调整调度策略...")
            
            # 临时增加检查间隔，减少CPU使用
            original_interval = self.check_interval
            self.check_interval = min(5, self.check_interval * 2)  # 最大5秒
            
            logger.info(f"临时调整检查间隔: {original_interval}秒 -> {self.check_interval}秒")
            
            # 30秒后恢复原间隔
            def restore_interval():
                time.sleep(30)
                self.check_interval = original_interval
                logger.info(f"恢复检查间隔: {self.check_interval}秒")
            
            threading.Thread(target=restore_interval, daemon=True).start()
            
        except Exception as e:
            logger.error(f"CPU过载处理失败: {str(e)}")
    
    def _check_task_timeouts(self):
        """检查任务执行超时情况"""
        try:
            current_time = datetime.now()
            
            # 定期检查任务超时
            if (current_time - self.last_timeout_check).total_seconds() >= self.task_timeout_check_interval:
                self.last_timeout_check = current_time
                
                timeout_tasks = []
                for scheduler_id, start_time in self.task_start_times.items():
                    execution_time = (current_time - start_time).total_seconds()
                    if execution_time > self.max_task_execution_time:
                        timeout_tasks.append((scheduler_id, execution_time))
                
                if timeout_tasks:
                    logger.warning(f"发现 {len(timeout_tasks)} 个超时任务:")
                    for scheduler_id, execution_time in timeout_tasks:
                        logger.warning(f"  任务 {scheduler_id} 已执行 {execution_time:.1f}秒 > {self.max_task_execution_time}秒")
                        
                        # 尝试终止超时任务
                        self._terminate_timeout_task(scheduler_id)
                        
                        # 从监控中移除
                        if scheduler_id in self.task_start_times:
                            del self.task_start_times[scheduler_id]
        
        except Exception as e:
            logger.error(f"任务超时检查失败: {str(e)}")
    
    def _terminate_timeout_task(self, scheduler_id: int):
        """终止超时任务"""
        try:
            if scheduler_id in self.active_schedulers:
                thread = self.active_schedulers[scheduler_id]
                if thread and thread.is_alive():
                    # 尝试优雅终止（Python线程无法强制终止，只能标记为需要停止）
                    logger.warning(f"尝试终止超时任务 {scheduler_id}")
                    
                    # 从线程池中移除
                    if thread in self.thread_pool:
                        self.thread_pool.remove(thread)
                    
                    # 从活跃调度中移除
                    del self.active_schedulers[scheduler_id]
                    
                    logger.info(f"已标记超时任务 {scheduler_id} 为终止状态")
                else:
                    # 线程已经完成，清理记录
                    if scheduler_id in self.active_schedulers:
                        del self.active_schedulers[scheduler_id]
        
        except Exception as e:
            logger.error(f"终止超时任务失败: {str(e)}")

    def _cleanup_threads(self):
        """清理已完成的线程并处理待处理任务"""
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
        
        # 处理待处理队列中的任务
        processed_tasks = []
        for scheduler in self.pending_tasks:
            if len(self.thread_pool) < self.max_threads:
                # 线程池有空闲，执行待处理任务
                scheduler_id = scheduler['id']
                scheduler_name = scheduler['name']
                
                thread = threading.Thread(
                    target=self._execute_scheduler_thread,
                    args=(scheduler,),
                    name=f"PendingScheduler-{scheduler_id}"
                )
                thread.daemon = True
                thread.start()
                
                self.thread_pool.append(thread)
                self.active_schedulers[scheduler_id] = thread
                processed_tasks.append(scheduler)
                
                logger.info(f"执行待处理调度 {scheduler_name} (ID: {scheduler_id})")
            else:
                break
        
        # 从待处理队列中移除已处理的任务
        for task in processed_tasks:
            self.pending_tasks.remove(task)
        
        if len(self.thread_pool) > 0 or len(self.pending_tasks) > 0:
            logger.info(f"当前活跃线程数: {len(self.thread_pool)}, 活跃调度数: {len(self.active_schedulers)}, 待处理任务数: {len(self.pending_tasks)}")
    
    def _check_and_execute_schedulers(self):
        """检查并执行符合条件的调度"""
        try:
            # 获取所有启用的调度
            schedulers = self._get_all_schedulers()
            enabled_schedulers = [s for s in schedulers if s.get('enabled', False)]
            
            current_time = datetime.now()
            
            logger.info(f"检查时间: {current_time}, 启用的调度数量: {len(enabled_schedulers)}")
            
            execution_count = 0
            
            # 检查过去一段时间内可能错过的任务（回溯检查）
            self._check_missed_schedulers(enabled_schedulers, current_time)
            
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
                # 扩大时间窗口容错（10秒），避免错过精确执行时间
                time_window = timedelta(seconds=10)
                if next_run and (next_run <= current_time or 
                               (next_run - current_time <= time_window and next_run >= current_time - time_window)):
                    logger.info(f"调度 {scheduler_name} (ID: {scheduler_id}) 需要执行")
                    
                    # 检查线程池容量
                    if len(self.thread_pool) >= self.max_threads:
                        # 线程池满，将任务加入待处理队列
                        if len(self.pending_tasks) < self.max_pending_tasks:
                            self.pending_tasks.append(scheduler)
                            logger.warning(f"线程池已满，调度 {scheduler_name} 加入待处理队列，当前队列长度: {len(self.pending_tasks)}")
                        else:
                            logger.error(f"线程池和待处理队列均已满，跳过调度 {scheduler_name}")
                        continue
                    
                    # 记录任务开始时间
                    self.task_start_times[scheduler_id] = datetime.now()
                    
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
    
    def _check_missed_schedulers(self, enabled_schedulers: List[Dict], current_time: datetime):
        """检查过去一段时间内可能错过的调度任务
        
        Args:
            enabled_schedulers: 启用的调度列表
            current_time: 当前时间
        """
        try:
            # 回溯检查过去30秒内的任务，避免错过执行
            check_back_seconds = 30
            past_time = current_time - timedelta(seconds=check_back_seconds)
            
            missed_count = 0
            
            for scheduler in enabled_schedulers:
                scheduler_id = scheduler['id']
                scheduler_name = scheduler['name']
                cron_expression = scheduler.get('cron_expression', '')
                
                if not cron_expression:
                    continue
                
                # 检查调度是否正在执行
                if scheduler_id in self.active_schedulers:
                    thread = self.active_schedulers[scheduler_id]
                    if thread and thread.is_alive():
                        continue
                
                # 检查过去一段时间内的执行时间
                check_time = past_time
                while check_time < current_time:
                    # 计算在check_time时的下次执行时间
                    next_run_at_check_time = self.cron_parser.get_next_run(cron_expression, check_time)
                    
                    if next_run_at_check_time and next_run_at_check_time < current_time:
                        # 找到错过的执行时间
                        time_diff = (current_time - next_run_at_check_time).total_seconds()
                        if time_diff <= check_back_seconds:  # 只处理最近错过的任务
                            logger.warning(f"发现错过的调度: {scheduler_name} (ID: {scheduler_id}), 应执行时间: {next_run_at_check_time}, 已错过: {time_diff:.1f}秒")
                            
                            # 立即执行错过的任务
                            self._execute_missed_scheduler(scheduler, next_run_at_check_time)
                            missed_count += 1
                            break
                    
                    # 移动到下一个检查点（每秒检查一次）
                    check_time += timedelta(seconds=1)
            
            if missed_count > 0:
                logger.info(f"回溯检查发现 {missed_count} 个错过的调度任务")
                
        except Exception as e:
            logger.error(f"回溯检查调度失败: {str(e)}")
    
    def _execute_missed_scheduler(self, scheduler_data: Dict, missed_time: datetime):
        """执行错过的调度任务
        
        Args:
            scheduler_data: 调度数据
            missed_time: 错过的执行时间
        """
        try:
            scheduler_id = scheduler_data['id']
            scheduler_name = scheduler_data['name']
            
            # 检查线程池容量
            if len(self.thread_pool) >= self.max_threads:
                # 线程池满，将任务加入待处理队列
                if len(self.pending_tasks) < self.max_pending_tasks:
                    self.pending_tasks.append(scheduler_data)
                    logger.warning(f"线程池已满，错过的调度 {scheduler_name} 加入待处理队列")
                else:
                    logger.error(f"线程池和待处理队列均已满，无法执行错过的调度 {scheduler_name}")
                return
            
            # 创建执行线程
            thread = threading.Thread(
                target=self._execute_missed_scheduler_thread,
                args=(scheduler_data, missed_time),
                name=f"MissedScheduler-{scheduler_id}"
            )
            thread.daemon = True
            thread.start()
            
            self.thread_pool.append(thread)
            self.active_schedulers[scheduler_id] = thread
            
            logger.info(f"执行错过的调度 {scheduler_name} (ID: {scheduler_id}), 原应执行时间: {missed_time}")
            
        except Exception as e:
            logger.error(f"执行错过调度失败: {str(e)}")
    
    def _execute_missed_scheduler_thread(self, scheduler_data: Dict, missed_time: datetime):
        """执行错过调度的线程函数
        
        Args:
            scheduler_data: 调度数据
            missed_time: 错过的执行时间
        """
        try:
            scheduler_id = scheduler_data['id']
            scheduler_name = scheduler_data['name']
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"{current_time} [INFO] 🔍 开始执行错过的调度: {scheduler_name} (ID: {scheduler_id})")
            logger.info(f"{current_time} [INFO] ⏰ 原应执行时间: {missed_time}")
            
            # 这里可以添加错过的调度特有的处理逻辑
            # 例如：记录错过执行的信息，或者调整执行参数等
            
            # 调用正常的执行逻辑
            self._execute_scheduler_thread(scheduler_data)
            
        except Exception as e:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.error(f"{current_time} [ERROR] ❌ 执行错过的调度失败: {str(e)}")
    
    def _execute_scheduler_thread(self, scheduler_data):
        """执行单个调度的线程函数"""
        try:
            scheduler_id = scheduler_data['id']
            scheduler_name = scheduler_data['name']
            
            # 添加与执行日志弹窗一致的调试信息
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"{current_time} [INFO] 🔍 开始执行调度: {scheduler_name} (ID: {scheduler_id})")
            
            # 获取调度中配置的测试用例ID列表
            case_ids = scheduler_data.get('case_ids', [])
            if not case_ids:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.warning(f"{current_time} [WARN] ⚠️ 调度 '{scheduler_name}' 中没有配置测试用例")
                return
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"{current_time} [INFO] 📋 调度 {scheduler_name} 包含 {len(case_ids)} 个测试用例")
            
            # 记录执行开始时间
            execution_start_time = datetime.now()
            
            # 创建唯一的测试报告
            report_data = {
                'scheduler_id': scheduler_id,
                'case_id': None,  # 调度执行，case_id设为None
                'project_id': scheduler_data.get('project_id'),
                'report_name': f"{scheduler_name}_执行报告",
                'status': 'running',
                'start_time': execution_start_time,
                'total_cases': len(case_ids),  # 总用例数
                'passed_cases': 0,  # 通过用例数
                'failed_cases': 0,  # 失败用例数
                'error_cases': 0   # 错误用例数
            }
            
            # 创建测试报告
            report_id = self.test_report_service.create_report(report_data)
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"{current_time} [INFO] 📄 创建测试报告成功，报告ID: {report_id}")
            
            # 执行测试用例
            success_count = 0
            total_count = len(case_ids)
            
            # 存储每个用例的执行结果
            case_results = []
            
            # 存储所有步骤结果
            all_step_results = []
            
            for i, case_id in enumerate(case_ids):
                try:
                    # 获取测试用例数据
                    case_data = self.test_case_service.get_case_with_steps(case_id)
                    if not case_data:
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        logger.warning(f"{current_time} [WARN] ⚠️ 测试用例ID {case_id} 不存在，跳过执行")
                        continue
                    
                    case_name = case_data.get('name', '未知用例')
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"{current_time} [INFO] 🚀 执行测试用例 [{i+1}/{total_count}]: {case_name} (ID: {case_id})")
                    
                    # 使用TestCaseExecutor工具类执行测试用例，不生成独立报告
                    # 创建新的TestCaseExecutor实例，传递正确的项目ID和执行模式
                    from src.utils.interface_utils.test_case_executor import TestCaseExecutor
                    test_case_executor = TestCaseExecutor(
                        execution_mode='scheduler',
                        project_id=scheduler_data.get('project_id', 0)
                    )
                    
                    execution_result = test_case_executor.execute_case(
                        case_data, 
                        stop_on_failure=True,  # 定时调度在断言失败后停止当前用例执行
                        generate_report=False,  # 不生成独立报告
                        scheduler_id=scheduler_id,
                        parent_report_id=report_id,  # 指定父报告ID，将步骤结果关联到统一报告
                        execution_source='scheduler'  # 设置执行来源为调度模式
                    )
                    
                    # 收集步骤结果
                    if execution_result.get('step_results'):
                        all_step_results.extend(execution_result['step_results'])
                    
                    if execution_result.get('success'):
                        success_count += 1
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        logger.info(f"{current_time} [SUCCESS] ✅ 测试用例 {case_name} (ID: {case_id}) 执行成功")
                        case_results.append({
                            'case_id': case_id,
                            'case_name': case_name,
                            'success': True,
                            'execution_time': datetime.now()
                        })
                    else:
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        logger.warning(f"{current_time} [FAILURE] ❌ 测试用例 {case_name} (ID: {case_id}) 执行失败")
                        case_results.append({
                            'case_id': case_id,
                            'case_name': case_name,
                            'success': False,
                            'execution_time': datetime.now()
                        })
                    
                except Exception as e:
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.error(f"{current_time} [ERROR] 💥 执行测试用例ID {case_id} 失败: {str(e)}")
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
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if success_count == total_count:
                logger.info(f"{current_time} [SUCCESS] 🎉 调度 {scheduler_name} 执行完成 - 成功: {success_count}/{total_count}, 耗时: {execution_duration:.2f}秒")
            else:
                logger.warning(f"{current_time} [FAILURE] ⚠️ 调度 {scheduler_name} 执行完成 - 成功: {success_count}/{total_count}, 耗时: {execution_duration:.2f}秒")
            
            # 更新测试报告的统计信息
            try:
                # 统计用例结果
                total_cases = total_count
                passed_cases = success_count
                failed_cases = total_count - success_count
                error_cases = 0  # 目前没有错误用例的概念，可以后续扩展
                
                # 更新测试报告
                update_data = {
                    'status': 'success' if success_count == total_count else 'failure',
                    'end_time': execution_end_time,
                    'duration': execution_duration,
                    'total_cases': total_cases,
                    'passed_cases': passed_cases,
                    'failed_cases': failed_cases,
                    'error_cases': error_cases
                }
                
                # 更新报告
                self.test_report_service.update_report(report_id, update_data)
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"{current_time} [INFO] 📊 测试报告已更新，统计信息: 用例{passed_cases}/{total_cases}通过")
                
            except Exception as e:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.error(f"{current_time} [ERROR] 💥 更新测试报告失败: {str(e)}")
            
            # 更新调度执行时间
            try:
                self._update_last_run(scheduler_id)
                self._update_next_run(scheduler_id)
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"{current_time} [INFO] ⏰ 调度 {scheduler_name} 执行时间已更新")
            except Exception as e:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.error(f"{current_time} [ERROR] 💥 更新调度执行时间失败: {str(e)}")
            
            # 发送邮件通知（如果配置了收件人且启用了邮件通知）
            notify_emails = scheduler_data.get('notify_emails', [])
            email_config = scheduler_data.get('email_config', {})
            email_enabled = email_config.get('enabled', True)  # 默认为启用状态
            
            if notify_emails and email_enabled:
                try:
                    self._send_test_report_email(notify_emails, case_results, scheduler_name, execution_duration)
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"{current_time} [INFO] 📧 测试报告邮件发送成功，收件人: {', '.join(notify_emails)}")
                except Exception as e:
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.error(f"{current_time} [ERROR] 💥 发送测试报告邮件失败: {str(e)}")
            elif notify_emails and not email_enabled:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"{current_time} [INFO] 📧 邮件通知已禁用，跳过发送")
            
            # 发送企业微信通知（如果配置了Webhook且启用了企业微信通知）
            notify_wechat = scheduler_data.get('notify_wechat', {})
            wechat_enabled = notify_wechat.get('enabled', True)  # 默认为启用状态
            wechat_webhook = notify_wechat.get('webhook', '')
            
            if wechat_webhook and wechat_enabled:
                try:
                    self._send_wechat_notification(wechat_webhook, case_results, scheduler_name, execution_duration)
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"{current_time} [INFO] 💬 企业微信通知发送成功")
                except Exception as e:
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.error(f"{current_time} [ERROR] 💥 发送企业微信通知失败: {str(e)}")
            elif wechat_webhook and not wechat_enabled:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"{current_time} [INFO] 💬 企业微信通知已禁用，跳过发送")
            
        except Exception as e:
            logger.error(f"执行调度失败: {str(e)}")
        finally:
            # 清理任务开始时间记录
            scheduler_id = scheduler_data.get('id')
            if scheduler_id and scheduler_id in self.task_start_times:
                del self.task_start_times[scheduler_id]
                logger.debug(f"清理任务 {scheduler_id} 的开始时间记录")
    
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
                                   case_ids, notify_emails, notify_wechat, email_config,
                                   last_run_at, next_run_at, created_by, created_at, updated_at, project_id
                            FROM test_schedulers 
                            WHERE project_id = %s
                            ORDER BY updated_at DESC
                        """, (project_id,))
                    else:
                        # 返回所有调度任务
                        cursor.execute("""
                            SELECT id, name, description, cron_expression, enabled, 
                                   case_ids, notify_emails, notify_wechat, email_config,
                                   last_run_at, next_run_at, created_by, created_at, updated_at, project_id
                            FROM test_schedulers 
                            ORDER BY updated_at DESC
                        """)
                    
                    schedulers = cursor.fetchall()
                    
                    # 处理JSON字段
                    for scheduler in schedulers:
                        for field in ['case_ids', 'notify_emails', 'notify_wechat', 'email_config']:
                            if scheduler.get(field) and scheduler[field] is not None:
                                scheduler[field] = json.loads(scheduler[field])
                            else:
                                if field in ['case_ids', 'notify_emails']:
                                    scheduler[field] = []
                                else:
                                    scheduler[field] = {}
                    
                    return schedulers
        except Exception as e:
            logger.error(f"获取项目调度列表失败: {e}")
            return []

    def get_schedulers_for_test_report(self, project_id):
        """根据项目ID获取调度任务列表（用于测试报告tab，按创建时间升序排列）
        
        Args:
            project_id: 项目ID，如果为None或空字符串则返回所有调度任务
            
        Returns:
            List[Dict]: 调度任务列表，按创建时间升序排列
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    if project_id:
                        # 按项目筛选
                        cursor.execute("""
                            SELECT id, name, description, cron_expression, enabled, 
                                   case_ids, notify_emails, notify_wechat, email_config,
                                   last_run_at, next_run_at, created_by, created_at, updated_at, project_id
                            FROM test_schedulers 
                            WHERE project_id = %s
                            ORDER BY created_at ASC
                        """, (project_id,))
                    else:
                        # 返回所有调度任务
                        cursor.execute("""
                            SELECT id, name, description, cron_expression, enabled, 
                                   case_ids, notify_emails, notify_wechat, email_config,
                                   last_run_at, next_run_at, created_by, created_at, updated_at, project_id
                            FROM test_schedulers 
                            ORDER BY created_at ASC
                        """)
                    
                    schedulers = cursor.fetchall()
                    
                    # 处理JSON字段
                    for scheduler in schedulers:
                        for field in ['case_ids', 'notify_emails', 'notify_wechat', 'email_config']:
                            if scheduler.get(field) and scheduler[field] is not None:
                                scheduler[field] = json.loads(scheduler[field])
                            else:
                                if field in ['case_ids', 'notify_emails']:
                                    scheduler[field] = []
                                else:
                                    scheduler[field] = {}
                    
                    return schedulers
        except Exception as e:
            logger.error(f"获取测试报告调度列表失败: {e}")
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
                         notify_emails, notify_wechat, email_config, created_by, created_at, updated_at, project_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s)
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
                        json.dumps(scheduler_data.get('email_config', {})),
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
                            notify_wechat = %s, email_config = %s, project_id = %s, updated_at = NOW()
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
                        json.dumps(scheduler_data.get('email_config', {})),
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
                               case_ids, notify_emails, notify_wechat, email_config,
                               last_run_at, next_run_at, created_by, created_at, updated_at, project_id
                        FROM test_schedulers 
                        ORDER BY updated_at DESC
                    """)
                    schedulers = cursor.fetchall()
                    
                    # 处理JSON字段
                    for scheduler in schedulers:
                        for field in ['case_ids', 'notify_emails', 'notify_wechat', 'email_config']:
                            if scheduler.get(field):
                                scheduler[field] = json.loads(scheduler[field])
                            else:
                                if field in ['case_ids', 'notify_emails']:
                                    scheduler[field] = []
                                else:
                                    scheduler[field] = {}
                    
                    return schedulers
        except Exception as e:
            logger.error(f"获取调度列表失败: {e}")
            return []

    def get_schedulers_with_pagination(self, page: int = 1, page_size: int = 10, project_id: int = None) -> tuple:
        """获取分页调度列表
        
        Args:
            page: 页码，从1开始
            page_size: 每页大小
            project_id: 项目ID，可选，用于筛选特定项目的调度
            
        Returns:
            tuple: (调度列表, 总记录数)
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 计算偏移量
                    offset = (page - 1) * page_size
                    
                    # 构建查询条件
                    where_clause = ""
                    params = []
                    
                    if project_id is not None:
                        where_clause = "WHERE project_id = %s"
                        params.append(project_id)
                    
                    # 获取分页数据
                    cursor.execute(f"""
                        SELECT id, name, description, cron_expression, enabled, 
                               case_ids, notify_emails, notify_wechat, email_config,
                               last_run_at, next_run_at, created_by, created_at, updated_at, project_id
                        FROM test_schedulers 
                        {where_clause}
                        ORDER BY updated_at DESC
                        LIMIT %s OFFSET %s
                    """, params + [page_size, offset])
                    schedulers = cursor.fetchall()
                    
                    # 处理JSON字段
                    for scheduler in schedulers:
                        for field in ['case_ids', 'notify_emails', 'notify_wechat', 'email_config']:
                            if scheduler.get(field):
                                scheduler[field] = json.loads(scheduler[field])
                            else:
                                if field in ['case_ids', 'notify_emails']:
                                    scheduler[field] = []
                                else:
                                    scheduler[field] = {}
                    
                    # 获取总数
                    cursor.execute(f"""
                        SELECT COUNT(*) as total FROM test_schedulers {where_clause}
                    """, params)
                    total = cursor.fetchone()['total']
                    
                    return schedulers, total
        except Exception as e:
            logger.error(f"获取分页调度列表失败: {e}")
            return [], 0

    def _send_test_report_email(self, recipients: list, case_results: list, 
                              scheduler_name: str, execution_duration: float) -> bool:
        """
        发送测试报告邮件
        
        Args:
            recipients: 收件人列表
            case_results: 用例执行结果列表
            scheduler_name: 调度任务名称
            execution_duration: 执行时长（秒）
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 获取邮件配置（这里需要从配置文件中读取）
            email_config = self._get_email_config()
            if not email_config:
                logger.warning("邮件配置未设置，跳过邮件发送")
                return False
            
            # 创建邮件服务
            from src.core.services.email_service import EmailService
            email_service = EmailService(email_config)
            
            # 生成测试报告数据
            report_data = self._generate_email_report_data(case_results, scheduler_name, execution_duration)
            
            # 发送邮件
            return email_service.send_test_report_email(recipients, report_data, 0, scheduler_name)
            
        except Exception as e:
            logger.error(f"发送测试报告邮件失败: {str(e)}")
            return False
    
    def _send_wechat_notification(self, webhook_url: str, case_results: list, 
                                scheduler_name: str, execution_duration: float) -> bool:
        """
        发送企业微信通知
        
        Args:
            webhook_url: 企业微信机器人Webhook URL
            case_results: 用例执行结果列表
            scheduler_name: 调度任务名称
            execution_duration: 执行时长（秒）
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 生成测试报告数据
            report_data = self._generate_wechat_report_data(case_results, scheduler_name, execution_duration)
            
            # 构建企业微信消息
            message = self._build_wechat_message(report_data)
            
            # 发送企业微信通知
            return self._send_wechat_webhook(webhook_url, message)
            
        except Exception as e:
            logger.error(f"发送企业微信通知失败: {str(e)}")
            return False
    
    def _generate_wechat_report_data(self, case_results: list, scheduler_name: str, 
                                   execution_duration: float) -> dict:
        """生成企业微信报告数据"""
        total_cases = len(case_results)
        success_cases = sum(1 for result in case_results if result.get('success', False))
        failed_cases = total_cases - success_cases
        
        # 确定整体状态
        if failed_cases == 0:
            status = '成功'
            status_emoji = '✅'
        elif success_cases == 0:
            status = '失败'
            status_emoji = '❌'
        else:
            status = '部分失败'
            status_emoji = '⚠️'
        
        return {
            'status': status,
            'status_emoji': status_emoji,
            'scheduler_name': scheduler_name,
            'total_cases': total_cases,
            'success_cases': success_cases,
            'failed_cases': failed_cases,
            'execution_duration': execution_duration,
            'execution_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _build_wechat_message(self, report_data: dict) -> dict:
        """构建企业微信消息"""
        # 构建消息内容
        content = f"""{report_data['status_emoji']} 测试任务执行报告

📋 任务名称: {report_data['scheduler_name']}
📊 执行状态: {report_data['status']}
⏰ 执行时间: {report_data['execution_time']}
⏱️ 执行时长: {report_data['execution_duration']:.2f}秒

📈 测试统计:
   • 总用例数: {report_data['total_cases']}
   • 成功用例: {report_data['success_cases']}
   • 失败用例: {report_data['failed_cases']}

💡 执行结果: {report_data['status']}"""
        
        return {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
    
    def _send_wechat_webhook(self, webhook_url: str, message: dict) -> bool:
        """发送企业微信Webhook消息"""
        try:
            import requests
            import json
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(webhook_url, data=json.dumps(message), headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    return True
                else:
                    logger.error(f"企业微信API返回错误: {result}")
                    return False
            else:
                logger.error(f"企业微信请求失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"发送企业微信Webhook失败: {str(e)}")
            return False
    
    def _get_email_config(self):
        """获取邮件配置"""
        try:
            from src.core.services.email_config_service import EmailConfigService
            email_config_service = EmailConfigService()
            return email_config_service.get_email_config()
        except Exception as e:
            logger.warning(f"获取邮件配置失败: {str(e)}")
            return None
    
    def _generate_email_report_data(self, case_results: list, scheduler_name: str, 
                                   execution_duration: float) -> dict:
        """生成邮件报告数据"""
        total_cases = len(case_results)
        success_cases = sum(1 for result in case_results if result.get('success', False))
        failed_cases = total_cases - success_cases
        
        # 确定整体状态
        if failed_cases == 0:
            status = 'success'
        elif success_cases == 0:
            status = 'error'
        else:
            status = 'failure'
        
        return {
            'status': status,
            'case_name': f"调度任务: {scheduler_name}",
            'start_time': datetime.now(),
            'end_time': datetime.now(),
            'duration': execution_duration,
            'total_cases': total_cases,
            'passed_cases': success_cases,
            'failed_cases': failed_cases,
            'error_cases': 0
        }
    
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
            logger.error(f"更新调度 {scheduler_id} 上次执行时间失败: {e}")
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