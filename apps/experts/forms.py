from django import forms
from .models import Dependant, ExpertProfile


class DependantForm(forms.ModelForm):
    class Meta:
        model = Dependant
        fields = ['first_name', 'last_name', 'relationship', 'date_of_birth', 'nationality', 'passport_number', 'passport_expiry_date']

        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3 transition-all duration-200'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3 transition-all duration-200'}),
            'relationship': forms.Select(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3 transition-all duration-200'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3 transition-all duration-200'}),
            'nationality': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3 transition-all duration-200'}),
            'passport_number': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3 transition-all duration-200'}),
            'passport_expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3 transition-all duration-200'}),
        }


# THE CLASS STARTS HERE AT THE VERY LEFT EDGE
class ExpertProfileForm(forms.ModelForm):
    class Meta:
        model = ExpertProfile
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender', 'nationality',
            'passport_number', 'passport_issue_date', 'passport_expiry_date',
            'job_title', 'job_category', 'employer_company', 'email', 'phone',
            'site', 'department'
        ]

        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'gender': forms.Select(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'nationality': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'passport_number': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'passport_issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'passport_expiry_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'job_title': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'job_category': forms.Select(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'employer_company': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'email': forms.EmailInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'phone': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'site': forms.Select(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'department': forms.Select(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
        }

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        if self.company:
            self.fields['site'].queryset = self.fields['site'].queryset.filter(company=self.company)
            self.fields['department'].queryset = self.fields['department'].queryset.filter(company=self.company)