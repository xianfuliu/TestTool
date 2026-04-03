from __future__ import annotations

import base64
import io

from PIL import Image

from .fillers import BusinessLicenseTemplateFiller, IDCardTemplateFiller


def _flatten_on_white(image: Image.Image) -> Image.Image:
    if image.mode != "RGBA":
        return image.convert("RGB")
    background = Image.new("RGB", image.size, "#ffffff")
    background.paste(image, mask=image.getchannel("A"))
    return background


def _resize_to_width(image: Image.Image, target_width: int) -> Image.Image:
    if image.width <= target_width:
        return image
    ratio = target_width / image.width
    return image.resize(
        (target_width, int(image.height * ratio)),
        Image.Resampling.LANCZOS,
    )


def _to_base64(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(
        buffer,
        format="JPEG",
        quality=84,
        optimize=True,
        progressive=True,
    )
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


class IdCardImageGenerator:
    """Use migrated ID card templates to generate preview images."""

    def __init__(self) -> None:
        self.filler = IDCardTemplateFiller()

    def generate_images(self, id_data: dict[str, str]) -> tuple[Image.Image, Image.Image]:
        full_image = self.filler.fill(id_data)
        front_image, back_image = self.filler.split(full_image)
        return (
            _resize_to_width(_flatten_on_white(front_image), 760),
            _resize_to_width(_flatten_on_white(back_image), 760),
        )

    def generate_images_base64(self, id_data: dict[str, str]) -> dict[str, str]:
        front_image, back_image = self.generate_images(id_data)
        return {
            "front": _to_base64(front_image),
            "back": _to_base64(back_image),
        }


class BusinessLicenseImageGenerator:
    """Use migrated business license template to generate preview image."""

    def __init__(self) -> None:
        self.filler = BusinessLicenseTemplateFiller()

    def generate_image(self, business_data: dict[str, str]) -> Image.Image:
        image = _flatten_on_white(self.filler.fill(business_data))
        return _resize_to_width(image, 780)

    def generate_image_base64(self, business_data: dict[str, str]) -> str:
        return _to_base64(self.generate_image(business_data))
