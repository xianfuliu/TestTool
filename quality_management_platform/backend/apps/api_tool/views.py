from __future__ import annotations

import json

import requests

from apps.common.http import api_view
from apps.common.legacy import load_json_file, write_json_file


PRODUCTS_CONFIG_PATH = "backend/config/products_config.json"


@api_view
def products(_request, payload=None):
    config = load_json_file(PRODUCTS_CONFIG_PATH)
    items = []
    for product_name, config_path in config.get("products", {}).items():
        items.append(
            {
                "name": product_name,
                "config_path": config_path,
                "locked": product_name in config.get("locked_products", []),
            }
        )
    return {
        "default_product": config.get("default_product"),
        "products": items,
    }


@api_view
def product_detail(request, product_name: str, payload=None):
    config = load_json_file(PRODUCTS_CONFIG_PATH)
    if product_name not in config.get("products", {}):
        raise ValueError("产品不存在")
    config_path = config["products"][product_name]
    if request.method == "GET":
        return {
            "name": product_name,
            "config_path": config_path,
            "config": load_json_file(config_path),
        }
    write_json_file(config_path, (payload or {}).get("config", {}))
    return {"saved": True, "config_path": config_path}


@api_view
def execute(_request, payload=None):
    url = (payload or {}).get("url", "").strip()
    method = (payload or {}).get("method", "POST").upper()
    headers = (payload or {}).get("headers", {})
    body = (payload or {}).get("body", {})
    encrypt_url = (payload or {}).get("encrypt_url", "").strip()
    decrypt_url = (payload or {}).get("decrypt_url", "").strip()
    timeout = int((payload or {}).get("timeout", 30))

    if not url:
        raise ValueError("url 不能为空")

    request_body = body
    encrypted_data = None

    if encrypt_url:
        encrypt_response = requests.post(
            encrypt_url,
            data=json.dumps(request_body, ensure_ascii=False),
            headers=headers,
            timeout=timeout,
        )
        if encrypt_response.status_code != 200:
            raise ValueError(f"加密接口调用失败: {encrypt_response.status_code}")
        encrypted_data = encrypt_response.text

    if method == "GET":
        response = requests.get(
            url,
            params=encrypted_data or request_body,
            headers=headers,
            timeout=timeout,
        )
    else:
        response = requests.request(
            method,
            url,
            data=encrypted_data if encrypted_data else None,
            json=None if encrypted_data else request_body,
            headers=headers,
            timeout=timeout,
        )

    decrypted_body = response.text
    if decrypt_url and response.status_code == 200:
        decrypt_response = requests.post(
            decrypt_url,
            data=response.text,
            headers=headers,
            timeout=timeout,
        )
        if decrypt_response.status_code != 200:
            raise ValueError(f"解密接口调用失败: {decrypt_response.status_code}")
        try:
            decrypt_json = decrypt_response.json()
            decrypted_body = (
                decrypt_json.get("decrypted_data")
                or decrypt_json.get("data")
                or decrypt_json
            )
        except Exception:
            decrypted_body = decrypt_response.text

    try:
        parsed_body = response.json()
    except Exception:
        parsed_body = response.text

    return {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body": parsed_body,
        "raw_body": response.text,
        "decrypted_body": decrypted_body,
    }
