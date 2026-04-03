import random
import re
from datetime import datetime


class UserInfoGenerator:
    """用户信息生成"""

    def __init__(self):
        # 常见姓氏
        self.surnames = [
            "王",
            "李",
            "张",
            "刘",
            "陈",
            "杨",
            "赵",
            "黄",
            "周",
            "吴",
            "徐",
            "孙",
            "胡",
            "朱",
            "高",
            "林",
            "何",
            "郭",
            "马",
            "罗",
            "梁",
            "宋",
            "郑",
            "谢",
            "韩",
            "唐",
            "冯",
            "于",
            "董",
            "萧",
            "程",
            "曹",
            "袁",
            "邓",
            "许",
            "傅",
            "沈",
            "曾",
            "彭",
            "吕",
        ]

        # 常见名字
        self.given_names = [
            "伟",
            "芳",
            "娜",
            "秀英",
            "敏",
            "静",
            "丽",
            "强",
            "磊",
            "军",
            "洋",
            "勇",
            "艳",
            "杰",
            "娟",
            "涛",
            "明",
            "超",
            "秀兰",
            "霞",
            "平",
            "燕",
            "华",
            "辉",
            "玲",
            "丹",
            "洁",
            "红",
            "健",
            "颖",
            "琳",
            "峰",
            "鑫",
            "蕾",
            "玮",
            "婷",
            "博",
            "宇",
            "欣",
            "昊",
        ]

        # 民族列表
        self.ethnic_groups = ["汉"]

        # 省份和地区代码
        self.area_codes = {
            "11": "北京市",
            "12": "天津市",
            "13": "河北省",
            "14": "山西省",
            "21": "辽宁省",
            "22": "吉林省",
            "23": "黑龙江省",
            "31": "上海市",
            "32": "江苏省",
            "33": "浙江省",
            "34": "安徽省",
            "35": "福建省",
            "36": "江西省",
            "37": "山东省",
            "41": "河南省",
            "42": "湖北省",
            "43": "湖南省",
            "44": "广东省",
            "46": "海南省",
            "50": "重庆市",
            "51": "四川省",
            "52": "贵州省",
            "53": "云南省",
            "61": "陕西省",
            "62": "甘肃省",
            "63": "青海省",
        }

        # 城市和区县代码
        self.city_codes = {
            "1101": "市辖区",
            "1102": "县",
            "1201": "市辖区",
            "1202": "县",
            "1301": "石家庄市",
            "1302": "唐山市",
            "1303": "秦皇岛市",
            "1304": "邯郸市",
            "1305": "邢台市",
            "1306": "保定市",
            "1307": "张家口市",
            "1308": "承德市",
            "1309": "沧州市",
            "1310": "廊坊市",
            "1311": "衡水市",
            "1401": "太原市",
            "1402": "大同市",
            "1403": "阳泉市",
            "1404": "长治市",
            "1405": "晋城市",
            "1406": "朔州市",
            "1407": "晋中市",
            "1408": "运城市",
            "1409": "忻州市",
            "1410": "临汾市",
            "1411": "吕梁市",
            "1501": "呼和浩特市",
            "1502": "包头市",
            "1503": "乌海市",
            "1504": "赤峰市",
            "1505": "通辽市",
            "2101": "沈阳市",
            "2102": "大连市",
            "2103": "鞍山市",
            "2104": "抚顺市",
            "2105": "本溪市",
            "2106": "丹东市",
            "2107": "锦州市",
            "2108": "营口市",
            "2109": "阜新市",
            "2110": "辽阳市",
            "2111": "盘锦市",
            "2112": "铁岭市",
            "2113": "朝阳市",
            "2114": "葫芦岛市",
            "2201": "长春市",
            "2202": "吉林市",
            "2203": "四平市",
            "2204": "辽源市",
            "2205": "通化市",
            "2206": "白山市",
            "2207": "松原市",
            "2208": "白城市",
            "2301": "哈尔滨市",
            "2303": "鸡西市",
            "2304": "鹤岗市",
            "2305": "双鸭山市",
            "2306": "大庆市",
            "2307": "伊春市",
            "2308": "佳木斯市",
            "2309": "七台河市",
            "2310": "牡丹江市",
            "2311": "黑河市",
            "2312": "绥化市",
            "3101": "市辖区",
            "3102": "县",
            "3201": "南京市",
            "3202": "无锡市",
            "3203": "徐州市",
            "3204": "常州市",
            "3205": "苏州市",
            "3206": "南通市",
            "3207": "连云港市",
            "3208": "淮安市",
            "3209": "盐城市",
            "3210": "扬州市",
            "3211": "镇江市",
            "3212": "泰州市",
            "3213": "宿迁市",
            "3301": "杭州市",
            "3302": "宁波市",
            "3303": "温州市",
            "3304": "嘉兴市",
            "3305": "湖州市",
            "3306": "绍兴市",
            "3307": "金华市",
            "3308": "衢州市",
            "3309": "舟山市",
            "3310": "台州市",
            "3311": "丽水市",
            "3401": "合肥市",
            "3402": "芜湖市",
            "3403": "蚌埠市",
            "3404": "淮南市",
            "3405": "马鞍山市",
            "3406": "淮北市",
            "3407": "铜陵市",
            "3408": "安庆市",
            "3410": "黄山市",
            "3411": "滁州市",
            "3412": "阜阳市",
            "3413": "宿州市",
            "3415": "六安市",
            "3416": "亳州市",
            "3417": "池州市",
            "3418": "宣城市",
            "3501": "福州市",
            "3502": "厦门市",
            "3503": "莆田市",
            "3504": "三明市",
            "3505": "泉州市",
            "3506": "漳州市",
            "3507": "南平市",
            "3508": "龙岩市",
            "3509": "宁德市",
            "3601": "南昌市",
            "3602": "景德镇市",
            "3603": "萍乡市",
            "3604": "九江市",
            "3605": "新余市",
            "3606": "鹰潭市",
            "3607": "赣州市",
            "3608": "吉安市",
            "3609": "宜春市",
            "3610": "抚州市",
            "3611": "上饶市",
            "3701": "济南市",
            "3702": "青岛市",
            "3703": "淄博市",
            "3704": "枣庄市",
            "3705": "东营市",
            "3706": "烟台市",
            "3707": "潍坊市",
            "3708": "济宁市",
            "3709": "泰安市",
            "3710": "威海市",
            "3711": "日照市",
            "3712": "莱芜市",
            "3713": "临沂市",
            "3714": "德州市",
            "3715": "聊城市",
            "3716": "滨州市",
            "3717": "菏泽市",
            "4101": "郑州市",
            "4102": "开封市",
            "4103": "洛阳市",
            "4104": "平顶山市",
            "4105": "安阳市",
            "4106": "鹤壁市",
            "4107": "新乡市",
            "4108": "焦作市",
            "4109": "濮阳市",
            "4110": "许昌市",
            "4111": "漯河市",
            "4112": "三门峡市",
            "4113": "南阳市",
            "4114": "商丘市",
            "4115": "信阳市",
            "4116": "周口市",
            "4117": "驻马店市",
            "4201": "武汉市",
            "4202": "黄石市",
            "4203": "十堰市",
            "4205": "宜昌市",
            "4206": "襄阳市",
            "4207": "鄂州市",
            "4208": "荆门市",
            "4209": "孝感市",
            "4210": "荆州市",
            "4211": "黄冈市",
            "4212": "咸宁市",
            "4213": "随州市",
            "4301": "长沙市",
            "4302": "株洲市",
            "4303": "湘潭市",
            "4304": "衡阳市",
            "4305": "邵阳市",
            "4306": "岳阳市",
            "4307": "常德市",
            "4308": "张家界市",
            "4309": "益阳市",
            "4310": "郴州市",
            "4311": "永州市",
            "4312": "怀化市",
            "4313": "娄底市",
            "4401": "广州市",
            "4402": "韶关市",
            "4403": "深圳市",
            "4404": "珠海市",
            "4405": "汕头市",
            "4406": "佛山市",
            "4407": "江门市",
            "4408": "湛江市",
            "4409": "茂名市",
            "4412": "肇庆市",
            "4413": "惠州市",
            "4414": "梅州市",
            "4415": "汕尾市",
            "4416": "河源市",
            "4417": "阳江市",
            "4418": "清远市",
            "4419": "东莞市",
            "4420": "中山市",
            "4451": "潮州市",
            "4452": "揭阳市",
            "4453": "云浮市",
            "4501": "南宁市",
            "4502": "柳州市",
            "4503": "桂林市",
            "4504": "梧州市",
            "4505": "北海市",
            "4506": "防城港市",
            "4507": "钦州市",
            "4508": "贵港市",
            "4509": "玉林市",
            "4510": "百色市",
            "4511": "贺州市",
            "4512": "河池市",
            "4513": "来宾市",
            "4514": "崇左市",
            "4601": "海口市",
            "4602": "三亚市",
            "4603": "三沙市",
            "4604": "儋州市",
            "5001": "市辖区",
            "5002": "县",
            "5101": "成都市",
            "5103": "自贡市",
            "5104": "攀枝花市",
            "5105": "泸州市",
            "5106": "德阳市",
            "5107": "绵阳市",
            "5108": "广元市",
            "5109": "遂宁市",
            "5110": "内江市",
            "5111": "乐山市",
            "5113": "南充市",
            "5114": "眉山市",
            "5115": "宜宾市",
            "5116": "广安市",
            "5117": "达州市",
            "5118": "雅安市",
            "5119": "巴中市",
            "5120": "资阳市",
            "5201": "贵阳市",
            "5202": "六盘水市",
            "5203": "遵义市",
            "5204": "安顺市",
            "5205": "毕节市",
            "5206": "铜仁市",
            "5301": "昆明市",
            "5303": "曲靖市",
            "5304": "玉溪市",
            "5305": "保山市",
            "5306": "昭通市",
            "5307": "丽江市",
            "5308": "普洱市",
            "5309": "临沧市",
            "5401": "拉萨市",
            "5402": "日喀则市",
            "5403": "昌都市",
            "5404": "林芝市",
            "5405": "山南市",
            "5406": "那曲市",
            "6101": "西安市",
            "6102": "铜川市",
            "6103": "宝鸡市",
            "6104": "咸阳市",
            "6105": "渭南市",
            "6106": "延安市",
            "6107": "汉中市",
            "6108": "榆林市",
            "6109": "安康市",
            "6110": "商洛市",
            "6201": "兰州市",
            "6202": "嘉峪关市",
            "6203": "金昌市",
            "6204": "白银市",
            "6205": "天水市",
            "6206": "武威市",
            "6207": "张掖市",
            "6208": "平凉市",
            "6209": "酒泉市",
            "6210": "庆阳市",
            "6211": "定西市",
            "6212": "陇南市",
            "6301": "西宁市",
            "6302": "海东市",
            "6401": "银川市",
            "6402": "石嘴山市",
            "6403": "吴忠市",
            "6404": "固原市",
            "6405": "中卫市",
            "6504": "吐鲁番市",
            "6505": "哈密市",
        }

        # 签发机关
        self.issuing_authorities = {
            "11": "北京市公安局",
            "12": "天津市公安局",
            "13": "河北省公安厅",
            "14": "山西省公安厅",
            "15": "内蒙古自治区公安厅",
            "21": "辽宁省公安厅",
            "22": "吉林省公安厅",
            "23": "黑龙江省公安厅",
            "31": "上海市公安局",
            "32": "江苏省公安厅",
            "33": "浙江省公安厅",
            "34": "安徽省公安厅",
            "35": "福建省公安厅",
            "36": "江西省公安厅",
            "37": "山东省公安厅",
            "41": "河南省公安厅",
            "42": "湖北省公安厅",
            "43": "湖南省公安厅",
            "44": "广东省公安厅",
            "45": "广西壮族自治区公安厅",
            "46": "海南省公安厅",
            "50": "重庆市公安局",
            "51": "四川省公安厅",
            "52": "贵州省公安厅",
            "53": "云南省公安厅",
            "54": "西藏自治区公安厅",
            "61": "陕西省公安厅",
            "62": "甘肃省公安厅",
            "63": "青海省公安厅",
            "64": "宁夏回族自治区公安厅",
            "65": "新疆维吾尔自治区公安厅",
        }

        # 扩展银行列表 - 包含多个BIN号
        self.banks = {
            "建设银行": {
                "储蓄卡": ["621700", "622700", "623094", "623668", "621081"],
                "信用卡": ["625966", "625362", "625363", "628316", "528056"],
            },
            "工商银行": {
                "储蓄卡": ["622202", "622203", "622208", "621225", "621226"],
                "信用卡": ["622230", "622235", "622210", "625858", "625859"],
            },
            "农业银行": {
                "储蓄卡": ["622848", "622845", "622846", "622847", "623052"],
                "信用卡": ["625996", "625997", "625998", "628268", "520082"],
            },
            "中国银行": {
                "储蓄卡": ["456351", "601382", "621661", "621663", "621667"],
                "信用卡": ["625908", "625910", "625909", "628312", "518378"],
            },
            "招商银行": {
                "储蓄卡": ["622588", "622609", "468203", "512425", "524011"],
                "信用卡": ["622575", "622576", "622577", "622578", "622579"],
            },
            "交通银行": {
                "储蓄卡": ["622260", "622262", "621059", "621335", "621069"],
                "信用卡": ["622253", "622254", "622255", "625029", "625030"],
            },
            "邮储银行": {
                "储蓄卡": ["621098", "621095", "622150", "622151", "621599"],
                "信用卡": ["625919", "625920", "625921", "625922", "625923"],
            },
            "中信银行": {
                "储蓄卡": ["622690", "622691", "622692", "622696", "622698"],
                "信用卡": ["622918", "622916", "622919", "628370", "628371"],
            },
            "光大银行": {
                "储蓄卡": ["622663", "622664", "622665", "622666", "622667"],
                "信用卡": ["622673", "622674", "622675", "622676", "622677"],
            },
            "民生银行": {
                "储蓄卡": ["622622", "622623", "622624", "622625", "622626"],
                "信用卡": ["622617", "622618", "622619", "622620", "622621"],
            },
            "浦发银行": {
                "储蓄卡": ["622516", "622517", "622518", "622521", "622522"],
                "信用卡": ["622276", "622277", "622278", "622279", "622280"],
            },
            "广发银行": {
                "储蓄卡": ["622568", "622569", "622570", "622571", "622572"],
                "信用卡": ["622556", "622557", "622558", "622559", "622560"],
            },
            "平安银行": {
                "储蓄卡": ["622986", "622989", "622298", "627066", "627067"],
                "信用卡": ["622155", "622156", "622157", "622158", "622159"],
            },
            "兴业银行": {
                "储蓄卡": ["622909", "622908", "622902", "622901", "622922"],
                "信用卡": ["622902", "622903", "622904", "622905", "622906"],
            },
            "华夏银行": {
                "储蓄卡": ["622630", "622631", "622632", "622633", "622635"],
                "信用卡": ["622636", "622637", "622638", "622639", "622640"],
            },
        }

        # 银行卡类型
        self.card_types = ["储蓄卡", "信用卡"]

        # 公司名称相关数据
        self.company_types = [
            "科技",
            "信息",
            "网络",
            "软件",
            "数据",
            "智能",
            "数字",
            "创新",
            "互联",
            "电子",
            "智能",
            "智慧",
            "云端",
            "物联",
            "区块",
            "人工",
            "机器",
            "自动",
            "智能",
            "数字",
            "高新",
            "先进",
            "现代",
            "未来",
            "前沿",
            "尖端",
            "领先",
            "卓越",
            "优质",
            "专业",
        ]

        self.company_suffixes = [
            "有限公司",
            "有限责任公司",
            "股份有限公司",
            "集团",
            "科技发展有限公司",
            "技术有限公司",
            "信息技术有限公司",
            "科技有限公司",
            "网络科技有限公司",
            "软件有限公司",
            "数据科技有限公司",
            "智能科技有限公司",
            "数字科技有限公司",
            "创新科技有限公司",
            "互联科技有限公司",
            "电子科技有限公司",
            "发展有限公司",
            "实业有限公司",
            "投资有限公司",
            "咨询有限公司",
            "服务有限公司",
            "工程有限公司",
        ]

        self.company_industries = [
            "科技",
            "信息",
            "网络",
            "软件",
            "数据",
            "智能",
            "数字",
            "创新",
            "互联",
            "电子",
            "金融",
            "投资",
            "咨询",
            "管理",
            "服务",
            "工程",
            "设计",
            "传媒",
            "文化",
            "教育",
            "医疗",
            "健康",
            "环保",
            "能源",
            "物流",
            "电商",
            "零售",
            "制造",
            "建筑",
            "农业",
            "旅游",
            "餐饮",
            "娱乐",
            "体育",
            "汽车",
            "房产",
            "家居",
            "服装",
            "食品",
            "饮料",
            "化工",
            "机械",
            "电子",
            "电气",
            "通信",
            "互联网",
            "人工智能",
            "大数据",
            "云计算",
            "物联网",
        ]

        self.company_regions = [
            "北京",
            "上海",
            "广州",
            "深圳",
            "杭州",
            "南京",
            "成都",
            "武汉",
            "西安",
            "重庆",
            "天津",
            "苏州",
            "宁波",
            "青岛",
            "大连",
            "厦门",
            "长沙",
            "郑州",
            "沈阳",
            "长春",
            "哈尔滨",
            "济南",
            "合肥",
            "福州",
            "南昌",
            "南宁",
            "贵阳",
            "昆明",
            "兰州",
            "西宁",
            "银川",
            "乌鲁木齐",
            "呼和浩特",
            "太原",
            "石家庄",
            "海口",
            "珠海",
            "佛山",
            "东莞",
            "中山",
            "惠州",
            "江门",
            "肇庆",
            "汕头",
            "湛江",
            "茂名",
            "韶关",
            "潮州",
            "揭阳",
            "汕尾",
        ]

        # 公司名称前缀（用于增加多样性）
        self.company_prefixes = [
            "新",
            "大",
            "中",
            "华",
            "国",
            "东",
            "南",
            "西",
            "北",
            "上",
            "下",
            "左",
            "右",
            "金",
            "银",
            "铜",
            "铁",
            "钢",
            "宝",
            "玉",
            "珠",
            "珍",
            "奇",
            "特",
            "优",
            "佳",
            "永",
            "恒",
            "久",
            "长",
            "远",
            "高",
            "深",
            "广",
            "阔",
            "宏",
            "伟",
            "大",
            "强",
        ]

        # 公司名称中间词（用于增加多样性）
        self.company_middle_words = [
            "时代",
            "世纪",
            "国际",
            "全球",
            "亚洲",
            "中国",
            "中华",
            "华夏",
            "神州",
            "大地",
            "阳光",
            "星光",
            "月光",
            "风云",
            "雷霆",
            "闪电",
            "火焰",
            "冰雪",
            "海洋",
            "天空",
            "大地",
            "山川",
            "河流",
            "森林",
            "草原",
            "沙漠",
            "绿洲",
            "花园",
            "乐园",
            "天堂",
        ]

        # 统一社会信用代码相关数据
        self.organization_codes = [
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
            "G",
            "H",
            "J",
            "K",
            "L",
            "M",
            "N",
            "P",
            "Q",
            "R",
            "T",
            "U",
            "W",
            "X",
            "Y",
        ]

    def generate_name(self, name=None):
        """生成随机姓名，如果提供了姓名则使用提供的姓名"""
        if name:
            return name
        surname = random.choice(self.surnames)
        given_name = random.choice(self.given_names)
        # 有一定概率生成双字名
        if random.random() > 0.7:
            given_name += random.choice(self.given_names)
        return surname + given_name

    def generate_gender(self, gender=None):
        """生成随机性别，如果提供了性别则使用提供的性别"""
        if gender:
            return gender
        return random.choice(["男", "女"])

    def generate_ethnic_group(self, ethnic=None):
        """生成随机民族，如果提供了民族则使用提供的民族"""
        if ethnic:
            return ethnic
        return random.choice(self.ethnic_groups)

    def generate_birth_date(self, min_age=22, max_age=55, birth_date=None):
        """生成随机出生日期，返回完整日期和分开的年月日"""
        if birth_date:
            # 解析提供的出生日期
            if isinstance(birth_date, str):
                # 尝试解析不同格式的日期
                if re.match(r"\d{4}年\d{1,2}月\d{1,2}日", birth_date):
                    match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", birth_date)
                    if match:
                        year, month, day = match.groups()
                        birth_year = int(year)
                        birth_month = int(month)
                        birth_day = int(day)
                elif re.match(r"\d{4}-\d{1,2}-\d{1,2}", birth_date):
                    parts = birth_date.split("-")
                    birth_year = int(parts[0])
                    birth_month = int(parts[1])
                    birth_day = int(parts[2])
                elif re.match(r"\d{4}\.\d{1,2}\.\d{1,2}", birth_date):
                    parts = birth_date.split(".")
                    birth_year = int(parts[0])
                    birth_month = int(parts[1])
                    birth_day = int(parts[2])
                else:
                    # 默认使用当前日期
                    today = datetime.now()
                    birth_year = today.year - random.randint(min_age, max_age)
                    birth_month = random.randint(1, 12)
                    birth_day = random.randint(1, 28)
            else:
                # 如果是datetime对象
                birth_year = birth_date.year
                birth_month = birth_date.month
                birth_day = birth_date.day
        else:
            # 随机生成出生日期
            current_year = datetime.now().year
            birth_year = random.randint(current_year - max_age, current_year - min_age)
            birth_month = random.randint(1, 12)

            # 简单处理月份天数
            if birth_month in [4, 6, 9, 11]:
                birth_day = random.randint(1, 30)
            elif birth_month == 2:
                # 简单闰年判断
                if birth_year % 4 == 0 and (
                    birth_year % 100 != 0 or birth_year % 400 == 0
                ):
                    birth_day = random.randint(1, 29)
                else:
                    birth_day = random.randint(1, 28)
            else:
                birth_day = random.randint(1, 31)

        # 返回完整日期和分开的年月日
        full_date = f"{birth_year:04d}年{birth_month:02d}月{birth_day:02d}日"
        year_only = f"{birth_year:04d}"
        month_only = f"{birth_month:02d}"
        day_only = f"{birth_day:02d}"

        return full_date, year_only, month_only, day_only

    def generate_address(self, area_code=None, address=None):
        """生成随机地址，如果提供了地址则使用提供的地址"""
        if address:
            return address

        if not area_code:
            area_code = random.choice(list(self.area_codes.keys()))

        province = self.area_codes.get(area_code[:2], "北京市")
        city = self.city_codes.get(area_code[:4], "市辖区")

        # 模拟街道和门牌号
        streets = [
            "中山路",
            "人民路",
            "解放路",
            "建设路",
            "文化路",
            "和平街",
            "幸福里",
            "光明巷",
        ]
        street = random.choice(streets)
        number = random.randint(1, 999)

        return f"{province}{city}{random.choice(['朝阳', '海淀', '东城', '西城', '丰台'])}区{street}{number}号"

    def generate_id_number(
        self, birth_date=None, area_code=None, gender=None, id_start=None
    ):
        """生成符合规则的身份证号码"""
        # 前6位：地区码
        if id_start:
            # 使用提供的身份证开头
            if len(id_start) >= 6:
                area_code = id_start[:6]
            else:
                # 如果提供的开头不足6位，补齐
                area_code = id_start.ljust(6, "0")
        elif not area_code:
            area_code = random.choice(list(self.area_codes.keys()))
            # 添加城市和区县代码
            possible_cities = [
                code for code in self.city_codes.keys() if code.startswith(area_code)
            ]
            if possible_cities:
                city_code = random.choice(possible_cities)
                # 随机生成区县代码（01-99）
                county_code = f"{random.randint(1, 99):02d}"
                area_code = city_code + county_code
            else:
                # 如果没有匹配的城市，使用默认区县代码
                area_code += "0101"

        # 确保地区码为6位
        area_code = area_code[:6].ljust(6, "0")

        # 中间8位：出生日期
        if not birth_date:
            birth_date = self.generate_birth_date()[0]  # 获取完整日期

        # 从文本格式提取年月日
        match = re.search(r"(\d{4})年(\d{2})月(\d{2})日", birth_date)
        if match:
            year, month, day = match.groups()
            birth_code = f"{year}{month}{day}"
        else:
            # 如果解析失败，使用当前日期
            today = datetime.now()
            birth_code = today.strftime("%Y%m%d")

        # 第15-17位：顺序码
        sequence = random.randint(1, 999)
        # 根据性别调整顺序码
        if gender == "女":
            sequence = sequence if sequence % 2 == 0 else sequence + 1
        else:
            sequence = sequence if sequence % 2 == 1 else sequence + 1

        # 前17位
        first_17 = f"{area_code}{birth_code}{sequence:03d}"[:17]

        # 第18位：校验码
        check_code = self._calculate_check_code(first_17)

        return first_17 + check_code

    def _calculate_check_code(self, first_17):
        """计算身份证校验码"""
        # 权重因子
        factors = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        # 校验码对应值
        check_codes = ["1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2"]

        # 确保前17位都是数字
        if not first_17.isdigit():
            # 如果有非数字字符，替换为随机数字
            first_17 = "".join(
                [c if c.isdigit() else str(random.randint(0, 9)) for c in first_17]
            )

        total = 0
        for i in range(17):
            total += int(first_17[i]) * factors[i]

        return check_codes[total % 11]

    def generate_issue_date(self, birth_date, valid_period=None):
        """根据出生日期生成签发日期，格式为YYYY.MM.DD"""
        if valid_period:
            return valid_period

        # 从出生日期解析年份
        birth_year = int(birth_date[:4])
        # 假设16岁首次签发，26岁、46岁换发
        current_year = datetime.now().year
        age = current_year - birth_year

        if age < 16:
            issue_year = birth_year + 16
            validity = 5  # 5年有效期
        elif age < 26:
            issue_year = birth_year + 16
            validity = 10  # 10年有效期
        elif age < 46:
            issue_year = birth_year + 26
            validity = 20  # 20年有效期
        else:
            issue_year = birth_year + 46
            validity = "长期"  # 长期有效

        issue_month = random.randint(1, 12)
        issue_day = random.randint(1, 28)  # 避免日期超出范围
        id_card_start_time = f"{issue_year:04d}{issue_month:02d}{issue_day:02d}"
        # 格式化为 YYYY.MM.DD
        issue_date = f"{issue_year:04d}.{issue_month:02d}.{issue_day:02d}"

        if validity == "长期":
            expiry_date = "长期"
            valid_period = f"{issue_date}-长期"
            id_card_end_time = f"2099{issue_month:02d}{issue_day:02d}"
        else:
            expiry_year = issue_year + validity
            expiry_month = issue_month
            expiry_day = issue_day
            id_card_end_time = f"{expiry_year:04d}{expiry_month:02d}{expiry_day:02d}"
            expiry_date = f"{expiry_year:04d}.{expiry_month:02d}.{expiry_day:02d}"
            valid_period = f"{issue_date}-{expiry_date}"

        return valid_period, id_card_start_time, id_card_end_time

    def luhn_check(self, card_number):
        """Luhn算法校验"""

        def digits_of(n):
            return [int(d) for d in str(n)]

        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        return checksum % 10 == 0

    def generate_valid_card_number(self, bin_code, length):
        """生成符合Luhn算法的银行卡号"""
        while True:
            # 生成中间数字
            middle_length = length - len(bin_code) - 1
            middle_digits = "".join(
                [str(random.randint(0, 9)) for _ in range(middle_length)]
            )

            # 生成最后一位校验码
            card_without_check = bin_code + middle_digits

            # 计算Luhn校验位
            total = 0
            reverse_digits = card_without_check[::-1]
            for i, digit in enumerate(reverse_digits):
                n = int(digit)
                if i % 2 == 0:
                    n *= 2
                    if n > 9:
                        n -= 9
                total += n

            check_digit = (10 - (total % 10)) % 10

            card_number = card_without_check + str(check_digit)

            # 验证生成的卡号
            if self.luhn_check(card_number):
                return card_number

    def generate_bank_card_number(self, bank_name="建设银行", card_type="储蓄卡"):
        """生成符合真实场景的银行卡号"""
        if bank_name not in self.banks:
            bank_name = "建设银行"

        if card_type not in self.banks[bank_name]:
            card_type = "储蓄卡"

        # 随机选择一个BIN号
        bin_code = random.choice(self.banks[bank_name][card_type])

        # 根据卡类型确定卡号长度
        if card_type == "储蓄卡":
            # 储蓄卡通常16位或19位
            length = random.choice([16, 19])
        else:
            # 信用卡通常16位
            length = 16

        # 生成符合Luhn算法的卡号
        card_number = self.generate_valid_card_number(bin_code, length)

        return card_number

    def generate_phone_number(self, prefix=None):
        """生成手机号"""
        # 合法的手机号前缀列表
        valid_prefixes = [
            "134",
            "135",
            "136",
            "137",
            "138",
            "139",
            "147",
            "150",
            "151",
            "152",
            "157",
            "158",
            "159",
            "178",
            "182",
            "183",
            "184",
            "187",
            "188",
            "198",
            "130",
            "131",
            "132",
            "145",
            "155",
            "156",
            "166",
            "175",
            "176",
            "185",
            "186",
            "133",
            "149",
            "153",
            "173",
            "177",
            "180",
            "181",
            "189",
            "199",
            "192",
        ]

        if prefix is None:
            prefix = random.choice(valid_prefixes)
        else:
            # 校验传入的前缀是否合法
            if prefix not in valid_prefixes:
                # 如果前缀不合法，则使用随机前缀
                prefix = random.choice(valid_prefixes)

        phone_suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
        return prefix + phone_suffix

    def generate_id_card_data(
        self,
        name=None,
        gender=None,
        ethnic=None,
        birth_date=None,
        address=None,
        id_start=None,
        issue_authority=None,
        valid_period=None,
        bank_name="建设银行",
        card_type="储蓄卡",
        phone_prefix=None,
        company_name=None,
        unified_social_credit_code=None,
    ):
        """生成完整的身份证数据"""
        # 生成基本信息
        name = self.generate_name(name)
        gender = self.generate_gender(gender)
        ethnic_group = self.generate_ethnic_group(ethnic)
        full_birth_date, birth_year, birth_month, birth_day = self.generate_birth_date(
            birth_date=birth_date
        )

        # 根据身份证开头确定地区码
        area_code = None
        if id_start and len(id_start) >= 2:
            area_code = id_start[:2]

        address = self.generate_address(area_code, address)

        # 生成身份证号码
        id_number = self.generate_id_number(
            full_birth_date, area_code, gender, id_start
        )

        # 生成签发信息
        valid_period, id_card_start_time, id_card_end_time = self.generate_issue_date(
            full_birth_date, valid_period
        )

        # 签发机关
        if issue_authority:
            issuing_authority = issue_authority
        else:
            # 根据身份证开头确定签发机关
            if id_start and len(id_start) >= 2:
                issuing_authority = self.issuing_authorities.get(
                    id_start[:2], f"{self.area_codes.get(id_start[:2], '北京市')}公安局"
                )
            else:
                area_code = random.choice(list(self.area_codes.keys()))
                issuing_authority = self.issuing_authorities.get(
                    area_code, f"{self.area_codes.get(area_code, '北京市')}公安局"
                )

        # 生成银行卡号
        bank_card_number = self.generate_bank_card_number(bank_name, card_type)

        # 生成手机号
        phone_number = self.generate_phone_number(phone_prefix)

        return {
            "name": name,  # 姓名
            "gender": gender,  # 性别
            "ethnic": ethnic_group,  # 民族
            "birth_full": full_birth_date,  # 完整出生日期
            "birth_year": birth_year,  # 出生年份
            "birth_month": birth_month,  # 出生月份
            "birth_day": birth_day,  # 出生日期
            "address": address,  # 住址
            "id_number": id_number,  # 公民身份号码
            "issue_authority": issuing_authority,  # 签发机关
            "valid_period": valid_period,  # 有效期限
            "id_card_start_time": id_card_start_time,  # 有效期开始时间，格式20251022
            "id_card_end_time": id_card_end_time,  # 有效期结束时间，格式20251022
            "bank_card_number": bank_card_number,  # 银行卡号
            "phone": phone_number,  # 手机号
            "company_name": company_name,  # 公司名称（由营业执照生成方法统一生成）
            "unified_social_credit_code": unified_social_credit_code,  # 统一社会信用代码（由营业执照生成方法统一生成）
        }

    def generate_company_name(self):
        """生成随机公司名称"""
        # 增加组合的随机性，避免重复
        max_attempts = 10  # 最大尝试次数，避免无限循环

        for attempt in range(max_attempts):
            region = random.choice(self.company_regions)
            industry = random.choice(self.company_industries)
            company_type = random.choice(self.company_types)
            suffix = random.choice(self.company_suffixes)

            # 随机决定是否添加前缀（增加概率）
            use_prefix = random.random() > 0.5
            prefix = random.choice(self.company_prefixes) if use_prefix else ""

            # 随机决定是否添加中间词（增加概率）
            use_middle = random.random() > 0.6
            middle_word = random.choice(self.company_middle_words) if use_middle else ""

            # 随机决定是否使用数字编号（进一步增加多样性）
            use_number = random.random() > 0.8
            number_suffix = ""
            if use_number:
                # 随机生成1-3位数字编号
                number_suffix = str(random.randint(1, 999))

            # 随机选择公司名称格式（增加更多格式组合）
            formats = [
                f"{region}{industry}{company_type}{suffix}",
                f"{region}{company_type}{industry}{suffix}",
                f"{industry}{company_type}{suffix}",
                f"{company_type}{industry}{suffix}",
                f"{prefix}{region}{industry}{company_type}{suffix}",
                f"{prefix}{region}{company_type}{industry}{suffix}",
                f"{region}{industry}{middle_word}{company_type}{suffix}",
                f"{region}{company_type}{middle_word}{industry}{suffix}",
                f"{prefix}{region}{industry}{middle_word}{company_type}{suffix}",
                f"{prefix}{region}{company_type}{middle_word}{industry}{suffix}",
                f"{industry}{middle_word}{company_type}{suffix}",
                f"{company_type}{middle_word}{industry}{suffix}",
                f"{prefix}{industry}{company_type}{suffix}",
                f"{prefix}{company_type}{industry}{suffix}",
                f"{industry}{company_type}{middle_word}{suffix}",
                f"{company_type}{industry}{middle_word}{suffix}",
                f"{region}{industry}{company_type}{number_suffix}{suffix}",
                f"{region}{company_type}{industry}{number_suffix}{suffix}",
                f"{industry}{company_type}{number_suffix}{suffix}",
                f"{company_type}{industry}{number_suffix}{suffix}",
                f"{prefix}{region}{industry}{company_type}{number_suffix}{suffix}",
                f"{prefix}{region}{company_type}{industry}{number_suffix}{suffix}",
                f"{region}{industry}{middle_word}{company_type}{number_suffix}{suffix}",
                f"{region}{company_type}{middle_word}{industry}{number_suffix}{suffix}",
                f"{prefix}{region}{industry}{middle_word}{company_type}{number_suffix}{suffix}",
                f"{prefix}{region}{company_type}{middle_word}{industry}{number_suffix}{suffix}",
                f"{industry}{middle_word}{company_type}{number_suffix}{suffix}",
                f"{company_type}{middle_word}{industry}{number_suffix}{suffix}",
                f"{prefix}{industry}{company_type}{number_suffix}{suffix}",
                f"{prefix}{company_type}{industry}{number_suffix}{suffix}",
                f"{industry}{company_type}{middle_word}{number_suffix}{suffix}",
                f"{company_type}{industry}{middle_word}{number_suffix}{suffix}",
            ]

            # 随机选择一种格式
            selected_format = random.choice(formats)

            # 清理格式中的空字符串（如果前缀或中间词为空）
            selected_format = selected_format.replace(" ", "").strip()

            # 检查是否生成了有效的公司名称（不是空字符串）
            if selected_format and len(selected_format) > 4:
                return selected_format

        # 如果所有尝试都失败，返回一个默认格式
        return f"{random.choice(self.company_regions)}{random.choice(self.company_industries)}{random.choice(self.company_types)}{random.choice(self.company_suffixes)}"

    def generate_unified_social_credit_code(self):
        """生成符合规则的真实统一社会信用代码（18位）
        结构：1位登记管理部门代码 + 1位机构类别代码 + 6位行政区划代码 + 9位组织机构代码 + 1位校验码
        """

        # 1. 第一位：登记管理部门代码
        # 1-企业，5-个体户，9-事业单位，Y-社会组织
        first_codes = ["1", "5", "9", "Y"]
        first_code = random.choice(first_codes)

        # 2. 第二位：机构类别代码（根据第一位确定范围）
        second_code_rules = {
            "1": [1, 2, 3, 9],  # 企业
            "5": [1, 2, 3, 9],  # 个体户
            "9": [1, 2, 3],  # 事业单位
            "Y": [1],  # 社会组织
        }
        second_code = str(random.choice(second_code_rules[first_code]))

        # 3. 第3-8位：行政区划代码（6位，使用真实存在的行政区划）
        # 这里使用部分真实行政区划代码
        admin_codes = [
            "110000",  # 北京市
            "310000",  # 上海市
            "440300",  # 深圳市
            "330100",  # 杭州市
            "320100",  # 南京市
            "120000",  # 天津市
            "500000",  # 重庆市
            "440100",  # 广州市
            "420100",  # 武汉市
            "610100",  # 西安市
        ]
        admin_code = random.choice(admin_codes)

        # 4. 第9-17位：组织机构代码（9位）
        # 前8位随机生成，第9位是校验码
        org_part = ""
        for i in range(8):
            # 可以是数字或大写字母（I、O、Z除外）
            char = random.choice("0123456789ABCDEFGHJKLMNPQRTUWXY")
            org_part += char

        # 5. 计算第17位（组织机构代码的校验码）
        org_weights = [3, 7, 9, 10, 5, 8, 4, 2]
        org_sum = 0

        for i, char in enumerate(org_part):
            if char.isdigit():
                value = int(char)
            else:
                # A=10, B=11, ... 但需要跳过I,O,Z
                value = ord(char) - ord("A") + 10
                # 跳过I,O,Z
                if char > "I":
                    value -= 1
                if char > "O":
                    value -= 1
                if char > "Z":
                    value -= 1

            org_sum += value * org_weights[i]

        org_check_code = 11 - (org_sum % 11)
        if org_check_code == 10:
            org_check_char = "X"
        elif org_check_code == 11:
            org_check_char = "0"
        else:
            org_check_char = str(org_check_code)

        org_part += org_check_char  # 第9位（总第17位）

        # 6. 第18位：统一社会信用代码校验码
        # 计算前17位的校验码
        full_code_without_check = first_code + second_code + admin_code + org_part

        # 字符映射表
        char_map = {
            "0": 0,
            "1": 1,
            "2": 2,
            "3": 3,
            "4": 4,
            "5": 5,
            "6": 6,
            "7": 7,
            "8": 8,
            "9": 9,
            "A": 10,
            "B": 11,
            "C": 12,
            "D": 13,
            "E": 14,
            "F": 15,
            "G": 16,
            "H": 17,
            "J": 18,
            "K": 19,
            "L": 20,
            "M": 21,
            "N": 22,
            "P": 23,
            "Q": 24,
            "R": 25,
            "T": 26,
            "U": 27,
            "W": 28,
            "X": 29,
            "Y": 30,
        }

        # 校验码权重
        weights = [1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]

        total = 0
        for i, char in enumerate(full_code_without_check):
            if char in char_map:
                total += char_map[char] * weights[i]
            else:
                # 对于不在映射表中的字符（如I,O,Z,S,V），理论上不应出现
                # 这里给一个随机值（实际应用中应避免这些字符）
                total += 10 * weights[i]  # 使用默认值

        remainder = total % 31
        check_code = 31 - remainder
        if check_code == 31:
            check_code = 0

        # 将数字转换为字符
        check_char_dict = "0123456789ABCDEFGHJKLMNPQRTUWXY"
        final_check_char = check_char_dict[check_code]

        # 7. 组合完整代码
        unified_code = full_code_without_check + final_check_char

        return unified_code

    def generate_business_license_data(self, config=None):
        """生成营业执照数据

        Args:
            config: 配置参数，包含以下可选字段：
                - company_type: 公司类型
                - legal_representative: 法定代表人
                - address: 住所
                - registered_capital: 注册资本（输入框值）
                - establishment_date: 成立日期
                - business_start_date: 营业期限开始日期
                - business_end_date: 营业期限结束日期
                - business_scope: 经营范围
                - industry_type: 行业类型
                - province: 省份
        """
        config = config or {}

        # 1. 统一社会信用代码（使用配置或生成）
        if config and config.get("unified_social_credit_code"):
            unified_social_credit_code = config["unified_social_credit_code"]
        else:
            unified_social_credit_code = self.generate_unified_social_credit_code()

        # 2. 名称（公司名称）（使用配置或生成）
        if config and config.get("company_name"):
            company_name = config["company_name"]
        else:
            company_name = self.generate_company_name()

        # 3. 类型（根据配置或统一社会信用代码第一位确定）
        if config.get("company_type"):
            company_type = config["company_type"]
        else:
            type_mapping = {
                "1": "有限责任公司",
                "5": "个体工商户",
                "9": "事业单位",
                "Y": "社会组织",
            }
            company_type = type_mapping.get(
                unified_social_credit_code[0], "有限责任公司"
            )

        # 4. 住所（使用配置或生成公司地址）
        if config.get("address"):
            address = config["address"]
        else:
            # 使用配置的省份或随机选择
            if config.get("province"):
                # 从配置的省份中随机选择城市
                province = config["province"]
                # 根据省份选择对应的城市
                province_cities = {
                    "北京市": ["北京市"],
                    "上海市": ["上海市"],
                    "天津市": ["天津市"],
                    "重庆市": ["重庆市"],
                    "广东省": ["广州市", "深圳市", "珠海市", "东莞市", "佛山市"],
                    "浙江省": ["杭州市", "宁波市", "温州市", "绍兴市", "嘉兴市"],
                    "江苏省": ["南京市", "苏州市", "无锡市", "常州市", "徐州市"],
                    "山东省": ["济南市", "青岛市", "烟台市", "潍坊市", "临沂市"],
                    "四川省": ["成都市", "绵阳市", "德阳市", "宜宾市", "南充市"],
                    "湖北省": ["武汉市", "宜昌市", "襄阳市", "黄石市", "十堰市"],
                    "湖南省": ["长沙市", "株洲市", "湘潭市", "衡阳市", "岳阳市"],
                    "河南省": ["郑州市", "洛阳市", "开封市", "新乡市", "安阳市"],
                    "河北省": ["石家庄市", "唐山市", "保定市", "邯郸市", "秦皇岛市"],
                    "陕西省": ["西安市", "宝鸡市", "咸阳市", "渭南市", "延安市"],
                    "辽宁省": ["沈阳市", "大连市", "鞍山市", "抚顺市", "锦州市"],
                    "福建省": ["福州市", "厦门市", "泉州市", "漳州市", "莆田市"],
                }
                city = random.choice(province_cities.get(province, ["北京市"]))
            else:
                # 使用真实存在的行政区划代码对应的地址
                area_codes = list(self.area_codes.keys())
                area_code = random.choice(area_codes)
                city = self.area_codes.get(area_code, "北京市")

            # 生成详细地址
            streets = [
                "人民路",
                "中山路",
                "解放路",
                "建设路",
                "新华路",
                "文化路",
                "和平路",
                "胜利路",
                "民主路",
                "自由路",
            ]
            street_numbers = [
                "1号",
                "2号",
                "10号",
                "15号",
                "20号",
                "25号",
                "30号",
                "35号",
                "40号",
                "45号",
            ]
            buildings = [
                "A座",
                "B座",
                "C座",
                "D座",
                "E座",
                "F座",
                "G座",
                "H座",
                "I座",
                "J座",
            ]
            floors = [
                "1层",
                "2层",
                "3层",
                "4层",
                "5层",
                "6层",
                "7层",
                "8层",
                "9层",
                "10层",
            ]

            address = f"{city}{random.choice(streets)}{random.choice(street_numbers)}{random.choice(buildings)}{random.choice(floors)}"

        # 5. 法定代表人（使用配置或生成人名）
        if config.get("legal_representative"):
            legal_representative = config["legal_representative"]
        else:
            legal_representative = self.generate_name()

        # 6. 注册资本（使用配置或随机生成）
        if config.get("registered_capital"):
            capital_input = config["registered_capital"]
            # 检查用户输入的是否为纯数字，如果是则自动添加"万元"单位
            if capital_input.isdigit():
                registered_capital = f"{capital_input}万元"
            else:
                registered_capital = capital_input
        else:
            capital_amounts = [
                "10万元",
                "50万元",
                "100万元",
                "200万元",
                "500万元",
                "1000万元",
            ]
            registered_capital = random.choice(capital_amounts)

        # 7. 成立日期（使用配置或生成）
        if config.get("establishment_date"):
            establishment_date = config["establishment_date"]
        else:
            current_year = datetime.now().year
            # 生成过去1-20年内的日期
            start_year = current_year - random.randint(1, 20)
            start_month = random.randint(1, 12)
            start_day = random.randint(1, 28)  # 避免2月29日等问题

            # 格式化日期为YYYYMMDD格式（图片填充器期望的格式）
            establishment_date = f"{start_year:04d}{start_month:02d}{start_day:02d}"

        # 8. 营业期限（使用配置或生成）
        if config.get("business_start_date") and config.get("business_end_date"):
            # 将用户输入的YYYY-MM-DD格式转换为YYYYMMDD格式
            start_date = config["business_start_date"].replace("-", "")
            end_date = config["business_end_date"].replace("-", "")
            business_term = f"{start_date}-{end_date}"
        else:
            # 解析成立日期
            if "-" in establishment_date:
                parts = establishment_date.split("-")
                start_year = int(parts[0])
                start_month = int(parts[1])
                start_day = int(parts[2])
            else:
                # 如果是旧格式，直接使用
                if len(establishment_date) == 8:
                    start_year = int(establishment_date[:4])
                    start_month = int(establishment_date[4:6])
                    start_day = int(establishment_date[6:8])
                else:
                    start_year = datetime.now().year - random.randint(1, 20)
                    start_month = random.randint(1, 12)
                    start_day = random.randint(1, 28)

            # 生成10-50年的营业期限
            term_years = random.randint(10, 50)
            end_year = start_year + term_years
            # 格式化为YYYYMMDD-YYYYMMDD格式（图片填充器期望的格式）
            business_term = f"{start_year:04d}{start_month:02d}{start_day:02d}-{end_year:04d}{start_month:02d}{start_day:02d}"

        # 9. 经营范围（使用配置或随机生成）
        if config.get("business_scope"):
            business_scope = config["business_scope"]
        else:
            if config.get("industry_type"):
                industry_scopes = {
                    "科技": "技术开发、技术咨询、技术服务、技术转让；销售计算机、软件及辅助设备、电子产品、通讯设备；货物进出口、技术进出口、代理进出口。",
                    "软件": "软件开发；计算机系统服务；数据处理；基础软件服务；应用软件服务；销售计算机、软件及辅助设备、电子产品；技术开发、技术咨询、技术转让、技术服务。",
                    "零售": "销售服装、鞋帽、针纺织品、化妆品、日用品、工艺品、珠宝首饰、文具用品、体育用品、玩具、五金交电、家用电器、电子产品；货物进出口、技术进出口。",
                    "餐饮": "餐饮服务；食品销售；餐饮管理；酒店管理；会议服务；展览展示服务；礼仪服务；企业形象策划；市场营销策划。",
                    "建筑": "建筑工程施工；建筑装饰装修工程设计与施工；市政公用工程施工；园林绿化工程施工；建筑材料销售；建筑机械设备租赁。",
                    "医疗": "医疗器械的技术开发、技术咨询、技术服务；销售医疗器械；货物进出口、技术进出口；健康咨询；医学研究与试验发展。",
                    "广告": "广告设计、制作、代理、发布；企业形象策划；市场营销策划；会议服务；展览展示服务；文化艺术交流活动策划。",
                    "房地产": "房地产开发；物业管理；房屋租赁；房地产信息咨询；建筑工程；装饰装修工程；建筑材料销售。",
                    "教育": "教育咨询；文化咨询；体育咨询；健康咨询；技术培训；会议服务；展览展示服务；组织文化艺术交流活动。",
                    "贸易": "批发、零售：日用百货、服装鞋帽、化妆品、家居用品、电子产品、办公用品、体育用品、玩具、工艺品。",
                }
                business_scope = industry_scopes.get(
                    config["industry_type"],
                    "技术开发、技术咨询、技术服务、技术转让；销售计算机、软件及辅助设备、电子产品、通讯设备；货物进出口、技术进出口、代理进出口。",
                )
            else:
                business_scopes = [
                    "技术开发、技术咨询、技术服务、技术转让；销售计算机、软件及辅助设备、电子产品、通讯设备；货物进出口、技术进出口、代理进出口。",
                    "软件开发；计算机系统服务；数据处理；基础软件服务；应用软件服务；销售计算机、软件及辅助设备、电子产品；技术开发、技术咨询、技术转让、技术服务。",
                    "销售服装、鞋帽、针纺织品、化妆品、日用品、工艺品、珠宝首饰、文具用品、体育用品、玩具、五金交电、家用电器、电子产品；货物进出口、技术进出口。",
                    "餐饮服务；食品销售；餐饮管理；酒店管理；会议服务；展览展示服务；礼仪服务；企业形象策划；市场营销策划。",
                    "建筑工程施工；建筑装饰装修工程设计与施工；市政公用工程施工；园林绿化工程施工；建筑材料销售；建筑机械设备租赁。",
                    "医疗器械的技术开发、技术咨询、技术服务；销售医疗器械；货物进出口、技术进出口；健康咨询；医学研究与试验发展。",
                    "广告设计、制作、代理、发布；企业形象策划；市场营销策划；会议服务；展览展示服务；文化艺术交流活动策划。",
                    "房地产开发；物业管理；房屋租赁；房地产信息咨询；建筑工程；装饰装修工程；建筑材料销售。",
                    "教育咨询；文化咨询；体育咨询；健康咨询；技术培训；会议服务；展览展示服务；组织文化艺术交流活动。",
                    "批发、零售：日用百货、服装鞋帽、化妆品、家居用品、电子产品、办公用品、体育用品、玩具、工艺品。",
                ]
                business_scope = random.choice(business_scopes)

        return {
            "unified_social_credit_code": unified_social_credit_code,
            "company_name": company_name,
            "company_type": company_type,
            "address": address,
            "legal_representative": legal_representative,
            "registered_capital": registered_capital,
            "establishment_date": establishment_date,
            "registration_date": establishment_date,  # 登记日期通常与成立日期相同
            "business_term": business_term,
            "business_scope": business_scope,
        }
