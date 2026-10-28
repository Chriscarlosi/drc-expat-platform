from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.organization.views import mfa_setup
from apps.organization.admin import download_procurement_pdf


urlpatterns = [
    # Public frontend (landing, login, dashboards)
    path("", include("apps.frontend.urls")),

    path('rosetta/', include('rosetta.urls')),

    # ─── FIXED LANGUAGE SWITCHER ───
    # Use Django's built-in i18n URLs instead of a custom view.
    # This automatically handles setting the django_language cookie.
    path("i18n/", include("django.conf.urls.i18n")),

    # Admin + MFA
    path("admin/mfa-setup/", mfa_setup, name="mfa_setup"),
    path("admin/", admin.site.urls),

    # Apps
    path("compliance/", include("apps.compliance.urls")),
    path("travel/", include("apps.travel.urls")),

    path('visas/', include('apps.visas.urls')),

    # Procurement PDF
    path("admin/proposal.pdf", download_procurement_pdf, name="procurement_pdf"),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)