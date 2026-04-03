from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "resources" / "images"


def _find_font() -> str | None:
    candidates = [
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_path = _find_font()
    if font_path:
        return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()


class IDCardTemplateFiller:
    def __init__(self) -> None:
        self.template_path = IMAGE_DIR / "id_card_template.png"
        self.face_images = [IMAGE_DIR / "ocr_face_1.png", IMAGE_DIR / "ocr_face_2.png"]
        self.face_box = (836, 286, 196, 272)

    def fill(self, id_data: dict[str, str]) -> Image.Image:
        image = Image.open(self.template_path).convert("RGBA")
        draw = ImageDraw.Draw(image)

        main_font = _load_font(29)
        id_font = _load_font(34)
        issue_font = _load_font(29)
        date_font = _load_font(29)

        positions = {
            "name": (326, 335),
            "gender": (326, 405),
            "ethnic_group": (538, 405),
            "birth_year": (326, 475),
            "birth_month": (484, 475),
            "birth_day": (584, 475),
            "address": (326, 542),
            "id_number": (480, 722),
            "issue_authority": (535, 1380),
            "valid_period": (535, 1450),
        }

        draw.text(positions["name"], id_data["name"], fill="black", font=main_font)
        draw.text(positions["gender"], id_data["gender"], fill="black", font=main_font)
        draw.text(positions["ethnic_group"], id_data["ethnic_group"], fill="black", font=main_font)
        draw.text(positions["birth_year"], id_data["birth_date"][:4], fill="black", font=date_font)
        draw.text(positions["birth_month"], id_data["birth_date"][4:6], fill="black", font=date_font)
        draw.text(positions["birth_day"], id_data["birth_date"][6:8], fill="black", font=date_font)
        self._draw_address(draw, id_data["address"], positions["address"], main_font)
        draw.text(positions["id_number"], id_data["id_number"], fill="black", font=id_font)
        draw.text(positions["issue_authority"], id_data["issue_authority"], fill="black", font=issue_font)
        draw.text(positions["valid_period"], id_data["valid_period"], fill="black", font=issue_font)

        available_faces = [path for path in self.face_images if path.exists()]
        if available_faces:
            image = self._add_face_image(image, random.choice(available_faces))
        return image

    def split(self, image: Image.Image) -> tuple[Image.Image, Image.Image]:
        front_box = (135, 240, 1095, 850)
        back_box = (135, 950, 1090, 1550)
        return image.crop(front_box), image.crop(back_box)

    def _draw_address(
        self,
        draw: ImageDraw.ImageDraw,
        address: str,
        position: tuple[int, int],
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    ) -> None:
        lines = self._split_text_by_width(address, font, max_width=452)
        line_height = 39
        max_lines = 3
        for index, line in enumerate(lines[:max_lines]):
            draw.text((position[0], position[1] + index * line_height), line, fill="black", font=font)

    def _add_face_image(self, image: Image.Image, face_image_path: Path) -> Image.Image:
        face_img = Image.open(face_image_path).convert("RGBA")
        face_img = face_img.resize(
            (self.face_box[2], self.face_box[3]),
            Image.Resampling.LANCZOS,
        )
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay.paste(face_img, (self.face_box[0], self.face_box[1]))
        return Image.alpha_composite(image, overlay)

    def _split_text_by_width(
        self,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
    ) -> list[str]:
        lines: list[str] = []
        current = ""
        for char in text:
            candidate = current + char
            bbox = font.getbbox(candidate)
            width = bbox[2] - bbox[0]
            if width <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = char
        if current:
            lines.append(current)
        return lines


class BusinessLicenseTemplateFiller:
    def __init__(self) -> None:
        self.template_path = IMAGE_DIR / "business_license_template.png"

    def fill(self, business_data: dict[str, str]) -> Image.Image:
        image = Image.open(self.template_path).convert("RGBA")
        draw = ImageDraw.Draw(image)

        main_font = _load_font(30)
        code_font = _load_font(30)
        scope_font = _load_font(24)

        positions = {
            "unified_social_credit_code": (795, 563),
            "company_name": (472, 653),
            "company_type": (472, 714),
            "address": (472, 782),
            "legal_person": (472, 848),
            "registered_capital": (472, 914),
            "establishment_year": (472, 986),
            "establishment_month": (592, 986),
            "establishment_day": (670, 986),
            "business_term_start_year": (472, 1049),
            "business_term_start_month": (590, 1049),
            "business_term_start_day": (662, 1049),
            "business_term_end_year": (777, 1049),
            "business_term_end_month": (875, 1049),
            "business_term_end_day": (953, 1049),
            "business_scope": (472, 1105),
            "registration_year": (780, 1379),
            "registration_month": (898, 1379),
            "registration_day": (983, 1379),
        }

        draw.text(positions["unified_social_credit_code"], business_data["unified_social_credit_code"], fill="black", font=code_font)
        draw.text(positions["company_name"], business_data["company_name"], fill="black", font=main_font)
        draw.text(positions["company_type"], business_data["company_type"], fill="black", font=main_font)
        self._draw_address(draw, business_data["address"], positions["address"], main_font)
        draw.text(positions["legal_person"], business_data["legal_person"], fill="black", font=main_font)
        draw.text(positions["registered_capital"], business_data["registered_capital"], fill="black", font=main_font)

        establish_date = business_data["establish_date"]
        draw.text(positions["establishment_year"], establish_date[:4], fill="black", font=main_font)
        draw.text(positions["establishment_month"], establish_date[4:6], fill="black", font=main_font)
        draw.text(positions["establishment_day"], establish_date[6:8], fill="black", font=main_font)

        start_date = business_data["business_term_start"]
        end_date = business_data["business_term_end"]
        draw.text(positions["business_term_start_year"], start_date[:4], fill="black", font=main_font)
        draw.text(positions["business_term_start_month"], start_date[4:6], fill="black", font=main_font)
        draw.text(positions["business_term_start_day"], start_date[6:8], fill="black", font=main_font)
        draw.text(positions["business_term_end_year"], end_date[:4], fill="black", font=main_font)
        draw.text(positions["business_term_end_month"], end_date[4:6], fill="black", font=main_font)
        draw.text(positions["business_term_end_day"], end_date[6:8], fill="black", font=main_font)

        scope_lines = self._split_text_by_width(business_data["business_scope"], scope_font, 600)
        scope_y = positions["business_scope"][1]
        for line in scope_lines:
            draw.text((positions["business_scope"][0], scope_y), line, fill="black", font=scope_font)
            scope_y += 30

        draw.text(positions["registration_year"], establish_date[:4], fill="black", font=main_font)
        draw.text(positions["registration_month"], establish_date[4:6], fill="black", font=main_font)
        draw.text(positions["registration_day"], establish_date[6:8], fill="black", font=main_font)
        return image

    def _draw_address(
        self,
        draw: ImageDraw.ImageDraw,
        address: str,
        position: tuple[int, int],
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    ) -> None:
        if len(address) <= 25:
            draw.text(position, address, fill="black", font=font)
            return
        first_line = address[:25]
        second_line = address[25:50]
        draw.text(position, first_line, fill="black", font=font)
        draw.text((position[0], position[1] + 25), second_line, fill="black", font=font)

    def _split_text_by_width(
        self,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
    ) -> list[str]:
        lines: list[str] = []
        current = ""
        for char in text:
            candidate = current + char
            bbox = font.getbbox(candidate)
            width = bbox[2] - bbox[0]
            if width <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = char
        if current:
            lines.append(current)
        return lines[:6]
