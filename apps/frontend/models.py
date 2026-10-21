"""Frontend models — contact form submissions."""

from django.db import models
from django.utils import timezone


class ContactMessage(models.Model):
    """Submitted via /contact/ form."""

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        READ = "READ", "Read"
        REPLIED = "REPLIED", "Replied"
        ARCHIVED = "ARCHIVED", "Archived"

    name = models.CharField(max_length=200)
    email = models.EmailField()
    company = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    role = models.CharField(max_length=100, blank=True)
    message = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW, db_index=True,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"

    def __str__(self):
        return f"{self.name} <{self.email}> — {self.created_at:%Y-%m-%d %H:%M}"