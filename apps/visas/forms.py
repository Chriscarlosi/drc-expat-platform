from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from .models import VisaProlongation, VisaRecord, VisaTypeCatalog


class VisaProlongationForm(forms.ModelForm):
    class Meta:
        model = VisaProlongation
        fields = ['expert', 'parent_visa', 'prolongation_type', 'prolongation_number', 'request_date',
                  'new_expiry_date', 'dgm_reference', 'scan', 'notes']

        widgets = {
            'expert': forms.Select(attrs={'id': 'id_expert'}),
            'parent_visa': forms.Select(attrs={'id': 'id_parent_visa'}),
            'prolongation_type': forms.Select(attrs={'id': 'id_prolongation_type'}),
            'prolongation_number': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-4 transition-all duration-200',
                'placeholder': 'Auto-generated if left blank'}),
            'request_date': forms.DateInput(attrs={'type': 'date',
                                                   'class': 'w-full bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-4 transition-all duration-200'}),
            'new_expiry_date': forms.DateInput(attrs={'type': 'date',
                                                      'class': 'w-full bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-4 transition-all duration-200'}),
            'dgm_reference': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-4 transition-all duration-200',
                'placeholder': 'DGM Reference Number'}),
            'scan': forms.FileInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-200 text-slate-500 text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3 transition-all duration-200 file:mr-4 file:py-3 file:px-6 file:rounded-lg file:border-0 file:text-sm file:font-bold file:bg-amber-50 file:text-amber-700 hover:file:bg-amber-100 cursor-pointer'}),
            'notes': forms.Textarea(attrs={'rows': 4,
                                           'class': 'w-full bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-4 transition-all duration-200',
                                           'placeholder': 'Additional notes for the compliance team...'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # 1. Filter experts based on role
        if self.user:
            if self.user.is_superuser:
                from apps.experts.models import ExpertProfile
                self.fields['expert'].queryset = ExpertProfile.objects.unscoped().order_by('last_name')
            elif hasattr(self.user, 'membership') and self.user.membership:
                company = self.user.membership.company
                self.fields['expert'].queryset = self.fields['expert'].queryset.filter(company=company)

        # 2. Filter parent_visa by selected expert (FIXED: Removed int() cast)
        if 'expert' in self.data:
            try:
                expert_id = self.data.get('expert')  # <--- UUID string, not integer
                self.fields['parent_visa'].queryset = VisaRecord.objects.filter(
                    expert_id=expert_id,
                    status=VisaRecord.Status.ACTIVE
                ).order_by('-issue_date')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['parent_visa'].queryset = self.instance.expert.visa_records.filter(
                status=VisaRecord.Status.ACTIVE
            ).order_by('-issue_date')
        else:
            self.fields['parent_visa'].queryset = VisaRecord.objects.none()

        # 3. Prolongation types
        self.fields['prolongation_type'].queryset = VisaTypeCatalog.objects.filter(
            category=VisaTypeCatalog.Category.PROLONGATION,
            is_active=True
        )

    def clean(self):
        cleaned_data = super().clean()
        parent_visa = cleaned_data.get('parent_visa')
        prolongation_type = cleaned_data.get('prolongation_type')
        request_date = cleaned_data.get('request_date')
        new_expiry_date = cleaned_data.get('new_expiry_date')

        if parent_visa and prolongation_type and request_date:

            # Ticket 1: Parent visa must be active
            if parent_visa.status != VisaRecord.Status.ACTIVE:
                self.add_error('parent_visa', "This visa is not active. Only active visas can be prolonged.")

            # Ticket 2: Type must allow prolongation
            if not parent_visa.visa_type.allows_prolongation:
                self.add_error('prolongation_type',
                               f"Visa type {parent_visa.visa_type.code} does not allow prolongations. The holder must exit the country.")

            # Ticket 10: Prolongation limit check
            if parent_visa.visa_type.max_prolongations > 0:
                existing_count = VisaProlongation.objects.filter(
                    parent_visa=parent_visa,
                    status=VisaProlongation.Status.APPROVED
                ).count()
                if existing_count >= parent_visa.visa_type.max_prolongations:
                    self.add_error('parent_visa',
                                   f"Maximum number of prolongations ({parent_visa.visa_type.max_prolongations}) reached for this visa.")

            # Ticket A.2: Deadline Rule (only if verified)
            if getattr(settings, 'VISA_PROLONGATION_NOTICE_VERIFIED', False):
                notice_days = getattr(settings, 'VISA_PROLONGATION_NOTICE_DAYS', 30)
                days_until_expiry = (parent_visa.expiry_date - request_date).days
                if days_until_expiry < notice_days:
                    self.add_error('request_date',
                                   f"Requests must be filed at least {notice_days} days before expiry. This visa expires in {days_until_expiry} days.")

            # Calculate new_expiry_date dynamically if not provided or validate
            if prolongation_type.extension_length_days:
                from datetime import timedelta
                expected_date = parent_visa.expiry_date + timedelta(days=prolongation_type.extension_length_days)
                if not new_expiry_date:
                    cleaned_data['new_expiry_date'] = expected_date
                else:
                    tolerance = 5
                    if abs((new_expiry_date - expected_date).days) > tolerance:
                        self.add_error('new_expiry_date',
                                       f"Expiry must be {prolongation_type.extension_length_days} days after current expiry ({parent_visa.expiry_date}), which is {expected_date}.")

        return cleaned_data