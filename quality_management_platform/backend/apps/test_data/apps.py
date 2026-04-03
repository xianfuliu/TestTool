from django.apps import AppConfig


class TestDataConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.test_data"
    verbose_name = "测试数据工厂"
