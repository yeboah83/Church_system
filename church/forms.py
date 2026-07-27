from django import forms
from django.contrib.auth import get_user_model
from .models import (
    Member, Visitor, AttendanceSession, FinanceTransaction, Sermon, Event, Announcement, Department
)

User = get_user_model()

class BootstrapModelForm(forms.ModelForm):
    """Base form that automatically applies Bootstrap 5 classes to fields."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.Textarea, forms.EmailInput, forms.PasswordInput, forms.NumberInput, forms.DateInput, forms.TimeInput)):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})


class MemberForm(BootstrapModelForm):
    class Meta:
        model = Member
        exclude = ['membership_id']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'date_joined': forms.DateInput(attrs={'type': 'date'}),
        }


class VisitorForm(BootstrapModelForm):
    class Meta:
        model = Visitor
        exclude = ['visitor_id']
        widgets = {
            'first_visit_date': forms.DateInput(attrs={'type': 'date'}),
        }


class AttendanceSessionForm(BootstrapModelForm):
    class Meta:
        model = AttendanceSession
        fields = '__all__'
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }


class FinanceTransactionForm(BootstrapModelForm):
    class Meta:
        model = FinanceTransaction
        exclude = ['recorded_by']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }


class SermonForm(BootstrapModelForm):
    class Meta:
        model = Sermon
        fields = '__all__'
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }


class EventForm(BootstrapModelForm):
    class Meta:
        model = Event
        fields = '__all__'
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
        }


class AnnouncementForm(BootstrapModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content']


class DepartmentForm(BootstrapModelForm):
    class Meta:
        model = Department
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter leaders to only include users with role Department Leader or Super Admin
        self.fields['leader'].queryset = User.objects.filter(role__in=['Department Leader', 'Super Admin'])


class CustomUserCreationForm(BootstrapModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Enter password'}), required=True, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password'}), required=True, label="Confirm Password")

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'is_active']
        labels = {
            'is_active': 'Active User Account',
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class CustomUserUpdateForm(BootstrapModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'is_active']
        labels = {
            'is_active': 'Active User Account',
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username


class AdminPasswordChangeForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'}),
        required=True,
        label="New Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
        required=True,
        label="Confirm Password"
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        if new_password and confirm_password and new_password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

