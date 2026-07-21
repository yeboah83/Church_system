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
