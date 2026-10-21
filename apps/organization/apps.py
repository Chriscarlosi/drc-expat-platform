

from django.apps import AppConfig

class OrganizationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.organization'

    def ready(self):
        # Register WorkforceSnapshot with django-auditlog for immutable tracking
        try:
            from auditlog.registry import auditlog
            from .models import WorkforceSnapshot
            auditlog.register(WorkforceSnapshot)
        except Exception:
            pass