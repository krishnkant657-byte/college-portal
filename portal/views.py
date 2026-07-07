from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from .models import ExamFormRecord, StudentProfile
import random

# --- CORE STUDENT DASHBOARD VIEW ---
@login_required
def dashboard(request):
    # Enforce strict Student-only access
    if request.user.user_type != 'student':
        return redirect('faculty_dashboard')
        
    try:
        profile = request.user.student_profile
    except Exception:
        profile = None
    # --- LOAD ACADEMIC DATA ---
    from .models import Subject, Batch, Notification
    
    # Load all unique batches mapped to subjects (for display)
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:10]
    
    # Calculate urgent deadlines (within 48 hours)
    from django.utils import timezone
    from .models import Assignment
    now = timezone.now()
    urgent_deadlines_count = 0
    if profile and profile.batch:
        upcoming = Assignment.objects.filter(batch=profile.batch, due_date__gte=now)
        for assign in upcoming:
            if (assign.due_date - now).total_seconds() <= (48 * 3600):
                urgent_deadlines_count += 1

    context = {
        'user': request.user,
        'profile': profile,
        'attendance': '85%', 
        'assignments_pending': '03',
        'notifications': notifications,
        'unread_count': unread_count,
        'urgent_deadlines_count': urgent_deadlines_count,
    }
    
    return render(request, 'portal/dashboard.html', context)

@login_required
def mark_notifications_read(request):
    if request.method == "POST":
        from .models import Notification
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return HttpResponse("Success")
    return HttpResponse("Invalid", status=400)


# --- CORE FACULTY DASHBOARD VIEW ---
@login_required
def faculty_dashboard_view(request):
    # Enforce Faculty & Coordinator access
    if not request.user.is_superuser and request.user.user_type not in ['faculty', 'coordinator']:
        return redirect('student_dashboard')
        
    from .models import CollegeUser, Batch, SubjectAllocation
    
    # Calculate personalized stats
    if request.user.user_type == 'coordinator' or request.user.is_superuser:
        allocations = SubjectAllocation.objects.all()
    else:
        allocations = SubjectAllocation.objects.filter(faculty=request.user)
        
    unique_batches = allocations.values('batch').distinct().count()
    unique_subjects = allocations.values('subject').distinct().count()
    
    assigned_batch_ids = allocations.values_list('batch_id', flat=True)
    total_students = CollegeUser.objects.filter(
        user_type='student',
        student_profile__batch__id__in=assigned_batch_ids
    ).count()
        
    return render(request, 'portal/faculty_dashboard.html', {
        'unique_batches': unique_batches,
        'unique_subjects': unique_subjects,
        'total_students': total_students
    })


# --- LOGIN PORTAL INTERFACE CONTROL ENGINE ---
def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser or getattr(request.user, 'user_type', None) in ['faculty', 'coordinator']:
            return redirect('faculty_dashboard')
        else:
            return redirect('student_dashboard')
            
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        selected_portal = request.POST.get('selected_portal')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check Role Validity
            if selected_portal == 'faculty' and user.user_type not in ['faculty', 'coordinator']:
                return render(request, 'portal/login.html', {'error': 'You are not authorized for the Faculty Portal.'})
            elif selected_portal == 'student' and user.user_type != 'student':
                return render(request, 'portal/login.html', {'error': 'You are not authorized for the Student Portal.'})
                
            login(request, user)
            
            # Dynamic Target Dashboard Branch Routing
            if selected_portal == 'faculty':
                return redirect('faculty_dashboard')
            else:
                return redirect('student_dashboard')
        else:
            return render(request, 'portal/login.html', {'error': 'Invalid Computer Code or Password for selected tier.'})
            
    return render(request, 'portal/login.html')


# --- LOGOUT METHOD ---
def logout_view(request):
    logout(request)
    return redirect('login_view')


# --- FORGOT PASSWORD MODULE (LIVE OTP SYSTEM) ---
def forgot_password_view(request):
    User = get_user_model()
    
    if request.method == 'POST':
        step = request.POST.get('step')
        
        # Step 1: User requests an OTP by providing their Computer Code
        if step == '1':
            computer_code = request.POST.get('username')
            try:
                user = User.objects.get(computer_code=computer_code)
                
                # Check if user has an email
                if not user.email:
                    return render(request, 'portal/forgot_password.html', {'step': 1, 'error': 'No email address registered for this Computer Code.'})
                
                # Generate a secure 6-digit OTP
                otp = str(random.randint(100000, 999999))
                
                # Store OTP temporarily in Django's secure backend session
                request.session['reset_otp'] = otp
                request.session['reset_computer_code'] = computer_code
                
                # Dispatch Email
                send_mail(
                    subject='IPS Academy - Password Reset OTP',
                    message=f'Hello {user.first_name},\n\nYour One-Time Password (OTP) to reset your account password is: {otp}\n\nDo not share this with anyone.',
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                
                return render(request, 'portal/forgot_password.html', {'step': 2, 'success': f'OTP sent securely to {user.email}'})
                
            except User.DoesNotExist:
                return render(request, 'portal/forgot_password.html', {'step': 1, 'error': 'Invalid Computer Code. User not found.'})
                
        # Step 2: User provides the OTP from email and their new password
        elif step == '2':
            entered_otp = request.POST.get('otp')
            new_password = request.POST.get('new_password')
            
            # Retrieve the real OTP from the backend session
            stored_otp = request.session.get('reset_otp')
            computer_code = request.session.get('reset_computer_code')
            
            # Prevent direct access if they didn't complete Step 1
            if not stored_otp or not computer_code:
                return render(request, 'portal/forgot_password.html', {'step': 1, 'error': 'Session expired or invalid. Please try again.'})
                
            # Verification Engine
            if entered_otp == stored_otp:
                try:
                    user = User.objects.get(computer_code=computer_code)
                    
                    # Securely hash and update the new password
                    user.set_password(new_password)
                    user.save()
                    
                    # Destroy the OTP session data for security
                    del request.session['reset_otp']
                    del request.session['reset_computer_code']
                    
                    return render(request, 'portal/login.html', {'success': 'Password changed successfully! You can now authenticate.'})
                except User.DoesNotExist:
                    return render(request, 'portal/forgot_password.html', {'step': 1, 'error': 'Critical error. User no longer exists.'})
            else:
                return render(request, 'portal/forgot_password.html', {'step': 2, 'error': 'Invalid OTP Code. Please check your email and try again.'})
            
    return render(request, 'portal/forgot_password.html', {'step': 1})


@login_required
def get_attendance_data(request):
    from .models import StudentAttendance
    import math
    
    student_attendances = StudentAttendance.objects.filter(student=request.user).select_related('record__subject')
    
    # Calculate percentage per subject
    attendance_stats = {}
    for sa in student_attendances:
        subj_name = sa.record.subject.name
        if subj_name not in attendance_stats:
            attendance_stats[subj_name] = {'present': 0, 'total': 0}
        
        attendance_stats[subj_name]['total'] += 1
        if sa.is_present:
            attendance_stats[subj_name]['present'] += 1
            
    # Format for template
    formatted_stats = []
    for subj_name, stats in attendance_stats.items():
        present = stats['present']
        total = stats['total']
        percentage = int((present / total) * 100) if total > 0 else 0
        
        prediction_text = ""
        prediction_type = ""
        if total > 0:
            if percentage >= 75:
                # How many classes they can miss
                bunkable = math.floor((present - 0.75 * total) / 0.75)
                if bunkable > 0:
                    prediction_text = f"You can safely miss {bunkable} more lecture{'s' if bunkable > 1 else ''}."
                    prediction_type = "safe"
                else:
                    prediction_text = "On the edge! Do not miss the next lecture."
                    prediction_type = "edge"
            else:
                # How many classes they need to attend
                needed = math.ceil((0.75 * total - present) / 0.25)
                prediction_text = f"You must attend the next {needed} lecture{'s' if needed > 1 else ''} to reach 75%."
                prediction_type = "danger"

        formatted_stats.append({
            'subject': subj_name,
            'present': present,
            'total': total,
            'absent': total - present,
            'percentage': percentage,
            'prediction_text': prediction_text,
            'prediction_type': prediction_type
        })
        
    return render(request, 'portal/attendance_snippet.html', {'attendance_stats': formatted_stats})
@login_required
def get_mst_data(request):
    from .models import MSTMark
    marks = MSTMark.objects.filter(student=request.user).select_related('subject')
    return render(request, 'portal/mst_snippet.html', {'marks': marks})

@login_required
def get_assignments_data(request):
    if request.user.user_type != 'student':
        return HttpResponse("Unauthorized", status=403)
        
    try:
        profile = request.user.student_profile
        batch = profile.batch
    except Exception:
        return HttpResponse("Student profile not found", status=400)
        
    from .models import Assignment, AssignmentSubmission
    
    # Get assignments for the student's batch
    assignments = list(Assignment.objects.filter(batch=batch).order_by('-due_date'))
    
    # Get submissions by this student
    submissions = AssignmentSubmission.objects.filter(student=request.user)
    submissions_dict = {sub.assignment_id: sub for sub in submissions}
    
    for assignment in assignments:
        assignment.sub = submissions_dict.get(assignment.id)
    
    context = {
        'assignments': assignments,
        'now': timezone.now()
    }
    
    return render(request, 'portal/assignments_snippet.html', context)

@login_required
def get_exams_data(request):
    return render(request, 'portal/exams_snippet.html')
    
@login_required
def get_faculty_attendance(request):
    from .models import SubjectAllocation, AttendanceRecord, StudentAttendance, CollegeUser
    from django.utils import timezone
    if request.user.user_type not in ['faculty', 'coordinator'] and not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=403)
        
    allocations = SubjectAllocation.objects.filter(faculty=request.user).select_related('subject', 'batch')
    selected_allocation_id = request.GET.get('allocation_id')
    selected_date = request.GET.get('date', timezone.now().date().isoformat())
    
    students_data = []
    selected_allocation = None
    existing_record = None
    
    if selected_allocation_id:
        try:
            selected_allocation = allocations.get(id=selected_allocation_id)
            students = CollegeUser.objects.filter(
                user_type='student', 
                student_profile__batch=selected_allocation.batch
            ).order_by('computer_code')
            
            # Check if an attendance record already exists for this date
            try:
                existing_record = AttendanceRecord.objects.get(
                    batch=selected_allocation.batch,
                    subject=selected_allocation.subject,
                    date=selected_date
                )
                attendance_dict = {a.student_id: a.is_present for a in existing_record.student_attendances.all()}
            except AttendanceRecord.DoesNotExist:
                attendance_dict = {}
            
            for student in students:
                is_present = attendance_dict.get(student.id, True) # Default to True (Present)
                students_data.append({
                    'student': student,
                    'is_present': is_present
                })
        except SubjectAllocation.DoesNotExist:
            pass
            
    return render(request, 'portal/faculty_attendance_snippet.html', {
        'allocations': allocations,
        'selected_allocation': selected_allocation,
        'selected_date': selected_date,
        'students_data': students_data,
        'existing_record': existing_record,
        'success': request.GET.get('success')
    })

@login_required
def save_attendance(request):
    if request.method == "POST":
        allocation_id = request.POST.get('allocation_id')
        attendance_date = request.POST.get('date')
        from .models import SubjectAllocation, AttendanceRecord, StudentAttendance, CollegeUser
        try:
            allocation = SubjectAllocation.objects.get(id=allocation_id, faculty=request.user)
            
            record, created = AttendanceRecord.objects.get_or_create(
                batch=allocation.batch,
                subject=allocation.subject,
                date=attendance_date,
                defaults={'faculty': request.user}
            )
            
            # Form will send checkbox values only for those who are marked (we'll set value=student_id for present)
            present_student_ids = request.POST.getlist('present_students')
            present_student_ids = [int(sid) for sid in present_student_ids]
            
            all_students_in_batch = CollegeUser.objects.filter(
                user_type='student', 
                student_profile__batch=allocation.batch
            )
            
            # Clear old records for this date
            StudentAttendance.objects.filter(record=record).delete()
            
            student_attendances = []
            for student in all_students_in_batch:
                student_attendances.append(StudentAttendance(
                    record=record,
                    student=student,
                    is_present=(student.id in present_student_ids)
                ))
                
            StudentAttendance.objects.bulk_create(student_attendances)
            return HttpResponse("OK")
        except Exception as e:
            return HttpResponse(str(e), status=400)
    return HttpResponse("Invalid request", status=400)

@login_required
def get_faculty_batches(request):
    from .models import Batch
    if request.user.user_type == 'coordinator' or request.user.is_superuser:
        batches = Batch.objects.select_related('branch').all()
    else:
        batches = Batch.objects.filter(allocations__faculty=request.user).select_related('branch').distinct()
    return render(request, 'portal/faculty_batches_snippet.html', {'batches': batches})

@login_required
def get_faculty_mst(request):
    from .models import SubjectAllocation, MSTMark, CollegeUser
    if request.user.user_type not in ['faculty', 'coordinator'] and not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=403)
        
    allocations = SubjectAllocation.objects.filter(faculty=request.user).select_related('subject', 'batch')
    selected_allocation_id = request.GET.get('allocation_id')
    students_data = []
    selected_allocation = None
    
    if selected_allocation_id:
        try:
            selected_allocation = allocations.get(id=selected_allocation_id)
            students = CollegeUser.objects.filter(
                user_type='student', 
                student_profile__batch=selected_allocation.batch
            ).order_by('computer_code')
            
            marks_dict = {m.student_id: m for m in MSTMark.objects.filter(subject=selected_allocation.subject)}
            
            for student in students:
                mark = marks_dict.get(student.id)
                students_data.append({
                    'student': student,
                    'mst_1': mark.mst_1_marks if mark else '',
                    'mst_2': mark.mst_2_marks if mark else '',
                })
        except SubjectAllocation.DoesNotExist:
            pass
            
    return render(request, 'portal/faculty_mst_snippet.html', {
        'allocations': allocations,
        'selected_allocation': selected_allocation,
        'students_data': students_data,
        'success': request.GET.get('success')
    })

@login_required
def save_mst_marks(request):
    if request.method == "POST":
        allocation_id = request.POST.get('allocation_id')
        from .models import SubjectAllocation, MSTMark
        try:
            allocation = SubjectAllocation.objects.get(id=allocation_id, faculty=request.user)
            subject = allocation.subject
            for key, value in request.POST.items():
                if key.startswith('student_') and key.endswith('_mst1'):
                    student_id = key.split('_')[1]
                    mst1 = value if value.strip() != '' else None
                    mst2 = request.POST.get(f'student_{student_id}_mst2')
                    mst2 = mst2 if mst2.strip() != '' else None
                    
                    if mst1 is not None or mst2 is not None:
                        MSTMark.objects.update_or_create(
                            student_id=student_id,
                            subject=subject,
                            defaults={
                                'mst_1_marks': mst1,
                                'mst_2_marks': mst2
                            }
                        )
            return redirect(f"/faculty-get-mst/?allocation_id={allocation_id}&success=1")
        except SubjectAllocation.DoesNotExist:
            return HttpResponse("Unauthorized", status=403)
    return HttpResponse("Invalid Method", status=405)

@login_required
def upload_mst_csv(request):
    if request.method == "POST":
        allocation_id = request.POST.get('allocation_id')
        csv_file = request.FILES.get('csv_file')
        from .models import SubjectAllocation, MSTMark, CollegeUser
        import csv
        import io
        
        if not csv_file:
            return redirect(f"/faculty-get-mst/?allocation_id={allocation_id}&error=No file uploaded")
            
        if not csv_file.name.endswith('.csv'):
            return redirect(f"/faculty-get-mst/?allocation_id={allocation_id}&error=File must be a CSV")
            
        try:
            allocation = SubjectAllocation.objects.get(id=allocation_id, faculty=request.user)
            subject = allocation.subject
            
            # Read CSV
            data_set = csv_file.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            
            # Skip header if it exists
            header = next(io_string, None)
            
            success_count = 0
            for row in csv.reader(io_string, delimiter=','):
                if len(row) >= 1:
                    computer_code = row[0].strip()
                    mst1 = row[1].strip() if len(row) > 1 and row[1].strip() else None
                    mst2 = row[2].strip() if len(row) > 2 and row[2].strip() else None
                    
                    try:
                        student = CollegeUser.objects.get(computer_code=computer_code, user_type='student')
                        # Check if student is in this batch
                        if student.student_profile.batch == allocation.batch:
                            MSTMark.objects.update_or_create(
                                student=student,
                                subject=subject,
                                defaults={
                                    'mst_1_marks': mst1 if mst1 else None,
                                    'mst_2_marks': mst2 if mst2 else None
                                }
                            )
                            success_count += 1
                    except CollegeUser.DoesNotExist:
                        continue # Skip invalid students
                        
            return redirect(f"/faculty-get-mst/?allocation_id={allocation_id}&success=Uploaded {success_count} records")
        except SubjectAllocation.DoesNotExist:
            return HttpResponse("Unauthorized", status=403)
        except Exception as e:
            return redirect(f"/faculty-get-mst/?allocation_id={allocation_id}&error={str(e)}")
            
    return HttpResponse("Invalid Method", status=405)

@login_required
def exam_form_regular(request):
    try:
        profile = request.user.student_profile
    except Exception:
        profile = None

    if request.method == 'POST':
        if profile:
            record = ExamFormRecord.objects.filter(student=request.user, form_type='Regular').first()
            if not record:
                return render(request, 'portal/exam_form_regular.html', {'profile': profile, 'error': 'Not forwarded by the institution.'})
                
            record.is_verified_by_student = True
            record.payment_status = 'Payment Pending'
            record.save()
            return render(request, 'portal/payment_gateway.html', {'record': record, 'profile': profile})
            
    # Fetch existing record to show current status
    record = None
    if profile:
        record = ExamFormRecord.objects.filter(student=request.user, form_type='Regular').first()
        
    return render(request, 'portal/exam_form_regular.html', {'profile': profile, 'record': record})

@login_required
def exam_form_atkt(request):
    try:
        profile = request.user.student_profile
    except Exception:
        profile = None

    if request.method == 'POST':
        if profile:
            record = ExamFormRecord.objects.filter(student=request.user, form_type='ATKT').first()
            if not record:
                return render(request, 'portal/exam_form_atkt.html', {'profile': profile, 'error': 'Not forwarded by the institution or not eligible.'})
                
            record.is_verified_by_student = True
            record.payment_status = 'Payment Pending'
            record.save()
            return render(request, 'portal/payment_gateway.html', {'record': record, 'profile': profile})
            
    record = ExamFormRecord.objects.filter(student=request.user, form_type='ATKT').first()
    return render(request, 'portal/exam_form_atkt.html', {'profile': profile, 'record': record})

@login_required
def process_payment(request, record_id):
    if request.method == 'POST':
        record = ExamFormRecord.objects.filter(id=record_id, student=request.user).first()
        if record:
            record.payment_status = 'Payment Successful'
            record.form_status = 'Submitted To IPS Academy'
            record.save()
            return render(request, 'portal/payment_success.html', {'record': record})
    return redirect('student_dashboard')

@login_required
def view_report(request):
    try:
        profile = request.user.student_profile
    except Exception:
        profile = None

    # Fetch all records to determine if any are submitted for generating the receipt
    records = ExamFormRecord.objects.filter(student=request.user)
    has_submitted_exam = any(r.form_status == 'Submitted To IPS Academy' for r in records)
    submitted_records = [r for r in records if r.form_status == 'Submitted To IPS Academy']
    
    context = {
        'profile': profile,
        'has_submitted_exam': has_submitted_exam,
        'submitted_records': submitted_records,
        'user': request.user
    }
    return render(request, 'portal/view_report.html', context)

@login_required
def identity_card(request):
    try:
        profile = request.user.student_profile
    except Exception:
        profile = None

    context = {
        'profile': profile,
        'user': request.user
    }
    return render(request, 'portal/identity_card.html', context)

@login_required
def get_defaulter_list(request):
    from .models import SubjectAllocation, StudentAttendance
    if request.user.user_type not in ['faculty', 'coordinator'] and not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=403)
        
    allocation_id = request.GET.get('allocation_id')
    defaulters = []
    selected_allocation = None
    
    if allocation_id:
        try:
            selected_allocation = SubjectAllocation.objects.get(id=allocation_id, faculty=request.user)
            student_attendances = StudentAttendance.objects.filter(
                record__batch=selected_allocation.batch,
                record__subject=selected_allocation.subject
            ).select_related('student')
            
            stats = {}
            for sa in student_attendances:
                sid = sa.student.id
                if sid not in stats:
                    stats[sid] = {'student': sa.student, 'total': 0, 'present': 0}
                stats[sid]['total'] += 1
                if sa.is_present:
                    stats[sid]['present'] += 1
            
            for sid, stat in stats.items():
                percentage = int((stat['present'] / stat['total']) * 100) if stat['total'] > 0 else 0
                if percentage < 75:
                    defaulters.append({
                        'student': stat['student'],
                        'percentage': percentage,
                        'total': stat['total'],
                        'attended': stat['present']
                    })
                    
            defaulters.sort(key=lambda x: x['percentage'])
        except SubjectAllocation.DoesNotExist:
            pass
            
    return render(request, 'portal/defaulter_snippet.html', {
        'defaulters': defaulters,
        'allocation': selected_allocation
    })

@login_required
def email_defaulters(request):
    if request.method == "POST":
        allocation_id = request.POST.get('allocation_id')
        from django.core.mail import send_mail
        from django.conf import settings
        from .models import SubjectAllocation, StudentAttendance
        
        try:
            allocation = SubjectAllocation.objects.get(id=allocation_id, faculty=request.user)
            student_attendances = StudentAttendance.objects.filter(
                record__batch=allocation.batch,
                record__subject=allocation.subject
            ).select_related('student')
            
            stats = {}
            for sa in student_attendances:
                sid = sa.student.id
                if sid not in stats:
                    stats[sid] = {'student': sa.student, 'total': 0, 'present': 0}
                stats[sid]['total'] += 1
                if sa.is_present:
                    stats[sid]['present'] += 1
                    
            for sid, stat in stats.items():
                percentage = int((stat['present'] / stat['total']) * 100) if stat['total'] > 0 else 0
                if percentage < 75:
                    student = stat['student']
                    if student.email:
                        faculty_name = f"{request.user.first_name} {request.user.last_name}".strip()
                        if not faculty_name:
                            faculty_name = "Your Faculty"
                        send_mail(
                            subject=f'IPS Academy - URGENT: Attendance Shortage in {allocation.subject.name}',
                            message=f'Hello {student.first_name},\n\nYour attendance in {allocation.subject.name} has dropped to {percentage}%. You must maintain at least a 75% attendance average to be eligible for the end-of-semester exams.\n\nPlease ensure you attend upcoming classes regularly.\n\nRegards,\n{faculty_name}',
                            from_email=settings.EMAIL_HOST_USER,
                            recipient_list=[student.email],
                            fail_silently=True,
                        )
            
            return HttpResponse("Emails dispatched successfully!")
        except Exception as e:
            return HttpResponse(str(e), status=400)
    return HttpResponse("Invalid request", status=400)

@login_required
def student_goal_tracker(request):
    if request.user.user_type != 'student':
        return HttpResponse("Unauthorized", status=403)
        
    try:
        profile = request.user.student_profile
        subjects = []
        if profile.batch:
            subjects = profile.batch.branch.subjects.all()
    except Exception:
        subjects = []
        
    context = {
        'subjects': subjects
    }
    return render(request, 'portal/cgpa_tracker_snippet.html', context)

@login_required
def student_fees_view(request):
    if request.user.user_type != 'student':
        return HttpResponse("Unauthorized", status=403)
        
    from .models import FeeInvoice, FeePayment
    
    invoices = FeeInvoice.objects.filter(student=request.user).order_by('due_date')
    unpaid_invoices = invoices.filter(is_paid=False)
    paid_invoices = invoices.filter(is_paid=True)
    
    payments = FeePayment.objects.filter(invoice__student=request.user).order_by('-payment_date')
    
    context = {
        'unpaid_invoices': unpaid_invoices,
        'paid_invoices': paid_invoices,
        'payments': payments,
    }
    return render(request, 'portal/fee_snippet.html', context)

@login_required
def process_dummy_payment(request, invoice_id):
    if request.method == "POST":
        if request.user.user_type != 'student':
            return HttpResponse("Unauthorized", status=403)
            
        from .models import FeeInvoice, FeePayment
        import uuid
        
        try:
            invoice = FeeInvoice.objects.get(id=invoice_id, student=request.user)
            if not invoice.is_paid:
                invoice.is_paid = True
                invoice.save()
                
                # Create fake transaction ID
                tx_id = f"TXN-{str(uuid.uuid4())[:8].upper()}"
                
                FeePayment.objects.create(
                    invoice=invoice,
                    amount_paid=invoice.amount,
                    transaction_id=tx_id
                )
                
            return JsonResponse({'status': 'success', 'transaction_id': getattr(invoice.payments.last(), 'transaction_id', '')})
        except FeeInvoice.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Invoice not found'}, status=404)
            
    return HttpResponse("Invalid Method", status=405)

@login_required
def student_leave_view(request):
    if request.user.user_type != 'student':
        return HttpResponse("Unauthorized", status=403)
        
    from .models import LeaveApplication
    
    if request.method == "POST":
        reason = request.POST.get('reason')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        document = request.FILES.get('document')
        
        LeaveApplication.objects.create(
            student=request.user,
            reason=reason,
            start_date=start_date,
            end_date=end_date,
            document=document
        )
        return redirect('/student-leave/?success=1')
        
    leaves = LeaveApplication.objects.filter(student=request.user).order_by('-applied_on')
    
    context = {
        'leaves': leaves,
    }
    return render(request, 'portal/student_leave_snippet.html', context)

@login_required
def faculty_leave_view(request):
    if request.user.user_type not in ['faculty', 'coordinator']:
        return HttpResponse("Unauthorized", status=403)
        
    from .models import LeaveApplication, SubjectAllocation
    
    # Get all students taught by this faculty
    allocations = SubjectAllocation.objects.filter(faculty=request.user)
    batches = [alloc.batch for alloc in allocations]
    
    # Get pending leaves for students in these batches
    pending_leaves = LeaveApplication.objects.filter(status='Pending', student__student_profile__batch__in=batches).distinct().order_by('-applied_on')
    # Also get recently reviewed
    reviewed_leaves = LeaveApplication.objects.filter(reviewed_by=request.user).order_by('-applied_on')[:10]
    
    context = {
        'pending_leaves': pending_leaves,
        'reviewed_leaves': reviewed_leaves,
    }
    return render(request, 'portal/faculty_leave_snippet.html', context)

@login_required
def process_leave_action(request, leave_id):
    if request.method == "POST":
        if request.user.user_type not in ['faculty', 'coordinator']:
            return HttpResponse("Unauthorized", status=403)
            
        action = request.POST.get('action') # 'Approve' or 'Reject'
        from .models import LeaveApplication
        
        try:
            leave = LeaveApplication.objects.get(id=leave_id)
            if action == 'Approve':
                leave.status = 'Approved'
            elif action == 'Reject':
                leave.status = 'Rejected'
            
            leave.reviewed_by = request.user
            leave.save()
            return JsonResponse({'status': 'success'})
        except LeaveApplication.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Leave application not found'})
            
    return HttpResponse("Invalid Method", status=405)

@login_required
def student_timetable_view(request):
    if request.user.user_type != 'student':
        return HttpResponse("Unauthorized", status=403)
        
    try:
        profile = request.user.student_profile
        batch = profile.batch
        
        # Group schedule by day
        from .models import ClassSchedule, Assignment
        raw_schedule = ClassSchedule.objects.filter(batch=batch).order_by('day_of_week', 'start_time')
        
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        schedule_by_day = {day: [] for day in days}
        
        for item in raw_schedule:
            day_name = days[item.day_of_week]
            schedule_by_day[day_name].append(item)
            
        # Get upcoming deadlines
        from django.utils import timezone
        import datetime
        now = timezone.now()
        upcoming_assignments = Assignment.objects.filter(
            batch=batch, 
            due_date__gte=now
        ).order_by('due_date')
        
        # Calculate urgency (due within 48 hours)
        for assignment in upcoming_assignments:
            time_difference = assignment.due_date - now
            assignment.is_urgent = time_difference.total_seconds() <= (48 * 3600)
        
    except Exception as e:
        schedule_by_day = {}
        upcoming_assignments = []
        
    context = {
        'schedule_by_day': schedule_by_day,
        'upcoming_assignments': upcoming_assignments,
    }
    return render(request, 'portal/timetable_snippet.html', context)

@login_required
def faculty_timetable_view(request):
    if request.user.user_type not in ['faculty', 'coordinator']:
        return HttpResponse("Unauthorized", status=403)
        
    try:
        from .models import ClassSchedule
        raw_schedule = ClassSchedule.objects.filter(faculty=request.user).order_by('day_of_week', 'start_time')
        
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        schedule_by_day = {day: [] for day in days}
        
        for item in raw_schedule:
            day_name = days[item.day_of_week]
            schedule_by_day[day_name].append(item)
            
    except Exception as e:
        schedule_by_day = {}
        
    context = {
        'schedule_by_day': schedule_by_day,
    }
    return render(request, 'portal/faculty_timetable_snippet.html', context)

@login_required
def faculty_get_assignments(request):
    if request.user.user_type not in ['faculty', 'coordinator']:
        return HttpResponse("Unauthorized", status=403)
    
    from .models import Assignment, SubjectAllocation
    # Get all assignments created by this faculty
    assignments = Assignment.objects.filter(faculty=request.user).order_by('-created_at').prefetch_related('submissions', 'submissions__student')
    
    # Get faculty's subject allocations for the create form
    allocations = SubjectAllocation.objects.filter(faculty=request.user)
    
    context = {
        'assignments': assignments,
        'allocations': allocations
    }
    return render(request, 'portal/faculty_assignments_snippet.html', context)

@login_required
def faculty_create_assignment(request):
    if request.method == "POST" and request.user.user_type in ['faculty', 'coordinator']:
        from .models import SubjectAllocation, Assignment
        allocation_id = request.POST.get('allocation_id')
        title = request.POST.get('title')
        description = request.POST.get('description')
        due_date = request.POST.get('due_date') # Expected format: YYYY-MM-DDTHH:MM
        points = request.POST.get('points', 10)
        document = request.FILES.get('document')
        
        if not all([allocation_id, title, description, due_date]):
            return HttpResponse("Missing required fields.", status=400)
            
        try:
            allocation = SubjectAllocation.objects.get(id=allocation_id, faculty=request.user)
            assignment = Assignment.objects.create(
                faculty=request.user,
                subject=allocation.subject,
                batch=allocation.batch,
                title=title,
                description=description,
                document=document,
                due_date=due_date,
                points=points
            )
            
            # Send Notification and Email
            from .models import StudentProfile, Notification, CollegeUser
            from django.core.mail import send_mail
            from django.conf import settings
            
            students = CollegeUser.objects.filter(user_type='student', student_profile__batch=allocation.batch)
            notifications = []
            recipient_list = []
            
            msg = f"{request.user.first_name} {request.user.last_name} published a new assignment: {title}"
            for student in students:
                notifications.append(Notification(recipient=student, message=msg))
                if student.email:
                    recipient_list.append(student.email)
                    
            Notification.objects.bulk_create(notifications)
            
            if recipient_list:
                send_mail(
                    subject=f"New Assignment: {title}",
                    message=f"Dear Student,\n\nA new assignment '{title}' has been uploaded by {request.user.first_name} {request.user.last_name} for {allocation.subject.name}.\n\nPlease log in to the portal to view the details and submit before the deadline.\n\nRegards,\nIPS Academy",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=recipient_list,
                    fail_silently=True,
                )
                
            return HttpResponse("Success")
        except Exception as e:
            return HttpResponse(str(e), status=400)
    return HttpResponse("Invalid request", status=400)

@login_required
def faculty_delete_assignment(request, assignment_id):
    if request.method == "POST" and request.user.user_type in ['faculty', 'coordinator']:
        from .models import Assignment
        try:
            assignment = Assignment.objects.get(id=assignment_id, faculty=request.user)
            assignment.delete()
            return HttpResponse("Success")
        except Assignment.DoesNotExist:
            return HttpResponse("Assignment not found.", status=404)
        except Exception as e:
            return HttpResponse(str(e), status=400)
    return HttpResponse("Invalid request", status=400)

@login_required
def student_submit_assignment(request):
    if request.method == "POST" and request.user.user_type == 'student':
        from .models import Assignment, AssignmentSubmission
        from django.utils import timezone
        
        assignment_id = request.POST.get('assignment_id')
        content = request.POST.get('content')
        
        if not all([assignment_id, content]):
            return HttpResponse("Missing required fields.", status=400)
            
        try:
            assignment = Assignment.objects.get(id=assignment_id)
            if timezone.now() > assignment.due_date:
                return HttpResponse("Deadline has passed.", status=400)
                
            AssignmentSubmission.objects.update_or_create(
                assignment=assignment,
                student=request.user,
                defaults={'content': content, 'submitted_at': timezone.now()}
            )
            return HttpResponse("Success")
        except Exception as e:
            return HttpResponse(str(e), status=400)
    return HttpResponse("Invalid request", status=400)