from django import forms
from django.utils import timezone
from .models import WorkforceSnapshot

class WorkforceSnapshotForm(forms.ModelForm):
    class Meta:
        model = WorkforceSnapshot
        fields = [
            'snapshot_date',
            'total_congolese_staff', 'total_expat_staff',
            'congolese_class_i_v', 'congolese_supervisor', 'congolese_management',
            'expat_class_i_v', 'expat_supervisor', 'expat_management',
            'notes', 'supporting_document'
        ]
        widgets = {
            'snapshot_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'total_congolese_staff': forms.NumberInput(attrs={'class': 'w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3', 'min': '0'}),
            'total_expat_staff': forms.NumberInput(attrs={'class': 'w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3', 'min': '0'}),
            'congolese_class_i_v': forms.NumberInput(attrs={'class': 'w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3', 'min': '0'}),
            'congolese_supervisor': forms.NumberInput(attrs={'class': 'w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3', 'min': '0'}),
            'congolese_management': forms.NumberInput(attrs={'class': 'w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3', 'min': '0'}),
            'expat_class_i_v': forms.NumberInput(attrs={'class': 'w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3', 'min': '0'}),
            'expat_supervisor': forms.NumberInput(attrs={'class': 'w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3', 'min': '0'}),
            'expat_management': forms.NumberInput(attrs={'class': 'w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3', 'min': '0'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'supporting_document': forms.FileInput(attrs={'class': 'w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 text-slate-500 text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3 transition-all duration-200 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-bold file:bg-amber-50 file:text-amber-700 hover:file:bg-amber-100 cursor-pointer'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['snapshot_date'].initial = timezone.now().date()

    def clean_snapshot_date(self):
        date = self.cleaned_data.get('snapshot_date')
        if date and date > timezone.now().date():
            raise forms.ValidationError("Snapshot date cannot be in the future.")
        return date