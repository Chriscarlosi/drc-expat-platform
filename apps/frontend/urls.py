from django.urls import path
from . import views

app_name = "frontend"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("features/", views.features, name="features"),
    path("modules/", views.modules, name="modules"),
    path("pricing/", views.pricing, name="pricing"),
    path("contact/", views.contact, name="contact"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.executive_dashboard, name="executive_dashboard"),
    path("my-portal/", views.expert_portal, name="expert_portal"),
    path("prolongation/new/", views.ProlongationRequestView.as_view(), name="prolongation_create"),
    path("prolongation/success/", views.ProlongationSuccessView.as_view(), name="prolongation_success"),
    path("security/", views.security, name="security"),
    path("privacy/", views.privacy, name="privacy"),
    path("terms/", views.terms, name="terms"),
    path("reports/", views.reports_dashboard, name="reports"),
    path("settings/", views.settings_dashboard, name="settings"),

    # Experts & Dependants
    path("experts/", views.expert_list, name="expert_list"),
    path("experts/add/", views.ExpertCreateView.as_view(), name="expert_add"),
    path("experts/<uuid:pk>/edit/", views.ExpertUpdateView.as_view(), name="expert_edit"),
    path("experts/<uuid:expert_id>/", views.expert_profile_view, name="expert_profile"),
    path("experts/<uuid:expert_id>/dependants/", views.expert_dependants, name="expert_dependants"),
    path("experts/<uuid:expert_id>/dependants/add/", views.DependantCreateView.as_view(), name="dependant_add"),

    # Visas, Penalties & Documents
    path("visas/", views.visa_records_list, name="visa_list"),
    path("penalties/", views.penalty_list, name="penalty_list"),
    path("penalties/<uuid:penalty_id>/resolve/", views.resolve_penalty, name="resolve_penalty"),
    path("documents/", views.document_list, name="document_list"),

    # Settings & Snapshots
    path("settings/import/", views.import_experts_csv, name="import_experts_csv"),
    path("workforce-snapshot/add/", views.add_workforce_snapshot, name="add_workforce_snapshot"),

    # Travel
    path("settings/invite/", views.invite_user, name="invite_user"),
    path("travel/", views.travel_dashboard, name="travel_dashboard"),
    path("travel/<uuid:flight_id>/manifest/", views.flight_manifest, name="flight_manifest"),
]