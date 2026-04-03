from __future__ import annotations

import os
from pathlib import Path

import pymysql

pymysql.version_info = (1, 4, 6, "final", 0)
pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent
from test_platform.db import DATABASE_CONFIG


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "test-platform-refactor-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "apps.common",
    "apps.authentication",
    "apps.test_data",
    "apps.api_tool",
    "apps.interface_auto",
    "apps.tool_cards",
    "apps.data_query",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "apps.common.middleware.CorsMiddleware",
]

ROOT_URLCONF = "test_platform.urls"
TEMPLATES: list[dict[str, object]] = []
WSGI_APPLICATION = "test_platform.wsgi.application"
ASGI_APPLICATION = "test_platform.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": DATABASE_CONFIG["database"],
        "USER": DATABASE_CONFIG["user"],
        "PASSWORD": DATABASE_CONFIG["password"],
        "HOST": DATABASE_CONFIG["host"],
        "PORT": DATABASE_CONFIG["port"],
        "OPTIONS": {
            "charset": "utf8mb4",
        },
    }
}

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = False

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
