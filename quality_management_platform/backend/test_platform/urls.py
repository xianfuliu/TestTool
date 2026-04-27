from django.urls import include, path

urlpatterns = [
    path("api/common/", include("apps.common.urls")),
    path("api/auth/", include("apps.authentication.urls")),
    path("api/test-data/", include("apps.test_data.urls")),
    path("api/api-tool/", include("apps.api_tool.urls")),
    path("api/interface-auto/", include("apps.interface_auto.urls")),
    path("api/tool-cards/", include("apps.tool_cards.urls")),
    path("api/data-query/", include("apps.data_query.urls")),
    path("api/data-assets/", include("apps.data_assets.urls")),
    path("api/scheduler/", include("apps.scheduler.urls")),
    path("api/performance/", include("apps.performance.urls")),
]
