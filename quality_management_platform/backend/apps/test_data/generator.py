from __future__ import annotations

import random
import string
from datetime import date, datetime
from typing import Any

from .image_generators import BusinessLicenseImageGenerator, IdCardImageGenerator


RANDOM_VALUE = "random"
DATE_FORMATS = ("%Y%m%d", "%Y-%m-%d", "%Y.%m.%d")
PHONE_PREFIXES = [
    "130",
    "131",
    "132",
    "133",
    "134",
    "135",
    "136",
    "137",
    "138",
    "139",
    "145",
    "147",
    "149",
    "150",
    "151",
    "152",
    "153",
    "155",
    "156",
    "157",
    "158",
    "159",
    "166",
    "173",
    "175",
    "176",
    "177",
    "178",
    "180",
    "181",
    "182",
    "183",
    "184",
    "185",
    "186",
    "187",
    "188",
    "189",
    "192",
    "198",
    "199",
]
LAST_NAMES = list("赵钱孙李周吴郑王冯陈卫蒋沈韩杨朱秦许何吕张孔曹严华金魏陶姜")
FIRST_NAMES = [
    "安",
    "宁",
    "宇",
    "可",
    "一",
    "子",
    "语",
    "欣",
    "雪",
    "梓",
    "英",
    "晴",
    "倩",
    "浩",
    "川",
    "晨",
    "菲",
    "琳",
    "蕾",
    "瑶",
    "昊",
    "悦",
    "茹",
    "露",
    "铎",
    "轩",
    "瑞",
    "萌",
    "尧",
    "航",
]
ETHNIC_GROUPS = [
    "随机",
    "汉",
    "满",
    "回",
    "苗",
    "壮",
    "土家",
    "蒙古",
    "藏",
    "维吾尔",
    "彝",
]
AREA_OPTIONS = [
    {"value": RANDOM_VALUE, "label": "随机"},
    {"value": "11", "label": "北京"},
    {"value": "31", "label": "上海"},
    {"value": "32", "label": "江苏"},
    {"value": "33", "label": "浙江"},
    {"value": "37", "label": "山东"},
    {"value": "41", "label": "河南"},
    {"value": "42", "label": "湖北"},
    {"value": "43", "label": "湖南"},
    {"value": "44", "label": "广东"},
    {"value": "50", "label": "重庆"},
    {"value": "51", "label": "四川"},
    {"value": "61", "label": "陕西"},
]
AREA_DETAILS = {
    "11": {
        "province": "北京市",
        "city": "北京市",
        "districts": ["朝阳区", "海淀区", "丰台区", "西城区", "东城区"],
        "authority": "北京市公安局",
        "codes": ["110101", "110105", "110108", "110106"],
    },
    "31": {
        "province": "上海市",
        "city": "上海市",
        "districts": ["浦东新区", "徐汇区", "闵行区", "长宁区", "静安区"],
        "authority": "上海市公安局",
        "codes": ["310101", "310104", "310112", "310115"],
    },
    "32": {
        "province": "江苏省",
        "city": "南京市",
        "districts": ["建邺区", "鼓楼区", "玄武区", "秦淮区", "雨花台区"],
        "authority": "江苏省公安厅",
        "codes": ["320102", "320104", "320106", "320114"],
    },
    "33": {
        "province": "浙江省",
        "city": "杭州市",
        "districts": ["西湖区", "滨江区", "余杭区", "上城区", "拱墅区"],
        "authority": "浙江省公安厅",
        "codes": ["330102", "330106", "330108", "330110"],
    },
    "37": {
        "province": "山东省",
        "city": "济南市",
        "districts": ["历下区", "槐荫区", "市中区", "天桥区", "历城区"],
        "authority": "山东省公安厅",
        "codes": ["370102", "370103", "370104", "370112"],
    },
    "41": {
        "province": "河南省",
        "city": "郑州市",
        "districts": ["金水区", "中原区", "二七区", "郑东新区", "管城回族区"],
        "authority": "河南省公安厅",
        "codes": ["410102", "410103", "410105", "410104"],
    },
    "42": {
        "province": "湖北省",
        "city": "武汉市",
        "districts": ["洪山区", "武昌区", "江汉区", "江岸区", "硚口区"],
        "authority": "湖北省公安厅",
        "codes": ["420102", "420103", "420106", "420111"],
    },
    "43": {
        "province": "湖南省",
        "city": "长沙市",
        "districts": ["岳麓区", "天心区", "开福区", "雨花区", "芙蓉区"],
        "authority": "湖南省公安厅",
        "codes": ["430102", "430103", "430104", "430111"],
    },
    "44": {
        "province": "广东省",
        "city": "深圳市",
        "districts": ["南山区", "福田区", "龙华区", "宝安区", "龙岗区"],
        "authority": "广东省公安厅",
        "codes": ["440303", "440304", "440305", "440306", "440307"],
    },
    "50": {
        "province": "重庆市",
        "city": "重庆市",
        "districts": ["渝中区", "江北区", "南岸区", "渝北区", "九龙坡区"],
        "authority": "重庆市公安局",
        "codes": ["500103", "500105", "500107", "500108", "500112"],
    },
    "51": {
        "province": "四川省",
        "city": "成都市",
        "districts": ["高新区", "武侯区", "锦江区", "青羊区", "成华区"],
        "authority": "四川省公安厅",
        "codes": ["510104", "510105", "510107", "510108"],
    },
    "61": {
        "province": "陕西省",
        "city": "西安市",
        "districts": ["雁塔区", "未央区", "碑林区", "莲湖区", "新城区"],
        "authority": "陕西省公安厅",
        "codes": ["610102", "610103", "610104", "610113"],
    },
}
BANKS = {
    "建设银行": {"储蓄卡": ["621700", "622700", "623668"], "信用卡": ["625966", "625362", "528056"]},
    "工商银行": {"储蓄卡": ["622202", "622208", "621226"], "信用卡": ["622230", "625858", "625859"]},
    "农业银行": {"储蓄卡": ["622848", "622845", "623052"], "信用卡": ["625996", "625997", "628268"]},
    "中国银行": {"储蓄卡": ["621661", "621663", "621667"], "信用卡": ["625908", "625909", "628312"]},
    "招商银行": {"储蓄卡": ["622588", "622609", "524011"], "信用卡": ["622575", "622576", "622577"]},
    "交通银行": {"储蓄卡": ["622260", "621069", "621335"], "信用卡": ["622253", "625029", "625030"]},
    "邮储银行": {"储蓄卡": ["621098", "622150", "621599"], "信用卡": ["625919", "625920", "625921"]},
    "平安银行": {"储蓄卡": ["622986", "622298", "627066"], "信用卡": ["622155", "622156", "622157"]},
}
COMPANY_TYPES = ["随机", "有限责任公司", "股份有限公司", "个人独资企业", "合伙企业", "个体工商户"]
INDUSTRY_TYPES = ["随机", "科技", "软件", "贸易", "服务", "教育", "医疗", "金融", "制造", "餐饮"]
BUSINESS_SCOPE_BY_INDUSTRY = {
    "科技": "技术开发、技术咨询、技术服务、技术转让；测试平台研发；自动化测试服务；货物及技术进出口。",
    "软件": "软件开发；计算机系统集成；数据处理服务；测试管理系统建设；应用软件服务。",
    "贸易": "国内贸易代理；电子产品、办公用品销售；供应链管理服务；货物进出口。",
    "服务": "企业管理咨询；测试服务；质量分析服务；会议会展服务；项目管理服务。",
    "教育": "教育咨询服务；培训服务；课程研发；数字化教学平台建设；企业内训服务。",
    "医疗": "医疗器械技术开发；健康管理咨询；医学研究与试验发展；信息技术服务。",
    "金融": "金融信息咨询；风控与质量分析；软件与数据服务；企业管理咨询。",
    "制造": "电子设备生产与销售；自动化设备研发；质量检测服务；工业软件开发。",
    "餐饮": "餐饮管理；食品销售；品牌策划；供应链管理；企业管理咨询。",
}


def _random_digits(length: int) -> str:
    return "".join(random.choices(string.digits, k=length))


def _parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"日期格式不正确：{value}，请使用 YYYYMMDD、YYYY-MM-DD 或 YYYY.MM.DD")


def _format_date_digits(value: date) -> str:
    return value.strftime("%Y%m%d")


def _format_display_date(value: date) -> str:
    return f"{value.year}年{value.month:02d}月{value.day:02d}日"


def _format_period_date(value: date) -> str:
    return value.strftime("%Y.%m.%d")


def _normalize_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


class TestDataGenerator:
    def __init__(self) -> None:
        self.id_card_images = IdCardImageGenerator()
        self.business_license_images = BusinessLicenseImageGenerator()

    def get_meta(self) -> dict[str, Any]:
        return {
            "defaults": self.default_config(),
            "options": {
                "ethnic_groups": ETHNIC_GROUPS,
                "areas": AREA_OPTIONS,
                "banks": list(BANKS.keys()),
                "company_types": COMPANY_TYPES,
                "industries": INDUSTRY_TYPES,
            },
        }

    def default_config(self) -> dict[str, Any]:
        return {
            "mode": "id_number",
            "min_age": 22,
            "max_age": 55,
            "age": "",
            "id_number": "",
            "name": "",
            "gender": "male",
            "ethnic_group": RANDOM_VALUE,
            "id_prefix": RANDOM_VALUE,
            "phone": "",
            "bank_name": "建设银行",
            "card_type": "debit",
            "bank_card": "",
            "company_type": RANDOM_VALUE,
            "company_name": "",
            "credit_code": "",
            "legal_representative": "",
            "address": "",
            "registered_capital": "",
            "establish_date": "",
            "business_start_date": "",
            "business_end_date": "",
            "business_scope": "",
            "industry_type": RANDOM_VALUE,
        }

    def normalize_config(self, raw: dict[str, Any] | None) -> dict[str, Any]:
        payload = raw or {}
        config = self.default_config()
        for key in config:
            if key in payload:
                config[key] = payload[key]

        config["mode"] = "age" if str(config.get("mode")) == "age" else "id_number"
        config["min_age"] = self._coerce_int(config.get("min_age"), 22)
        config["max_age"] = self._coerce_int(config.get("max_age"), 55)
        if config["min_age"] > config["max_age"]:
            config["min_age"], config["max_age"] = config["max_age"], config["min_age"]
        config["min_age"] = max(16, min(config["min_age"], 60))
        config["max_age"] = max(config["min_age"], min(config["max_age"], 60))

        text_fields = (
            "age",
            "id_number",
            "name",
            "gender",
            "ethnic_group",
            "id_prefix",
            "phone",
            "bank_name",
            "card_type",
            "bank_card",
            "company_type",
            "company_name",
            "credit_code",
            "legal_representative",
            "address",
            "registered_capital",
            "establish_date",
            "business_start_date",
            "business_end_date",
            "business_scope",
            "industry_type",
        )
        for key in text_fields:
            config[key] = _normalize_text(config.get(key))

        if config["gender"] not in {"random", "male", "female"}:
            config["gender"] = "random"
        if config["ethnic_group"] not in {RANDOM_VALUE, *ETHNIC_GROUPS}:
            config["ethnic_group"] = RANDOM_VALUE
        if config["id_prefix"] not in {RANDOM_VALUE, *AREA_DETAILS.keys()}:
            raise ValueError("身份证开头地区不正确")
        if config["bank_name"] not in BANKS:
            config["bank_name"] = "建设银行"
        if config["card_type"] not in {"debit", "credit"}:
            config["card_type"] = "debit"
        if config["company_type"] not in {RANDOM_VALUE, *COMPANY_TYPES}:
            config["company_type"] = RANDOM_VALUE
        if config["industry_type"] not in {RANDOM_VALUE, *INDUSTRY_TYPES}:
            config["industry_type"] = RANDOM_VALUE
        return config

    def generate_workspace(self, raw_config: dict[str, Any] | None = None) -> dict[str, Any]:
        config = self.normalize_config(raw_config)
        id_data = self._build_id_data(config)
        business_data = self._build_business_license_data(config, id_data)
        self._sync_business_to_id(id_data, business_data)
        return self._compose_workspace(config, id_data, business_data)

    def refresh_field(
        self,
        raw_config: dict[str, Any] | None,
        state: dict[str, Any] | None,
        field: str,
    ) -> dict[str, Any]:
        config = self.normalize_config(raw_config)
        saved_state = state or {}
        id_data = dict(saved_state.get("id_data") or {})
        business_data = dict(saved_state.get("business_data") or {})

        if not id_data:
            id_data = self._build_id_data(config)
        if not business_data:
            business_data = self._build_business_license_data(config, id_data)
            self._sync_business_to_id(id_data, business_data)

        notice = ""
        if field == "name":
            if config["name"]:
                notice = "姓名已在左侧配置区指定，未执行刷新。"
            else:
                new_name = self.generate_name()
                id_data["name"] = new_name
                if not config["legal_representative"]:
                    business_data["legal_person"] = new_name
        elif field == "id_number":
            if config["id_number"]:
                notice = "身份证号已在左侧配置区指定，未执行刷新。"
            else:
                self._refresh_id_number(config, id_data)
        elif field == "phone":
            id_data["phone_number"] = self._resolve_phone(config["phone"])
        elif field == "bank_card":
            if config["bank_card"]:
                notice = "银行卡号已在左侧配置区指定，未执行刷新。"
            else:
                id_data["bank_card_number"] = self.generate_bank_card_number(
                    config["bank_name"],
                    self._card_kind_label(config["card_type"]),
                )
        elif field == "company_name":
            if config["company_name"]:
                notice = "公司名称已在左侧配置区指定，未执行刷新。"
            else:
                business_data["company_name"] = self.generate_company_name()
        elif field == "credit_code":
            if config["credit_code"]:
                notice = "信用代码已在左侧配置区指定，未执行刷新。"
            else:
                business_data["unified_social_credit_code"] = self.generate_unified_social_credit_code()
        elif field == "legal_person":
            if config["legal_representative"]:
                notice = "法人姓名已在左侧配置区指定，未执行刷新。"
            else:
                business_data["legal_person"] = self.generate_name()
        else:
            raise ValueError("不支持的刷新字段")

        self._sync_business_to_id(id_data, business_data)
        workspace = self._compose_workspace(config, id_data, business_data)
        if notice:
            workspace["notice"] = notice
        return workspace

    def generate_user_workspace(self, raw_config: dict[str, Any] | None = None) -> dict[str, Any]:
        config = self.normalize_config(raw_config)
        id_data = self._build_id_data(config)
        return self._compose_user_workspace(config, id_data)

    def refresh_user_field(
        self,
        raw_config: dict[str, Any] | None,
        state: dict[str, Any] | None,
        field: str,
    ) -> dict[str, Any]:
        config = self.normalize_config(raw_config)
        saved_state = state or {}
        id_data = dict(saved_state.get("id_data") or {})
        if not id_data:
            id_data = self._build_id_data(config)

        notice = ""
        if field == "name":
            if config["name"]:
                notice = "姓名已在左侧配置区指定，未执行刷新。"
            else:
                id_data["name"] = self.generate_name()
        elif field == "id_number":
            if config["id_number"]:
                notice = "身份证号已在左侧配置区指定，未执行刷新。"
            else:
                self._refresh_id_number(config, id_data)
        elif field == "phone":
            id_data["phone_number"] = self._resolve_phone(config["phone"])
        elif field == "bank_card":
            if config["bank_card"]:
                notice = "银行卡号已在左侧配置区指定，未执行刷新。"
            else:
                id_data["bank_card_number"] = self.generate_bank_card_number(
                    config["bank_name"],
                    self._card_kind_label(config["card_type"]),
                )
        elif field == "address":
            id_data["address"] = config["address"] or self._generate_address(id_data["area_code"])
        else:
            raise ValueError("不支持的用户字段刷新")

        workspace = self._compose_user_workspace(config, id_data)
        if notice:
            workspace["notice"] = notice
        return workspace

    def generate_enterprise_workspace(self, raw_config: dict[str, Any] | None = None) -> dict[str, Any]:
        config = self.normalize_config(raw_config)
        seed_data = self._build_business_seed_data(config)
        business_data = self._build_business_license_data(config, seed_data)
        return self._compose_enterprise_workspace(config, business_data)

    def refresh_enterprise_field(
        self,
        raw_config: dict[str, Any] | None,
        state: dict[str, Any] | None,
        field: str,
    ) -> dict[str, Any]:
        config = self.normalize_config(raw_config)
        saved_state = state or {}
        business_data = dict(saved_state.get("business_data") or {})
        if not business_data:
            business_data = self._build_business_license_data(config, self._build_business_seed_data(config))

        notice = ""
        if field == "company_name":
            if config["company_name"]:
                notice = "公司名称已在左侧配置区指定，未执行刷新。"
            else:
                business_data["company_name"] = self.generate_company_name()
        elif field == "credit_code":
            if config["credit_code"]:
                notice = "统一社会信用代码已在左侧配置区指定，未执行刷新。"
            else:
                business_data["unified_social_credit_code"] = self.generate_unified_social_credit_code()
        elif field == "legal_person":
            if config["legal_representative"]:
                notice = "法人姓名已在左侧配置区指定，未执行刷新。"
            else:
                business_data["legal_person"] = self.generate_name()
        elif field == "address":
            if config["address"]:
                notice = "企业地址已在左侧配置区指定，未执行刷新。"
            else:
                business_data["address"] = self._generate_company_address(
                    self._resolve_area_prefix(config["id_prefix"], config["id_number"])
                )
        elif field == "registered_capital":
            if config["registered_capital"]:
                notice = "注册资本已在左侧配置区指定，未执行刷新。"
            else:
                business_data["registered_capital"] = f"{random.choice([50, 100, 200, 500, 1000, 2000])}万元"
        elif field == "business_scope":
            if config["business_scope"]:
                notice = "经营范围已在左侧配置区指定，未执行刷新。"
            else:
                industry_type = (
                    config["industry_type"]
                    if config["industry_type"] not in {"", RANDOM_VALUE, "随机"}
                    else random.choice(INDUSTRY_TYPES[1:])
                )
                business_data["industry_type"] = industry_type
                business_data["business_scope"] = BUSINESS_SCOPE_BY_INDUSTRY[industry_type]
        else:
            raise ValueError("不支持的企业字段刷新")

        workspace = self._compose_enterprise_workspace(config, business_data)
        if notice:
            workspace["notice"] = notice
        return workspace

    def generate_name(self) -> str:
        surname = random.choice(LAST_NAMES)
        given_name = random.choice(FIRST_NAMES)
        if random.random() > 0.72:
            given_name += random.choice(FIRST_NAMES)
        return f"{surname}{given_name}"

    def generate_company_name(self) -> str:
        prefix = random.choice(["优测", "数航", "智检", "云策", "星辰", "启明", "新衡", "云桥"])
        industry = random.choice(["质量", "测试", "软件", "数据", "科技", "协同", "平台"])
        suffix = random.choice(["有限公司", "科技有限公司", "数字科技有限公司", "软件有限公司"])
        tail = random.choice(["", "", "", "研发", "管理", "服务"])
        return f"{prefix}{industry}{tail}{suffix}"

    def generate_unified_social_credit_code(self) -> str:
        chars = "0123456789ABCDEFGHJKLMNPQRTUWXY"
        base = (
            random.choice(["1", "5", "9", "Y"])
            + str(random.choice([1, 2, 3, 9]))
            + random.choice(
                [
                    "110000",
                    "310000",
                    "320100",
                    "330100",
                    "370100",
                    "410100",
                    "420100",
                    "430100",
                    "440300",
                    "500000",
                    "510100",
                    "610100",
                ]
            )
            + "".join(random.choice(chars) for _ in range(9))
        )[:17]
        char_map = {char: index for index, char in enumerate(chars)}
        weights = [1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]
        total = sum(char_map[char] * weights[index] for index, char in enumerate(base))
        return base + chars[(31 - total % 31) % 31]

    def generate_bank_card_number(self, bank_name: str, card_kind: str) -> str:
        bank = BANKS.get(bank_name, BANKS["建设银行"])
        target_kind = card_kind if card_kind in bank else "储蓄卡"
        bin_code = random.choice(bank[target_kind])
        length = 19 if target_kind == "储蓄卡" and random.random() > 0.35 else 16
        payload = "".join(random.choice(string.digits) for _ in range(length - len(bin_code) - 1))
        partial = f"{bin_code}{payload}"
        return partial + self._luhn_check_digit(partial)

    def generate_id_card_images(self, data: dict[str, Any]) -> dict[str, str]:
        return self.id_card_images.generate_images_base64(data)

    def generate_business_license_image(self, data: dict[str, Any]) -> str:
        return self.business_license_images.generate_image_base64(data)

    def _compose_user_workspace(
        self,
        config: dict[str, Any],
        id_data: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "config": config,
            "id_card": {
                "data": id_data,
                "ocr": self._build_id_card_ocr(id_data),
                "images": self.generate_id_card_images(id_data),
            },
            "clipboard_text": self._build_user_clipboard_text(id_data),
        }

    def _compose_enterprise_workspace(
        self,
        config: dict[str, Any],
        business_data: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "config": config,
            "business_license": {
                "data": business_data,
                "image_base64": self.generate_business_license_image(business_data),
            },
            "clipboard_text": self._build_enterprise_clipboard_text(business_data),
        }

    def _compose_workspace(
        self,
        config: dict[str, Any],
        id_data: dict[str, Any],
        business_data: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "config": config,
            "id_card": {
                "data": id_data,
                "images": self.generate_id_card_images(id_data),
            },
            "business_license": {
                "data": business_data,
                "image_base64": self.generate_business_license_image(business_data),
            },
            "clipboard_text": self._build_clipboard_text(id_data),
        }

    def _build_id_card_ocr(self, id_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "front": {
                "name": id_data["name"],
                "gender": id_data["gender"],
                "ethnic_group": id_data["ethnic_group"],
                "birth_date": id_data["birth_date_display"],
                "address": id_data["address"],
                "id_number": id_data["id_number"],
            },
            "back": {
                "issue_authority": id_data["issue_authority"],
                "valid_period": id_data["valid_period"],
            },
        }

    def _build_business_seed_data(self, config: dict[str, Any]) -> dict[str, Any]:
        area_prefix = self._resolve_area_prefix(config["id_prefix"], config["id_number"])
        return {
            "name": config["legal_representative"] or config["name"] or self.generate_name(),
            "area_prefix": area_prefix,
        }

    def _build_id_data(self, config: dict[str, Any]) -> dict[str, Any]:
        explicit_id = config["id_number"]
        explicit_age = config["age"]
        if explicit_id and explicit_age:
            raise ValueError("年龄和身份证号只能输入一个。")

        resolved_gender = self._resolve_gender(config["gender"])
        ethnic_group = (
            config["ethnic_group"]
            if config["ethnic_group"] not in {"", RANDOM_VALUE, "随机"}
            else random.choice(ETHNIC_GROUPS[1:])
        )
        area_prefix = self._resolve_area_prefix(config["id_prefix"], explicit_id)

        if explicit_id:
            self._validate_id_number(explicit_id)
            id_number = explicit_id.strip().upper()
            area_code = id_number[:6]
            birth_date = datetime.strptime(id_number[6:14], "%Y%m%d").date()
            resolved_gender = "男" if int(id_number[16]) % 2 else "女"
        else:
            age = self._resolve_age(
                config["age"],
                config["mode"],
                config["min_age"],
                config["max_age"],
            )
            birth_date = self._birth_date_from_age(age, config["min_age"], config["max_age"])
            area_code = self._random_area_code(area_prefix)
            id_number = self._generate_id_number(area_code, birth_date, resolved_gender)

        valid_period, issue_date, expiry_date = self._generate_issue_period(birth_date)
        return {
            "name": config["name"] or self.generate_name(),
            "gender": resolved_gender,
            "ethnic_group": ethnic_group,
            "birth_date": _format_date_digits(birth_date),
            "birth_date_display": _format_display_date(birth_date),
            "address": config["address"] or self._generate_address(area_code),
            "id_number": id_number,
            "issue_authority": AREA_DETAILS[area_code[:2]]["authority"],
            "issue_date": issue_date,
            "expiry_date": expiry_date,
            "valid_period": valid_period,
            "bank_card_number": self._resolve_bank_card(config["bank_card"])
            if config["bank_card"]
            else self.generate_bank_card_number(
                config["bank_name"],
                self._card_kind_label(config["card_type"]),
            ),
            "phone_number": self._resolve_phone(config["phone"]),
            "area_code": area_code,
            "area_prefix": area_code[:2],
            "company_name": "",
            "unified_social_credit_code": "",
            "legal_representative": "",
        }

    def _build_business_license_data(
        self,
        config: dict[str, Any],
        id_data: dict[str, Any],
    ) -> dict[str, Any]:
        establish_date = _parse_date(config["establish_date"]) or self._random_past_date(1, 18)
        start_date = _parse_date(config["business_start_date"]) or establish_date
        end_date = _parse_date(config["business_end_date"]) or date(
            start_date.year + random.randint(10, 30),
            start_date.month,
            min(start_date.day, 28),
        )
        if end_date < start_date:
            raise ValueError("营业期限结束日期不能早于开始日期。")

        industry_type = (
            config["industry_type"]
            if config["industry_type"] not in {"", RANDOM_VALUE, "随机"}
            else random.choice(INDUSTRY_TYPES[1:])
        )
        company_type = (
            config["company_type"]
            if config["company_type"] not in {"", RANDOM_VALUE, "随机"}
            else random.choice(COMPANY_TYPES[1:])
        )
        registered_capital = config["registered_capital"] or f"{random.choice([50, 100, 200, 500, 1000, 2000])}万元"
        if registered_capital.isdigit():
            registered_capital = f"{registered_capital}万元"

        return {
            "company_name": config["company_name"] or self.generate_company_name(),
            "company_type": company_type,
            "industry_type": industry_type,
            "unified_social_credit_code": config["credit_code"] or self.generate_unified_social_credit_code(),
            "legal_person": config["legal_representative"] or id_data["name"],
            "registered_capital": registered_capital,
            "establish_date": _format_date_digits(establish_date),
            "establish_date_display": _format_display_date(establish_date),
            "business_term_start": _format_date_digits(start_date),
            "business_term_end": _format_date_digits(end_date),
            "business_term_display": f"{_format_display_date(start_date)} 至 {_format_display_date(end_date)}",
            "address": config["address"] or self._generate_company_address(id_data["area_prefix"]),
            "business_scope": config["business_scope"] or BUSINESS_SCOPE_BY_INDUSTRY[industry_type],
        }

    def _sync_business_to_id(
        self,
        id_data: dict[str, Any],
        business_data: dict[str, Any],
    ) -> None:
        id_data["company_name"] = business_data["company_name"]
        id_data["unified_social_credit_code"] = business_data["unified_social_credit_code"]
        id_data["legal_representative"] = business_data["legal_person"]

    def _build_clipboard_text(self, id_data: dict[str, Any]) -> str:
        lines = [
            f"name: {id_data['name']}",
            f"idNo: {id_data['id_number']}",
            f"mobile: {id_data['phone_number']}",
            f"bankCard: {id_data['bank_card_number']}",
        ]
        if id_data.get("company_name"):
            lines.append(f"company: {id_data['company_name']}")
        if id_data.get("unified_social_credit_code"):
            lines.append(f"creditCode: {id_data['unified_social_credit_code']}")
        if id_data.get("legal_representative"):
            lines.append(f"legalPerson: {id_data['legal_representative']}")
        return "\n".join(lines)

    def _build_user_clipboard_text(self, id_data: dict[str, Any]) -> str:
        return "\n".join(
            [
                f"name: {id_data['name']}",
                f"idNo: {id_data['id_number']}",
                f"mobile: {id_data['phone_number']}",
                f"bankCard: {id_data['bank_card_number']}",
                f"address: {id_data['address']}",
            ]
        )

    def _build_enterprise_clipboard_text(self, business_data: dict[str, Any]) -> str:
        return "\n".join(
            [
                f"company: {business_data['company_name']}",
                f"creditCode: {business_data['unified_social_credit_code']}",
                f"legalPerson: {business_data['legal_person']}",
                f"capital: {business_data['registered_capital']}",
                f"address: {business_data['address']}",
            ]
        )

    def _resolve_gender(self, config_gender: str) -> str:
        if config_gender == "male":
            return "男"
        if config_gender == "female":
            return "女"
        return random.choice(["男", "女"])

    def _resolve_age(self, age_text: str, mode: str, min_age: int, max_age: int) -> int | None:
        if age_text:
            if not age_text.isdigit():
                raise ValueError("年龄必须为数字。")
            age = int(age_text)
            if age < 16 or age > 60:
                raise ValueError("年龄必须在 16 到 60 岁之间。")
            return age
        if mode == "age":
            return random.randint(min_age, max_age)
        return None

    def _birth_date_from_age(self, age: int | None, min_age: int, max_age: int) -> date:
        today = date.today()
        resolved_age = age if age is not None else random.randint(min_age, max_age)
        return date(
            today.year - resolved_age,
            random.randint(1, 12),
            random.randint(1, 28),
        )

    def _resolve_area_prefix(self, value: str, id_number: str) -> str:
        if id_number:
            prefix = id_number[:2]
            if prefix not in AREA_DETAILS:
                raise ValueError("身份证号中的地区码不在支持范围内。")
            return prefix
        if value and value != RANDOM_VALUE:
            return value
        return random.choice([item["value"] for item in AREA_OPTIONS[1:]])

    def _random_area_code(self, area_prefix: str) -> str:
        return random.choice(AREA_DETAILS[area_prefix]["codes"])

    def _generate_address(self, area_code: str) -> str:
        details = AREA_DETAILS[area_code[:2]]
        district = random.choice(details["districts"])
        street = random.choice(["人民路", "创新大道", "质量路", "研发街", "软件园路", "测试路", "高新大道"])
        return f"{details['province']}{details['city']}{district}{street}{random.randint(1, 299)}号{random.randint(1, 18)}层{random.randint(101, 2808)}室"

    def _generate_company_address(self, area_prefix: str) -> str:
        details = AREA_DETAILS[area_prefix]
        district = random.choice(details["districts"])
        street = random.choice(["质量大道", "创新路", "协同行", "智测路", "云控路"])
        return f"{details['province']}{details['city']}{district}{street}{random.randint(6, 88)}号"

    def _generate_issue_period(self, birth_date: date) -> tuple[str, str, str]:
        age = date.today().year - birth_date.year
        years = 10 if age < 26 else 20 if age < 46 else 30
        issue_date = date(
            max(birth_date.year + 18, date.today().year - years),
            random.randint(1, 12),
            random.randint(1, 28),
        )
        expiry_date = date(issue_date.year + years, issue_date.month, issue_date.day)
        return (
            f"{_format_period_date(issue_date)}-{_format_period_date(expiry_date)}",
            _format_period_date(issue_date),
            _format_period_date(expiry_date),
        )

    def _resolve_phone(self, phone_input: str) -> str:
        if not phone_input:
            return random.choice(PHONE_PREFIXES) + _random_digits(8)
        if len(phone_input) == 3 and phone_input.isdigit():
            if phone_input not in PHONE_PREFIXES:
                raise ValueError("手机号前三位有误，请重新输入。")
            return phone_input + _random_digits(8)
        if len(phone_input) == 11 and phone_input.isdigit():
            if phone_input[:3] not in PHONE_PREFIXES:
                raise ValueError("手机号前三位有误，请重新输入。")
            return phone_input
        raise ValueError("手机号位数有误，请输入 3 位前缀或 11 位完整手机号。")

    def _resolve_bank_card(self, bank_card_input: str) -> str:
        cleaned = "".join(char for char in str(bank_card_input) if char.isdigit())
        if not cleaned:
            raise ValueError("银行卡号不能为空。")
        if len(cleaned) < 16 or len(cleaned) > 19:
            raise ValueError("银行卡号长度必须在 16 到 19 位之间。")
        return cleaned

    def _generate_id_number(self, area_code: str, birth_date: date, gender: str) -> str:
        sequence = random.randint(1, 999)
        if gender == "女":
            sequence = sequence if sequence % 2 == 0 else sequence + 1
        else:
            sequence = sequence if sequence % 2 == 1 else sequence + 1
        first_17 = f"{area_code}{birth_date.strftime('%Y%m%d')}{sequence:03d}"[:17]
        return first_17 + self._id_check_code(first_17)

    def _validate_id_number(self, id_number: str) -> None:
        cleaned = id_number.strip().upper()
        if len(cleaned) != 18:
            raise ValueError("身份证号必须是 18 位。")
        if not cleaned[:17].isdigit():
            raise ValueError("身份证号前 17 位必须为数字。")
        prefix = cleaned[:2]
        if prefix not in AREA_DETAILS:
            raise ValueError("身份证号中的地区码不在支持范围内。")
        try:
            birth_date = datetime.strptime(cleaned[6:14], "%Y%m%d").date()
        except ValueError as exc:
            raise ValueError("身份证号中的出生日期不正确。") from exc
        if birth_date > date.today():
            raise ValueError("身份证号中的出生日期不能晚于当前日期。")
        if self._id_check_code(cleaned[:17]) != cleaned[17]:
            raise ValueError("身份证号校验码不正确。")

    def _id_check_code(self, first_17: str) -> str:
        factors = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        codes = ["1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2"]
        total = sum(int(first_17[index]) * factors[index] for index in range(17))
        return codes[total % 11]

    def _random_past_date(self, min_years_ago: int, max_years_ago: int) -> date:
        today = date.today()
        return date(
            today.year - random.randint(min_years_ago, max_years_ago),
            random.randint(1, 12),
            random.randint(1, 28),
        )

    def _coerce_int(self, value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _refresh_id_number(self, config: dict[str, Any], id_data: dict[str, Any]) -> None:
        area_prefix = self._resolve_area_prefix(config["id_prefix"], "")
        birth_date = self._birth_date_from_age(
            self._resolve_age(
                config["age"],
                config["mode"],
                config["min_age"],
                config["max_age"],
            ),
            config["min_age"],
            config["max_age"],
        )
        area_code = self._random_area_code(area_prefix)
        valid_period, issue_date, expiry_date = self._generate_issue_period(birth_date)
        id_data.update(
            {
                "id_number": self._generate_id_number(
                    area_code,
                    birth_date,
                    id_data.get("gender") or self._resolve_gender(config["gender"]),
                ),
                "birth_date": _format_date_digits(birth_date),
                "birth_date_display": _format_display_date(birth_date),
                "address": self._generate_address(area_code),
                "issue_authority": AREA_DETAILS[area_prefix]["authority"],
                "issue_date": issue_date,
                "expiry_date": expiry_date,
                "valid_period": valid_period,
                "area_code": area_code,
                "area_prefix": area_prefix,
            }
        )

    def _luhn_check_digit(self, partial: str) -> str:
        total = 0
        for index, char in enumerate(reversed(partial)):
            value = int(char)
            if index % 2 == 0:
                value *= 2
                if value > 9:
                    value -= 9
            total += value
        return str((10 - total % 10) % 10)

    def _card_kind_label(self, card_type: str) -> str:
        return "储蓄卡" if card_type == "debit" else "信用卡"
