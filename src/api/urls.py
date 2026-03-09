"""
FastAPI URL路由配置 - 集成版
"""

from fastapi import APIRouter
from typing import Dict, List, Any, Callable


def create_route_config(
    method: str,
    path: str,
    controller_method: Callable,
    summary: str = "",
    tags: List[str] = None,
) -> Dict[str, Any]:
    """创建路由配置"""
    return {
        "method": method,
        "path": path,
        "controller_method": controller_method,
        "summary": summary,
        "tags": tags or [],
    }


class RouteMapper:
    """路由映射器"""

    def __init__(self, router: APIRouter):
        self.router = router

    def map_routes(self, route_configs: List[Dict[str, Any]]):
        """映射路由配置"""
        for config in route_configs:
            self._add_route(config)

    def _add_route(self, config: Dict[str, Any]):
        """添加单个路由"""
        method = config["method"]
        path = config["path"]
        controller_method = config["controller_method"]
        summary = config.get("summary", "")
        tags = config.get("tags", [])

        # 根据HTTP方法添加路由
        if method.upper() == "GET":
            self.router.get(path, summary=summary, tags=tags)(controller_method)
        elif method.upper() == "POST":
            self.router.post(path, summary=summary, tags=tags)(controller_method)
        elif method.upper() == "PUT":
            self.router.put(path, summary=summary, tags=tags)(controller_method)
        elif method.upper() == "DELETE":
            self.router.delete(path, summary=summary, tags=tags)(controller_method)
        elif method.upper() == "PATCH":
            self.router.patch(path, summary=summary, tags=tags)(controller_method)


# 导入API服务
from .api_services.addMerchantAndSuppliers import AddMerchantAndSuppliers
from .api_services.creditOrderApproval import CreditOrderApproval
from .api_services.generateUserData import GenerateUserData
from .api_services.deleteUserData import DeleteUserData
from .api_services.creditPreOperation import CreditPreOperation
from .api_services.modifyPhone import ModifyPhone
from .api_services.riskControlReRun import RiskControlReRun

# 创建主路由器
api_router = APIRouter()

# 创建路由映射器
mapper = RouteMapper(api_router)

# 创建API实例
add_merchant_and_suppliers_api = AddMerchantAndSuppliers()
credit_order_approval_api = CreditOrderApproval()
generate_user_data_api = GenerateUserData()
delete_user_data_api = DeleteUserData()
credit_pre_operation_api = CreditPreOperation()
modify_phone_api = ModifyPhone()
risk_control_rerun_api = RiskControlReRun()

# 路由配置 - 使用create_route_config函数
url_routes = [
    # 商户管理接口
    create_route_config(
        "POST",
        "/merchant/add-and-suppliers",
        add_merchant_and_suppliers_api.add_merchant_and_suppliers,
        "新增商户和供应商接口",
        ["商户管理"],
    ),
    # 授信订单审批接口
    create_route_config(
        "POST",
        "/credit-order/approval",
        credit_order_approval_api.credit_order_approval,
        "授信订单审批接口",
        ["授信订单审批"],
    ),
    # 用户造数接口
    create_route_config(
        "POST",
        "/user/generate-data",
        generate_user_data_api.generate_user_data,
        "用户造数接口",
        ["用户管理"],
    ),
    # 用户删除接口
    create_route_config(
        "POST",
        "/user/delete-data",
        delete_user_data_api.delete_user_data,
        "用户删除接口",
        ["用户管理"],
    ),
    # 征信前置操作接口
    create_route_config(
        "POST",
        "/credit/pre-operation",
        credit_pre_operation_api.credit_pre_operation,
        "征信前置操作接口",
        ["征信前置"],
    ),
    # 修改用户手机号接口
    create_route_config(
        "POST",
        "/user/modify-phone",
        modify_phone_api.modify_phone,
        "修改用户手机号接口",
        ["用户管理"],
    ),
    # 风控重跑接口
    create_route_config(
        "POST",
        "/risk-control/rerun",
        risk_control_rerun_api.risk_control_rerun,
        "风控重跑接口",
        ["风控管理"],
    ),
]

# 映射路由
mapper.map_routes(url_routes)
