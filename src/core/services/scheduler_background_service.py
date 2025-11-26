"""
后台调度服务 - 负责定时执行调度任务
"""
import threading
import time
import logging
import os
import json
from datetime import datetime
from typing import Dict, List, Any

from PyQt5.QtCore import QObject, pyqtSignal, QThread

from src.core.services.scheduler_service import SchedulerService
from src.core.services.test_case_service import TestCaseService
from src.core.services.test_report_service import TestReportService
from src.utils.interface_utils.cron_parser import CronParser
from src.ui.interface_auto.components.tabbed_case_editor import CaseExecutionThread
from src.utils.interface_utils.report_generator import HTMLReportGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler_service.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SchedulerBackgroundService')


class SchedulerBackgroundService(QObject):
    """后台调度服务"""
    
    # 信号定义
    scheduler_executed = pyqtSignal(dict, bool, str)  # 调度数据, 执行结果, 消息
    scheduler_error = pyqtSignal(dict, str)  # 调度数据, 错误消息
    
    def __init__(self):
        super().__init__()
        self.scheduler_service = SchedulerService()
        self.test_case_service = TestCaseService()
        self.cron_parser = CronParser()
        
        # 调度执行状态
        self.running = False
        self.thread = None
        self.check_interval = 60  # 检查间隔（秒）
        
        # 正在执行的调度
        self.active_schedulers: Dict[int, CaseExecutionThread] = {}
    
    def start_service(self):
        """启动后台服务"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_service, daemon=True)
        self.thread.start()
        
        logger.info(f"后台调度服务已启动，检查间隔: {self.check_interval}秒")
    
    def stop_service(self):
        """停止后台服务"""
        self.running = False
        
        # 停止所有正在执行的调度
        for scheduler_id, thread in self.active_schedulers.items():
            if thread and thread.isRunning():
                thread.stop()
        
        self.active_schedulers.clear()
        logger.info("后台调度服务已停止")
    
    def _run_service(self):
        """服务主循环"""
        while self.running:
            try:
                self._check_and_execute_schedulers()
            except Exception as e:
                logger.error(f"检查调度时发生错误: {str(e)}")
            
            # 等待下一次检查
            time.sleep(self.check_interval)
    
    def _check_and_execute_schedulers(self):
        """检查并执行符合条件的调度"""
        try:
            # 获取所有启用的调度
            schedulers = self.scheduler_service.get_all_schedulers()
            enabled_schedulers = [s for s in schedulers if s.get('enabled', False)]
            
            current_time = datetime.now()
            
            for scheduler in enabled_schedulers:
                # 检查调度是否正在执行
                if scheduler['id'] in self.active_schedulers:
                    continue
                
                # 检查Cron表达式是否匹配当前时间
                cron_expression = scheduler.get('cron_expression', '')
                if not cron_expression:
                    continue
                
                # 计算下次执行时间
                next_run = self.cron_parser.get_next_run(cron_expression)
                
                # 如果下次执行时间早于当前时间，说明需要执行
                if next_run and next_run <= current_time:
                    # 执行调度
                    self._execute_scheduler(scheduler)
                    
                    # 更新下次执行时间
                    self.scheduler_service.update_next_run(scheduler['id'])
        
        except Exception as e:
            logger.error(f"检查调度失败: {str(e)}")
    
    def execute_scheduler(self, scheduler_id):
        """执行指定ID的调度（公共方法）"""
        try:
            # 获取调度数据
            scheduler_data = self.scheduler_service.get_scheduler_by_id(scheduler_id)
            if not scheduler_data:
                error_msg = f"调度ID {scheduler_id} 不存在"
                logger.error(error_msg)
                return
            
            # 检查调度是否启用
            if not scheduler_data.get('enabled', False):
                error_msg = f"调度 '{scheduler_data['name']}' 未启用，无法执行"
                logger.warning(error_msg)
                return
            
            # 调用私有方法执行调度
            self._execute_scheduler(scheduler_data)
            
        except Exception as e:
            error_msg = f"执行调度ID {scheduler_id} 失败: {str(e)}"
            logger.error(error_msg)
    
    def _execute_scheduler(self, scheduler_data):
        """执行单个调度"""
        try:
            scheduler_id = scheduler_data['id']
            scheduler_name = scheduler_data['name']
            
            # 检查是否已经在执行
            if scheduler_id in self.active_schedulers:
                thread = self.active_schedulers[scheduler_id]
                if thread and thread.isRunning():
                    logger.warning(f"调度 {scheduler_id} 正在执行中，跳过本次执行")
                    return
            
            logger.info(f"开始执行调度: {scheduler_name} (ID: {scheduler_id})")
            
            # 获取调度中配置的测试用例ID列表
            case_ids = scheduler_data.get('case_ids', [])
            if not case_ids:
                error_msg = f"调度 '{scheduler_name}' 中没有配置测试用例"
                self.scheduler_error.emit(scheduler_data, error_msg)
                return
            
            # 创建执行线程
            execution_thread = SchedulerExecutionThread(
                scheduler_data=scheduler_data,
                case_ids=case_ids,
                test_case_service=self.test_case_service
            )
            
            # 连接信号
            execution_thread.scheduler_finished.connect(self._on_scheduler_execution_finished)
            execution_thread.scheduler_error.connect(self._on_scheduler_execution_error)
            
            # 记录正在执行的调度
            self.active_schedulers[scheduler_id] = execution_thread
            
            # 启动执行线程
            execution_thread.start()
            
            # 发送执行开始信号
            self.scheduler_executed.emit(scheduler_data, True, f"调度 '{scheduler_name}' 开始执行")
            
        except Exception as e:
            error_msg = f"执行调度失败: {str(e)}"
            logger.error(error_msg)
            self.scheduler_error.emit(scheduler_data, error_msg)
    
    def _on_scheduler_execution_finished(self, scheduler_data, success_count, total_count):
        """调度执行完成回调"""
        scheduler_id = scheduler_data['id']
        scheduler_name = scheduler_data['name']
        
        # 移除正在执行的调度记录
        if scheduler_id in self.active_schedulers:
            del self.active_schedulers[scheduler_id]
        
        # 更新上次执行时间
        self.scheduler_service.update_last_run(scheduler_id)
        
        # 发送执行完成信号
        if success_count == total_count:
            message = f"调度 '{scheduler_name}' 执行完成: 成功 {success_count}/{total_count} 个测试用例"
            self.scheduler_executed.emit(scheduler_data, True, message)
        else:
            message = f"调度 '{scheduler_name}' 执行完成: 成功 {success_count}/{total_count} 个测试用例"
            self.scheduler_executed.emit(scheduler_data, False, message)
        
        logger.info(f"调度 {scheduler_name} (ID: {scheduler_id}) 执行完成 - 成功: {success_count}, 失败: {total_count - success_count}, 总用例数: {total_count}")
    
    def _on_scheduler_execution_error(self, scheduler_data, error_msg):
        """调度执行错误回调"""
        scheduler_id = scheduler_data['id']
        scheduler_name = scheduler_data['name']
        
        # 移除正在执行的调度记录
        if scheduler_id in self.active_schedulers:
            del self.active_schedulers[scheduler_id]
        
        # 发送错误信号
        self.scheduler_error.emit(scheduler_data, error_msg)
        
        logger.error(f"调度 {scheduler_name} (ID: {scheduler_id}) 执行错误: {error_msg}")


class SchedulerExecutionThread(QThread):
    """调度执行线程"""
    
    # 信号定义
    scheduler_finished = pyqtSignal(dict, int, int)  # 调度数据, 成功数量, 总数量
    scheduler_error = pyqtSignal(dict, str)  # 调度数据, 错误消息
    
    def __init__(self, scheduler_data, case_ids, test_case_service):
        super().__init__()
        self.scheduler_data = scheduler_data
        self.case_ids = case_ids
        self.test_case_service = test_case_service
        self.test_report_service = TestReportService()
        self.report_generator = HTMLReportGenerator()
    
    def run(self):
        """执行调度"""
        try:
            success_count = 0
            total_count = len(self.case_ids)
            
            logger.info(f"开始执行调度线程，共 {total_count} 个测试用例")
            
            # 记录执行开始时间
            execution_start_time = datetime.now()
            
            # 存储每个用例的执行结果
            case_results = []
            
            for case_id in self.case_ids:
                try:
                    # 获取测试用例数据
                    case_data = self.test_case_service.get_case_with_steps(case_id)
                    if not case_data:
                        logger.warning(f"测试用例ID {case_id} 不存在，跳过执行")
                        continue
                    
                    logger.info(f"执行测试用例: {case_data.get('name', '未知用例')} (ID: {case_id})")
                    
                    # 创建测试用例执行线程
                    execution_thread = CaseExecutionThread(
                        case_data=case_data,
                        environment_config={},  # 使用默认环境配置
                        project_id=case_data.get('project_id', 0)
                    )
                    
                    # 启动执行线程
                    execution_thread.start()
                    
                    # 等待执行完成
                    execution_thread.wait()
                    
                    # 检查执行结果
                    if not execution_thread.isRunning():
                        success_count += 1
                        logger.info(f"测试用例 {case_id} 执行成功")
                        case_results.append({
                            'case_id': case_id,
                            'case_name': case_data.get('name', '未知用例'),
                            'success': True,
                            'execution_time': datetime.now()
                        })
                    else:
                        logger.warning(f"测试用例 {case_id} 执行失败或超时")
                        case_results.append({
                            'case_id': case_id,
                            'case_name': case_data.get('name', '未知用例'),
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
            
            logger.info(f"调度线程执行完成 - 成功: {success_count}/{total_count}, 耗时: {execution_duration:.2f}秒")
            
            # 生成测试报告
            self._generate_test_report(case_results, execution_start_time, execution_end_time, execution_duration)
            
            # 发送执行完成信号
            self.scheduler_finished.emit(self.scheduler_data, success_count, total_count)
            
        except Exception as e:
            error_msg = f"调度执行线程异常: {str(e)}"
            logger.error(error_msg)
            self.scheduler_error.emit(self.scheduler_data, error_msg)
    
    def _generate_test_report(self, case_results, start_time, end_time, duration):
        """生成测试报告"""
        try:
            scheduler_id = self.scheduler_data['id']
            scheduler_name = self.scheduler_data['name']
            
            # 计算统计信息
            total_cases = len(case_results)
            success_cases = len([r for r in case_results if r.get('success', False)])
            failed_cases = total_cases - success_cases
            
            # 确定调度执行状态
            if total_cases == 0:
                status = 'error'
            elif success_cases == total_cases:
                status = 'success'
            elif success_cases > 0:
                status = 'failure'
            else:
                status = 'error'
            
            # 为每个执行的测试用例创建单独的报告记录
            report_ids = []
            for case_result in case_results:
                case_id = case_result['case_id']
                case_name = case_result['case_name']
                case_status = 'success' if case_result.get('success', False) else 'failure'
                
                # 生成报告名称
                report_name = f"调度报告-{scheduler_name}-{case_name}-{start_time.strftime('%Y%m%d%H%M%S')}"
                
                # 准备报告数据
                report_data = {
                    'scheduler_id': scheduler_id,
                    'case_id': case_id,
                    'report_name': report_name,
                    'status': case_status,
                    'total_steps': 1,  # 每个用例单独报告，步骤数为1
                    'passed_steps': 1 if case_result.get('success', False) else 0,
                    'failed_steps': 0 if case_result.get('success', False) else 1,
                    'error_steps': 0,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'log_path': '',  # 暂时留空
                    'case_results': [case_result]  # 只包含当前用例的结果
                }
                
                # 保存报告到数据库
                report_id = self._save_report_to_database(report_data)
                if report_id:
                    report_ids.append(report_id)
                    logger.info(f"测试用例 {case_name} 报告保存成功，报告ID: {report_id}")
                    
                    # 生成HTML报告文件
                    self._generate_html_report(report_data, report_id)
                else:
                    logger.error(f"测试用例 {case_name} 报告保存失败")
            
            if report_ids:
                logger.info(f"测试报告生成完成，共生成 {len(report_ids)} 个报告")
            else:
                logger.error("测试报告保存失败")
                
        except Exception as e:
            logger.error(f"生成测试报告失败: {str(e)}")
    
    def _save_report_to_database(self, report_data):
        """保存测试报告到数据库"""
        try:
            # 构建插入SQL - 使用%s作为MySQL占位符
            sql = """
            INSERT INTO test_reports 
            (scheduler_id, case_id, report_name, status, total_steps, passed_steps, failed_steps, error_steps, 
             start_time, end_time, duration, log_path, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            # 准备参数
            params = (
                report_data['scheduler_id'],
                report_data['case_id'],
                report_data['report_name'],
                report_data['status'],
                report_data['total_steps'],
                report_data['passed_steps'],
                report_data['failed_steps'],
                report_data['error_steps'],
                report_data['start_time'],
                report_data['end_time'],
                report_data['duration'],
                report_data['log_path']
            )
            
            # 执行插入操作
            from src.utils.interface_utils.database_utils import DatabaseUtils
            db_utils = DatabaseUtils()
            
            # 获取数据库配置（使用项目实际的MySQL配置）
            from config.settings import DATABASE_CONFIG
            db_config = {
                'database_type': 'mysql',
                'host': DATABASE_CONFIG['host'],
                'port': DATABASE_CONFIG['port'],
                'username': DATABASE_CONFIG['user'],
                'password': DATABASE_CONFIG['password'],
                'database': DATABASE_CONFIG['database'],
                'charset': 'utf8mb4'
            }
            
            # 执行插入
            connection = db_utils.get_connection(db_config)
            cursor = connection.cursor()
            cursor.execute(sql, params)
            connection.commit()
            
            # 获取插入的ID
            report_id = cursor.lastrowid
            
            # 关闭连接
            cursor.close()
            connection.close()
            
            return report_id
            
        except Exception as e:
            logger.error(f"保存测试报告到数据库失败: {str(e)}")
            return None
    
    def _generate_html_report(self, report_data, report_id):
        """生成HTML测试报告文件"""
        try:
            # 创建报告目录
            reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            # 生成报告文件路径
            report_filename = f"report_{report_id}_{report_data['start_time'].strftime('%Y%m%d%H%M%S')}.html"
            report_filepath = os.path.join(reports_dir, report_filename)
            
            # 生成报告
            self.report_generator.generate_report(report_data, report_filepath)
            
            # 更新数据库中的日志路径
            self._update_report_log_path(report_id, report_filepath)
            
            logger.info(f"HTML测试报告生成成功: {report_filepath}")
            
        except Exception as e:
            logger.error(f"生成HTML测试报告失败: {str(e)}")
    
    def _update_report_log_path(self, report_id, log_path):
        """更新报告日志路径"""
        try:
            sql = "UPDATE test_reports SET log_path = %s WHERE id = %s"
            
            from src.utils.interface_utils.database_utils import DatabaseUtils
            db_utils = DatabaseUtils()
            
            # 获取数据库配置（使用项目实际的MySQL配置）
            from config.settings import DATABASE_CONFIG
            db_config = {
                'database_type': 'mysql',
                'host': DATABASE_CONFIG['host'],
                'port': DATABASE_CONFIG['port'],
                'username': DATABASE_CONFIG['user'],
                'password': DATABASE_CONFIG['password'],
                'database': DATABASE_CONFIG['database'],
                'charset': 'utf8mb4'
            }
            
            connection = db_utils.get_connection(db_config)
            cursor = connection.cursor()
            cursor.execute(sql, (log_path, report_id))
            connection.commit()
            
            cursor.close()
            connection.close()
            
        except Exception as e:
            logger.error(f"更新报告日志路径失败: {str(e)}")