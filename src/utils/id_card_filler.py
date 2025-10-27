import os
from PIL import Image, ImageDraw, ImageFont
from src.utils.resource_utils import resource_path


class IDCardFiller:
    """身份证图片填充"""
    def __init__(self, template_path):
        """初始化身份证填充器"""
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
                raise FileNotFoundError(f"无法找到身份证模板文件: {template_path}")
        self.font_path = self._find_font()
        print(f"模板路径: {self.template_path}")  # 调试信息

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

    def add_face_image(self, image, face_image_path, face_position, face_size=(210, 290)):
        """
        将人脸图片添加到身份证上
        """
        try:
            # 使用 resource_path 处理人脸图片路径
            actual_face_path = resource_path(face_image_path)

            if not os.path.exists(actual_face_path):
                # 如果找不到文件，尝试直接使用 resources 目录下的文件
                static_face_path = os.path.normpath(os.path.join("src/resources/images", os.path.basename(face_image_path)))
                if os.path.exists(static_face_path):
                    actual_face_path = static_face_path
                    print(f"使用静态目录下的人脸图片: {actual_face_path}")
                else:
                    print(f"警告: 无法找到人脸图片: {face_image_path}")
                    return image

            # 打开人脸图片
            face_img = Image.open(actual_face_path).convert("RGBA")
            # 调整人脸图片大小
            face_img = face_img.resize(face_size, Image.Resampling.LANCZOS)
            # 将人脸图片粘贴到身份证上
            image.paste(face_img, face_position)
            print(f"成功添加人脸图片: {actual_face_path}")

            return image
        except Exception as e:
            print(f"添加人脸图片时出错: {e}")
            return image

    def fill_id_card(self, id_data, face_image_path=None):
        """将身份证数据填充到模板中"""
        try:
            # 检查模板文件是否存在
            if not os.path.exists(self.template_path):
                print(f"错误: 模板文件不存在: {self.template_path}")
                return None
            print(f'模板路径{self.template_path}')
            # 打开模板图片
            image = Image.open(self.template_path).convert("RGBA")
            draw = ImageDraw.Draw(image)

            # 定义字体和大小
            # 主信息字体（姓名、性别、民族、出生、住址）
            main_font_size = 29
            # 身份证号码字体（较大）
            id_font_size = 34
            # 签发机关和有效期限字体
            issue_font_size = 29
            # 年月日数字字体（可能比普通文字稍大）
            date_font_size = 29

            if self.font_path:
                main_font = ImageFont.truetype(self.font_path, main_font_size)
                id_font = ImageFont.truetype(self.font_path, id_font_size)
                issue_font = ImageFont.truetype(self.font_path, issue_font_size)
                date_font = ImageFont.truetype(self.font_path, date_font_size)
            else:
                main_font = ImageFont.load_default()
                id_font = ImageFont.load_default()
                issue_font = ImageFont.load_default()
                date_font = ImageFont.load_default()
                print("警告：未找到中文字体，中文显示可能不正常")

            # 根据身份证模板标准布局定义字段位置
            # 这些坐标需要根据实际模板图片进行调整
            # 根据您提供的图片描述，出生日期的年月日需要分开填充
            positions = {
                # 正面信息（个人信息面）
                "name": (326, 335),  # 姓名位置
                "gender": (326, 405),  # 性别位置
                "ethnic": (538, 405),  # 民族位置
                "birth_year": (326, 475),  # 出生年份位置
                "birth_month": (484, 475),  # 出生月份位置
                "birth_day": (584, 475),  # 出生日期位置
                "address": (326, 542),  # 住址位置
                "id_number": (480, 722),  # 身份证号码位置

                # 反面信息（国徽面）
                "issue_authority": (535, 1380),  # 签发机关位置
                "valid_period": (535, 1450),  # 有效期限位置
            }

            # 绘制文本
            try:
                # 姓名
                draw.text(positions["name"], id_data["name"], fill="black", font=main_font)

                # 性别
                draw.text(positions["gender"], id_data["gender"], fill="black", font=main_font)

                # 民族
                draw.text(positions["ethnic"], id_data["ethnic"], fill="black", font=main_font)

                # 出生日期
                draw.text(positions["birth_year"], id_data["birth_year"], fill="black", font=date_font)
                draw.text(positions["birth_month"], id_data["birth_month"], fill="black", font=date_font)
                draw.text(positions["birth_day"], id_data["birth_day"], fill="black", font=date_font)

                # 住址
                address = id_data["address"]
                if len(address) > 20:
                    part1 = address[:20]
                    part2 = address[20:40]
                    draw.text(positions["address"], part1, fill="black", font=main_font)
                    second_line_pos = (positions["address"][0], positions["address"][1] + 35)
                    draw.text(second_line_pos, part2, fill="black", font=main_font)
                else:
                    draw.text(positions["address"], address, fill="black", font=main_font)

                # 身份证号码
                id_num = id_data["id_number"]
                draw.text(positions["id_number"], id_num, fill="black", font=id_font)

                # 签发机关
                draw.text(positions["issue_authority"], id_data["issue_authority"], fill="black", font=issue_font)

                # 有效期限
                draw.text(positions["valid_period"], id_data["valid_period"], fill="black", font=issue_font)

            except Exception as draw_error:
                print(f"绘制文本时出错: {draw_error}")
                return None

            # 添加人脸图片
            print(f'人脸路径：{face_image_path}')
            if face_image_path and os.path.exists(face_image_path):
                try:
                    face_position = (814, 284)
                    face_size = (210, 290)
                    image = self.add_face_image(image, face_image_path, face_position, face_size)
                except Exception as face_error:
                    print(f"添加人脸图片时出错: {face_error}")
                print("身份证图片生成成功")
                return image
            else:
                print("身份证图片生成失败")
                return None

        except Exception as e:
            print(f"生成身份证时出错: {e}")
            import traceback
            traceback.print_exc()  # 打印完整堆栈跟踪
            return None

    def split_id_card(self, image):
        """将身份证图片切割成正反面两张图片"""
        try:
            # 获取图片尺寸
            width, height = image.size

            # 定义切割坐标（根据您提供的图片描述）
            # 正面部分（个人信息面） - 上半部分
            front_box = (135, 240, 1095, 850)  # 假设正面高度为1000像素

            # 反面部分（国徽面） - 下半部分
            back_box = (135, 950, 1090, 1550)  # 假设反面从1000像素开始

            # 切割图片
            front_image = image.crop(front_box)
            back_image = image.crop(back_box)
            print(f"切割身份证图片成功")
            return front_image, back_image

        except Exception as e:
            print(f"切割身份证图片时出错: {e}")
            return None, None
