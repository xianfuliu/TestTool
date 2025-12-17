import os
from PIL import Image, ImageDraw, ImageFont
from src.utils.resource_utils import resource_path


class BusinessLicenseFiller:
    """营业执照图片填充器"""

    def __init__(self, template_path):
        """初始化营业执照填充器"""
        # 使用 resource_path 处理模板路径
        self.template_path = resource_path(template_path)
        if not os.path.exists(self.template_path):
            # 如果找不到文件，尝试直接使用 resources 目录下的文件
            static_path = os.path.normpath(os.path.join("src/resources/images", os.path.basename(template_path)))
            if os.path.exists(static_path):
                self.template_path = static_path
                print(f"使用静态目录下的模板: {self.template_path}")
            else:
                # 如果还是找不到，抛出异常
                raise FileNotFoundError(f"无法找到营业执照模板文件: {template_path}")
        self.font_path = self._find_font()
        print(f"营业执照模板路径: {self.template_path}")

    def _find_font(self):
        """尝试找到可用的中文字体"""
        # 常见中文字体路径
        font_paths = [
            "C:/Windows/Fonts/simhei.ttf",  # Windows 黑体
            "C:/Windows/Fonts/simsun.ttc",  # Windows 宋体
            "/System/Library/Fonts/PingFang.ttc",  # macOS 苹方
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"  # Linux
        ]

        for path in font_paths:
            if os.path.exists(path):
                return path

        # 如果找不到系统字体，使用PIL默认字体（可能不支持中文）
        return None

    def fill_business_license(self, business_data):
        """将营业执照数据填充到模板中"""
        try:
            # 检查模板文件是否存在
            if not os.path.exists(self.template_path):
                print(f"错误: 模板文件不存在: {self.template_path}")
                return None
            
            print(f"营业执照模板路径: {self.template_path}")
            
            # 打开模板图片
            image = Image.open(self.template_path).convert("RGBA")
            draw = ImageDraw.Draw(image)

            # 定义字体和大小
            # 主要信息字体
            main_font_size = 30
            # 统一社会信用代码字体（稍大）
            code_font_size = 30
            # 经营范围字体（稍小，因为内容较多）
            scope_font_size = 24

            if self.font_path:
                main_font = ImageFont.truetype(self.font_path, main_font_size)
                code_font = ImageFont.truetype(self.font_path, code_font_size)
                scope_font = ImageFont.truetype(self.font_path, scope_font_size)
            else:
                main_font = ImageFont.load_default()
                code_font = ImageFont.load_default()
                scope_font = ImageFont.load_default()
                print("警告：未找到中文字体，中文显示可能不正常")

            # 根据营业执照模板定义字段位置
            # 这些坐标需要根据实际模板图片进行调整
            positions = {
                # 统一社会信用代码
                "unified_social_credit_code": (795, 563),
                
                # 名称
                "company_name": (472, 653),
                
                # 类型
                "company_type": (472, 714),
                
                # 住所
                "address": (472, 782),
                
                # 法定代表人
                "legal_representative": (472, 848),
                
                # 注册资本
                "registered_capital": (472, 914),
                
                # 成立日期 - 年
                "establishment_year": (472, 986),
                # 成立日期 - 月
                "establishment_month": (592, 986),
                # 成立日期 - 日
                "establishment_day": (670, 986),
                
                # 营业期限 - 开始年
                "business_term_start_year": (472, 1049),
                # 营业期限 - 开始月
                "business_term_start_month": (590, 1049),
                # 营业期限 - 开始日
                "business_term_start_day": (662, 1049),
                # 营业期限 - 结束年
                "business_term_end_year": (777, 1049),
                # 营业期限 - 结束月
                "business_term_end_month": (875, 1049),
                # 营业期限 - 结束日
                "business_term_end_day": (953, 1049),
                
                # 经营范围
                "business_scope": (472, 1105),

                # 登记日期 - 年
                "registration_year": (780, 1379),
                # 登记日期 - 月
                "registration_month": (898, 1379),
                # 登记日期 - 日
                "registration_day": (983, 1379)
            }

            # 绘制文本
            try:
                # 1. 统一社会信用代码
                draw.text(positions["unified_social_credit_code"], 
                         business_data["unified_social_credit_code"], 
                         fill="black", font=code_font)

                # 2. 名称
                draw.text(positions["company_name"], 
                         business_data["company_name"], 
                         fill="black", font=main_font)

                # 3. 类型
                draw.text(positions["company_type"], 
                         business_data["company_type"], 
                         fill="black", font=main_font)

                # 4. 住所
                address = business_data["address"]
                # 如果地址太长，分两行显示
                if len(address) > 25:
                    part1 = address[:25]
                    part2 = address[25:50]
                    draw.text(positions["address"], part1, fill="black", font=main_font)
                    second_line_pos = (positions["address"][0], positions["address"][1] + 25)
                    draw.text(second_line_pos, part2, fill="black", font=main_font)
                else:
                    draw.text(positions["address"], address, fill="black", font=main_font)

                # 5. 法定代表人
                draw.text(positions["legal_representative"], 
                         business_data["legal_representative"], 
                         fill="black", font=main_font)

                # 6. 注册资本
                draw.text(positions["registered_capital"], 
                         business_data["registered_capital"], 
                         fill="black", font=main_font)

                # 7. 成立日期
                establishment_date = business_data["establishment_date"]
                year = establishment_date[:4]
                month = establishment_date[4:6]
                day = establishment_date[6:8]
                
                draw.text(positions["establishment_year"], year, fill="black", font=main_font)
                draw.text(positions["establishment_month"], month, fill="black", font=main_font)
                draw.text(positions["establishment_day"], day, fill="black", font=main_font)

                # 8. 营业期限
                business_term = business_data["business_term"]
                if business_term == "长期":
                    # 如果是长期，在开始日期位置显示"长期"
                    draw.text(positions["business_term_start_year"], "长期", fill="black", font=main_font)
                else:
                    # 如果是具体期限，分别显示开始和结束日期
                    start_end = business_term.split("-")
                    if len(start_end) == 2:
                        start_date = start_end[0]
                        end_date = start_end[1]
                        
                        start_year = start_date[:4]
                        start_month = start_date[4:6]
                        start_day = start_date[6:8]
                        
                        end_year = end_date[:4]
                        end_month = end_date[4:6]
                        end_day = end_date[6:8]
                        
                        draw.text(positions["business_term_start_year"], start_year, fill="black", font=main_font)
                        draw.text(positions["business_term_start_month"], start_month, fill="black", font=main_font)
                        draw.text(positions["business_term_start_day"], start_day, fill="black", font=main_font)
                        draw.text(positions["business_term_end_year"], end_year, fill="black", font=main_font)
                        draw.text(positions["business_term_end_month"], end_month, fill="black", font=main_font)
                        draw.text(positions["business_term_end_day"], end_day, fill="black", font=main_font)

                # 9. 经营范围
                scope = business_data["business_scope"]
                # 经营范围内容较多，需要分行显示，根据模板实际宽度调整每行字符数
                scope_lines = self._split_text_by_width(scope, scope_font, max_width=600)  # 缩小宽度到600像素
                scope_y = positions["business_scope"][1]
                
                for line in scope_lines:
                    draw.text((positions["business_scope"][0], scope_y), line, fill="black", font=scope_font)
                    scope_y += 30  # 增加行间距，避免文字重叠

                # 10. 登记日期
                if "registration_date" in business_data:
                    registration_date = business_data["registration_date"]
                    reg_year = registration_date[:4]
                    reg_month = registration_date[4:6]
                    reg_day = registration_date[6:8]
                    
                    draw.text(positions["registration_year"], reg_year, fill="black", font=main_font)
                    draw.text(positions["registration_month"], reg_month, fill="black", font=main_font)
                    draw.text(positions["registration_day"], reg_day, fill="black", font=main_font)

            except Exception as draw_error:
                print(f"绘制文本时出错: {draw_error}")
                return None

            print("营业执照图片生成成功")
            return image

        except Exception as e:
            print(f"生成营业执照时出错: {e}")
            import traceback
            traceback.print_exc()  # 打印完整堆栈跟踪
            return None

    def _split_text(self, text, max_line_length):
        """将长文本分割为多行"""
        lines = []
        current_line = ""
        
        for char in text:
            # 如果当前行加上新字符不超过最大长度，或者当前行为空
            if len(current_line) + len(char) <= max_line_length or not current_line:
                current_line += char
            else:
                # 如果遇到标点符号，尽量在标点后换行
                if char in ['，', '。', '；', '、', '：']:
                    current_line += char
                    lines.append(current_line)
                    current_line = ""
                else:
                    # 在最后一个空格或标点处换行
                    last_space = max(current_line.rfind(' '), current_line.rfind('，'), 
                                   current_line.rfind('。'), current_line.rfind('；'))
                    
                    if last_space > 0 and last_space > len(current_line) - 10:
                        # 在空格或标点处分割
                        lines.append(current_line[:last_space + 1])
                        current_line = current_line[last_space + 1:] + char
                    else:
                        # 强制分割
                        lines.append(current_line)
                        current_line = char
        
        if current_line:
            lines.append(current_line)
        
        return lines

    def _split_text_by_width(self, text, font, max_width):
        """根据字体宽度智能分割文本，确保不超出模板宽度"""
        lines = []
        current_line = ""
        
        # 获取字体对象以计算文本宽度
        from PIL import ImageFont
        
        for char in text:
            # 测试当前行加上新字符的宽度
            test_line = current_line + char
            
            try:
                # 计算文本宽度
                bbox = font.getbbox(test_line)
                text_width = bbox[2] - bbox[0]
            except:
                # 如果无法计算宽度，使用字符数作为近似值
                text_width = len(test_line) * 20  # 近似值，每个字符约20像素
            
            # 如果宽度不超过最大宽度，或者当前行为空
            if text_width <= max_width or not current_line:
                current_line += char
            else:
                # 尝试在合适的断点处分割
                # 优先在标点符号处分割
                split_positions = []
                for i in range(len(current_line)-1, -1, -1):
                    if current_line[i] in ['，', '。', '；', '、', '：', '、', ' ', '；']:
                        split_positions.append(i)
                    elif i > 0 and current_line[i-1] in ['，', '。', '；', '、', '：', '、', ' ', '；']:
                        split_positions.append(i)
                
                # 找到最合适的断点
                best_split = -1
                for pos in split_positions:
                    if pos > len(current_line) * 0.6:  # 尽量在行尾附近分割
                        best_split = pos
                        break
                
                if best_split == -1 and split_positions:
                    best_split = split_positions[0]
                
                if best_split > 0:
                    # 在断点处分割
                    lines.append(current_line[:best_split + 1])
                    current_line = current_line[best_split + 1:] + char
                else:
                    # 强制分割
                    lines.append(current_line)
                    current_line = char
        
        if current_line:
            lines.append(current_line)
        
        # 限制最大行数，避免超出模板高度
        max_lines = 6  # 根据模板高度限制行数
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            # 在最后一行添加省略号表示内容被截断
            if len(lines) > 0:
                last_line = lines[-1]
                if len(last_line) > 3:
                    lines[-1] = last_line[:-3] + "..."
                else:
                    lines[-1] = "..."
        
        return lines