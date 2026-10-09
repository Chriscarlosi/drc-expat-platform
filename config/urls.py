from django.contrib import admin
from django.urls import path, include
from apps.organization.views import mfa_setup

urlpatterns = [
    path('admin/mfa-setup/', mfa_setup, name='mfa_setup'),
    path('admin/', admin.site.urls),
    path('compliance/', include('apps.compliance.urls')),
]