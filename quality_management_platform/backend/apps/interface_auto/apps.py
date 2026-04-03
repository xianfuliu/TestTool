from django.apps import AppConfig


class InterfaceAutoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.interface_auto"
    verbose_name = "接口自动化"
