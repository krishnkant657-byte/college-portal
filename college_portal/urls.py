from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from portal import views

urlpatterns = [
    # 🛡️ OBFUSCATED ADMIN PANEL: Changed from 'admin/' to prevent automated bot brute-forcing.
    path('secure-backend-admin/', admin.site.urls),
    
    # 🎯 Match this name parameter with what your login view redirects to
    path('', views.dashboard, name='student_dashboard'), 
    
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('faculty-dashboard/', views.faculty_dashboard_view, name='faculty_dashboard'),
    path('get-attendance/', views.get_attendance_data, name='get_attendance_data'),
    path('exam-form/regular/', views.exam_form_regular, name='exam_form_regular'),
    path('exam-form/atkt/', views.exam_form_atkt, name='exam_form_atkt'),
    path('process-payment/<int:record_id>/', views.process_payment, name='process_payment'),
    path('view-report/', views.view_report, name='view_report'),
    path('identity-card/', views.identity_card, name='identity_card'),
    path('get-mst/', views.get_mst_data, name='get_mst_data'),
    path('get-assignments/', views.get_assignments_data, name='get_assignments_data'),
    path('get-exams/', views.get_exams_data, name='get_exams_data'),
    path('faculty-get-attendance/', views.get_faculty_attendance, name='get_faculty_attendance'),
    path('save-attendance/', views.save_attendance, name='save_attendance'),
    path('faculty-get-defaulters/', views.get_defaulter_list, name='get_defaulter_list'),
    path('faculty-email-defaulters/', views.email_defaulters, name='email_defaulters'),
    path('faculty-get-batches/', views.get_faculty_batches, name='get_faculty_batches'),
    path('faculty-get-mst/', views.get_faculty_mst, name='get_faculty_mst'),
    path('faculty-save-mst/', views.save_mst_marks, name='save_mst_marks'),
    path('upload-mst-csv/', views.upload_mst_csv, name='upload_mst_csv'),
    path('faculty-get-assignments/', views.faculty_get_assignments, name='faculty_get_assignments'),
    path('faculty-create-assignment/', views.faculty_create_assignment, name='faculty_create_assignment'),
    path('faculty-delete-assignment/<int:assignment_id>/', views.faculty_delete_assignment, name='faculty_delete_assignment'),
    path('student-submit-assignment/', views.student_submit_assignment, name='student_submit_assignment'),
    path('mark-notifications-read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('student-goal-tracker/', views.student_goal_tracker, name='student_goal_tracker'),
    path('student-timetable/', views.student_timetable_view, name='student_timetable_view'),
    path('faculty-timetable/', views.faculty_timetable_view, name='faculty_timetable_view'),
    path('student-fees/', views.student_fees_view, name='student_fees_view'),
    path('process-dummy-payment/<int:invoice_id>/', views.process_dummy_payment, name='process_dummy_payment'),
    path('student-leave/', views.student_leave_view, name='student_leave_view'),
    path('faculty-leave/', views.faculty_leave_view, name='faculty_leave_view'),
    path('process-leave-action/<int:leave_id>/', views.process_leave_action, name='process_leave_action'),
    path('settings/', views.settings_view, name='settings_view'),
    path('upload-avatar/', views.upload_avatar_view, name='upload_avatar_view'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp_view'),
    path('update-setting/', views.update_setting_view, name='update_setting_view'),
    path('revoke-sessions/', views.revoke_sessions_view, name='revoke_sessions_view'),
    path('change-password/', views.change_password_view, name='change_password_view'),
    path('help-center/', views.help_center_view, name='help_center_view'),
    path('submit-ticket/', views.submit_ticket_view, name='submit_ticket_view'),
    path('resolve-ticket/<int:ticket_id>/', views.resolve_ticket_view, name='resolve_ticket_view'),
    path('delete-ticket/<int:ticket_id>/', views.delete_ticket_view, name='delete_ticket_view'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)