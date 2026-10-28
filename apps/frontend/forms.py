from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from apps.organization.models import UserCompanyMembership


class CSVImportForm(forms.Form):
    csv_file = forms.FileField(
        label="Upload CSV File",
        widget=forms.FileInput(attrs={
            'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3 transition-all duration-200 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-bold file:bg-amber-50 file:text-amber-700 hover:file:bg-amber-100 cursor-pointer',
            'accept': '.csv'
        })
    )


class InviteUserForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'})
    )
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'})
    )
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'})
    )
    role = forms.ChoiceField(
        choices=UserCompanyMembership.Role.choices,
        widget=forms.Select(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'})
    )


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']  # Email is excluded to prevent login issues
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'}),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 block p-3'
            })