from __future__ import annotations

import base64
import io
from typing import Any

from PIL import Image

from .generator import TestDataGenerator


_FRONT_IMAGE_SOURCE_SIZE = (960, 610)
_FACE_BOX_IN_FRONT = (701, 46, 897, 318)


def _normalize_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _image_to_base64(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.convert("RGB").save(
        buffer,
        format="JPEG",
        quality=84,
        optimize=True,
        progressive=True,
    )
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


class GeneratedDataToolkit:
    def __init__(self) -> None:
        self.generator = TestDataGenerator()

    def generate_user_workspace(self, raw_config: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.generator.generate_user_workspace(raw_config)

    def generate_enterprise_workspace(self, raw_config: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.generator.generate_enterprise_workspace(raw_config)

    def generate_workspace(self, raw_config: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.generator.generate_workspace(raw_config)

    def build_runtime_variables(
        self,
        raw_config: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        workspace = self.generate_workspace(raw_config)
        id_data = workspace["id_card"]["data"]
        id_images = workspace["id_card"]["images"]
        business_data = workspace["business_license"]["data"]
        business_image_base64 = _normalize_text(workspace["business_license"]["image_base64"])

        issue_date = _normalize_text(id_data.get("issue_date"))
        expiry_date = _normalize_text(id_data.get("expiry_date"))
        valid_period = _normalize_text(id_data.get("valid_period"))
        front_base64 = _normalize_text(id_images.get("front"))
        back_base64 = _normalize_text(id_images.get("back"))
        face_base64 = self._build_face_base64(front_base64)

        variables: dict[str, str] = {}
        self._assign_aliases(
            variables,
            ["name", "user_name", "userName"],
            id_data.get("name"),
        )
        self._assign_aliases(
            variables,
            ["id_card", "id_number", "idNo", "id_card_no", "idCardNo", "cert_no", "certNo"],
            id_data.get("id_number"),
        )
        self._assign_aliases(
            variables,
            ["phone", "mobile", "mobile_no", "mobileNo", "phone_no", "phoneNo"],
            id_data.get("phone_number"),
        )
        self._assign_aliases(
            variables,
            ["bank_card", "bank_card_no", "bank_card_number", "bankCardNo"],
            id_data.get("bank_card_number"),
        )
        self._assign_aliases(
            variables,
            ["address", "user_address", "id_card_address", "addressOCR", "address_ocr"],
            id_data.get("address"),
        )
        self._assign_aliases(
            variables,
            ["gender", "sex", "genderOCR", "sexOCR", "sex_ocr"],
            id_data.get("gender"),
        )
        self._assign_aliases(
            variables,
            ["ethnic_group", "ethnic", "ethnicOCR", "ethnic_ocr"],
            id_data.get("ethnic_group"),
        )
        self._assign_aliases(
            variables,
            ["birth_date", "birthDate", "birth_date_display"],
            id_data.get("birth_date_display"),
        )
        self._assign_aliases(
            variables,
            ["issue_authority", "issue_org", "issueOrgOCR", "issue_authority_ocr"],
            id_data.get("issue_authority"),
        )
        self._assign_aliases(
            variables,
            ["valid_period", "id_card_valid_period", "cert_valid_period"],
            valid_period,
        )
        self._assign_aliases(
            variables,
            ["id_card_start_time", "issue_date", "beginTimeOCR", "begin_time_ocr"],
            issue_date,
        )
        self._assign_aliases(
            variables,
            ["id_card_end_time", "expiry_date", "duetimeOCR", "due_time_ocr"],
            expiry_date,
        )
        self._assign_aliases(
            variables,
            ["id_card_start_time_digits", "issue_date_digits", "cert_valid_start"],
            issue_date.replace(".", ""),
        )
        self._assign_aliases(
            variables,
            ["id_card_end_time_digits", "expiry_date_digits", "cert_valid_end"],
            expiry_date.replace(".", ""),
        )
        self._assign_aliases(
            variables,
            ["id_card_front_base64", "front_base64", "positive", "positive_base64"],
            front_base64,
        )
        self._assign_aliases(
            variables,
            ["id_card_back_base64", "back_base64", "negative", "negative_base64"],
            back_base64,
        )
        self._assign_aliases(
            variables,
            ["face_base64", "face_best_base64", "best", "best_base64"],
            face_base64 or front_base64,
        )

        self._assign_aliases(
            variables,
            ["company_name", "company", "companyName"],
            business_data.get("company_name"),
        )
        self._assign_aliases(
            variables,
            ["credit_code", "creditCode", "unified_social_credit_code"],
            business_data.get("unified_social_credit_code"),
        )
        self._assign_aliases(
            variables,
            ["legal_person", "legalPerson", "legal_representative"],
            business_data.get("legal_person"),
        )
        self._assign_aliases(
            variables,
            ["registered_capital", "capital"],
            business_data.get("registered_capital"),
        )
        self._assign_aliases(
            variables,
            ["company_type"],
            business_data.get("company_type"),
        )
        self._assign_aliases(
            variables,
            ["industry_type"],
            business_data.get("industry_type"),
        )
        self._assign_aliases(
            variables,
            ["business_scope"],
            business_data.get("business_scope"),
        )
        self._assign_aliases(
            variables,
            ["business_address", "company_address"],
            business_data.get("address"),
        )
        self._assign_aliases(
            variables,
            ["business_license_base64", "business_license_image_base64", "license_base64"],
            business_image_base64,
        )
        self._assign_aliases(
            variables,
            ["business_term_start", "business_start_date"],
            business_data.get("business_term_start"),
        )
        self._assign_aliases(
            variables,
            ["business_term_end", "business_end_date"],
            business_data.get("business_term_end"),
        )
        self._assign_aliases(
            variables,
            ["business_term", "business_term_display"],
            business_data.get("business_term_display"),
        )
        self._assign_aliases(
            variables,
            ["establish_date", "establish_date_display"],
            business_data.get("establish_date_display"),
        )

        return variables

    def _assign_aliases(
        self,
        target: dict[str, str],
        keys: list[str],
        value: Any,
    ) -> None:
        normalized = _normalize_text(value)
        for key in keys:
            target[key] = normalized

    def _build_face_base64(self, front_base64: str) -> str:
        if not front_base64:
            return ""
        try:
            raw_bytes = base64.b64decode(front_base64)
            with Image.open(io.BytesIO(raw_bytes)) as image:
                left, top, right, bottom = _FACE_BOX_IN_FRONT
                width_scale = image.width / _FRONT_IMAGE_SOURCE_SIZE[0]
                height_scale = image.height / _FRONT_IMAGE_SOURCE_SIZE[1]
                crop_box = (
                    int(left * width_scale),
                    int(top * height_scale),
                    int(right * width_scale),
                    int(bottom * height_scale),
                )
                face_image = image.crop(crop_box)
                return _image_to_base64(face_image)
        except Exception:
            return front_base64


toolkit = GeneratedDataToolkit()
