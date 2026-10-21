from django.shortcuts import render
from django.views.generic import CreateView, TemplateView, ListView
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.http import JsonResponse
from django.conf import settings
from datetime import timedelta

from .models import VisaProlongation, VisaRecord
from .forms import VisaProlongationForm


# ═══════════════════════════════════════════════════════════════
# VISA PROLONGATION WORKFLOW
# ═══════════════════════════════════════════════════════════════

class VisaProlongationCreateView(LoginRequiredMixin, CreateView):
    model = VisaProlongation
    form_class = VisaProlongationForm
    template_name = 'visas/prolongation_form.html'
    success_url = reverse_lazy('visas:prolongation_success')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notice_days'] = getattr(settings, 'VISA_PROLONGATION_NOTICE_DAYS', 30)
        return context

    def form_valid(self, form):
        form.instance.status = VisaProlongation.Status.REQUESTED
        if form.instance.parent_visa:
            form.instance.expert = form.instance.parent_visa.expert
        return super().form_valid(form)


class ProlongationSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'visas/prolongation_success.html'


class ExpiringVisaListView(LoginRequiredMixin, ListView):
    model = VisaRecord
    template_name = 'visas/expiring_visas.html'
    context_object_name = 'visas'

    def get_queryset(self):
        cutoff = timezone.now().date() + timedelta(days=90)
        return VisaRecord.objects.filter(
            expiry_date__lte=cutoff,
            status__in=[VisaRecord.Status.ACTIVE, VisaRecord.Status.EXPIRING_SOON]
        ).select_related('expert', 'visa_type').order_by('expiry_date')


# ═══════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

class GetParentVisasAPIView(LoginRequiredMixin, View):
    """Ticket 7: API endpoint to fetch active visas for a specific expert."""

    def get(self, request, *args, **kwargs):
        expert_id = request.GET.get('expert_id')
        if not expert_id:
            return JsonResponse({'visas': []})

        visas = VisaRecord.objects.filter(
            expert_id=expert_id,
            status=VisaRecord.Status.ACTIVE
        ).values('id', 'visa_number', 'visa_type__code', 'expiry_date')

        visa_list = []
        for visa in visas:
            visa_list.append({
                'id': visa['id'],
                'visa_number': visa['visa_number'],
                'visa_type__code': visa['visa_type__code'],
                'expiry_date': visa['expiry_date'].strftime('%Y-%m-%d') if visa['expiry_date'] else ''
            })

        return JsonResponse({'visas': visa_list})