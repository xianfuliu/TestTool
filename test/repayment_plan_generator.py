import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from scipy.optimize import newton
import os
import json
import re
from collections import defaultdict
import random
import pickle
import time
from tqdm import tqdm
import math


class RepaymentPlanGenerator:
    """
    优化的还款计划生成器
    特点：
    1. 一次性分析，多次使用（缓存分析结果）
    2. 提供简单的API接口
    3. 支持进度条显示
    4. 性能优化
    """

    def __init__(self, template_file_path=None):
        """
        初始化生成器

        Args:
            template_file_path: 模板文件路径，如果提供则自动加载分析
        """
        self.template_file_path = template_file_path
        self.analysis_cache_file = "repayment_analysis_cache.pkl"
        self.period_analysis = defaultdict(list)
        self.period_stats = {}
        self.period_summary = {}
        self.period_plans = {}
        self.is_analyzed = False

        # 如果提供了模板文件路径，自动加载
        if template_file_path and os.path.exists(template_file_path):
            self.load_and_analyze_file(template_file_path)

    def load_and_analyze_file(self, file_path, use_cache=True, force_reload=False):
        """
        加载并分析还款计划文件，支持缓存

        Args:
            file_path: 还款计划文件路径
            use_cache: 是否使用缓存
            force_reload: 是否强制重新分析
        """
        # 检查缓存
        if use_cache and not force_reload:
            cache_data = self._load_cache()
            if cache_data and cache_data.get("template_file_path") == file_path:
                print("✅ 使用缓存的分析数据")
                self._load_from_cache(cache_data)
                return True

        print(f"正在加载文件: {file_path}")
        start_time = time.time()

        try:
            # 读取TXT文件
            df = pd.read_csv(file_path, sep="|")

            # 提取唯一的借据号
            unique_loan_nos = df["loanApplyNo"].unique()
            print(f"发现 {len(unique_loan_nos)} 个借据")

            # 使用进度条显示分析进度
            for i, loan_no in enumerate(tqdm(unique_loan_nos, desc="分析借据进度")):
                # 提取该借据的数据
                loan_data = df[df["loanApplyNo"] == loan_no].copy()

                # 分析这个借据
                analysis_result = self._analyze_single_loan(loan_data)

                if analysis_result:
                    period = analysis_result["installment_cnt"]
                    self.period_analysis[period].append(
                        {"loan_no": loan_no, "analysis": analysis_result}
                    )

            # 计算统计信息
            self._calculate_period_statistics()
            self._extract_template_plans()

            # 保存缓存
            if use_cache:
                self._save_cache(file_path)

            self.is_analyzed = True

            elapsed_time = time.time() - start_time
            print(f"✅ 文件分析完成！耗时: {elapsed_time:.2f}秒")
            self.show_period_summary()

            return True

        except Exception as e:
            print(f"❌ 分析文件时出错: {e}")
            return False

    def _load_cache(self):
        """加载缓存数据"""
        if os.path.exists(self.analysis_cache_file):
            try:
                with open(self.analysis_cache_file, "rb") as f:
                    return pickle.load(f)
            except:
                return None
        return None

    def _save_cache(self, template_file_path):
        """保存缓存数据"""
        cache_data = {
            "template_file_path": template_file_path,
            "period_analysis": dict(self.period_analysis),
            "period_stats": self.period_stats,
            "period_summary": self.period_summary,
            "period_plans": self.period_plans,
            "cache_timestamp": time.time(),
        }

        try:
            with open(self.analysis_cache_file, "wb") as f:
                pickle.dump(cache_data, f)
            print("✅ 分析数据已缓存")
        except Exception as e:
            print(f"❌ 缓存保存失败: {e}")

    def _load_from_cache(self, cache_data):
        """从缓存加载数据"""
        self.period_analysis = defaultdict(list, cache_data["period_analysis"])
        self.period_stats = cache_data["period_stats"]
        self.period_summary = cache_data["period_summary"]
        self.period_plans = cache_data["period_plans"]
        self.is_analyzed = True

    def generate_plan(
        self,
        loan_amount,
        installment_count,
        loan_apply_no,
        start_date="20250227",
        output_file=None,
        generate_loan_file=True,
    ):
        """
        生成还款计划的主要API接口，支持借款文件生成

        Args:
            loan_amount: 借款金额
            installment_count: 期数
            loan_apply_no: 借据号 (必填)
            start_date: 开始日期 (YYYYMMDD格式)
            output_file: 输出文件路径 (可选)
            generate_loan_file: 是否生成借款文件 (默认True)

        Returns:
            DataFrame: 生成的还款计划
        """
        if not self.is_analyzed:
            print("❌ 请先加载分析数据")
            return None

        # 检查期数是否支持
        if installment_count not in self.period_plans:
            available_periods = sorted(self.period_plans.keys())
            print(f"❌ 期数 {installment_count} 不支持")
            print(f"   可用期数: {available_periods}")
            return None

        # 生成还款计划
        plan_df = self._generate_repayment_plan(
            loan_amount, installment_count, start_date, loan_apply_no
        )

        # 保存还款计划到文件
        if not output_file:
            # 自动生成文件名：plan_{start_date}.txt
            output_file = f"plan_{start_date}.txt"

        self._save_plan_to_file(plan_df, output_file)

        # 生成借款文件（如果启用）
        if generate_loan_file:
            cap_loan_no = plan_df["capLoanNo"].iloc[0]  # 从还款计划中获取capLoanNo
            loan_file = self.generate_loan_file(
                loan_apply_no, cap_loan_no, loan_amount, installment_count, start_date
            )
            print(f"✅ 借款文件已保存到: {loan_file}")

        print(f"✅ 还款计划已保存到: {output_file}")

        return plan_df

    def generate_multiple_plans(self, plans_config, generate_loan_files=True):
        """
        批量生成多个还款计划，支持借款文件生成

        Args:
            plans_config: 计划配置列表，每个配置包含:
                {
                    'loan_amount': 金额,
                    'installment_count': 期数,
                    'loan_apply_no': 借据号,
                    'start_date': 开始日期
                }
            generate_loan_files: 是否生成借款文件 (默认True)

        Returns:
            dict: 生成的还款计划字典 {文件名: DataFrame}
        """
        results = {}
        loan_file_results = {}

        # 按日期分组配置，用于批量生成借款文件
        date_groups = {}
        for config in plans_config:
            start_date = config.get("start_date", "20250227")
            if start_date not in date_groups:
                date_groups[start_date] = []
            date_groups[start_date].append(config)

        for i, config in enumerate(tqdm(plans_config, desc="生成还款计划进度")):
            try:
                # 生成还款计划（不自动生成借款文件，由批量逻辑统一处理）
                plan_df = self.generate_plan(
                    loan_amount=config["loan_amount"],
                    installment_count=config["installment_count"],
                    loan_apply_no=config["loan_apply_no"],
                    start_date=config.get("start_date", "20250227"),
                    generate_loan_file=False,  # 禁用单个生成，由批量逻辑处理
                )

                if plan_df is not None:
                    # 自动生成的文件名格式为 plan_{start_date}.txt
                    start_date = config.get("start_date", "20250227")
                    filename = f"plan_{start_date}.txt"
                    results[filename] = plan_df

                    # 保存capLoanNo用于借款文件生成
                    config["cap_loan_no"] = plan_df["capLoanNo"].iloc[0]

            except Exception as e:
                print(f"❌ 生成计划 {i+1} 失败: {e}")

        # 批量生成借款文件（如果启用）
        if generate_loan_files:
            for start_date, configs in date_groups.items():
                try:
                    loan_file = f"loan_{start_date}.txt"
                    self._generate_combined_loan_file(configs, loan_file)
                    loan_file_results[start_date] = loan_file
                    print(f"✅ 借款文件已保存到: {loan_file}")
                except Exception as e:
                    print(f"❌ 生成借款文件 {start_date} 失败: {e}")

        # 合并结果
        combined_results = {"plan_files": results, "loan_files": loan_file_results}

        return combined_results

    def get_supported_periods(self):
        """获取支持的期数列表"""
        return sorted(self.period_plans.keys()) if self.is_analyzed else []

    def get_period_statistics(self, period=None):
        """获取期数统计信息"""
        if not self.is_analyzed:
            return None

        if period:
            return self.period_stats.get(period)
        else:
            return self.period_stats

    def _generate_repayment_plan(
        self, loan_amount, installment_count, start_date, loan_apply_no
    ):
        """生成还款计划的核心逻辑"""
        # 获取样板数据
        template_loan = self.period_plans[installment_count]
        template_analysis = template_loan["analysis"]
        template_df = template_analysis["raw_data"].sort_values("installCnt")

        # 获取本金比例
        if "avg_principal_ratios" in self.period_stats[installment_count]:
            principal_ratios = self.period_stats[installment_count][
                "avg_principal_ratios"
            ]
        else:
            principal_ratios = template_analysis["principal_ratios"]

        # 生成capLoanNo - 格式：J25022701208127A30MZHG31QZ4LC
        # 使用日期和随机字符生成
        date_part = start_date[2:]  # 取后6位，如250227
        random_part = "".join(
            random.choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=20)
        )
        cap_loan_no = f"J{date_part}{random_part}"

        # 处理日期
        try:
            start_date_dt = datetime.strptime(start_date, "%Y%m%d")
        except:
            start_date_dt = datetime.strptime("20250227", "%Y%m%d")

        # 获取费率结构
        fee_structure = template_analysis["fee_structure"]
        regular_fee_structure = fee_structure.get("regular", {})
        last_fee_structure = fee_structure.get("last", regular_fee_structure)

        # 计算费用
        regular_fee = round(
            loan_amount * regular_fee_structure.get("fee_rate", 0)
        )  # 四舍五入
        regular_other_fee = round(
            loan_amount * regular_fee_structure.get("other_fee_rate", 0)
        )  # 四舍五入
        last_fee = round(
            loan_amount * last_fee_structure.get("fee_rate", 0)
        )  # 四舍五入
        last_other_fee = round(
            loan_amount * last_fee_structure.get("other_fee_rate", 0)
        )  # 四舍五入

        # 生成还款计划
        repayment_plan = []

        for i in range(1, installment_count + 1):
            # 本金比例
            principal_ratio = (
                principal_ratios[i - 1] if i - 1 < len(principal_ratios) else 0
            )
            principal_portion = round(loan_amount * principal_ratio)  # 四舍五入

            # 还款日期（固定为传入的start_date）
            pay_date = start_date_dt

            # 利息计算
            template_interest_rate = (
                template_df[template_df["installCnt"] == i]["totalInterest"].iloc[0]
                / template_analysis["loan_amt"]
            )
            interest = round(loan_amount * template_interest_rate)  # 四舍五入

            # 费用计算
            if i == installment_count:
                fee = last_fee
                other_fee = last_other_fee
            else:
                fee = regular_fee
                other_fee = regular_other_fee

            total_payment = principal_portion + interest + fee + other_fee

            # 结束日期（按月递增计算）
            end_date = start_date_dt + relativedelta(months=i)

            plan_record = {
                "loanApplyNo": loan_apply_no,
                "capLoanNo": cap_loan_no,
                "loanAmt": round(loan_amount),  # 四舍五入
                "installCnt": i,
                "payDate": pay_date.strftime("%Y%m%d"),
                "endDate": end_date.strftime("%Y%m%d"),
                "payOffDate": "",
                "totalAmt": round(total_payment),  # 四舍五入
                "totalPrincipal": round(principal_portion),  # 四舍五入
                "totalFee": round(fee),  # 四舍五入
                "totalInterest": round(interest),  # 四舍五入
                "totalOverdueInterest": 0,
                "repayAmt": 0,
                "repayPrincipal": 0,
                "repayFee": 0,
                "repayInterest": 0,
                "repayOverdueInterest": 0,
                "preAmt": 0,
                "prePrincipal": 0,
                "preFee": 0,
                "preInterest": 0,
                "preROverdueInterest": 0,
                "settledStatus": "11",
                "orderStatus": "00",
                "totalOtherFee": round(other_fee),  # 四舍五入
                "repayOtherFee": 0,
                "preOtherFee": 0,
            }

            repayment_plan.append(plan_record)

        return pd.DataFrame(repayment_plan)

    def _save_plan_to_file(self, plan_df, output_file):
        """保存还款计划到文件"""
        plan_df.to_csv(output_file, sep="|", index=False)

    def generate_loan_file(
        self,
        loan_apply_no,
        cap_loan_no,
        loan_amt,
        install_cnt,
        pay_date,
        output_file=None,
    ):
        """
        生成借款文件

        Args:
            loan_apply_no: 贷款申请编号
            cap_loan_no: 资金方贷款编号
            loan_amt: 贷款金额
            install_cnt: 分期期数
            pay_date: 放款日期
            output_file: 输出文件路径

        Returns:
            str: 生成的借款文件路径
        """
        if not output_file:
            output_file = f"loan_{pay_date}.txt"

        # 借款文件字段配置（参考gen_bill_file.py）
        year_rate = "0.359805"
        cap_rate = "0.12"
        asset_side = "HLCX"
        cap_code = "XYXJ"

        loan_header = [
            "loanApplyNo",
            "capLoanNo",
            "transDate",
            "payDate",
            "transAmt",
            "totalCnt",
            "yearRate",
            "capRate",
            "assetSide",
            "capCode",
        ]

        loan_data = [
            loan_apply_no,
            cap_loan_no,
            pay_date,
            pay_date,
            str(loan_amt),
            str(install_cnt),
            year_rate,
            cap_rate,
            asset_side,
            cap_code,
        ]

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("|".join(loan_header) + "\n")
            f.write("|".join(loan_data) + "\n")

        return output_file

    def _generate_combined_loan_file(self, configs, output_file):
        """
        为多个配置生成合并的借款文件

        Args:
            configs: 配置列表
            output_file: 输出文件路径
        """
        # 借款文件字段配置
        year_rate = "0.359805"
        cap_rate = "0.12"
        asset_side = "HLCX"
        cap_code = "XYXJ"

        loan_header = [
            "loanApplyNo",
            "capLoanNo",
            "transDate",
            "payDate",
            "transAmt",
            "totalCnt",
            "yearRate",
            "capRate",
            "assetSide",
            "capCode",
        ]

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("|".join(loan_header) + "\n")

            # 为每个配置生成一行数据
            for config in configs:
                if "cap_loan_no" in config:
                    # 使用start_date作为pay_date（两者相同）
                    pay_date = config.get("start_date", "20250227")
                    data_row = [
                        config["loan_apply_no"],
                        config["cap_loan_no"],
                        pay_date,
                        pay_date,
                        str(config["loan_amount"]),
                        str(config["installment_count"]),
                        year_rate,
                        cap_rate,
                        asset_side,
                        cap_code,
                    ]
                    f.write("|".join(data_row) + "\n")

    # 以下方法继承自原FixedPlanLoanAnalyzer
    def _analyze_single_loan(self, loan_df):
        """分析单个借据的还款计划"""
        try:
            loan_df["installCnt"] = pd.to_numeric(
                loan_df["installCnt"], errors="coerce"
            )

            loan_amt = float(loan_df["loanAmt"].iloc[0])
            installment_cnt = int(loan_df["installCnt"].max())

            numeric_cols = [
                "totalAmt",
                "totalPrincipal",
                "totalFee",
                "totalInterest",
                "totalOtherFee",
            ]
            for col in numeric_cols:
                loan_df[col] = pd.to_numeric(loan_df[col], errors="coerce")

            total_repayment = loan_df["totalAmt"].sum()
            total_interest = loan_df["totalInterest"].sum()
            total_fee = loan_df["totalFee"].sum()
            total_other_fee = loan_df["totalOtherFee"].sum()
            total_fees = total_fee + total_other_fee

            fee_structure = self._analyze_fee_structure(loan_df, loan_amt)
            interest_rate, apr = self._calculate_apr(loan_df, loan_amt)
            principal_ratios = loan_df["totalPrincipal"].values / loan_amt

            return {
                "loan_amt": loan_amt,
                "installment_cnt": installment_cnt,
                "total_repayment": total_repayment,
                "total_interest": total_interest,
                "total_fees": total_fees,
                "fee_structure": fee_structure,
                "interest_rate": interest_rate,
                "apr": apr,
                "principal_ratios": principal_ratios.tolist(),
                "raw_data": loan_df,
            }

        except Exception as e:
            print(f"分析借据时出错: {e}")
            return None

    def _analyze_fee_structure(self, loan_df, loan_amt):
        """分析费率结构"""
        fee_structure = {}
        loan_df = loan_df.sort_values("installCnt")

        regular_periods = loan_df[
            loan_df["installCnt"] < loan_df["installCnt"].max()
        ].copy()
        if not regular_periods.empty:
            regular_periods.loc[:, "fee_rate"] = regular_periods["totalFee"] / loan_amt
            regular_periods.loc[:, "other_fee_rate"] = (
                regular_periods["totalOtherFee"] / loan_amt
            )
            regular_periods.loc[:, "total_fee_rate"] = (
                regular_periods["fee_rate"] + regular_periods["other_fee_rate"]
            )

            fee_structure["regular"] = {
                "fee_rate": regular_periods["fee_rate"].mean(),
                "other_fee_rate": regular_periods["other_fee_rate"].mean(),
                "total_fee_rate": regular_periods["total_fee_rate"].mean(),
                "fee_amount": regular_periods["totalFee"].mean(),
                "other_fee_amount": regular_periods["totalOtherFee"].mean(),
                "sample_count": len(regular_periods),
            }

        last_period = loan_df[loan_df["installCnt"] == loan_df["installCnt"].max()]
        if not last_period.empty:
            last_fee_rate = last_period["totalFee"].iloc[0] / loan_amt
            last_other_fee_rate = last_period["totalOtherFee"].iloc[0] / loan_amt
            last_total_fee_rate = last_fee_rate + last_other_fee_rate

            fee_structure["last"] = {
                "fee_rate": last_fee_rate,
                "other_fee_rate": last_other_fee_rate,
                "total_fee_rate": last_total_fee_rate,
                "fee_amount": last_period["totalFee"].iloc[0],
                "other_fee_amount": last_period["totalOtherFee"].iloc[0],
            }

        return fee_structure

    def _calculate_apr(self, loan_df, loan_amt):
        """计算年化利率"""
        try:
            loan_df = loan_df.sort_values("installCnt")
            cashflows = [-loan_amt]

            for _, row in loan_df.iterrows():
                cashflows.append(float(row["totalAmt"]))

            def npv(rate, cashflows):
                return sum([cf / (1 + rate) ** i for i, cf in enumerate(cashflows)])

            try:
                monthly_irr = newton(
                    lambda r: npv(r, cashflows), 0.01, maxiter=100, tol=1e-10
                )
            except:
                low, high = -0.99, 10.0
                for _ in range(10000):
                    mid = (low + high) / 2
                    npv_mid = npv(mid, cashflows)
                    if abs(npv_mid) < 1e-10:
                        monthly_irr = mid
                        break
                    if npv_mid > 0:
                        low = mid
                    else:
                        high = mid
                else:
                    monthly_irr = (low + high) / 2

            annual_irr = (1 + monthly_irr) ** 12 - 1
            return monthly_irr, annual_irr

        except Exception as e:
            print(f"计算年化利率时出错: {e}")
            return None, None

    def _calculate_period_statistics(self):
        """计算每个期数的统计信息"""
        for period, loans in self.period_analysis.items():
            if loans:
                apr_list = []
                interest_rate_list = []
                loan_amt_list = []
                fee_structures = []
                principal_ratios_list = []

                for loan in loans:
                    analysis = loan["analysis"]
                    apr_list.append(analysis["apr"])
                    interest_rate_list.append(analysis["interest_rate"])
                    loan_amt_list.append(analysis["loan_amt"])
                    fee_structures.append(analysis["fee_structure"])
                    principal_ratios_list.append(analysis["principal_ratios"])

                self.period_stats[period] = {
                    "sample_count": len(loans),
                    "avg_apr": np.mean(apr_list) * 100,
                    "min_apr": np.min(apr_list) * 100,
                    "max_apr": np.max(apr_list) * 100,
                    "std_apr": np.std(apr_list) * 100,
                    "avg_interest_rate": np.mean(interest_rate_list),
                    "avg_loan_amt": np.mean(loan_amt_list),
                    "min_loan_amt": np.min(loan_amt_list),
                    "max_loan_amt": np.max(loan_amt_list),
                }

                self.period_summary[period] = self._calculate_average_fee_structure(
                    fee_structures
                )

                if principal_ratios_list:
                    avg_principal_ratios = np.mean(principal_ratios_list, axis=0)
                    self.period_stats[period][
                        "avg_principal_ratios"
                    ] = avg_principal_ratios.tolist()

    def _calculate_average_fee_structure(self, fee_structures):
        """计算平均费率结构"""
        avg_structure = {}

        regular_fee_rates = []
        regular_other_fee_rates = []
        regular_total_fee_rates = []

        last_fee_rates = []
        last_other_fee_rates = []
        last_total_fee_rates = []

        for fs in fee_structures:
            if "regular" in fs:
                regular_fee_rates.append(fs["regular"]["fee_rate"])
                regular_other_fee_rates.append(fs["regular"]["other_fee_rate"])
                regular_total_fee_rates.append(fs["regular"]["total_fee_rate"])

            if "last" in fs:
                last_fee_rates.append(fs["last"]["fee_rate"])
                last_other_fee_rates.append(fs["last"]["other_fee_rate"])
                last_total_fee_rates.append(fs["last"]["total_fee_rate"])

        if regular_fee_rates:
            avg_structure["regular"] = {
                "fee_rate": np.mean(regular_fee_rates),
                "other_fee_rate": np.mean(regular_other_fee_rates),
                "total_fee_rate": np.mean(regular_total_fee_rates),
                "sample_count": len(regular_fee_rates),
            }

        if last_fee_rates:
            avg_structure["last"] = {
                "fee_rate": np.mean(last_fee_rates),
                "other_fee_rate": np.mean(last_other_fee_rates),
                "total_fee_rate": np.mean(last_total_fee_rates),
                "sample_count": len(last_fee_rates),
            }

        return avg_structure

    def _extract_template_plans(self):
        """提取样板还款计划"""
        for period, loans in self.period_analysis.items():
            if loans:
                template_loan = min(loans, key=lambda x: x["analysis"]["loan_amt"])
                self.period_plans[period] = template_loan

    def show_period_summary(self):
        """显示按期数分类的汇总信息"""
        if not self.period_stats:
            print("没有分析数据")
            return

        print("\n" + "=" * 100)
        print(
            f"{'期数':>6} {'样本数':>8} {'平均年化利率':>12} {'最低年化':>10} {'最高年化':>10} {'平均借款金额':>12}"
        )
        print("-" * 100)

        sorted_periods = sorted(self.period_stats.keys())
        for period in sorted_periods:
            stats = self.period_stats[period]
            print(
                f"{period:6d} {stats['sample_count']:8d} {stats['avg_apr']:12.2f}% "
                f"{stats['min_apr']:10.2f}% {stats['max_apr']:10.2f}% "
                f"{stats['avg_loan_amt']:12,.0f}"
            )

        print("=" * 100)


# 使用示例
def main():
    """使用示例"""
    # 初始化生成器（自动加载模板文件）
    generator = RepaymentPlanGenerator(
        r"C:\Users\admin\Desktop\哈喽催收管理\对账文件造数\20250227\plan_20250227.txt"
    )

    # 或者手动加载
    # generator = RepaymentPlanGenerator()
    # generator.load_and_analyze_file("your_template_file.txt")

    # # 生成单个还款计划
    # plan_df = generator.generate_plan(
    #     loan_amount=100000,  # 10万元
    #     installment_count=12,  # 12期
    #     loan_apply_no='202502270000000001',  # 借据号
    #     start_date='20250227'  # 自动生成文件名：plan_20250227.txt
    # )

    # 批量生成多个还款计划
    plans_config = [
        {
            "loan_amount": 100000,
            "installment_count": 12,
            "loan_apply_no": "202503010000000003",
            "start_date": "20250301",  # 自动生成文件名：plan_20250301.txt
        }
    ]

    results = generator.generate_multiple_plans(plans_config)

    # 获取支持的期数
    supported_periods = generator.get_supported_periods()
    print(f"支持的期数: {supported_periods}")


if __name__ == "__main__":
    main()
