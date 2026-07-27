import datetime
import io
from decimal import Decimal
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import HttpResponse, Http404

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from .models import (
    CustomUser, Department, Member, Visitor, AttendanceSession, AttendanceRecord,
    Event, FinanceTransaction, Sermon, Announcement
)
from .forms import (
    MemberForm, VisitorForm, AttendanceSessionForm, FinanceTransactionForm,
    SermonForm, EventForm, AnnouncementForm, DepartmentForm,
    CustomUserCreationForm, CustomUserUpdateForm, AdminPasswordChangeForm
)
from .decorators import role_required


# --- AUTHENTICATION ---

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, 'login.html')


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


# --- DASHBOARD ---

@login_required
def dashboard(request):
    today = datetime.date.today()
    
    # Basic statistics
    total_members = Member.objects.count()
    total_visitors = Visitor.objects.count()
    
    # Today's attendance
    today_sessions = AttendanceSession.objects.filter(date=today)
    today_attendance = AttendanceRecord.objects.filter(session__in=today_sessions, status='Present').count()
    
    # Upcoming events (next 30 days)
    upcoming_events = Event.objects.filter(date__gte=today, date__lte=today + datetime.timedelta(days=30)).order_by('date')
    
    # Total offerings/income this month
    start_of_month = today.replace(day=1)
    monthly_income = FinanceTransaction.objects.filter(
        transaction_type='Income',
        date__gte=start_of_month,
        date__lte=today
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Recent registrations (last 5)
    recent_registrations = Member.objects.all().order_by('-date_joined')[:5]
    
    # Birthdays in the next 7 days
    birthdays = []
    active_members = Member.objects.filter(status='Active')
    for m in active_members:
        if m.date_of_birth:
            # Check birthday this year
            try:
                b_day = m.date_of_birth.replace(year=today.year)
            except ValueError:  # Handle leap year Feb 29
                b_day = m.date_of_birth.replace(year=today.year, day=28)
            
            if b_day < today:
                # If birthday passed, check next year
                try:
                    b_day = b_day.replace(year=today.year + 1)
                except ValueError:
                    b_day = b_day.replace(year=today.year + 1, day=28)
            
            delta = (b_day - today).days
            if 0 <= delta <= 7:
                birthdays.append({
                    'member': m,
                    'days_until': delta,
                    'date': b_day
                })
    birthdays.sort(key=lambda x: x['days_until'])

    # Weekly Attendance Data for Chart.js
    last_4_sundays = []
    for i in range(4):
        last_4_sundays.append(today - datetime.timedelta(days=today.weekday() + 1 + 7*i))
    last_4_sundays.reverse()
    
    chart_labels = []
    chart_data = []
    for sun_date in last_4_sundays:
        chart_labels.append(sun_date.strftime('%b %d'))
        sun_sess = AttendanceSession.objects.filter(service_type='Sunday Service', date=sun_date).first()
        if sun_sess:
            count = AttendanceRecord.objects.filter(session=sun_sess, status='Present').count()
            chart_data.append(count)
        else:
            chart_data.append(0)

    # Announcements (latest 3)
    announcements = Announcement.objects.all().order_by('-date_posted')[:3]

    context = {
        'total_members': total_members,
        'total_visitors': total_visitors,
        'today_attendance': today_attendance,
        'upcoming_events_count': upcoming_events.count(),
        'upcoming_events': upcoming_events[:3],
        'monthly_income': monthly_income,
        'recent_registrations': recent_registrations,
        'birthdays': birthdays,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'announcements': announcements,
    }
    return render(request, 'dashboard.html', context)


# --- MEMBER MANAGEMENT ---

@login_required
@role_required(['Super Admin', 'Pastor', 'Secretary'])
def member_list(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    dept_filter = request.GET.get('department', '')
    
    members = Member.objects.all().order_by('full_name')
    
    if query:
        members = members.filter(
            Q(full_name__icontains=query) |
            Q(membership_id__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(cell_group__icontains=query)
        )
    if status_filter:
        members = members.filter(status=status_filter)
    if dept_filter:
        members = members.filter(department_id=dept_filter)
        
    departments = Department.objects.all()
    
    context = {
        'members': members,
        'departments': departments,
        'query': query,
        'status_filter': status_filter,
        'dept_filter': dept_filter,
    }
    return render(request, 'members/member_list.html', context)


@login_required
@role_required(['Super Admin', 'Secretary'])
def member_create(request):
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES)
        if form.is_valid():
            member = form.save()
            messages.success(request, f"Member '{member.full_name}' registered successfully with ID: {member.membership_id}")
            return redirect('member_list')
    else:
        form = MemberForm()
    return render(request, 'members/member_form.html', {'form': form, 'title': 'Register Member'})


@login_required
@role_required(['Super Admin', 'Secretary'])
def member_update(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, f"Member '{member.full_name}' updated successfully.")
            return redirect('member_profile', pk=member.pk)
    else:
        form = MemberForm(instance=member)
    return render(request, 'members/member_form.html', {'form': form, 'title': 'Update Member', 'member': member})


@login_required
@role_required(['Super Admin', 'Pastor'])
def member_delete(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == 'POST':
        name = member.full_name
        member.delete()
        messages.success(request, f"Member '{name}' has been deleted.")
        return redirect('member_list')
    return render(request, 'confirm_delete.html', {'object': member, 'type': 'Member', 'cancel_url': 'member_list'})


@login_required
def member_profile(request, pk):
    member = get_object_or_404(Member, pk=pk)
    # Check permissions (Department leaders can only see members in their department, other staff can see all)
    if request.user.role == 'Department Leader':
        dept_led = Department.objects.filter(leader=request.user).first()
        if not dept_led or member.department != dept_led:
            messages.error(request, "Permission Denied: You can only view members of your department.")
            return redirect('dashboard')
            
    attendance = AttendanceRecord.objects.filter(member=member).order_by('-session__date')
    context = {
        'member': member,
        'attendance': attendance,
    }
    return render(request, 'members/member_profile.html', context)


@login_required
def member_card_print(request, pk):
    member = get_object_or_404(Member, pk=pk)
    return render(request, 'members/member_card_print.html', {'member': member})


# --- VISITOR MANAGEMENT ---

@login_required
@role_required(['Super Admin', 'Pastor', 'Secretary'])
def visitor_list(request):
    query = request.GET.get('q', '')
    visitors = Visitor.objects.all().order_by('-first_visit_date')
    if query:
        visitors = visitors.filter(
            Q(name__icontains=query) |
            Q(visitor_id__icontains=query) |
            Q(phone__icontains=query) |
            Q(invited_by__icontains=query)
        )
    return render(request, 'visitors/visitor_list.html', {'visitors': visitors, 'query': query})


@login_required
@role_required(['Super Admin', 'Secretary'])
def visitor_create(request):
    if request.method == 'POST':
        form = VisitorForm(request.POST)
        if form.is_valid():
            v = form.save()
            messages.success(request, f"Visitor '{v.name}' registered successfully with ID: {v.visitor_id}")
            return redirect('visitor_list')
    else:
        form = VisitorForm()
    return render(request, 'visitors/visitor_form.html', {'form': form, 'title': 'Register Visitor'})


@login_required
@role_required(['Super Admin', 'Secretary'])
def visitor_update(request, pk):
    visitor = get_object_or_404(Visitor, pk=pk)
    if request.method == 'POST':
        form = VisitorForm(request.POST, instance=visitor)
        if form.is_valid():
            form.save()
            messages.success(request, f"Visitor '{visitor.name}' updated successfully.")
            return redirect('visitor_list')
    else:
        form = VisitorForm(instance=visitor)
    return render(request, 'visitors/visitor_form.html', {'form': form, 'title': 'Update Visitor', 'visitor': visitor})


@login_required
@role_required(['Super Admin'])
def visitor_delete(request, pk):
    visitor = get_object_or_404(Visitor, pk=pk)
    if request.method == 'POST':
        name = visitor.name
        visitor.delete()
        messages.success(request, f"Visitor '{name}' has been deleted.")
        return redirect('visitor_list')
    return render(request, 'confirm_delete.html', {'object': visitor, 'type': 'Visitor', 'cancel_url': 'visitor_list'})


# --- ATTENDANCE MANAGEMENT ---

@login_required
@role_required(['Super Admin', 'Pastor', 'Secretary', 'Department Leader'])
def attendance_list(request):
    sessions = AttendanceSession.objects.all().order_by('-date')
    return render(request, 'attendance/attendance_list.html', {'sessions': sessions})


@login_required
@role_required(['Super Admin', 'Secretary'])
def attendance_session_create(request):
    if request.method == 'POST':
        form = AttendanceSessionForm(request.POST)
        if form.is_valid():
            session = form.save()
            # Prefill all active members as Present for this session by default
            active_members = Member.objects.filter(status='Active')
            for m in active_members:
                AttendanceRecord.objects.create(session=session, member=m, status='Absent')
            messages.success(request, f"Attendance session for {session.service_type} on {session.date} created. Please mark attendance.")
            return redirect('attendance_session_detail', pk=session.pk)
    else:
        form = AttendanceSessionForm(initial={'date': datetime.date.today()})
    return render(request, 'attendance/session_form.html', {'form': form, 'title': 'Create Attendance Session'})


@login_required
@role_required(['Super Admin', 'Pastor', 'Secretary', 'Department Leader'])
def attendance_session_detail(request, pk):
    session = get_object_or_404(AttendanceSession, pk=pk)
    
    # Save attendance updates
    if request.method == 'POST':
        if request.user.role not in ['Super Admin', 'Secretary']:
            messages.error(request, "Permission Denied: Only Secretary or Super Admin can record attendance.")
            return redirect('attendance_session_detail', pk=session.pk)
            
        present_member_ids = request.POST.getlist('members_present')
        present_visitor_ids = request.POST.getlist('visitors_present')
        
        # Update Member records for this session
        all_records = AttendanceRecord.objects.filter(session=session)
        for rec in all_records:
            if rec.member:
                rec.status = 'Present' if str(rec.member.pk) in present_member_ids else 'Absent'
                rec.save()
            elif rec.visitor:
                rec.status = 'Present' if str(rec.visitor.pk) in present_visitor_ids else 'Absent'
                rec.save()
                
        # Handle adding visitors that were present but not previously in this session
        for vis_id in present_visitor_ids:
            if not all_records.filter(visitor_id=vis_id).exists():
                v = Visitor.objects.filter(pk=vis_id).first()
                if v:
                    AttendanceRecord.objects.create(session=session, visitor=v, status='Present')
                    
        messages.success(request, "Attendance logged successfully.")
        return redirect('attendance_session_detail', pk=session.pk)

    # Restrict viewing department members if the user is a Department Leader
    dept_led = None
    if request.user.role == 'Department Leader':
        dept_led = Department.objects.filter(leader=request.user).first()

    member_records = AttendanceRecord.objects.filter(session=session, member__isnull=False).select_related('member')
    if dept_led:
        member_records = member_records.filter(member__department=dept_led)
        
    visitor_records = AttendanceRecord.objects.filter(session=session, visitor__isnull=False).select_related('visitor')
    
    # Visitors available to add (registered on or before service date)
    available_visitors = Visitor.objects.filter(first_visit_date__lte=session.date)
    
    total_present = AttendanceRecord.objects.filter(session=session, status='Present').count()
    total_absent = AttendanceRecord.objects.filter(session=session, status='Absent').count()
    
    context = {
        'session': session,
        'member_records': member_records,
        'visitor_records': visitor_records,
        'available_visitors': available_visitors,
        'total_present': total_present,
        'total_absent': total_absent,
        'dept_led': dept_led,
    }
    return render(request, 'attendance/session_detail.html', context)


# --- DEPARTMENTS ---

@login_required
def department_list(request):
    departments = Department.objects.annotate(member_count=Count('members'))
    return render(request, 'departments/department_list.html', {'departments': departments})


@login_required
@role_required(['Super Admin', 'Pastor'])
def department_create(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department created successfully.")
            return redirect('department_list')
    else:
        form = DepartmentForm()
    return render(request, 'departments/department_form.html', {'form': form, 'title': 'Add Department'})


@login_required
@role_required(['Super Admin', 'Pastor'])
def department_update(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            form.save()
            messages.success(request, f"Department '{dept.name}' updated successfully.")
            return redirect('department_list')
    else:
        form = DepartmentForm(instance=dept)
    return render(request, 'departments/department_form.html', {'form': form, 'title': 'Edit Department'})


@login_required
def department_detail(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    
    # Role check: Department Leaders can only see their own department details
    if request.user.role == 'Department Leader':
        led_dept = Department.objects.filter(leader=request.user).first()
        if not led_dept or led_dept != dept:
            messages.error(request, "Permission Denied: You can only view your own department.")
            return redirect('dashboard')
            
    members = dept.members.all()
    context = {
        'department': dept,
        'members': members,
    }
    return render(request, 'departments/department_detail.html', context)


# --- FINANCE MODULE ---

@login_required
@role_required(['Super Admin', 'Finance Officer'])
def finance_dashboard(request):
    today = datetime.date.today()
    transactions = FinanceTransaction.objects.all().order_by('-date')
    
    # Calculate Income vs Expenses
    total_income = FinanceTransaction.objects.filter(transaction_type='Income').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_expense = FinanceTransaction.objects.filter(transaction_type='Expense').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    net_balance = total_income - total_expense
    
    # Category Breakdowns
    category_summary = FinanceTransaction.objects.values('category', 'transaction_type').annotate(total=Sum('amount'))
    
    income_categories = []
    income_amounts = []
    expense_categories = []
    expense_amounts = []
    
    for item in category_summary:
        if item['transaction_type'] == 'Income':
            income_categories.append(item['category'])
            income_amounts.append(float(item['total']))
        else:
            expense_categories.append(item['category'])
            expense_amounts.append(float(item['total']))
            
    context = {
        'transactions': transactions[:10],
        'total_income': total_income,
        'total_expense': total_expense,
        'net_balance': net_balance,
        'income_categories': income_categories,
        'income_amounts': income_amounts,
        'expense_categories': expense_categories,
        'expense_amounts': expense_amounts,
    }
    return render(request, 'finance/finance_dashboard.html', context)


@login_required
@role_required(['Super Admin', 'Finance Officer'])
def finance_transaction_create(request):
    if request.method == 'POST':
        form = FinanceTransactionForm(request.POST)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.recorded_by = request.user
            tx.save()
            messages.success(request, f"{tx.transaction_type} transaction of GHS {tx.amount} logged successfully.")
            return redirect('finance_dashboard')
    else:
        form = FinanceTransactionForm(initial={'date': datetime.date.today()})
    return render(request, 'finance/transaction_form.html', {'form': form, 'title': 'Log Transaction'})


@login_required
@role_required(['Super Admin', 'Finance Officer'])
def finance_transaction_update(request, pk):
    tx = get_object_or_404(FinanceTransaction, pk=pk)
    if request.method == 'POST':
        form = FinanceTransactionForm(request.POST, instance=tx)
        if form.is_valid():
            form.save()
            messages.success(request, "Transaction updated successfully.")
            return redirect('finance_dashboard')
    else:
        form = FinanceTransactionForm(instance=tx)
    return render(request, 'finance/transaction_form.html', {'form': form, 'title': 'Update Transaction', 'transaction': tx})


@login_required
@role_required(['Super Admin'])
def finance_transaction_delete(request, pk):
    tx = get_object_or_404(FinanceTransaction, pk=pk)
    if request.method == 'POST':
        amount = tx.amount
        category = tx.category
        tx.delete()
        messages.success(request, f"Transaction '{category} : {amount}' deleted.")
        return redirect('finance_dashboard')
    return render(request, 'confirm_delete.html', {'object': tx, 'type': 'Transaction', 'cancel_url': 'finance_dashboard'})


# --- SERMON MANAGEMENT ---

@login_required
def sermon_list(request):
    query = request.GET.get('q', '')
    sermons = Sermon.objects.all().order_by('-date')
    if query:
        sermons = sermons.filter(
            Q(title__icontains=query) |
            Q(speaker__icontains=query) |
            Q(scripture__icontains=query) |
            Q(notes__icontains=query)
        )
    return render(request, 'sermons/sermon_list.html', {'sermons': sermons, 'query': query})


@login_required
@role_required(['Super Admin', 'Pastor'])
def sermon_create(request):
    if request.method == 'POST':
        form = SermonForm(request.POST)
        if form.is_valid():
            s = form.save()
            messages.success(request, f"Sermon '{s.title}' added successfully.")
            return redirect('sermon_list')
    else:
        form = SermonForm(initial={'date': datetime.date.today()})
    return render(request, 'sermons/sermon_form.html', {'form': form, 'title': 'Add Sermon'})


@login_required
@role_required(['Super Admin', 'Pastor'])
def sermon_update(request, pk):
    sermon = get_object_or_404(Sermon, pk=pk)
    if request.method == 'POST':
        form = SermonForm(request.POST, instance=sermon)
        if form.is_valid():
            form.save()
            messages.success(request, "Sermon details updated successfully.")
            return redirect('sermon_list')
    else:
        form = SermonForm(instance=sermon)
    return render(request, 'sermons/sermon_form.html', {'form': form, 'title': 'Edit Sermon', 'sermon': sermon})


@login_required
@role_required(['Super Admin'])
def sermon_delete(request, pk):
    sermon = get_object_or_404(Sermon, pk=pk)
    if request.method == 'POST':
        title = sermon.title
        sermon.delete()
        messages.success(request, f"Sermon '{title}' has been deleted.")
        return redirect('sermon_list')
    return render(request, 'confirm_delete.html', {'object': sermon, 'type': 'Sermon', 'cancel_url': 'sermon_list'})


# --- EVENTS ---

@login_required
def event_list(request):
    events = Event.objects.all().order_by('-date')
    return render(request, 'events/event_list.html', {'events': events})


@login_required
@role_required(['Super Admin', 'Pastor', 'Secretary'])
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            ev = form.save()
            messages.success(request, f"Event '{ev.event_name}' created successfully.")
            return redirect('event_list')
    else:
        form = EventForm()
    return render(request, 'events/event_form.html', {'form': form, 'title': 'Create Event'})


@login_required
@role_required(['Super Admin', 'Pastor', 'Secretary'])
def event_update(request, pk):
    ev = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        form = EventForm(request.POST, instance=ev)
        if form.is_valid():
            form.save()
            messages.success(request, f"Event '{ev.event_name}' updated successfully.")
            return redirect('event_list')
    else:
        form = EventForm(instance=ev)
    return render(request, 'events/event_form.html', {'form': form, 'title': 'Update Event', 'event': ev})


@login_required
@role_required(['Super Admin'])
def event_delete(request, pk):
    ev = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        name = ev.event_name
        ev.delete()
        messages.success(request, f"Event '{name}' deleted successfully.")
        return redirect('event_list')
    return render(request, 'confirm_delete.html', {'object': ev, 'type': 'Event', 'cancel_url': 'event_list'})


# --- ANNOUNCEMENTS ---

@login_required
def announcement_list(request):
    announcements = Announcement.objects.all().order_by('-date_posted')
    return render(request, 'announcements/announcement_list.html', {'announcements': announcements})


@login_required
@role_required(['Super Admin', 'Pastor', 'Secretary'])
def announcement_create(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            ann = form.save(commit=False)
            ann.author = request.user
            ann.save()
            messages.success(request, "Announcement published.")
            return redirect('dashboard')
    else:
        form = AnnouncementForm()
    return render(request, 'announcements/announcement_form.html', {'form': form, 'title': 'Publish Announcement'})


@login_required
@role_required(['Super Admin', 'Pastor', 'Secretary'])
def announcement_update(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=ann)
        if form.is_valid():
            form.save()
            messages.success(request, "Announcement updated.")
            return redirect('announcement_list')
    else:
        form = AnnouncementForm(instance=ann)
    return render(request, 'announcements/announcement_form.html', {'form': form, 'title': 'Update Announcement', 'announcement': ann})


@login_required
@role_required(['Super Admin', 'Pastor'])
def announcement_delete(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        title = ann.title
        ann.delete()
        messages.success(request, f"Announcement '{title}' deleted.")
        return redirect('announcement_list')
    return render(request, 'confirm_delete.html', {'object': ann, 'type': 'Announcement', 'cancel_url': 'announcement_list'})


# --- DOCUMENT & DATA EXPORT (EXCEL & PDF) ---

@login_required
@role_required(['Super Admin', 'Pastor', 'Secretary'])
def export_members_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Members Directory"

    font_header = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    fill_header = PatternFill(start_color="312E81", end_color="312E81", fill_type="solid")  # Indigo-900 style
    align_center = Alignment(horizontal="center", vertical="center")

    headers = [
        "Membership ID", "Full Name", "Gender", "Date of Birth", 
        "Phone Number", "Address", "Marital Status", "Baptized", 
        "Date Joined", "Department", "Cell Group", "Status"
    ]
    ws.append(headers)

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center

    members = Member.objects.all().order_by('full_name')
    for m in members:
        dept = m.department.name if m.department else "None"
        ws.append([
            m.membership_id,
            m.full_name,
            m.gender,
            m.date_of_birth.strftime('%Y-%m-%d') if m.date_of_birth else '',
            m.phone_number,
            m.address,
            m.marital_status,
            "Yes" if m.baptized else "No",
            m.date_joined.strftime('%Y-%m-%d') if m.date_joined else '',
            dept,
            m.cell_group,
            m.status
        ])

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 10)

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="church_members_list.xlsx"'
    wb.save(response)
    return response


@login_required
@role_required(['Super Admin', 'Pastor', 'Secretary'])
def export_members_pdf(request):
    members = Member.objects.all().order_by('full_name')
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#312E81'),
        spaceAfter=15,
        alignment=1
    )

    story.append(Paragraph("Church Members Directory", title_style))
    story.append(Spacer(1, 10))

    data = [["ID", "Full Name", "Gender", "Phone", "Status", "Joined", "Department"]]
    for m in members:
        dept = m.department.name if m.department else "None"
        data.append([
            m.membership_id,
            m.full_name,
            m.gender,
            m.phone_number,
            m.status,
            m.date_joined.strftime('%Y-%m-%d') if m.date_joined else '',
            dept
        ])

    t = Table(data, colWidths=[85, 120, 50, 80, 50, 75, 110])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#312E81')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F3F4F6')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')])
    ]))

    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf', headers={'Content-Disposition': 'attachment; filename="members_directory.pdf"'})


@login_required
@role_required(['Super Admin', 'Pastor', 'Secretary'])
def download_member_card_pdf(request, pk):
    member = get_object_or_404(Member, pk=pk)
    buffer = io.BytesIO()
    
    # 350x220 points is approximately credit card sized layout
    p = canvas.Canvas(buffer, pagesize=(350, 220))
    
    # Card Background - Deep Indigo
    p.setFillColor(colors.HexColor('#1E1B4B'))
    p.rect(0, 0, 350, 220, fill=True, stroke=False)
    
    # Top bar - Violet accent
    p.setFillColor(colors.HexColor('#4F46E5'))
    p.rect(0, 180, 350, 40, fill=True, stroke=False)
    
    # Text Header
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 13)
    p.drawString(15, 193, "COMMUNITY CHURCH")
    
    p.setFont("Helvetica", 8)
    p.setFillColor(colors.HexColor('#E0E7FF'))
    p.drawString(250, 196, "MEMBER CARD")

    # Member Photo
    photo_drawn = False
    if member.photo:
        try:
            photo_path = member.photo.path
            p.drawImage(photo_path, 15, 45, width=90, height=110)
            photo_drawn = True
        except Exception:
            pass

    if not photo_drawn:
        # Placeholder picture
        p.setStrokeColor(colors.HexColor('#4F46E5'))
        p.setFillColor(colors.HexColor('#312E81'))
        p.rect(15, 45, 90, 110, fill=True, stroke=True)
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 10)
        p.drawCentredString(60, 95, "NO PHOTO")

    # Details
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(120, 140, member.full_name[:22].upper())
    
    p.setFont("Helvetica", 9)
    p.setFillColor(colors.HexColor('#C7D2FE'))
    p.drawString(120, 118, f"Membership ID: {member.membership_id}")
    p.drawString(120, 98, f"Dept: {member.department.name if member.department else 'General Member'}")
    p.drawString(120, 78, f"Joined: {member.date_joined.strftime('%b %d, %Y') if member.date_joined else 'N/A'}")
    p.drawString(120, 58, f"Status: {member.status}")
    
    # Divider line
    p.setStrokeColor(colors.HexColor('#4F46E5'))
    p.setLineWidth(1)
    p.line(120, 48, 335, 48)
    
    # Footer Notice
    p.setFont("Helvetica-Oblique", 7)
    p.setFillColor(colors.HexColor('#818CF8'))
    p.drawString(120, 36, "Authorized Member ID. Non-transferable.")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="member_card_{member.membership_id}.pdf"'})


@login_required
@role_required(['Super Admin', 'Finance Officer'])
def export_finance_report(request):
    format_type = request.GET.get('format', 'excel')
    transactions = FinanceTransaction.objects.all().order_by('-date')

    if format_type == 'excel':
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Financial Transactions"

        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="065F46", end_color="065F46", fill_type="solid")  # Greenish-900 style
        align_center = Alignment(horizontal="center", vertical="center")

        headers = ["Date", "Type", "Category", "Amount (GHS)", "Description", "Recorded By"]
        ws.append(headers)

        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = align_center

        for tx in transactions:
            ws.append([
                tx.date.strftime('%Y-%m-%d'),
                tx.transaction_type,
                tx.category,
                float(tx.amount),
                tx.description,
                tx.recorded_by.username if tx.recorded_by else 'System'
            ])

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 10)

        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="financial_transactions.xlsx"'
        wb.save(response)
        return response

    elif format_type == 'pdf':
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'FinanceDocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=20,
            textColor=colors.HexColor('#065F46'),
            spaceAfter=15,
            alignment=1
        )

        story.append(Paragraph("Church Financial Statement", title_style))
        story.append(Spacer(1, 10))

        data = [["Date", "Type", "Category", "Amount (GHS)", "Recorded By"]]
        total_income = Decimal('0.00')
        total_expense = Decimal('0.00')

        for tx in transactions:
            data.append([
                tx.date.strftime('%Y-%m-%d'),
                tx.transaction_type,
                tx.category,
                f"{tx.amount:.2f}",
                tx.recorded_by.username if tx.recorded_by else 'System'
            ])
            if tx.transaction_type == 'Income':
                total_income += tx.amount
            else:
                total_expense += tx.amount

        # Summary box
        summary_text = f"<b>Total Income:</b> GHS {total_income:.2f} &nbsp;&nbsp;&nbsp;&nbsp; <b>Total Expense:</b> GHS {total_expense:.2f} &nbsp;&nbsp;&nbsp;&nbsp; <b>Net Balance:</b> GHS {(total_income - total_expense):.2f}"
        summary_style = ParagraphStyle('SummaryStyle', parent=styles['Normal'], fontSize=11, spaceAfter=15)
        story.append(Paragraph(summary_text, summary_style))

        t = Table(data, colWidths=[100, 80, 120, 100, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#065F46')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F0FDF4')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#A7F3D0')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')])
        ]))

        story.append(t)
        doc.build(story)
        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf', headers={'Content-Disposition': 'attachment; filename="financial_statement.pdf"'})

    raise Http404("Invalid format requested.")


# --- USER MANAGEMENT ---

@login_required
@role_required(['Super Admin'])
def user_list(request):
    users = CustomUser.objects.all().order_by('username')
    return render(request, 'users/user_list.html', {'users': users})


@login_required
@role_required(['Super Admin'])
def user_create(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User '{user.username}' created successfully!")
            return redirect('user_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/user_form.html', {'form': form, 'title': 'Add New User'})


@login_required
@role_required(['Super Admin'])
def user_update(request, pk):
    target_user = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        form = CustomUserUpdateForm(request.POST, instance=target_user)
        if form.is_valid():
            form.save()
            messages.success(request, f"User '{target_user.username}' updated successfully.")
            return redirect('user_list')
    else:
        form = CustomUserUpdateForm(instance=target_user)
    return render(request, 'users/user_form.html', {
        'form': form,
        'title': f'Edit User: {target_user.username}',
        'target_user': target_user
    })


@login_required
@role_required(['Super Admin'])
def user_change_password(request, pk):
    target_user = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        form = AdminPasswordChangeForm(request.POST)
        if form.is_valid():
            new_pass = form.cleaned_data['new_password']
            target_user.set_password(new_pass)
            target_user.save()
            messages.success(request, f"Password for '{target_user.username}' changed successfully.")
            return redirect('user_list')
    else:
        form = AdminPasswordChangeForm()
    return render(request, 'users/change_password.html', {
        'form': form,
        'target_user': target_user
    })


@login_required
@role_required(['Super Admin'])
def user_delete(request, pk):
    target_user = get_object_or_404(CustomUser, pk=pk)
    if target_user == request.user:
        messages.error(request, "You cannot delete your own admin account!")
        return redirect('user_list')
    
    if request.method == 'POST':
        username = target_user.username
        target_user.delete()
        messages.success(request, f"User '{username}' has been deleted.")
        return redirect('user_list')
    
    return render(request, 'confirm_delete.html', {
        'object': target_user,
        'type': 'User',
        'cancel_url': 'user_list'
    })

