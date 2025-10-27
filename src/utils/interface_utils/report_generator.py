import os
import json
from datetime import datetime
from typing import Dict, Any, List


class HTMLReportGenerator:
    """HTML报告生成器"""

    def generate_report(self, report_data: Dict[str, Any], output_path: str) -> str:
        """生成HTML测试报告"""

        # 报告数据
        report_name = report_data.get('report_name', '测试报告')
        case_name = report_data.get('case_name', '未知用例')
        status = report_data.get('status', 'unknown')
        start_time = report_data.get('start_time')
        end_time = report_data.get('end_time')
        duration = report_data.get('duration', 0)

        total_steps = report_data.get('total_steps', 0)
        passed_steps = report_data.get('passed_steps', 0)
        failed_steps = report_data.get('failed_steps', 0)
        error_steps = report_data.get('error_steps', 0)

        if total_steps > 0:
            success_rate = (passed_steps / total_steps) * 100
        else:
            success_rate = 0

        # 状态颜色
        status_color = {
            'success': '#4CAF50',
            'failure': '#F44336',
            'error': '#FF9800',
            'running': '#2196F3'
        }.get(status, '#9E9E9E')

        status_text = {
            'success': '成功',
            'failure': '失败',
            'error': '错误',
            'running': '执行中'
        }.get(status, '未知')

        # 生成HTML内容
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{report_name}</title>
            <style>
                body {{
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                    color: #333;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 2px solid #eee;
                }}
                .header h1 {{
                    color: #2196F3;
                    margin-bottom: 10px;
                }}
                .status-badge {{
                    display: inline-block;
                    padding: 6px 12px;
                    background-color: {status_color};
                    color: white;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(5, 1fr);
                    gap: 15px;
                    margin: 20px 0;
                }}
                .stat-card {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 6px;
                    text-align: center;
                    border-left: 4px solid #2196F3;
                }}
                .stat-number {{
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 5px;
                }}
                .stat-label {{
                    color: #666;
                    font-size: 14px;
                }}
                .progress-bar {{
                    background: #e9ecef;
                    border-radius: 10px;
                    height: 20px;
                    margin: 20px 0;
                    overflow: hidden;
                }}
                .progress-fill {{
                    height: 100%;
                    background: #4CAF50;
                    transition: width 0.3s ease;
                }}
                .info-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin: 20px 0;
                }}
                .info-card {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 6px;
                }}
                .steps-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                .steps-table th,
                .steps-table td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                .steps-table th {{
                    background-color: #f8f9fa;
                    font-weight: bold;
                }}
                .status-success {{
                    color: #4CAF50;
                    font-weight: bold;
                }}
                .status-failure {{
                    color: #F44336;
                    font-weight: bold;
                }}
                .status-error {{
                    color: #FF9800;
                    font-weight: bold;
                }}
                .status-skipped {{
                    color: #9E9E9E;
                    font-weight: bold;
                }}
                .timestamp {{
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{report_name}</h1>
                    <div class="status-badge">{status_text}</div>
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{total_steps}</div>
                        <div class="stat-label">总步骤</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" style="color: #4CAF50;">{passed_steps}</div>
                        <div class="stat-label">通过</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" style="color: #F44336;">{failed_steps}</div>
                        <div class="stat-label">失败</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" style="color: #FF9800;">{error_steps}</div>
                        <div class="stat-label">错误</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" style="color: #2196F3;">{success_rate:.1f}%</div>
                        <div class="stat-label">通过率</div>
                    </div>
                </div>

                <div class="progress-bar">
                    <div class="progress-fill" style="width: {success_rate}%;"></div>
                </div>

                <div class="info-grid">
                    <div class="info-card">
                        <h3>基本信息</h3>
                        <p><strong>测试用例:</strong> {case_name}</p>
                        <p><strong>开始时间:</strong> {start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else 'N/A'}</p>
                        <p><strong>结束时间:</strong> {end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else 'N/A'}</p>
                        <p><strong>执行时长:</strong> {duration:.2f} 秒</p>
                    </div>
                    <div class="info-card">
                        <h3>环境信息</h3>
                        <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p><strong>报告版本:</strong> 1.0</p>
                    </div>
                </div>

                <h2>执行步骤</h2>
                <table class="steps-table">
                    <thead>
                        <tr>
                            <th>步骤</th>
                            <th>接口名称</th>
                            <th>状态</th>
                            <th>开始时间</th>
                            <th>结束时间</th>
                            <th>时长(秒)</th>
                            <th>错误信息</th>
                        </tr>
                    </thead>
                    <tbody>
                        {self._generate_steps_table(report_data)}
                    </tbody>
                </table>

                <div class="timestamp">
                    报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return output_path

    def _generate_steps_table(self, report_data: Dict[str, Any]) -> str:
        """生成步骤表格内容"""
        try:
            from src.core.services.test_report_service import TestReportService
            service = TestReportService()
            steps = service.get_step_results_by_report(report_data['id'])

            rows = []
            for step in steps:
                step_order = step.get('step_order', 0)
                api_name = step.get('api_name', '未知接口')

                status = step.get('status', 'skipped')
                status_class = f"status-{status}"
                status_text = {
                    'success': '成功',
                    'failure': '失败',
                    'error': '错误',
                    'skipped': '跳过'
                }.get(status, status)

                start_time = step.get('start_time')
                start_text = start_time.strftime('%H:%M:%S') if start_time else 'N/A'

                end_time = step.get('end_time')
                end_text = end_time.strftime('%H:%M:%S') if end_time else 'N/A'

                duration = step.get('duration', 0)
                duration_text = f"{duration:.3f}" if duration > 0 else 'N/A'

                error_msg = step.get('error_message', '')

                row = f"""
                <tr>
                    <td>{step_order}</td>
                    <td>{api_name}</td>
                    <td class="{status_class}">{status_text}</td>
                    <td>{start_text}</td>
                    <td>{end_text}</td>
                    <td>{duration_text}</td>
                    <td>{error_msg}</td>
                </tr>
                """
                rows.append(row)

            return ''.join(rows)

        except Exception as e:
            return f"<tr><td colspan='7'>加载步骤数据失败: {str(e)}</td></tr>"