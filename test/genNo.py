import random


def generate_unified_social_credit_code():
    """
    生成符合规则的真实统一社会信用代码（18位）
    结构：1位登记管理部门代码 + 1位机构类别代码 + 6位行政区划代码 + 9位组织机构代码 + 1位校验码
    """

    # 1. 第一位：登记管理部门代码
    # 1-企业，5-个体户，9-事业单位，Y-社会组织
    first_codes = ['1', '5', '9', 'Y']
    first_code = random.choice(first_codes)

    # 2. 第二位：机构类别代码（根据第一位确定范围）
    second_code_rules = {
        '1': [1, 2, 3, 9],  # 企业
        '5': [1, 2, 3, 9],  # 个体户
        '9': [1, 2, 3],  # 事业单位
        'Y': [1]  # 社会组织
    }
    second_code = str(random.choice(second_code_rules[first_code]))

    # 3. 第3-8位：行政区划代码（6位，使用真实存在的行政区划）
    # 这里使用部分真实行政区划代码
    admin_codes = [
        '110000',  # 北京市
        '310000',  # 上海市
        '440300',  # 深圳市
        '330100',  # 杭州市
        '320100',  # 南京市
        '120000',  # 天津市
        '500000',  # 重庆市
        '440100',  # 广州市
        '420100',  # 武汉市
        '610100',  # 西安市
    ]
    admin_code = random.choice(admin_codes)

    # 4. 第9-17位：组织机构代码（9位）
    # 前8位随机生成，第9位是校验码
    org_part = ''
    for i in range(8):
        # 可以是数字或大写字母（I、O、Z除外）
        char = random.choice('0123456789ABCDEFGHJKLMNPQRTUWXY')
        org_part += char

    # 5. 计算第17位（组织机构代码的校验码）
    org_weights = [3, 7, 9, 10, 5, 8, 4, 2]
    org_sum = 0

    for i, char in enumerate(org_part):
        if char.isdigit():
            value = int(char)
        else:
            # A=10, B=11, ... 但需要跳过I,O,Z
            value = ord(char) - ord('A') + 10
            # 跳过I,O,Z
            if char > 'I':
                value -= 1
            if char > 'O':
                value -= 1
            if char > 'Z':
                value -= 1

        org_sum += value * org_weights[i]

    org_check_code = 11 - (org_sum % 11)
    if org_check_code == 10:
        org_check_char = 'X'
    elif org_check_code == 11:
        org_check_char = '0'
    else:
        org_check_char = str(org_check_code)

    org_part += org_check_char  # 第9位（总第17位）

    # 6. 第18位：统一社会信用代码校验码
    # 计算前17位的校验码
    full_code_without_check = first_code + second_code + admin_code + org_part

    # 字符映射表
    char_map = {
        '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
        'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15, 'G': 16, 'H': 17,
        'J': 18, 'K': 19, 'L': 20, 'M': 21, 'N': 22, 'P': 23, 'Q': 24,
        'R': 25, 'T': 26, 'U': 27, 'W': 28, 'X': 29, 'Y': 30
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


def validate_unified_social_credit_code(code):
    """验证统一社会信用代码是否有效"""
    if len(code) != 18:
        return False

    # 验证校验码
    char_map = {
        '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
        'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15, 'G': 16, 'H': 17,
        'J': 18, 'K': 19, 'L': 20, 'M': 21, 'N': 22, 'P': 23, 'Q': 24,
        'R': 25, 'T': 26, 'U': 27, 'W': 28, 'X': 29, 'Y': 30
    }

    weights = [1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]

    total = 0
    for i in range(17):
        char = code[i]
        if char in char_map:
            total += char_map[char] * weights[i]
        else:
            return False

    remainder = total % 31
    check_code = 31 - remainder
    if check_code == 31:
        check_code = 0

    check_char_dict = "0123456789ABCDEFGHJKLMNPQRTUWXY"
    expected_check_char = check_char_dict[check_code]

    return code[17] == expected_check_char


# 使用示例
if __name__ == "__main__":
    # 生成10个统一社会信用代码
    print("生成的统一社会信用代码示例：")
    for i in range(10):
        code = generate_unified_social_credit_code()
        is_valid = validate_unified_social_credit_code(code)
        print(f"{i + 1}. {code} {'✓' if is_valid else '✗'}")

    # 验证已有代码（示例）
    print("\n验证示例代码：")
    test_codes = [
        "91350100M000100Y43",  # 真实示例（可能已失效）
        "911101087000000000",  # 格式正确但虚构
    ]

    for test_code in test_codes:
        is_valid = validate_unified_social_credit_code(test_code)
        print(f"{test_code}: {'有效' if is_valid else '无效'}")