import os
import random
from src.utils.resource_utils import resource_path
import base64
import io
from PIL import Image


class IdCardImageGenerator:
    """身份证图片生成工具类"""

    def __init__(self, parent_app=None):
        self.parent_app = parent_app
        self.face_images = ["src/resources/images/ocr_face_1.png", "src/resources/images/ocr_face_2.png"]

        # 压缩设置
        self.compression_config = {
            'max_size': (400, 300),  # 最大尺寸
            'quality': 85,  # JPEG质量 (1-100)
            'optimize': True  # 优化
        }

    def generate_id_card_images(self, id_data=None, face_image_path=None):
        """
        生成身份证图片

        Args:
            id_data: 身份证数据，如果为None则自动生成
            face_image_path: 人脸图片路径，如果为None则随机选择

        Returns:
            tuple: (front_image, back_image) 正反面图片
        """
        # 如果没有提供数据，则生成数据
        if id_data is None:
            id_data = self.parent_app.generator.generate_id_card_data()
            self.parent_app.id_data = id_data

        # 处理人脸图片路径
        if face_image_path is None:
            face_image_path = self._get_random_face_image()

        # 检查模板文件是否存在
        if not os.path.exists(self.parent_app.filler.template_path):
            raise FileNotFoundError(f"身份证模板文件不存在: {self.parent_app.filler.template_path}")

        # 生成完整身份证图片
        full_image = self.parent_app.filler.fill_id_card(id_data, face_image_path=face_image_path)

        if full_image is None:
            raise Exception("身份证图片生成失败")

        # 分割正反面
        front_image, back_image = self.parent_app.filler.split_id_card(full_image)

        if front_image is None or back_image is None:
            raise Exception("身份证图片分割失败")

        return front_image, back_image

    def generate_id_card_images_base64(self, id_data=None, face_image_path=None, format="JPEG",
                                       compression_config=None):
        """
        生成身份证图片并返回Base64编码

        Args:
            id_data: 身份证数据，如果为None则自动生成
            face_image_path: 人脸图片路径，如果为None则随机选择
            format: 图片格式，默认JPEG（压缩效果更好）
            compression_config: 压缩配置，如果为None使用默认配置

        Returns:
            dict: 包含正反面Base64编码的字典
                {
                    'front': 'base64编码的正面图片',
                    'back': 'base64编码的反面图片'
                }
        """
        try:
            # 生成图片
            front_image, back_image = self.generate_id_card_images(id_data, face_image_path)

            # 应用压缩配置
            config = compression_config or self.compression_config

            # 转换为Base64（带压缩）
            front_base64 = self._pil_image_to_base64_compressed(front_image, format, config)
            back_base64 = self._pil_image_to_base64_compressed(back_image, format, config)

            # 人脸图片也压缩
            face_pil_image = Image.open(self._get_random_face_image())
            face_base64 = self._pil_image_to_base64_compressed(face_pil_image, format, config)

            return {
                'front': front_base64,
                'back': back_base64,
                'face': face_base64
            }

        except Exception as e:
            raise Exception(f"生成Base64编码的身份证图片失败: {str(e)}")

    def _pil_image_to_base64_compressed(self, pil_image, format="JPEG", compression_config=None):
        """
        将PIL图像转换为Base64编码（带压缩）

        Args:
            pil_image: PIL图像对象
            format: 图片格式，推荐JPEG以获得更好的压缩
            compression_config: 压缩配置

        Returns:
            str: Base64编码的图片字符串
        """
        if pil_image is None:
            raise ValueError("PIL图像不能为None")

        # 使用默认压缩配置
        config = compression_config or self.compression_config

        # 调整图片尺寸
        if config.get('max_size'):
            pil_image = self._resize_image(pil_image, config['max_size'])

        # 转换为RGB模式（如果是RGBA）
        if pil_image.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', pil_image.size, (255, 255, 255))
            background.paste(pil_image, mask=pil_image.split()[-1])
            pil_image = background

        # 将图像保存到内存缓冲区（带压缩）
        buffer = io.BytesIO()

        save_kwargs = {
            'format': format,
            'optimize': config.get('optimize', True)
        }

        if format.upper() == 'JPEG':
            save_kwargs['quality'] = config.get('quality', 75)
        elif format.upper() == 'PNG':
            save_kwargs['compress_level'] = 6  # PNG压缩级别 (0-9, 9为最高压缩)

        pil_image.save(buffer, **save_kwargs)

        # 获取字节数据并编码为Base64
        image_bytes = buffer.getvalue()
        base64_string = base64.b64encode(image_bytes).decode('utf-8')

        return base64_string

    def _resize_image(self, image, max_size):
        """
        调整图片尺寸，保持宽高比

        Args:
            image: PIL图像
            max_size: 最大尺寸 (width, height)

        Returns:
            调整后的PIL图像
        """
        original_width, original_height = image.size
        max_width, max_height = max_size

        # 计算调整比例
        width_ratio = max_width / original_width
        height_ratio = max_height / original_height
        ratio = min(width_ratio, height_ratio)

        # 如果图片已经小于最大尺寸，则不调整
        if ratio >= 1:
            return image

        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)

        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _get_random_face_image(self):
        """获取随机人脸图片路径"""
        available_faces = []

        for face_file in self.face_images:
            face_path = resource_path(face_file)
            if not os.path.exists(face_path):
                # 尝试直接使用 resources 目录
                static_face = os.path.normpath(face_file)
                if os.path.exists(static_face):
                    face_path = static_face

            if face_path and os.path.exists(face_path):
                available_faces.append(face_path)
                print(f"找到人脸图片: {face_path}")

        if available_faces:
            selected_face = random.choice(available_faces)
            print(f"使用人脸图片: {selected_face}")
            return selected_face
        else:
            print("警告: 未找到人脸图片，将生成不带人脸的身份证")
            return None

    def _pil_image_to_base64(self, pil_image, format="PNG"):
        """
        将PIL图像转换为Base64编码（原方法，保持兼容性）
        """
        if pil_image is None:
            raise ValueError("PIL图像不能为None")

        buffer = io.BytesIO()
        pil_image.save(buffer, format=format)
        image_bytes = buffer.getvalue()
        base64_string = base64.b64encode(image_bytes).decode('utf-8')

        return base64_string

    def base64_to_pil_image(self, base64_string):
        """
        将Base64编码转换为PIL图像
        """
        if not base64_string:
            raise ValueError("Base64字符串不能为空")

        if base64_string.startswith('data:image'):
            base64_string = base64_string.split(',', 1)[1]

        image_bytes = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_bytes))

        return image

    def set_compression_config(self, max_size=None, quality=None, optimize=None):
        """
        设置压缩配置

        Args:
            max_size: 最大尺寸 (width, height)
            quality: JPEG质量 (1-100)
            optimize: 是否优化
        """
        if max_size:
            self.compression_config['max_size'] = max_size
        if quality is not None:
            self.compression_config['quality'] = quality
        if optimize is not None:
            self.compression_config['optimize'] = optimize