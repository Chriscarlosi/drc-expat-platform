from django.contrib import admin
from django.utils.html import format_html
from .models import ExpertProfile


@admin.register(ExpertProfile)
class ExpertProfileAdmin(admin.ModelAdmin):
    list_display = (
        'full_name_display', 'nationality', 'passport_expiry_display',
        'employer_company', 'job_title', 'is_active',
    )
    list_filter = ('nationality', 'gender', 'is_active', 'employer_company')
    search_fields = (
        'first_name', 'last_name', 'email', 'passport_number',
        'onem_registry_number', 'employer_company',
    )
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'

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
        ('Status', {
            'fields': ('is_active', 'notes', 'id', 'created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Name', ordering='last_name')
    def full_name_display(self, obj):
        return f"{obj.last_name}, {obj.first_name}"

    @admin.display(description='Passport Expiry')
    def passport_expiry_display(self, obj):
        days = (obj.passport_expiry_date - __import__('datetime').date.today()).days
        if days < 0:
            return format_html('<span style="color:red;font-weight:bold;">{}</span>', 'EXPIRED')
        if days < 90:
            return format_html(
                '<span style="color:orange;font-weight:bold;">{} days</span>', days,
            )
        return obj.passport_expiry_date