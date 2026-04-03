import requests
import time
import logging
from typing import Dict, Any

from ..utils.micro_login import MicroLogin

logger = logging.getLogger(__name__)


class AddMerchantAndSuppliersImpl:
    """新增商户和供应商实现类"""

    def __init__(self):
        self.base_urls = {
            "cdms": "http://47.106.192.83/stage-cdms-api"
        }
        self.micro_login = MicroLogin()

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        return str(int(time.time()))

    def _build_headers(self, token: str = None) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        if token:
            headers["Cookie"] = f"XXL_JOB_LOGIN_IDENTITY=7b226964223a312c22757365726e616d65223a2261646d696e222c2270617373776f7264223a226531306164633339343962613539616262653536653035376632306638383365222c22726f6c65223a312c227065726d697373696f6e223a6e756c6b7d; sidebarStatus=1; Luna-Token={token}; Luna-UserCn=%E6%B5%8B%E8%AF%9520000; Luna-Org=10000; Luna-User=test20000"
            headers["x-authorization"] = token
        
        return headers

    def login(self) -> str:
        """登录接口 - 使用工具类"""
        return self.micro_login.login()

    def add_merchant(self, enterpriseName: str, creditCode: str, legalPersonName: str, merchantId: str, token: str) -> Dict[str, Any]:
        """新增商户接口"""
        timestamp = self._get_timestamp()
        
        params = {
            "enterpriseName": enterpriseName,
            "creditCode": creditCode,
            "legalPersonName": legalPersonName,
            "merchantId": merchantId,
            "merchantName": f"SHMC{timestamp}",
            "alipayAccountName": f"ZFBZHMC{timestamp}",
            "alipayAccount": f"ZFBZHM{timestamp}",
            "guaranteeFeeRate": "0.01",
            "status": "y",
            "remark": "",
            "operateUser": "test20000"
        }
        
        url = f"{self.base_urls['cdms']}/cdms/merchant/addMerchant"
        
        logger.info(f"新增商户请求: {url} with params: {params}")
        
        response = requests.get(url, params=params, headers=self.micro_login.get_auth_headers(token))
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"新增商户响应: {result}")
            return result
        else:
            raise Exception(f"HTTP错误: {response.status_code}")

    def get_suppliers_list(self, merchantId: str, token: str) -> Dict[str, Any]:
        """查询供应商列表"""
        url = f"{self.base_urls['cdms']}/cdms/merchant/suppliersDetails/{merchantId}"
        
        logger.info(f"查询供应商列表请求: {url}")
        
        response = requests.get(url, headers=self.micro_login.get_auth_headers(token))
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"查询供应商列表响应: {result}")
            return result
        else:
            raise Exception(f"HTTP错误: {response.status_code}")

    def edit_suppliers(self, merchantId: str, legalPersonName: str, idNumber: str, bankCardNo: str, bankName: str, openBankName: str, token: str) -> Dict[str, Any]:
        """编辑供应商接口 - 合并现有供应商和新增供应商"""
        timestamp = self._get_timestamp()
        
        # 1. 查询现有供应商列表
        suppliers_result = self.get_suppliers_list(merchantId, token)
        
        if not suppliers_result.get("success"):
            raise Exception(f"查询供应商列表失败: {suppliers_result.get('message')}")
        
        # 2. 构建供应商列表
        suppliers_dto_list = []
        index = 0
        
        # 添加现有供应商
        existing_suppliers = suppliers_result.get("data", [])
        for supplier in existing_suppliers:
            suppliers_dto_list.append({
                "supplierName": supplier.get("supplierName", ""),
                "bankAccount": supplier.get("bankAccount", ""),  # 银行户名
                "idNumber": supplier.get("idNumber", ""),  # 身份证号
                "bankCardNo": supplier.get("bankCardNo", ""),
                "bankName": supplier.get("bankName", ""),
                "openBankName": supplier.get("openBankName", ""),
                "unionBankNo": supplier.get("unionBankNo", ""),
                "accountType": supplier.get("accountType", "1"),
                "index": index
            })
            index += 1
        
        # 3. 添加新增供应商
        suppliers_dto_list.append({
            "supplierName": f"GYSMC{timestamp}",
            "bankAccount": legalPersonName,  # 银行户名使用法人姓名
            "idNumber": idNumber,  # 身份证号，必填
            "bankCardNo": bankCardNo,
            "bankName": bankName,
            "openBankName": openBankName,
            "unionBankNo": f"LHH{timestamp}",
            "accountType": "1",
            "index": index
        })
        
        # 4. 构建请求数据
        data = {
            "merchantId": merchantId,
            "suppliersDtoList": suppliers_dto_list
        }
        
        url = f"{self.base_urls['cdms']}/cdms/merchant/editSuppliers"
        
        logger.info(f"编辑供应商请求: {url} with data: {data}")
        
        response = requests.post(url, json=data, headers=self.micro_login.get_auth_headers(token))
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"编辑供应商响应: {result}")
            return result
        else:
            raise Exception(f"HTTP错误: {response.status_code}")