from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.shortcuts import get_object_or_404, render, redirect
from django.conf import settings
from django.utils.translation import activate

from .models import Company, Site, Department, WorkforceSnapshot
from .managers import TenantManager


# ═══════════════════════════════════════════════════════════════
# COMPANY VIEWS
# ═══════════════════════════════════════════════════════════════

class CompanyListView(LoginRequiredMixin, ListView):
    model = Company
    template_name = 'organization/company_list.html'
    context_object_name = 'companies'

    def get_queryset(self):
        # Superusers see everything. Regular users see only their company.
        if self.request.user.is_superuser:
            return Company.objects.filter(is_active=True)
        return Company.objects.filter(
            id=self.request.user.membership.company_id,
            is_active=True
        )


class CompanyDetailView(LoginRequiredMixin, DetailView):
    model = Company
    template_name = 'organization/company_detail.html'
    context_object_name = 'company'

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Company.objects.all()
        return Company.objects.filter(id=self.request.user.membership.company_id)


# ═══════════════════════════════════════════════════════════════
# SITE VIEWS
# ═══════════════════════════════════════════════════════════════

class SiteListView(LoginRequiredMixin, ListView):
    model = Site
    template_name = 'organization/site_list.html'
    context_object_name = 'sites'

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Site.objects.select_related('company').all()
        return Site.objects.filter(
            company=self.request.user.membership.company
        ).select_related('company')


# ═══════════════════════════════════════════════════════════════
# DEPARTMENT VIEWS
# ═══════════════════════════════════════════════════════════════

class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = 'organization/department_list.html'
    context_object_name = 'departments'

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Department.objects.select_related('company').all()
        return Department.objects.filter(
            company=self.request.user.membership.company
        ).select_related('company')


# ═══════════════════════════════════════════════════════════════
# WORKFORCE SNAPSHOT VIEWS (Auditable HR data for quota calculation)
# ═══════════════════════════════════════════════════════════════

class WorkforceSnapshotListView(LoginRequiredMixin, ListView):
    model = WorkforceSnapshot
    template_name = 'organization/workforce_snapshot_list.html'
    context_object_name = 'snapshots'
    paginate_by = 20

    def get_queryset(self):
        if self.request.user.is_superuser:
            return WorkforceSnapshot.objects.select_related('company', 'created_by').all()
        return WorkforceSnapshot.objects.filter(
            company=self.request.user.membership.company
        ).select_related('company', 'created_by')


class WorkforceSnapshotCreateView(LoginRequiredMixin, CreateView):
    model = WorkforceSnapshot
    template_name = 'organization/workforce_snapshot_form.html'
    fields = [
        'company', 'snapshot_date',
        'total_congolese_staff', 'total_expat_staff',
        'congolese_class_i_v', 'congolese_supervisor', 'congolese_management',
        'expat_class_i_v', 'expat_supervisor', 'expat_management',
        'notes'
    ]
    success_url = reverse_lazy('organization:workforce_snapshot_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Non-superusers can only create snapshots for their own company
        if not self.request.user.is_superuser:
            form.fields['company'].queryset = Company.objects.filter(
                id=self.request.user.membership.company_id
            )
            form.fields['company'].initial = self.request.user.membership.company
            form.fields['company'].disabled = True
        return form

    def form_valid(self, form):
        # Set the creator automatically
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class WorkforceSnapshotUpdateView(LoginRequiredMixin, UpdateView):
    model = WorkforceSnapshot
    template_name = 'organization/workforce_snapshot_form.html'
    fields = [
        'snapshot_date',
        'total_congolese_staff', 'total_expat_staff',
        'congolese_class_i_v', 'congolese_supervisor', 'congolese_management',
        'expat_class_i_v', 'expat_supervisor', 'expat_management',
        'notes'
    ]
    success_url = reverse_lazy('organization:workforce_snapshot_list')

    def get_queryset(self):
        if self.request.user.is_superuser:
            return WorkforceSnapshot.objects.all()
        return WorkforceSnapshot.objects.filter(
            company=self.request.user.membership.company
        )


class WorkforceSnapshotDeleteView(LoginRequiredMixin, DeleteView):
    model = WorkforceSnapshot
    template_name = 'organization/workforce_snapshot_confirm_delete.html'
    success_url = reverse_lazy('organization:workforce_snapshot_list')

    def get_queryset(self):
        if self.request.user.is_superuser:
            return WorkforceSnapshot.objects.all()
        return WorkforceSnapshot.objects.filter(
            company=self.request.user.membership.company
        )


# ═══════════════════════════════════════════════════════════════
# UTILITY VIEWS (MFA Setup, Language Switching)
# ═══════════════════════════════════════════════════════════════

def mfa_setup(request):
    """
    Placeholder view for MFA setup.
    Redirects to the admin MFA setup or renders a basic template.
    """
    # If using django-otp, you can render a template showing the QR code.
    # For now, we redirect to the admin dashboard where MFA can be configured.
    return redirect("/admin/")


def set_language_view(request):
    """
    Sets the language preference in the session and redirects back.
    Usage: /organization/set-language/?lang=fr&next=/dashboard/
    """
    lang = request.GET.get("lang", "en")
    next_url = request.GET.get("next", "/dashboard/")

    if lang in dict(settings.LANGUAGES):
        activate(lang)
        request.session[settings.LANGUAGE_COOKIE_NAME] = lang

        # Optional: Save preference to the user profile if you add a 'language' field later
        # if request.user.is_authenticated:
        #     request.user.language = lang
        #     request.user.save(update_fields=["language"])

    return redirect(next_url)