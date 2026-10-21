import datetime
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin

from .models import ExpertProfile


@admin.register(ExpertProfile)
class ExpertProfileAdmin(ModelAdmin):
    list_display = (
        'full_name_display', 'nationality', 'employer_company',
        'job_title', 'passport_expiry_display', 'is_active'
    )
    list_filter = ('nationality', 'gender', 'is_active', 'employer_company')
    search_fields = (
        'first_name', 'last_name', 'email', 'passport_number',
        'onem_registry_number', 'employer_company',
    )
    date_hierarchy = 'created_at'

    # Ensure manage_family is in readonly_fields
    readonly_fields = ('id', 'created_at', 'updated_at', 'manage_family')

    fieldsets = (
        ('Identity', {
            'fields': (
                'user', 'first_name', 'last_name', 'date_of_birth',
                'gender', 'nationality',
            ),
        }),
        ('Passport (AES-256 encrypted)', {
            'fields': (
                'passport_number', 'passport_issue_date',
                'passport_expiry_date', 'passport_scan',
            ),
        }),
        ('Health', {
            'fields': (
                'yellow_fever_card_number', 'yellow_fever_expiry_date',
                'yellow_fever_scan',
            ),
        }),
        ('Labour Registry', {
            'fields': ('onem_registry_number',),
        }),
        ('Contact', {
            'fields': ('email', 'phone'),
        }),
        ('Employment', {
            'fields': ('employer_company', 'job_title', 'job_title_fr'),
        }),
        ('Family & Dependants', {
            'fields': ('manage_family',),
            'description': 'Manage spouse and children for visa and flight manifest generation.'
        }),
        ('Status', {
            'fields': ('is_active', 'notes', 'id', 'created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Name', ordering='last_name')
    def full_name_display(self, obj):
        return f"{obj.last_name}, {obj.first_name}"

    @admin.display(description='Passport Expiry')
    def passport_expiry_display(self, obj):
        if not obj.passport_expiry_date:
            return "—"
        days = (obj.passport_expiry_date - datetime.date.today()).days
        if days < 0:
            return format_html('<span style="color:red;font-weight:bold;">{}</span>', 'EXPIRED')
        if days < 90:
            return format_html(
                '<span style="color:orange;font-weight:bold;">{} days</span>', days,
            )
        return obj.passport_expiry_date

    # --- THE MISSING METHOD IS DEFINED HERE ---
    @admin.display(description="Manage Family Members")
    def manage_family(self, obj):
        """Adds a premium button to the admin to manage dependants."""
        if obj.pk:
            url = reverse('frontend:expert_dependants', kwargs={'expert_id': obj.pk})
            # Using mark_safe with an f-string to avoid Django 6.0 format_html strictness
            return mark_safe(
                f'<a href="{url}" target="_blank" style="display:inline-flex; align-items:center; gap:8px; '
                'background:#F59E0B; color:white; padding:8px 16px; border-radius:8px; '
                'font-weight:700; text-decoration:none; font-size:13px; box-shadow: 0 4px 6px -1px rgba(245, 158, 11, 0.3);">'
                '<svg style="width:16px;height:16px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
                '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>'
                'Manage Family Members (Dependants) →</a>'
            )
        return "—"