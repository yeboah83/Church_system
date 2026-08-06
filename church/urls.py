from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login_explicit'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Members
    path('members/', views.member_list, name='member_list'),
    path('members/add/', views.member_create, name='member_create'),
    path('members/export/excel/', views.export_members_excel, name='export_members_excel'),
    path('members/export/pdf/', views.export_members_pdf, name='export_members_pdf'),
    path('members/<path:pk>/edit/', views.member_update, name='member_update'),
    path('members/<path:pk>/delete/', views.member_delete, name='member_delete'),
    path('members/<path:pk>/card/pdf/', views.download_member_card_pdf, name='download_member_card_pdf'),
    path('members/<path:pk>/card/', views.member_card_print, name='member_card_print'),
    path('members/<path:pk>/', views.member_profile, name='member_profile'),
    
    # Visitors
    path('visitors/', views.visitor_list, name='visitor_list'),
    path('visitors/add/', views.visitor_create, name='visitor_create'),
    path('visitors/<path:pk>/edit/', views.visitor_update, name='visitor_update'),
    path('visitors/<path:pk>/delete/', views.visitor_delete, name='visitor_delete'),
    
    # Attendance
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/session/add/', views.attendance_session_create, name='attendance_session_create'),
    path('attendance/session/<int:pk>/', views.attendance_session_detail, name='attendance_session_detail'),
    path('attendance/session/<int:pk>/qr/', views.attendance_session_qr, name='attendance_session_qr'),
    path('attendance/session/<int:pk>/check-in/', views.attendance_self_checkin, name='attendance_self_checkin'),
    
    # Departments
    path('departments/', views.department_list, name='department_list'),
    path('departments/add/', views.department_create, name='department_create'),
    path('departments/<int:pk>/edit/', views.department_update, name='department_update'),
    path('departments/<int:pk>/', views.department_detail, name='department_detail'),
    
    # Finance
    path('finance/', views.finance_dashboard, name='finance_dashboard'),
    path('finance/transaction/add/', views.finance_transaction_create, name='finance_transaction_create'),
    path('finance/transaction/<int:pk>/edit/', views.finance_transaction_update, name='finance_transaction_update'),
    path('finance/transaction/<int:pk>/delete/', views.finance_transaction_delete, name='finance_transaction_delete'),
    path('finance/export/', views.export_finance_report, name='export_finance_report'),
    
    # Sermons
    path('sermons/', views.sermon_list, name='sermon_list'),
    path('sermons/add/', views.sermon_create, name='sermon_create'),
    path('sermons/<int:pk>/edit/', views.sermon_update, name='sermon_update'),
    path('sermons/<int:pk>/delete/', views.sermon_delete, name='sermon_delete'),
    
    # Events
    path('events/', views.event_list, name='event_list'),
    path('events/add/', views.event_create, name='event_create'),
    path('events/<int:pk>/edit/', views.event_update, name='event_update'),
    path('events/<int:pk>/delete/', views.event_delete, name='event_delete'),
    
    # Announcements
    path('announcements/', views.announcement_list, name='announcement_list'),
    path('announcements/add/', views.announcement_create, name='announcement_create'),
    path('announcements/<int:pk>/edit/', views.announcement_update, name='announcement_update'),
    path('announcements/<int:pk>/delete/', views.announcement_delete, name='announcement_delete'),

    # User Management (Admin only)
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_update, name='user_update'),
    path('users/<int:pk>/password/', views.user_change_password, name='user_change_password'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    # Audit Logs
    path('audit-logs/', views.audit_log_list, name='audit_log_list'),
    path('audit-logs/export-csv/', views.export_audit_logs_csv, name='export_audit_logs_csv'),

    # Contact & Email Verification
    path('verify/<str:entity_type>/<path:pk>/<str:verify_type>/send/', views.send_verification_code, name='send_verification_code'),
    path('verify/<str:entity_type>/<path:pk>/<str:verify_type>/confirm/', views.verify_code, name='verify_code'),
]


