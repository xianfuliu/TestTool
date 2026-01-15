import os
import base64
import io
from PIL import Image
from src.utils.business_license_filler import BusinessLicenseFiller


class BusinessLicenseImageGenerator:
    """营业执照图片生成器"""

    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.filler = None

    def _ensure_filler(self):
        """确保填充器已初始化"""
        if self.filler is None:
            try:
                # 使用相对路径，让 BusinessLicenseFiller 处理路径转换
                template_path = "src/resources/images/business_license_template.png"
                self.filler = BusinessLicenseFiller(template_path)
            except Exception as e:
                print(f"初始化营业执照填充器失败: {e}")
                return False
        return True

    def generate_business_license_images(self, business_data):
        """生成营业执照图片"""
        if not self._ensure_filler():
            return None

        try:
            # 生成营业执照图片
            business_license_image = self.filler.fill_business_license(business_data)

            if business_license_image:
                # 转换为RGB模式（如果需要）
                if business_license_image.mode != "RGB":
                    business_license_image = business_license_image.convert("RGB")

                # 调整图片大小（如果需要）
                target_size = (800, 1132)  # 保持宽高比
                business_license_image = business_license_image.resize(
                    target_size, Image.Resampling.LANCZOS
                )

                return business_license_image

            return None

        except Exception as e:
            print(f"生成营业执照图片时出错: {e}")
            import traceback

            traceback.print_exc()
            return None

    def generate_business_license_images_base64(self, business_data):
        """生成Base64编码的营业执照图片"""
        business_license_image = self.generate_business_license_images(business_data)

        if business_license_image:
            try:
                # 将图片转换为Base64
                buffered = io.BytesIO()
                business_license_image.save(buffered, format="PNG", quality=95)
                img_str = base64.b64encode(buffered.getvalue()).decode()

                return img_str

            except Exception as e:
                print(f"转换营业执照图片为Base64时出错: {e}")
                return None

        return None

    def save_business_license_image(self, business_data, save_path):
        """保存营业执照图片到文件"""
        business_license_image = self.generate_business_license_images(business_data)

        if business_license_image:
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(save_path), exist_ok=True)

                # 保存图片
                business_license_image.save(save_path, "PNG", quality=95)
                print(f"营业执照图片已保存到: {save_path}")
                return True

            except Exception as e:
                print(f"保存营业执照图片时出错: {e}")
                return False

        return False
