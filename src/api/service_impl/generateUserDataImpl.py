import logging
import random
import time
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

# 使用项目中现有的用户信息生成工具
from src.utils.id_card_generator import UserInfoGenerator
# 使用API项目的公共工具类
from ..utils.validation_utils import is_empty_value
from ..utils.database_utils import get_database_manager

logger = logging.getLogger(__name__)


class GenerateUserDataImpl:
    """用户造数实现类"""

    def __init__(self):
        # 使用公共数据库管理器
        self.db_manager = get_database_manager()
        
        # 使用现有的用户信息生成工具
        self.user_generator = UserInfoGenerator()
        
        # 固定值配置
        self.relationship_options = ["1", "2", "3", "4"]  # 关系选项
        self.contract_types = ["hgpz", "fkpz", "dkxy", "zxxy", "sfxxsqs", "dbxy"]  # 合同类型
        self.contract_names = ["回购凭证", "放款凭证", "贷款协议", "担保咨询协议", "三方信息授权书", "担保协议"]  # 合同名称
        self.attachment_names = ["回购凭证", "放款凭证", "贷款协议", "担保咨询协议", "三方信息授权书", "担保协议", "活体影像", "身份证反面", "身份证正面"]  # 附件名称
        self.file_types = ["pdf", "pdf", "pdf", "pdf", "pdf", "pdf", "jpg", "jpg", "jpg"]  # 文件类型
        
        # 固定文件ID和OSS ID（按照需求文档中的示例）
        self.fixed_file_ids = [
            "FILE_1350185086018932902", "FILE_1350185086018932901", "FILE_1350185086018932736",
            "FILE_1333640877107597312", "FILE_1333640873647296512", "FILE_1333640870317019136",
            "FILE_1333302103514046464", "FILE_1333302100859052032", "FILE_1333302097881096192"
        ]
        self.fixed_oss_ids = [
            "2019027099670659073", "2019026963636797442", "2018562913064800257",
            "2018563130451382274", "2018562124283990017", "2018562662580965378",
            "2018534178924089346", "2018523245912870913", "2018530226300080130"
        ]

    def _get_connection(self):
        """获取数据库连接"""
        return self.db_manager.get_connection()

    def _generate_random_number(self, length: int) -> str:
        """生成指定位数的随机数字"""
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])

    def _generate_phone(self) -> str:
        """生成随机手机号 - 使用现有的工具"""
        # 使用项目中现有的手机号生成方法
        return self.user_generator.generate_phone_number()

    def _generate_name(self) -> str:
        """生成随机姓名 - 使用现有的工具"""
        return self.user_generator.generate_name()

    def _generate_id_card(self) -> str:
        """生成随机身份证号 - 使用现有的工具"""
        # 使用generate_id_card_data方法生成完整的身份证数据，然后提取身份证号
        id_card_data = self.user_generator.generate_id_card_data()
        return id_card_data.get("id_number", "")

    def _generate_bank_card(self) -> str:
        """生成随机银行卡号 - 使用现有的工具"""
        return self.user_generator.generate_bank_card_number()

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        return str(int(time.time() * 1000))

    def _is_empty_value(self, value) -> bool:
        """判断值是否为空（未传、空字符串、None、null）"""
        return is_empty_value(value)

    async def generate_user_data(self, **kwargs) -> Dict[str, Any]:
        """生成用户数据主方法"""
        try:
            # 获取原始参数（不重新生成，用于存在性校验）
            original_guarantor_loan_no = kwargs.get('guarantor_loan_no')
            original_loan_apply_no = kwargs.get('loan_apply_no')
            
            # 数据存在性校验（使用原始参数）
            logger.info(f"开始数据存在性校验: guarantor_loan_no={original_guarantor_loan_no}, loan_apply_no={original_loan_apply_no}")
            check_result = await self.check_user_exists(original_guarantor_loan_no, original_loan_apply_no)
            logger.info(f"存在性校验结果: {check_result}")
            
            if check_result["exists"]:
                return {
                    "error": "用户数据已存在",
                    "check_result": check_result,
                    "message": "请勿重复插入用户数据"
                }
            
            # 生成唯一标识（只有在数据不存在时才生成）
            guarantor_loan_no = original_guarantor_loan_no
            if is_empty_value(guarantor_loan_no):
                guarantor_loan_no = f"APPLY_{self._generate_random_number(19)}"
            
            loan_apply_no = original_loan_apply_no
            if is_empty_value(loan_apply_no):
                loan_apply_no = self._generate_random_number(19)
            
            # 生成基础数据（使用新的空值判断逻辑）
            phone = kwargs.get('phone')
            if self._is_empty_value(phone):
                phone = self._generate_phone()
            
            name_OCR = kwargs.get('name_OCR')
            if self._is_empty_value(name_OCR):
                name_OCR = self._generate_name()
            
            id_card_no_OCR = kwargs.get('id_card_no_OCR')
            if self._is_empty_value(id_card_no_OCR):
                id_card_no_OCR = self._generate_id_card()
            
            bank_card_no = kwargs.get('bank_card_no')
            if self._is_empty_value(bank_card_no):
                bank_card_no = self._generate_bank_card()
            
            # 生成联系人数据（使用新的空值判断逻辑）
            relationship_A = kwargs.get('relationship_A')
            if self._is_empty_value(relationship_A):
                relationship_A = random.choice(self.relationship_options)
            
            relationship_B = kwargs.get('relationship_B')
            if self._is_empty_value(relationship_B):
                relationship_B = random.choice(self.relationship_options)
            
            phone_A = kwargs.get('phone_A')
            if self._is_empty_value(phone_A):
                phone_A = self._generate_phone()
            
            phone_B = kwargs.get('phone_B')
            if self._is_empty_value(phone_B):
                phone_B = self._generate_phone()
            
            name_A = kwargs.get('name_A')
            if self._is_empty_value(name_A):
                name_A = self._generate_name()
            
            name_B = kwargs.get('name_B')
            if self._is_empty_value(name_B):
                name_B = self._generate_name()
            
            # 生成OpenID
            open_id = f"_{self._generate_random_number(30)}"
            
            # 使用固定的文件ID和OSS ID（按照需求文档要求）
            file_ids = self.fixed_file_ids
            oss_ids = self.fixed_oss_ids
            
            # 生成合同编号
            contract_nos = [
                f"hgpz_{self._generate_random_number(19)}",
                f"fkpz_{self._generate_random_number(19)}",
                f"dkxy_{self._generate_random_number(19)}",
                f"zxxy_{self._generate_random_number(19)}",
                f"sfxxsqs_{self._generate_random_number(19)}",
                f"dbxy_{self._generate_random_number(19)}"
            ]
            
            # 插入数据库
            connection = self._get_connection()
            try:
                with connection.cursor() as cursor:
                    # 1. 插入hl_user_info表
                    user_sql = """
                    INSERT INTO hl_user_info 
                    (guarantor_loan_no, loan_apply_no, phone, phone_enc, phone_md5, marital, monthly_income, education, job, 
                     province, city, district, work_unit, work_addr, work_property, addr_detail, industry, create_time, update_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(user_sql, (
                        guarantor_loan_no, loan_apply_no, phone, None, None, 2, 7, 4, 1,
                        '310000', '310100', '310112', '深圳哈行网络科技有限公司', '', None, '上海上海市闵行区疏影路711号东苑新天地33-1301', 109,
                        datetime.now(), datetime.now()
                    ))
                    
                    # 2. 插入hl_linkman_info表
                    linkman_sql = """
                    INSERT INTO hl_linkman_info 
                    (guarantor_loan_no, loan_apply_no, relationship_A, name_A, phone_A, phone_A_enc, phone_A_md5, 
                     relationship_B, name_B, phone_B, phone_B_enc, phone_B_md5, create_time, update_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(linkman_sql, (
                        guarantor_loan_no, loan_apply_no, relationship_A, name_A, phone_A, None, None,
                        relationship_B, name_B, phone_B, None, None, datetime.now(), datetime.now()
                    ))
                    
                    # 3. 插入hl_id_card_info表
                    id_card_sql = """
                    INSERT INTO hl_id_card_info 
                    (guarantor_loan_no, loan_apply_no, id_type, name_OCR, id_card_no_OCR, id_card_no_ocr_enc, id_card_no_ocr_md5, 
                     begin_time_OCR, duetime_OCR, id_address_province, id_address_city, id_address_area, 
                     address_ocr, sex_OCR, ethnic_OCR, issue_org_OCR, nationality, 
                     front_file_id, opposite_file_id, living_influence_file_id, living_time, create_time, update_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(id_card_sql, (
                        guarantor_loan_no, loan_apply_no, '1', name_OCR, id_card_no_OCR, None, None,
                        '20181019', '20381019', '440000', '440300', '440305',
                        '广东省深圳市南山区高新南四道10号', 1, '汉', '深圳市公安局南山分局', 'CHN',
                        file_ids[8], file_ids[7], file_ids[6], None, datetime.now(), datetime.now()
                    ))
                    
                    # 4. 插入hl_contract_info表（6份合同）
                    contract_sql = """
                    INSERT INTO hl_contract_info 
                    (order_no, contract_no, contract_type, contract_name, file_id, create_time, update_time, app_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    for i in range(6):
                        app_status = 'N' if i == 1 else None  # 只有放款凭证有app_status
                        cursor.execute(contract_sql, (
                            guarantor_loan_no, contract_nos[i], self.contract_types[i], 
                            self.contract_names[i], file_ids[i], datetime.now(), datetime.now(), app_status
                        ))
                    
                    # 5. 插入hl_bank_card_info表
                    bank_card_sql = """
                    INSERT INTO hl_bank_card_info 
                    (guarantor_loan_no, loan_apply_no, bank_code, id_card_no, id_card_no_enc, id_card_no_md5, 
                     user_mobile, user_mobile_enc, user_mobile_md5, user_name, bank_card_no, bank_card_no_enc, bank_card_no_md5, 
                     create_time, update_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(bank_card_sql, (
                        guarantor_loan_no, loan_apply_no, '0104', id_card_no_OCR, None, None,
                        phone, None, None, name_OCR, bank_card_no, None, None,
                        datetime.now(), datetime.now()
                    ))
                    
                    # 6. 插入hl_attachment_info表（9份附件）
                    attachment_sql = """
                    INSERT INTO hl_attachment_info 
                    (attachments_id, order_no, file_name, file_path, file_oss_id, file_type, attachment_info, create_time, update_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    for i in range(9):
                        cursor.execute(attachment_sql, (
                            file_ids[i], guarantor_loan_no, self.attachment_names[i], None, oss_ids[i], self.file_types[i], None,
                            datetime.now(), datetime.now()
                        ))
                    
                    # 7. 插入hl_loan_app_info表
                    loan_app_sql = """
                    INSERT INTO hl_loan_app_info 
                    (guarantor_loan_no, loan_apply_no, open_id, order_type, loan_purpose, term, 
                     repay_method, order_status, order_desc, apply_time, apply_status, apply_channel, 
                     product_no, hq_examine_time, zf_examine_time, create_time, update_time, module_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(loan_app_sql, (
                        guarantor_loan_no, loan_apply_no, open_id, 'loan', '1', kwargs['term'],
                        '2', 'S', '成功', datetime.now(), 'ZFS', 'hl', 'hlLoan',
                        datetime.now(), datetime.now(), datetime.now(), datetime.now(), kwargs['module_type']
                    ))
                    
                    connection.commit()
                    
                    # 返回详细的关键信息
                    return {
                        "basic_info": {
                            "guarantor_loan_no": guarantor_loan_no,
                            "loan_apply_no": loan_apply_no,
                            "phone": phone,
                            "name_OCR": name_OCR,
                            "id_card_no_OCR": id_card_no_OCR,
                            "bank_card_no": bank_card_no,
                            "open_id": open_id,
                            "term": kwargs['term'],
                            "module_type": kwargs['module_type']
                        },
                        "contact_info": {
                            "relationship_A": relationship_A,
                            "name_A": name_A,
                            "phone_A": phone_A,
                            "relationship_B": relationship_B,
                            "name_B": name_B,
                            "phone_B": phone_B
                        },
                        "file_info": {
                            "attachment_files": [
                                {"file_name": self.attachment_names[i], "file_id": file_ids[i], "oss_id": oss_ids[i]} 
                                for i in range(9)
                            ],
                            "contract_files": [
                                {"contract_name": self.contract_names[i], "contract_no": contract_nos[i], "file_id": file_ids[i]} 
                                for i in range(6)
                            ]
                        },
                        "summary": {
                            "tables_created": 7,
                            "total_records": 7 + 1 + 1 + 6 + 1 + 9 + 1,  # 各表记录数总和
                            "tables": [
                                "hl_user_info", "hl_linkman_info", "hl_id_card_info", 
                                "hl_contract_info", "hl_bank_card_info", "hl_attachment_info", "hl_loan_app_info"
                            ]
                        },
                        "message": "用户数据生成成功，已插入7个相关数据表"
                    }
                    
            except Exception as e:
                connection.rollback()
                raise e
            finally:
                connection.close()
                
        except Exception as e:
            logger.error(f"生成用户数据失败: {str(e)}")
            raise e

    async def check_user_exists(self, guarantor_loan_no: str = None, loan_apply_no: str = None) -> Dict[str, Any]:
        """检查用户是否存在（通过担保编号或申请号）"""
        try:
            if is_empty_value(guarantor_loan_no) and is_empty_value(loan_apply_no):
                return {
                    "exists": False,
                    "message": "未提供担保编号或申请号",
                    "record_counts": {},
                    "total_records": 0
                }
            
            connection = self._get_connection()
            
            try:
                with connection.cursor() as cursor:
                    # 首先确定要使用的担保编号
                    actual_guarantor_loan_no = guarantor_loan_no
                    
                    # 如果只提供了申请号，需要查询对应的担保编号
                    if is_empty_value(guarantor_loan_no) and not is_empty_value(loan_apply_no):
                        loan_no_sql = "SELECT guarantor_loan_no FROM hl_user_info WHERE loan_apply_no = %s"
                        cursor.execute(loan_no_sql, (loan_apply_no,))
                        loan_result = cursor.fetchone()
                        if loan_result:
                            actual_guarantor_loan_no = loan_result['guarantor_loan_no']
                    
                    # 如果最终没有担保编号，说明数据不存在
                    if is_empty_value(actual_guarantor_loan_no):
                        return {
                            "guarantor_loan_no": guarantor_loan_no,
                            "loan_apply_no": loan_apply_no,
                            "exists": False,
                            "record_counts": {},
                            "total_records": 0,
                            "message": "用户数据不存在"
                        }
                    
                    # 使用担保编号检查所有表
                    check_sql = """
                    SELECT 
                        (SELECT COUNT(*) FROM hl_user_info WHERE guarantor_loan_no = %s) as user_count,
                        (SELECT COUNT(*) FROM hl_linkman_info WHERE guarantor_loan_no = %s) as linkman_count,
                        (SELECT COUNT(*) FROM hl_id_card_info WHERE guarantor_loan_no = %s) as id_card_count,
                        (SELECT COUNT(*) FROM hl_bank_card_info WHERE guarantor_loan_no = %s) as bank_card_count,
                        (SELECT COUNT(*) FROM hl_loan_app_info WHERE guarantor_loan_no = %s) as loan_app_count,
                        (SELECT COUNT(*) FROM hl_contract_info WHERE order_no = %s) as contract_count,
                        (SELECT COUNT(*) FROM hl_attachment_info WHERE order_no = %s) as attachment_count,
                        (SELECT COUNT(*) FROM hl_loan_info WHERE guarantor_loan_no = %s) as loan_info_count,
                        (SELECT COUNT(*) FROM hl_plan_info WHERE guarantor_loan_no = %s) as plan_info_count
                    """
                    
                    # 总共9个占位符，全部使用同一个担保编号
                    params = [actual_guarantor_loan_no] * 9
                    
                    cursor.execute(check_sql, tuple(params))
                    result = cursor.fetchone()
                    
                    exists = any(result.values()) if result else False
                    
                    return {
                        "guarantor_loan_no": actual_guarantor_loan_no,
                        "original_guarantor_loan_no": guarantor_loan_no,
                        "loan_apply_no": loan_apply_no,
                        "exists": exists,
                        "record_counts": {
                            "hl_user_info": result["user_count"] if result else 0,
                            "hl_linkman_info": result["linkman_count"] if result else 0,
                            "hl_id_card_info": result["id_card_count"] if result else 0,
                            "hl_bank_card_info": result["bank_card_count"] if result else 0,
                            "hl_loan_app_info": result["loan_app_count"] if result else 0,
                            "hl_contract_info": result["contract_count"] if result else 0,
                            "hl_attachment_info": result["attachment_count"] if result else 0,
                            "hl_loan_info": result["loan_info_count"] if result else 0,
                            "hl_plan_info": result["plan_info_count"] if result else 0
                        },
                        "total_records": sum(result.values()) if result else 0,
                        "message": "用户数据已存在" if exists else "用户数据不存在"
                    }
                    
            except Exception as e:
                raise e
            finally:
                connection.close()
                
        except Exception as e:
            logger.error(f"检查用户存在性失败: {str(e)}")
            raise e