import datetime
from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('Super Admin', 'Super Admin'),
        ('Pastor', 'Pastor'),
        ('Secretary', 'Secretary'),
        ('Finance Officer', 'Finance Officer'),
        ('Department Leader', 'Department Leader'),
    )
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='Secretary')
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


class Department(models.Model):
    DEPT_CHOICES = (
        ('Choir', 'Choir'),
        ('Ushers', 'Ushers'),
        ('Children\'s Ministry', 'Children\'s Ministry'),
        ('Youth', 'Youth'),
        ('Women\'s Ministry', 'Women\'s Ministry'),
        ('Men\'s Ministry', 'Men\'s Ministry'),
        ('Media Team', 'Media Team'),
        ('Protocol', 'Protocol'),
    )
    name = models.CharField(max_length=50, choices=DEPT_CHOICES, unique=True)
    leader = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True, related_name='led_departments')
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Member(models.Model):
    GENDER_CHOICES = (
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    )
    MARITAL_CHOICES = (
        ('Single', 'Single'),
        ('Married', 'Married'),
        ('Divorced', 'Divorced'),
        ('Widowed', 'Widowed'),
    )
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    )

    membership_id = models.CharField(max_length=30, unique=True, primary_key=True)
    full_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    marital_status = models.CharField(max_length=20, choices=MARITAL_CHOICES)
    baptized = models.BooleanField(default=False)
    date_joined = models.DateField(default=datetime.date.today)
    photo = models.ImageField(upload_to='members/', blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, blank=True, null=True, related_name='members')
    cell_group = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')

    @classmethod
    def generate_next_id(cls, date_joined=None):
        if date_joined is None:
            date_joined = datetime.date.today()
        year_yy = date_joined.strftime('%y')
        prefix = f"RACI{year_yy}/"
        last_num = 0
        for m in cls.objects.filter(membership_id__startswith=prefix):
            try:
                num = int(m.membership_id.split('/')[-1])
                if num > last_num:
                    last_num = num
            except (ValueError, IndexError):
                pass
        new_num = last_num + 1
        return f"{prefix}{new_num:03d}"

    def save(self, *args, **kwargs):
        if not self.membership_id:
            self.membership_id = Member.generate_next_id(self.date_joined)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.membership_id})"


class Visitor(models.Model):
    visitor_id = models.CharField(max_length=30, unique=True, primary_key=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    invited_by = models.CharField(max_length=100, blank=True)
    first_visit_date = models.DateField(default=datetime.date.today)

    def save(self, *args, **kwargs):
        if not self.visitor_id:
            current_year = datetime.date.today().year
            prefix = f"VIS-{current_year}-"
            last_visitor = Visitor.objects.filter(visitor_id__startswith=prefix).order_by('-visitor_id').first()
            if last_visitor:
                try:
                    last_num = int(last_visitor.visitor_id.split('-')[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1
            self.visitor_id = f"{prefix}{new_num:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.visitor_id})"


class AttendanceSession(models.Model):
    SERVICE_CHOICES = (
        ('Sunday Service', 'Sunday Service'),
        ('Midweek Service', 'Midweek Service'),
        ('Prayer Meeting', 'Prayer Meeting'),
        ('Youth Service', 'Youth Service'),
    )
    service_type = models.CharField(max_length=30, choices=SERVICE_CHOICES)
    date = models.DateField(default=datetime.date.today)
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ('service_type', 'date')

    @property
    def present_count(self):
        return self.records.filter(status='Present').count()

    def __str__(self):
        return f"{self.service_type} - {self.date}"


class AttendanceRecord(models.Model):
    STATUS_CHOICES = (
        ('Present', 'Present'),
        ('Absent', 'Absent'),
    )
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, blank=True, null=True, related_name='attendance')
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, blank=True, null=True, related_name='attendance')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Present')

    class Meta:
        unique_together = (('session', 'member'), ('session', 'visitor'))

    def __str__(self):
        subject = self.member.full_name if self.member else self.visitor.name
        return f"{subject} - {self.session.service_type} ({self.status})"


class Event(models.Model):
    event_name = models.CharField(max_length=100)
    event_type = models.CharField(max_length=50)
    date = models.DateField()
    time = models.TimeField()
    venue = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    organizer = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.event_name} on {self.date}"


class FinanceTransaction(models.Model):
    TYPE_CHOICES = (
        ('Income', 'Income'),
        ('Expense', 'Expense'),
    )
    CATEGORY_CHOICES = (
        # Income
        ('Offering', 'Offering'),
        ('Tithe', 'Tithe'),
        ('Thanksgiving', 'Thanksgiving'),
        ('Building Fund', 'Building Fund'),
        ('Donations', 'Donations'),
        # Expenses
        ('Utilities', 'Utilities'),
        ('Salaries', 'Salaries'),
        ('Maintenance', 'Maintenance'),
        ('Evangelism', 'Evangelism'),
        ('Other', 'Other'),
    )
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=datetime.date.today)
    description = models.TextField(blank=True)
    recorded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='transactions')

    def __str__(self):
        return f"{self.transaction_type} - {self.category}: {self.amount} ({self.date})"


class Sermon(models.Model):
    title = models.CharField(max_length=200)
    speaker = models.CharField(max_length=100)
    date = models.DateField(default=datetime.date.today)
    scripture = models.CharField(max_length=100)
    notes = models.TextField()
    audio_file = models.FileField(upload_to='sermons/audio/', blank=True, null=True)

    def __str__(self):
        return f"{self.title} by {self.speaker}"


class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    date_posted = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='announcements')

    def __str__(self):
        return self.title


class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('EXPORT', 'Export'),
    )
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    user_display = models.CharField(max_length=150, default='System')
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    module = models.CharField(max_length=50)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.user_display} - {self.action_type} ({self.module}): {self.description}"


def log_activity(request, action_type, module, description):
    user = request.user if request and hasattr(request, 'user') and request.user.is_authenticated else None
    user_disp = user.username if user else 'System/Anonymous'
    ip = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

    AuditLog.objects.create(
        user=user,
        user_display=user_disp,
        action_type=action_type,
        module=module,
        description=description,
        ip_address=ip
    )


