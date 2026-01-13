import pymysql
import random
import string
import uuid
from datetime import datetime
import logging
from typing import Optional, Dict, Any, List, Tuple

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataGeneratorService:
    def __init__(self, db_config: Dict[str, Any]):
        """
        初始化数据生成服务
        
        Args:
            db_config: 数据库配置字典，包含host, port, user, password, database
        """
        self.db_config = db_config
        self.conn = None
        self.cursor = None
        
    def connect_db(self) -> bool:
        """连接数据库"""
        try:
            self.conn = pymysql.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                charset='utf8mb4',
                autocommit=False  # 使用事务
            )
            self.cursor = self.conn.cursor(cursor=pymysql.cursors.DictCursor)
            logger.info("数据库连接成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False
    
    def disconnect_db(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("数据库连接已关闭")
    
    def execute_query(self, sql: str, params: Optional[Tuple] = None) -> List[Dict]:
        """执行查询"""
        try:
            self.cursor.execute(sql, params)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"查询执行失败: {e}, SQL: {sql}")
            return []
    
    def execute_insert(self, sql: str, params: Optional[Tuple] = None) -> bool:
        """执行插入"""
        try:
            self.cursor.execute(sql, params)
            return True
        except Exception as e:
            logger.error(f"插入执行失败: {e}, SQL: {sql}")
            return False
    
    def generate_customer_id(self) -> str:
        """生成唯一的客户ID"""
        # 使用UUID生成唯一ID
        return f"CT{str(uuid.uuid4()).replace('-', '')[:16]}"

    
    def get_bank_name_by_card_number(self, card_number: str) -> str:
        """
        根据银行卡号判断银行名称
        
        Args:
            card_number: 银行卡号
            
        Returns:
            银行名称
        """
        if not card_number:
            return "未知银行"
        
        # 常见的银行卡BIN号（简化版）
        bank_bins = {
            # 中国银行
            '622760': '中国银行',
            '621785': '中国银行',
            '621569': '中国银行',
            # 工商银行
            '622202': '工商银行',
            '622203': '工商银行',
            '621225': '工商银行',
            # 建设银行
            '622700': '建设银行',
            '621700': '建设银行',
            # 农业银行
            '622848': '农业银行',
            '622845': '农业银行',
            '621336': '农业银行',
            # 招商银行
            '622588': '招商银行',
            '622609': '招商银行',
            '622575': '招商银行',
            # 交通银行
            '622262': '交通银行',
            '621059': '交通银行',
            # 民生银行
            '622620': '民生银行',
            '621691': '民生银行',
            # 兴业银行
            '622909': '兴业银行',
            '622908': '兴业银行',
            # 中信银行
            '622698': '中信银行',
            '622690': '中信银行',
            # 浦发银行
            '622516': '浦发银行',
            '622517': '浦发银行',
            # 平安银行
            '622155': '平安银行',
            '622156': '平安银行',
            # 邮储银行
            '622150': '邮储银行',
            '622151': '邮储银行',
        }
        
        # 根据前6位判断
        for prefix, bank_name in bank_bins.items():
            if card_number.startswith(prefix):
                return bank_name
        
        # 如果不在已知列表中，根据卡号长度和格式猜测
        if len(card_number) == 16:
            return "借记卡/信用卡"
        elif len(card_number) == 19:
            return "借记卡"
        else:
            return "未知银行"
    
    def get_user_data_for_insert(self, guarantor_loan_no: str, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        获取插入user_info表所需的数据
        
        Args:
            guarantor_loan_no: 融担进件申请流水号
            customer_id: 生成的客户ID
        
        Returns:
            Dict包含以下字段:
            - customer_id: 客户ID
            - dept_id: 随机部门ID
            - job_id: 随机岗位ID
            - name: 姓名
            - id_type: 证件类型(固定为'身份证')
            - id_number: 证件号码
            - phone: 手机号
            - gender: 性别
            - province: 省份
            - city: 城市
            - area: 随机区
            - id_start_date: 身份证开始日期
            - id_end_date: 身份证失效日期
            - marital_status: 婚姻状况
            - education: 教育程度
            - address: 居住地址
            - email: 随机邮箱
        """
        try:
            # 查询hl_user_info和hl_id_card_info表数据
            sql = """
            SELECT 
                hui.phone, hui.marital, hui.education, hui.province, hui.city, hui.district, hui.addr_detail,
                hici.name_OCR, hici.id_card_no_OCR, hici.sex_OCR, hici.begin_time_OCR, hici.duetime_OCR
            FROM cfloan_biz.hl_user_info hui
            LEFT JOIN cfloan_biz.hl_id_card_info hici ON hui.guarantor_loan_no = hici.guarantor_loan_no
            WHERE hui.guarantor_loan_no = %s
            """
            
            result = self.execute_query(sql, (guarantor_loan_no,))
            
            if not result:
                logger.warning(f"未找到guarantor_loan_no为{guarantor_loan_no}的用户数据")
                return None
            
            data = result[0]
            
            # 准备数据
            name = data['name_OCR']
            
            # 处理性别：1=男，2=女，其他=未知
            gender_mapping = {1: '男', 2: '女'}
            gender = gender_mapping.get(data['sex_OCR'], '未知')
            
            # 构建返回数据
            user_data = {
                'customer_id': customer_id,
                'dept_id': random.randint(1, 100),  # 随机部门ID
                'job_id': random.randint(1, 100),   # 随机岗位ID
                'name': name,
                'id_type': '身份证',  # 固定值
                'id_number': data['id_card_no_OCR'],
                'phone': data['phone'],
                'gender': gender,
                'province': data['province'],
                'city': data['city'],
                'area': data['district'] if data['district'] else None,  # 从district字段获取
                'id_start_date': data['begin_time_OCR'],
                'id_end_date': data['duetime_OCR'],
                'marital_status': str(data['marital']) if data['marital'] else None,
                'education': str(data['education']) if data['education'] else None,
                'address': data['addr_detail'],
                'email': None  # 邮箱默认为NULL
            }
            
            return user_data
            
        except Exception as e:
            logger.error(f"获取user_info数据失败: {e}")
            return None
    
    def get_contact_data_for_insert(self, guarantor_loan_no: str, customer_id: str) -> List[Dict[str, Any]]:
        """
        获取插入contact_info表所需的数据
        
        Args:
            guarantor_loan_no: 融担进件申请流水号
            customer_id: 生成的客户ID
            
        Returns:
            List[Dict] 每个Dict包含以下字段:
            - customer_id: 客户ID
            - relationship_type: 关系类型(A/B)
            - name: 姓名(A/B)
            - phone: 手机号(A/B)
            - id_type: 空字符串
            - id_number: 空字符串
            - company_name: 空字符串
        """
        try:
            # 查询hl_linkman_info表
            sql = """
            SELECT 
                relationship_A, name_A, phone_A,
                relationship_B, name_B, phone_B
            FROM cfloan_biz.hl_linkman_info 
            WHERE guarantor_loan_no = %s
            """
            
            result = self.execute_query(sql, (guarantor_loan_no,))
            
            if not result:
                logger.warning(f"未找到guarantor_loan_no为{guarantor_loan_no}的联系人数据")
                return []
            
            data = result[0]
            contact_list = []
            
            # 构建联系人A的数据
            if data.get('relationship_A') and data.get('name_A') and data.get('phone_A'):
                contact_a = {
                    'customer_id': customer_id,
                    'relationship_type': data['relationship_A'],
                    'name': data['name_A'],
                    'phone': data['phone_A'],
                    'id_type': None,
                    'id_number': None,
                    'company_name': None
                }
                contact_list.append(contact_a)
            
            # 构建联系人B的数据
            if data.get('relationship_B') and data.get('name_B') and data.get('phone_B'):
                contact_b = {
                    'customer_id': customer_id,
                    'relationship_type': data['relationship_B'],
                    'name': data['name_B'],
                    'phone': data['phone_B'],
                    'id_type': None,
                    'id_number': None,
                    'company_name': None
                }
                contact_list.append(contact_b)
            
            return contact_list
            
        except Exception as e:
            logger.error(f"获取contact_info数据失败: {e}")
            return []
    
    def get_bank_card_data_for_insert(self, guarantor_loan_no: str, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        获取插入bank_card_info表所需的数据
        
        Args:
            guarantor_loan_no: 融担进件申请流水号
            customer_id: 生成的客户ID
            
        Returns:
            Dict包含以下字段:
            - customer_id: 客户ID
            - product_no: 随机产品编号
            - bank_name: 银行名称
            - card_number: 银行卡号
            - bank_phone: 银行预留手机号
            - sign_status: 签约状态
        """
        try:
            # 查询hl_bank_card_info表
            sql = """
            SELECT 
                bank_card_no, user_mobile
            FROM cfloan_biz.hl_bank_card_info 
            WHERE guarantor_loan_no = %s
            """
            
            result = self.execute_query(sql, (guarantor_loan_no,))
            
            if not result:
                logger.warning(f"未找到guarantor_loan_no为{guarantor_loan_no}的银行卡数据")
                return None
            
            data = result[0]
            card_number = data['bank_card_no']
            
            # 根据银行卡号判断银行名称
            bank_name = self.get_bank_name_by_card_number(card_number)
            
            # 构建银行卡数据
            bank_card_data = {
                'customer_id': customer_id,
                'product_no': None,  # 默认NULL
                'bank_name': bank_name,  # 根据银行卡号判断
                'card_number': card_number,
                'bank_phone': data['user_mobile'],
                'sign_status': None  # 默认NULL
            }
            
            return bank_card_data
            
        except Exception as e:
            logger.error(f"获取bank_card_info数据失败: {e}")
            return None
    
    def get_loan_data_for_insert(self, guarantor_loan_no: str, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        获取插入loan_info表所需的数据
        
        Args:
            guarantor_loan_no: 融担进件申请流水号
            customer_id: 生成的客户ID
            
        Returns:
            Dict包含以下字段:
            - customer_id: 客户ID
            - loan_no: 借据号
            - loan_apply_no: 资产方借据号
            - cap_loan_no: 资金方借据号
            - product_no: 产品编号
            - channel: 渠道来源
            - funding_party: 资金方
            - busi_date: 借款日期
            - busi_date_ym: 放款年月
            - pay_date: 放款日期
            - due_date: 到期日期
            - paid_off_date: 结清日期
            - loan_amt: 借款金额
            - loan_term: 借款期数
            - paid_principal: 已还本金
            - paid_int_fee: 已还利息
            - paid_overdue_fee: 已还罚息
            - paid_guaranteed_fee: 已还担保费
            - paid_other_fee: 已还担保咨询费
            - reduction_principal: 已减免本金
            - reduction_interest: 已减免利息
            - reduction_overdue_interest: 已减免罚息
            - reduction_fee: 已减免担保费
            - reduction_other_fee: 已减免担保咨询费
            - loan_status: 借据状态
            - order_status: 订单状态
            - order_paid_off_date: 订单结清日期
            - repay_type: 还款方式
            - year_rate: 综合利率
            - cap_rate: 资方利率
            - guaranteed_rate: 担保费率
            - guaranteed_other_fee_rate: 担保咨询费率
            - equity_fee: 权益金额
            - buy_back: 是否回购
            - buy_back_date: 回购日期
            - module_type: 融担模式
            - compensate_status: 代偿状态
            - reduction_guaranteed_fee: 已代偿金额
            - alter_comp_principal: 代偿前还款本金
            - comp_principal: 代偿本金
            - extension_status: 是否展期
            - extension_date: 展期日期
            - tran_status: 是否转债
            - tran_date: 转债日期
            - overdue_date: 逾期日期(默认为NULL)
            - overdue_days: 当前逾期天数
            - overdue_amt: 逾期总金额(使用默认值0.00)
            - unpaid_principal: 剩余未还本金
            - asset_side: 资产方来源
            - cap_code: 贷款机构
        """
        try:
            # 查询hl_loan_info表数据
            sql = """
            SELECT 
                loan_no, loan_apply_no, cap_loan_no, product_no, channel, funding_party,
                busi_date, busi_date_ym, pay_date, due_date, paid_off_date,
                loan_amt, loan_term, loan_status, compensate_status,
                paid_principal, paid_int_fee, paid_overdue_fee, paid_guaranteed_fee,
                repay_type, year_rate, cap_rate, asset_side, cap_code,
                guaranteed_rate, equity_fee, buy_back, buy_back_date,
                reduction_principal, reduction_interest, reduction_fee, reduction_overdue_interest,
                reduction_guaranteed_fee, module_type, order_status, order_paid_off_date,
                paid_other_fee, reduction_other_fee, guaranteed_other_fee_rate,
                alter_comp_principal, comp_principal, extension_status, extension_date,
                tran_status, tran_date, overdue_days, unpaid_principal
            FROM cfloan_biz.hl_loan_info 
            WHERE guarantor_loan_no = %s
            """
            
            result = self.execute_query(sql, (guarantor_loan_no,))
            
            if not result:
                logger.warning(f"未找到guarantor_loan_no为{guarantor_loan_no}的借据数据")
                return None
            
            data = result[0]
            
            # 处理buy_back字段：yes->Y，no->N
            buy_back = None
            if data.get('buy_back'):
                buy_back = 'Y' if data['buy_back'].lower() == 'yes' else 'N' if data['buy_back'].lower() == 'no' else None
            
            # 处理compensate_status字段：已有值直接使用，否则根据逻辑判断
            compensate_status = data.get('compensate_status')
            if compensate_status:
                # 如果值为'Y'或'N'则直接使用，否则转换
                if compensate_status.upper() not in ['Y', 'N']:
                    compensate_status = 'Y' if compensate_status.lower() == 'yes' else 'N' if compensate_status.lower() == 'no' else None
            
            # 处理extension_status字段
            extension_status = None
            if data.get('extension_status'):
                extension_status = 'Y' if data['extension_status'].lower() == 'yes' else 'N' if data['extension_status'].lower() == 'no' else None
            
            # 构建借据数据
            loan_data = {
                'customer_id': customer_id,
                'loan_no': data['loan_no'],
                'loan_apply_no': data['loan_apply_no'],
                'cap_loan_no': data['cap_loan_no'],
                'product_no': data['product_no'],
                'channel': data['channel'],
                'funding_party': data['funding_party'],
                'busi_date': data['busi_date'],
                'busi_date_ym': data['busi_date_ym'],
                'pay_date': data['pay_date'],
                'due_date': data['due_date'],
                'paid_off_date': data['paid_off_date'],
                'loan_amt': data['loan_amt'] if data['loan_amt'] else 0.0000,
                'loan_term': data['loan_term'],
                'paid_principal': data['paid_principal'] if data['paid_principal'] else 0.0000,
                'paid_int_fee': data['paid_int_fee'] if data['paid_int_fee'] else 0.0000,
                'paid_overdue_fee': data['paid_overdue_fee'] if data['paid_overdue_fee'] else 0.0000,
                'paid_guaranteed_fee': data['paid_guaranteed_fee'] if data['paid_guaranteed_fee'] else 0.0000,
                'paid_other_fee': data['paid_other_fee'] if data['paid_other_fee'] else 0.00,
                'reduction_principal': data['reduction_principal'] if data['reduction_principal'] else 0.00,
                'reduction_interest': data['reduction_interest'] if data['reduction_interest'] else 0.00,
                'reduction_overdue_interest': data['reduction_overdue_interest'] if data['reduction_overdue_interest'] else 0.00,
                'reduction_fee': data['reduction_fee'] if data['reduction_fee'] else 0.00,
                'reduction_other_fee': data['reduction_other_fee'] if data['reduction_other_fee'] else 0.00,
                'loan_status': data['loan_status'],
                'order_status': data['order_status'],
                'order_paid_off_date': data['order_paid_off_date'],
                'repay_type': data['repay_type'],
                'year_rate': data['year_rate'] if data['year_rate'] else 0.000000,
                'cap_rate': data['cap_rate'] if data['cap_rate'] else 0.000000,
                'guaranteed_rate': data['guaranteed_rate'] if data['guaranteed_rate'] else 0.000000,
                'guaranteed_other_fee_rate': data['guaranteed_other_fee_rate'] if data['guaranteed_other_fee_rate'] else 0.000000,
                'equity_fee': data['equity_fee'] if data['equity_fee'] else 0.0000,
                'buy_back': buy_back,
                'buy_back_date': data['buy_back_date'],
                'module_type': data['module_type'],
                'compensate_status': compensate_status,
                'reduction_guaranteed_fee': data['reduction_guaranteed_fee'] if data['reduction_guaranteed_fee'] else 0.00,
                'alter_comp_principal': data['alter_comp_principal'] if data['alter_comp_principal'] else 0.00,
                'comp_principal': data['comp_principal'] if data['comp_principal'] else 0.00,
                'extension_status': extension_status,
                'extension_date': data['extension_date'],
                'tran_status': data['tran_status'],
                'tran_date': data['tran_date'],
                'overdue_date': None,  # 默认NULL
                'overdue_days': data['overdue_days'],
                'overdue_amt': 0.00,  # 使用默认值
                'unpaid_principal': data['unpaid_principal'] if data['unpaid_principal'] else 0.00,
                'asset_side': data['asset_side'],
                'cap_code': data['cap_code']
            }
            
            return loan_data
            
        except Exception as e:
            logger.error(f"获取loan_info数据失败: {e}")
            return None
    
    def get_plan_data_for_insert(self, guarantor_loan_no: str) -> List[Dict[str, Any]]:
        """
        获取插入plan_info表所需的数据
        
        Args:
            guarantor_loan_no: 融担进件申请流水号
            
        Returns:
            List[Dict] 每个Dict包含以下字段:
            - product_no: 产品编号
            - loan_no: 借据号
            - loan_apply_no: 资产方借据号
            - cap_loan_no: 资金方借据号
            - loan_amt: 借款金额
            - loan_term: 借款期数
            - pay_date: 放款日期
            - end_date: 应还日期
            - paid_off_date: 本期结清日期
            - overdue_days: 逾期天数
            - settled_status: 本期结清状态
            - loan_paid_off_date: 当期借据结清日期
            - order_status: 订单状态
            - total_amt: 应还总金额
            - total_principal: 应还本金
            - total_interest: 应还利息
            - total_overdue_interest: 应还罚息
            - total_fee: 应还担保费
            - total_other_fee: 应还担保咨询费
            - total_guarantee_overdue_interest: 应还担保罚息
            - repay_amt: 实还总金额
            - repay_principal: 实还本金
            - repay_interest: 实还利息
            - repay_overdue_interest: 实还罚息
            - repay_fee: 实还担保费
            - repay_other_fee: 实还担保咨询费
            - repay_total_guarantee_overdue_interest: 实还担保罚息
            - pre_amt: 优惠或减免总金额
            - pre_principal: 优惠或减免本金
            - pre_interest: 优惠或减免利息
            - pre_overdue_interest: 优惠或减免罚息
            - pre_fee: 优惠或减免担保费
            - pre_other_fee: 减免担保咨询费
            - pre_guarantee_overdue_interest: 减免担保罚息
            - init_amt: 初始应还总金额
            - init_principal: 初始应还本金
            - init_interest: 初始应还利息
            - init_overdue_interest: 初始应还罚息
            - init_fee: 初始应还担保费
            - init_other_fee: 初始应还担保咨询费
            - comp_status: 当期代偿状态
        """
        try:
            # 查询hl_plan_info表数据
            sql = """
            SELECT 
                product_no, loan_no, loan_apply_no, cap_loan_no, loan_amt, loan_term,
                pay_date, end_date, paid_off_date, overdue_days, settled_status,
                loan_paid_off_date, order_status, total_amt, total_principal,
                total_interest, total_overdue_interest, total_fee, total_other_fee,
                total_guarantee_overdue_interest, repay_amt, repay_principal,
                repay_interest, repay_overdue_interest, repay_fee, repay_other_fee,
                repay_total_guarantee_overdue_interest, pre_amt, pre_principal,
                pre_interest, pre_overdue_interest, pre_fee, pre_other_fee,
                pre_guarantee_overdue_interest, init_amt, init_principal,
                init_interest, init_overdue_interest, init_fee, init_other_fee,
                comp_status
            FROM cfloan_biz.hl_plan_info 
            WHERE guarantor_loan_no = %s
            ORDER BY end_date  # 按应还日期排序
            """
            
            results = self.execute_query(sql, (guarantor_loan_no,))
            
            if not results:
                logger.warning(f"未找到guarantor_loan_no为{guarantor_loan_no}的还款计划数据")
                return []
            
            plan_list = []
            for data in results:
                # 构建还款计划数据
                plan_data = {
                    'product_no': data['product_no'],
                    'loan_no': data['loan_no'],
                    'loan_apply_no': data['loan_apply_no'],
                    'cap_loan_no': data['cap_loan_no'],
                    'loan_amt': data['loan_amt'] if data['loan_amt'] else 0.0000,
                    'loan_term': data['loan_term'],
                    'pay_date': data['pay_date'],
                    'end_date': data['end_date'],
                    'paid_off_date': data['paid_off_date'],
                    'overdue_days': data['overdue_days'] if data['overdue_days'] else 0,
                    'settled_status': data['settled_status'],
                    'loan_paid_off_date': data['loan_paid_off_date'],
                    'order_status': data['order_status'],
                    'total_amt': data['total_amt'] if data['total_amt'] else 0.0000,
                    'total_principal': data['total_principal'] if data['total_principal'] else 0.0000,
                    'total_interest': data['total_interest'] if data['total_interest'] else 0.0000,
                    'total_overdue_interest': data['total_overdue_interest'] if data['total_overdue_interest'] else 0.0000,
                    'total_fee': data['total_fee'] if data['total_fee'] else 0.0000,
                    'total_other_fee': data['total_other_fee'] if data['total_other_fee'] else 0.00,
                    'total_guarantee_overdue_interest': data['total_guarantee_overdue_interest'] if data['total_guarantee_overdue_interest'] else 0.0000,
                    'repay_amt': data['repay_amt'] if data['repay_amt'] else 0.0000,
                    'repay_principal': data['repay_principal'] if data['repay_principal'] else 0.0000,
                    'repay_interest': data['repay_interest'] if data['repay_interest'] else 0.0000,
                    'repay_overdue_interest': data['repay_overdue_interest'] if data['repay_overdue_interest'] else 0.0000,
                    'repay_fee': data['repay_fee'] if data['repay_fee'] else 0.0000,
                    'repay_other_fee': data['repay_other_fee'] if data['repay_other_fee'] else 0.00,
                    'repay_total_guarantee_overdue_interest': data['repay_total_guarantee_overdue_interest'] if data['repay_total_guarantee_overdue_interest'] else 0.0000,
                    'pre_amt': data['pre_amt'] if data['pre_amt'] else 0.0000,
                    'pre_principal': data['pre_principal'] if data['pre_principal'] else 0.0000,
                    'pre_interest': data['pre_interest'] if data['pre_interest'] else 0.0000,
                    'pre_overdue_interest': data['pre_overdue_interest'] if data['pre_overdue_interest'] else 0.0000,
                    'pre_fee': data['pre_fee'] if data['pre_fee'] else 0.0000,
                    'pre_other_fee': data['pre_other_fee'] if data['pre_other_fee'] else 0.00,
                    'pre_guarantee_overdue_interest': data['pre_guarantee_overdue_interest'] if data['pre_guarantee_overdue_interest'] else 0.0000,
                    'init_amt': data['init_amt'] if data['init_amt'] else 0.00,
                    'init_principal': data['init_principal'] if data['init_principal'] else 0.00,
                    'init_interest': data['init_interest'] if data['init_interest'] else 0.00,
                    'init_overdue_interest': data['init_overdue_interest'] if data['init_overdue_interest'] else 0.00,
                    'init_fee': data['init_fee'] if data['init_fee'] else 0.00,
                    'init_other_fee': data['init_other_fee'] if data['init_other_fee'] else 0.00,
                    'comp_status': data['comp_status']
                }
                plan_list.append(plan_data)
            
            logger.info(f"获取到 {len(plan_list)} 条还款计划数据")
            return plan_list
            
        except Exception as e:
            logger.error(f"获取plan_info数据失败: {e}")
            return []
    
    def insert_user_info(self, user_data: Dict[str, Any]) -> bool:
        """插入数据到user_info表"""
        try:
            # 先检查身份证号是否已存在
            check_sql = "SELECT COUNT(*) as count FROM csadmin.user_info WHERE id_number = %s"
            check_result = self.execute_query(check_sql, (user_data['id_number'],))
            
            if check_result and check_result[0]['count'] > 0:
                logger.warning(f"身份证号 {user_data['id_number']} 已存在，跳过插入user_info数据")
                return True  # 返回True表示跳过插入，不算失败
            
            sql = """
            INSERT INTO csadmin.user_info (
                customer_id, dept_id, job_id, name, id_type, id_number, phone, gender,
                province, city, area, id_start_date, id_end_date, marital_status, education,
                address, email, create_time, update_time
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, NOW(), NOW()
            )
            """
            
            params = (
                user_data['customer_id'], user_data['dept_id'], user_data['job_id'], 
                user_data['name'], user_data['id_type'], user_data['id_number'], 
                user_data['phone'], user_data['gender'],
                user_data['province'], user_data['city'], user_data['area'], 
                user_data['id_start_date'], user_data['id_end_date'], 
                user_data['marital_status'], user_data['education'],
                user_data['address'], user_data['email']
            )
            
            success = self.execute_insert(sql, params)
            if success:
                logger.info(f"成功插入user_info数据，customer_id: {user_data['customer_id']}")
            return success
                
        except Exception as e:
            logger.error(f"插入user_info数据失败: {e}")
            return False
    
    def insert_contact_info(self, contact_list: List[Dict[str, Any]]) -> int:
        """批量插入数据到contact_info表，返回成功插入的数量"""
        success_count = 0
        
        for contact in contact_list:
            try:
                sql = """
                INSERT INTO csadmin.contact_info (
                    customer_id, relationship_type, name, phone, id_type, id_number,
                    company_name, created_by, updated_by, data_source, create_time, update_time
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, NOW(), NOW()
                )
                """
                
                params = (
                    contact['customer_id'], contact['relationship_type'], contact['name'], 
                    contact['phone'], contact['id_type'], contact['id_number'],
                    contact['company_name'], 'system', 'system', 'system'
                )
                
                success = self.execute_insert(sql, params)
                if success:
                    success_count += 1
                    logger.info(f"成功插入联系人数据: {contact['name']}")
                    
            except Exception as e:
                logger.error(f"插入联系人数据失败: {e}")
        
        return success_count
    
    def insert_bank_card_info(self, bank_card_data: Dict[str, Any]) -> bool:
        """插入数据到bank_card_info表"""
        try:
            # 先检查该customer_id和银行卡号是否已存在
            check_sql = "SELECT COUNT(*) as count FROM csadmin.bank_card_info WHERE customer_id = %s AND card_number = %s"
            check_result = self.execute_query(check_sql, (bank_card_data['customer_id'], bank_card_data['card_number']))
            
            if check_result and check_result[0]['count'] > 0:
                logger.warning(f"客户 {bank_card_data['customer_id']} 的银行卡号 {bank_card_data['card_number']} 已存在，跳过插入bank_card_info数据")
                return True  # 返回True表示跳过插入，不算失败
            
            sql = """
            INSERT INTO csadmin.bank_card_info (
                customer_id, product_no, bank_name, card_number, bank_phone, sign_status,
                create_time, update_time
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                NOW(), NOW()
            )
            """
            
            params = (
                bank_card_data['customer_id'], bank_card_data['product_no'], 
                bank_card_data['bank_name'], bank_card_data['card_number'], 
                bank_card_data['bank_phone'], bank_card_data['sign_status']
            )
            
            success = self.execute_insert(sql, params)
            if success:
                logger.info(f"成功插入银行卡数据，卡号: {bank_card_data['card_number']}, 银行: {bank_card_data['bank_name']}")
            return success
                
        except Exception as e:
            logger.error(f"插入bank_card_info数据失败: {e}")
            return False
    
    def insert_loan_info(self, loan_data: Dict[str, Any]) -> bool:
        """插入数据到loan_info表"""
        try:
            # 先检查借据号是否已存在
            check_sql = "SELECT COUNT(*) as count FROM csadmin.loan_info WHERE loan_no = %s"
            check_result = self.execute_query(check_sql, (loan_data['loan_no'],))
            
            if check_result and check_result[0]['count'] > 0:
                logger.warning(f"借据号 {loan_data['loan_no']} 已存在，跳过插入loan_info数据")
                return True  # 返回True表示跳过插入，不算失败
            
            sql = """
            INSERT INTO csadmin.loan_info (
                customer_id, loan_no, loan_apply_no, cap_loan_no, product_no, channel, funding_party,
                busi_date, busi_date_ym, pay_date, due_date, paid_off_date, loan_amt, loan_term,
                paid_principal, paid_int_fee, paid_overdue_fee, paid_guaranteed_fee, paid_other_fee,
                reduction_principal, reduction_interest, reduction_overdue_interest, reduction_fee, reduction_other_fee,
                loan_status, order_status, order_paid_off_date, repay_type, year_rate, cap_rate,
                guaranteed_rate, guaranteed_other_fee_rate, equity_fee, buy_back, buy_back_date,
                module_type, compensate_status, reduction_guaranteed_fee, alter_comp_principal, comp_principal,
                extension_status, extension_date, tran_status, tran_date, overdue_date, overdue_days, overdue_amt,
                unpaid_principal, asset_side, cap_code, create_time, update_time
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, NOW(), NOW()
            )
            """
            
            params = (
                loan_data['customer_id'], loan_data['loan_no'], loan_data['loan_apply_no'], 
                loan_data['cap_loan_no'], loan_data['product_no'], loan_data['channel'], 
                loan_data['funding_party'], loan_data['busi_date'], loan_data['busi_date_ym'], 
                loan_data['pay_date'], loan_data['due_date'], loan_data['paid_off_date'], 
                loan_data['loan_amt'], loan_data['loan_term'], loan_data['paid_principal'], 
                loan_data['paid_int_fee'], loan_data['paid_overdue_fee'], loan_data['paid_guaranteed_fee'], 
                loan_data['paid_other_fee'], loan_data['reduction_principal'], loan_data['reduction_interest'], 
                loan_data['reduction_overdue_interest'], loan_data['reduction_fee'], loan_data['reduction_other_fee'], 
                loan_data['loan_status'], loan_data['order_status'], loan_data['order_paid_off_date'], 
                loan_data['repay_type'], loan_data['year_rate'], loan_data['cap_rate'], 
                loan_data['guaranteed_rate'], loan_data['guaranteed_other_fee_rate'], loan_data['equity_fee'], 
                loan_data['buy_back'], loan_data['buy_back_date'], loan_data['module_type'], 
                loan_data['compensate_status'], loan_data['reduction_guaranteed_fee'], loan_data['alter_comp_principal'], 
                loan_data['comp_principal'], loan_data['extension_status'], loan_data['extension_date'], 
                loan_data['tran_status'], loan_data['tran_date'], loan_data['overdue_date'], 
                loan_data['overdue_days'], loan_data['overdue_amt'], loan_data['unpaid_principal'], 
                loan_data['asset_side'], loan_data['cap_code']
            )
            
            success = self.execute_insert(sql, params)
            if success:
                logger.info(f"成功插入借据数据，借据号: {loan_data['loan_no']}")
            return success
                
        except Exception as e:
            logger.error(f"插入loan_info数据失败: {e}")
            return False
    
    def insert_plan_info(self, plan_list: List[Dict[str, Any]]) -> int:
        """批量插入数据到plan_info表，返回成功插入的数量"""
        success_count = 0
    
        for plan_data in plan_list:
            try:
                # 先检查是否已存在相同loan_no和end_date的记录
                check_sql = """
                SELECT COUNT(*) as count FROM csadmin.plan_info 
                WHERE loan_no = %s AND end_date = %s
                """
                check_result = self.execute_query(check_sql, (plan_data['loan_no'], plan_data['end_date']))
                
                if check_result and check_result[0]['count'] > 0:
                    logger.warning(f"借据号 {plan_data['loan_no']} 在 {plan_data['end_date']} 的还款计划已存在，跳过插入")
                    continue  # 跳过已存在的记录
                
                sql = """
                INSERT INTO csadmin.plan_info (
                    product_no, loan_no, loan_apply_no, cap_loan_no, loan_amt, loan_term,
                    pay_date, end_date, paid_off_date, overdue_days, settled_status,
                    loan_paid_off_date, order_status, total_amt, total_principal,
                    total_interest, total_overdue_interest, total_fee, total_other_fee,
                    total_guarantee_overdue_interest, repay_amt, repay_principal,
                    repay_interest, repay_overdue_interest, repay_fee, repay_other_fee,
                    repay_total_guarantee_overdue_interest, pre_amt, pre_principal,
                    pre_interest, pre_overdue_interest, pre_fee, pre_other_fee,
                    pre_guarantee_overdue_interest, init_amt, init_principal,
                    init_interest, init_overdue_interest, init_fee, init_other_fee,
                    comp_status, create_time, update_time
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, NOW(), NOW()
                )
                """
                
                # 重新组织参数，确保数量与占位符匹配
                params = (
                    plan_data['product_no'], plan_data['loan_no'], plan_data['loan_apply_no'], 
                    plan_data['cap_loan_no'], plan_data['loan_amt'], plan_data['loan_term'],
                    plan_data['pay_date'], plan_data['end_date'], plan_data['paid_off_date'], 
                    plan_data['overdue_days'], plan_data['settled_status'], 
                    plan_data['loan_paid_off_date'], plan_data['order_status'], 
                    plan_data['total_amt'], plan_data['total_principal'], 
                    plan_data['total_interest'], plan_data['total_overdue_interest'], 
                    plan_data['total_fee'], plan_data['total_other_fee'], 
                    plan_data['total_guarantee_overdue_interest'], plan_data['repay_amt'], 
                    plan_data['repay_principal'], plan_data['repay_interest'], 
                    plan_data['repay_overdue_interest'], plan_data['repay_fee'], 
                    plan_data['repay_other_fee'], plan_data['repay_total_guarantee_overdue_interest'], 
                    plan_data['pre_amt'], plan_data['pre_principal'], plan_data['pre_interest'], 
                    plan_data['pre_overdue_interest'], plan_data['pre_fee'], 
                    plan_data['pre_other_fee'], plan_data['pre_guarantee_overdue_interest'], 
                    plan_data['init_amt'], plan_data['init_principal'], plan_data['init_interest'], 
                    plan_data['init_overdue_interest'], plan_data['init_fee'], 
                    plan_data['init_other_fee'], plan_data['comp_status']
                )
                
                # 调试：打印参数数量
                # logger.debug(f"SQL占位符数量: 41, 参数数量: {len(params)}")
                
                success = self.execute_insert(sql, params)
                if success:
                    success_count += 1
                    logger.info(f"成功插入还款计划数据，借据号: {plan_data['loan_no']}, 应还日期: {plan_data['end_date']}")
                    
            except Exception as e:
                logger.error(f"插入还款计划数据失败: {e}")
                # 打印更多调试信息
                logger.error(f"参数数量: {len(params)}, SQL: {sql}")
    
        return success_count
    
    def get_id_number_by_guarantor_loan_no(self, guarantor_loan_no: str) -> Optional[str]:
        """
        根据guarantor_loan_no查询身份证号
        
        Args:
            guarantor_loan_no: 融担进件申请流水号
            
        Returns:
            身份证号，如果未找到则返回None
        """
        try:
            sql = """
            SELECT hici.id_card_no_OCR 
            FROM cfloan_biz.hl_user_info hui
            LEFT JOIN cfloan_biz.hl_id_card_info hici ON hui.guarantor_loan_no = hici.guarantor_loan_no
            WHERE hui.guarantor_loan_no = %s
            """
            
            result = self.execute_query(sql, (guarantor_loan_no,))
            
            if result and result[0].get('id_card_no_OCR'):
                id_number = result[0]['id_card_no_OCR']
                logger.info(f"查询到身份证号: {id_number}")
                return id_number
            else:
                logger.warning(f"未找到guarantor_loan_no为{guarantor_loan_no}的身份证号")
                return None
                
        except Exception as e:
            logger.error(f"查询身份证号失败: {e}")
            return None
    
    def get_existing_customer_id_by_id_number(self, id_number: str) -> Optional[str]:
        """
        根据身份证号查询user_info表中是否已存在对应的customer_id
        
        Args:
            id_number: 身份证号
            
        Returns:
            已存在的customer_id，如果不存在则返回None
        """
        try:
            sql = "SELECT customer_id FROM csadmin.user_info WHERE id_number = %s"
            result = self.execute_query(sql, (id_number,))
            
            if result and result[0].get('customer_id'):
                customer_id = result[0]['customer_id']
                logger.info(f"身份证号 {id_number} 已存在对应的customer_id: {customer_id}")
                return customer_id
            else:
                logger.info(f"身份证号 {id_number} 在user_info表中不存在对应的customer_id")
                return None
                
        except Exception as e:
            logger.error(f"查询customer_id失败: {e}")
            return None
    
    def generate_data(self, guarantor_loan_no: str) -> Dict[str, Any]:
        """
        主接口方法：根据guarantor_loan_no生成数据
        
        Args:
            guarantor_loan_no: 融担进件申请流水号
            
        Returns:
            Dict包含执行结果:
            - success: 是否全部成功
            - message: 结果消息
            - details: 详细执行结果
        """
        logger.info(f"开始为guarantor_loan_no: {guarantor_loan_no}生成数据")
        
        # 连接数据库
        if not self.connect_db():
            return {
                'success': False,
                'message': '数据库连接失败',
                'details': {}
            }
        
        # 第一步：根据guarantor_loan_no查询身份证号
        id_number = self.get_id_number_by_guarantor_loan_no(guarantor_loan_no)
        
        if not id_number:
            return {
                'success': False,
                'message': f'未找到guarantor_loan_no为{guarantor_loan_no}的身份证号',
                'details': {}
            }
        
        # 第二步：根据身份证号查询user_info表，看是否存在对应的customer_id
        existing_customer_id = self.get_existing_customer_id_by_id_number(id_number)
        
        if existing_customer_id:
            # 如果已存在customer_id，则使用已有的customer_id
            customer_id = existing_customer_id
            logger.info(f"使用已存在的customer_id: {customer_id}")
            need_insert_user_info = False  # 不需要插入user_info数据
        else:
            # 如果不存在，则生成新的customer_id
            customer_id = self.generate_customer_id()
            logger.info(f"生成新的customer_id: {customer_id}")
            need_insert_user_info = True  # 需要插入user_info数据
        
        result = {
            'success': True,
            'message': '数据生成成功',
            'details': {
                'customer_id': customer_id,
                'user_info_inserted': False,
                'contact_info_inserted': 0,
                'bank_card_info_inserted': False,
                'loan_info_inserted': False,
                'plan_info_inserted': 0,
                'need_insert_user_info': need_insert_user_info
            }
        }
        
        try:
            # 开始事务
            self.conn.begin()
            
            # 1. 插入user_info表（只有在需要插入时才执行）
            if need_insert_user_info:
                user_data = self.get_user_data_for_insert(guarantor_loan_no, customer_id)
                if user_data:
                    insert_result = self.insert_user_info(user_data)
                    if insert_result:
                        result['details']['user_info_inserted'] = True
                        logger.info(f"成功插入user_info数据，customer_id: {customer_id}")
                    else:
                        result['success'] = False
                        result['message'] = 'user_info表插入失败'
                else:
                    result['success'] = False
                    result['message'] = '未找到user_info相关数据'
                    logger.warning(f"未找到guarantor_loan_no: {guarantor_loan_no}的user_info数据")
            else:
                # 如果不需要插入user_info，说明customer_id已存在
                result['details']['user_info_inserted'] = False
                logger.info("customer_id已存在，跳过user_info表插入")
            
            # 2. 插入contact_info表
            if result['success']:
                contact_list = self.get_contact_data_for_insert(guarantor_loan_no, customer_id)
                if contact_list:
                    inserted_count = self.insert_contact_info(contact_list)
                    result['details']['contact_info_inserted'] = inserted_count
                    if inserted_count == 0:
                        logger.warning("联系人数据插入失败")
                else:
                    logger.warning("未找到联系人数据，跳过插入")
            
            # 3. 插入bank_card_info表
            if result['success']:
                bank_card_data = self.get_bank_card_data_for_insert(guarantor_loan_no, customer_id)
                if bank_card_data:
                    insert_result = self.insert_bank_card_info(bank_card_data)
                    if insert_result:
                        result['details']['bank_card_info_inserted'] = True
                    else:
                        result['success'] = False
                        result['message'] = 'bank_card_info表插入失败'
                else:
                    logger.warning("未找到银行卡数据，跳过插入")
            
            # 4. 插入loan_info表
            if result['success']:
                loan_data = self.get_loan_data_for_insert(guarantor_loan_no, customer_id)
                if loan_data:
                    insert_result = self.insert_loan_info(loan_data)
                    if insert_result:
                        result['details']['loan_info_inserted'] = True
                    else:
                        result['success'] = False
                        result['message'] = 'loan_info表插入失败'
                else:
                    logger.warning("未找到借据数据，跳过插入")
            
            # 5. 插入plan_info表（新增）
            if result['success']:
                plan_list = self.get_plan_data_for_insert(guarantor_loan_no)
                if plan_list:
                    inserted_count = self.insert_plan_info(plan_list)
                    result['details']['plan_info_inserted'] = inserted_count
                    logger.info(f"成功插入 {inserted_count} 条还款计划数据")
                    if inserted_count == 0:
                        logger.warning("还款计划数据插入失败")
                else:
                    logger.warning("未找到还款计划数据，跳过插入")
            
            # 提交事务
            if result['success']:
                self.conn.commit()
                logger.info(f"guarantor_loan_no: {guarantor_loan_no} 的数据生成完成")
            else:
                self.conn.rollback()
                logger.error(f"guarantor_loan_no: {guarantor_loan_no} 的数据生成失败，已回滚")
                
        except Exception as e:
            self.conn.rollback()
            result['success'] = False
            result['message'] = f'数据生成过程中出现异常: {str(e)}'
            logger.error(f"数据生成异常: {e}")
            
        finally:
            # 关闭数据库连接
            self.disconnect_db()
        
        return result


# 使用示例
if __name__ == "__main__":
    import sys
    import os
    
    # 添加项目根目录到Python路径，以便导入settings
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    try:
        from config.settings import BIZ_DATABASES
        
        # 使用第一个数据库配置（可以根据需要选择不同的数据库）
        if BIZ_DATABASES:
            db_config = BIZ_DATABASES[0]  # 使用第一个数据库配置
            print(f"使用数据库配置: {db_config['name']}")
            
            # 创建服务实例
            service = DataGeneratorService(db_config)
            
            # 测试数据生成
            test_loan_no = "APPLY_1289337558739476480"  # 替换为实际的guarantor_loan_no
            result = service.generate_data(test_loan_no)
            
            print("执行结果:")
            print(f"成功: {result['success']}")
            print(f"消息: {result['message']}")
            print(f"详情: {result['details']}")
        else:
            print("错误: 未找到数据库配置，请检查settings.py中的BIZ_DATABASES配置")
            
    except ImportError as e:
        print(f"导入配置失败: {e}")
        print("请确保settings.py文件存在且包含正确的BIZ_DATABASES配置")
    except Exception as e:
        print(f"执行过程中出现错误: {e}")