from django.urls import path
from . import exports, views, rotation_views

app_name = "travel"

urlpatterns = [
    path(
        "flight/<uuid:flight_id>/manifest/",
        exports.export_dgm_manifest,
        name="dgm_manifest",
    ),
    path(
        "flight/<uuid:flight_id>/manifest/print/",
        views.flight_manifest_print,
        name="manifest_print",
    ),
    path(
        "cost-dashboard/",
        views.cost_dashboard,
        name="cost_dashboard",
    ),
    path(
        "rotation-calendar/",
        rotation_views.rotation_calendar,
        name="rotation_calendar",
    ),
    path(
        "medevac/",
        rotation_views.medevac_dashboard,
        name="medevac_dashboard",
    ),
]