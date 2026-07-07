from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class CollegeUser(AbstractUser):
    username = None # Remove the default username field

    # Differentiate between user roles
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('coordinator', 'Coordinator'),
    )
    user_type = models.CharField(max_length=15, choices=USER_TYPE_CHOICES, default='student')
    
    computer_code = models.CharField(max_length=5, unique=True, verbose_name="Computer Code")

    USERNAME_FIELD = 'computer_code'
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.computer_code} - {self.get_user_type_display()}"

# --- PROXY MODELS FOR ADMIN PANEL ---
class Student(CollegeUser):
    class Meta:
        proxy = True
        verbose_name = "Student"
        verbose_name_plural = "Students"

class Faculty(CollegeUser):
    class Meta:
        proxy = True
        verbose_name = "Faculty"
        verbose_name_plural = "2. Faculties"

class Coordinator(CollegeUser):
    class Meta:
        proxy = True
        verbose_name = "Coordinator"
        verbose_name_plural = "1. Coordinators"


# --- BRANCH & BATCH MANAGEMENT MODELS ---
class Branch(models.Model):
    YEAR_CHOICES = (
        (1, '1st Year'),
        (2, '2nd Year'),
        (3, '3rd Year'),
        (4, '4th Year'),
    )
    name = models.CharField(max_length=100)
    year = models.IntegerField(choices=YEAR_CHOICES, default=1)
    
    class Meta:
        verbose_name = "Branch"
        verbose_name_plural = "All Branches"
        
    def __str__(self):
        return f"{self.name} ({self.get_year_display()})"

class Batch(models.Model):
    name = models.CharField(max_length=50, default='Section A')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='batches', null=True)
    
    class Meta:
        verbose_name = "Batch"
        verbose_name_plural = "Batches"
        
    def __str__(self):
        return f"{self.branch.name if self.branch else 'Unknown'} - {self.name}"

# Proxy Models for Admin Tabs
class FirstYearBranch(Branch):
    class Meta:
        proxy = True
        verbose_name = "1st Year Branches"
        verbose_name_plural = "3. B.Tech (1st Year)"

class SecondYearBranch(Branch):
    class Meta:
        proxy = True
        verbose_name = "2nd Year Branches"
        verbose_name_plural = "4. B.Tech (2nd Year)"

class ThirdYearBranch(Branch):
    class Meta:
        proxy = True
        verbose_name = "3rd Year Branches"
        verbose_name_plural = "5. B.Tech (3rd Year)"

class FourthYearBranch(Branch):
    class Meta:
        proxy = True
        verbose_name = "4th Year Branches"
        verbose_name_plural = "6. B.Tech (4th Year)"


class StudentProfile(models.Model):
    user = models.OneToOneField(CollegeUser, on_delete=models.CASCADE, related_name='student_profile')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    enrollment_number = models.CharField(max_length=50, blank=True, null=True)
    father_name = models.CharField(max_length=100, blank=True, null=True)
    mother_name = models.CharField(max_length=100, blank=True, null=True)
    degree = models.CharField(max_length=50, blank=True, null=True, default='B.Tech.')
    branch = models.CharField(max_length=100, blank=True, null=True)
    sex = models.CharField(max_length=10, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    pin_code = models.CharField(max_length=10, blank=True, null=True)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    admission_year = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Profile: {self.user.first_name} {self.user.last_name} ({self.enrollment_number})"

class ExamFormRecord(models.Model):
    SESSION_CHOICES = (
        ('2026-2027(July-Dec)', '2026-2027(July-Dec)'),
        ('2025-2026(Jan-June)', '2025-2026(Jan-June)'),
    )
    FORM_TYPE_CHOICES = (
        ('Regular', 'Regular'),
        ('ATKT', 'ATKT'),
    )
    FORM_STATUS_CHOICES = (
        ('Not forwarded by the institution.', 'Not Forwarded by Institution'),
        ('Forwarded by Institution', 'Forwarded by Institution'),
        ('Submitted To IPS Academy', 'Submitted To IPS Academy'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('Payment Closed.', 'Payment Closed'),
        ('Payment Pending', 'Payment Pending'),
        ('Payment Successful', 'Payment Successful'),
    )

    student = models.ForeignKey(CollegeUser, on_delete=models.CASCADE, related_name='exam_forms')
    session = models.CharField(max_length=50, choices=SESSION_CHOICES, default='2026-2027(July-Dec)') 
    form_type = models.CharField(max_length=20, choices=FORM_TYPE_CHOICES, default='Regular') 
    form_status = models.CharField(max_length=50, choices=FORM_STATUS_CHOICES, default='Not forwarded by the institution.')
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, default='Payment Closed.')
    is_verified_by_student = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.computer_code} - {self.form_type} ({self.session})"

# --- ACADEMIC & MST MODELS ---

class Subject(models.Model):
    name = models.CharField(max_length=150)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='subjects')
    
    class Meta:
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"
        
    def __str__(self):
        return f"{self.name} ({self.branch.get_year_display()})"

class SubjectAllocation(models.Model):
    faculty = models.ForeignKey(CollegeUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'faculty'}, related_name='allocations')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='allocations')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='allocations')
    
    class Meta:
        verbose_name = "Subject Allocation"
        verbose_name_plural = "Subject Allocations"
        unique_together = ('faculty', 'batch', 'subject')
        
    def __str__(self):
        faculty_name = self.faculty.first_name or self.faculty.computer_code
        return f"{faculty_name} -> {self.subject.name} [{self.batch.name}]"

class MSTMark(models.Model):
    student = models.ForeignKey(CollegeUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'student'}, related_name='mst_marks')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='mst_marks')
    mst_1_marks = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    mst_2_marks = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    
    class Meta:
        verbose_name = "MST Mark"
        verbose_name_plural = "MST Marks"
        unique_together = ('student', 'subject')
        
    def __str__(self):
        return f"{self.student.computer_code} - {self.subject.name}"

class AttendanceRecord(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='attendance_records')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='attendance_records')
    faculty = models.ForeignKey(CollegeUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'faculty'})
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"
        unique_together = ('batch', 'subject', 'date')
        
    def __str__(self):
        return f"{self.batch.name} - {self.subject.name} - {self.date}"

class StudentAttendance(models.Model):
    record = models.ForeignKey(AttendanceRecord, on_delete=models.CASCADE, related_name='student_attendances')
    student = models.ForeignKey(CollegeUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'student'})
    is_present = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Student Attendance"
        verbose_name_plural = "Student Attendances"
        unique_together = ('record', 'student')
        
    def __str__(self):
        return f"{self.student.computer_code} - {'Present' if self.is_present else 'Absent'}"

class Assignment(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assignments')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='assignments')
    faculty = models.ForeignKey(CollegeUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'faculty'})
    title = models.CharField(max_length=200)
    description = models.TextField()
    document = models.FileField(upload_to='assignments/', null=True, blank=True)
    due_date = models.DateTimeField()
    points = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Assignment"
        verbose_name_plural = "Assignments"
        
    def __str__(self):
        return f"{self.title} - {self.subject.name} [{self.batch.name}]"

class AssignmentSubmission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(CollegeUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'student'})
    content = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    marks_awarded = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    feedback = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Assignment Submission"
        verbose_name_plural = "Assignment Submissions"
        unique_together = ('assignment', 'student')
        
    def __str__(self):
        return f"{self.student.computer_code} - {self.assignment.title}"

class Notification(models.Model):
    recipient = models.ForeignKey(CollegeUser, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
        
    def __str__(self):
        return f"To {self.recipient.computer_code}: {self.message}"

class ClassSchedule(models.Model):
    DAY_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
    )
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='schedules')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='schedules')
    faculty = models.ForeignKey(CollegeUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'faculty'})
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        verbose_name = "Class Schedule"
        verbose_name_plural = "Class Schedules"
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.batch.name} | {self.get_day_of_week_display()} | {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

class FeeInvoice(models.Model):
    student = models.ForeignKey(CollegeUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'student'}, related_name='fee_invoices')
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fee Invoice"
        verbose_name_plural = "Fee Invoices"
        ordering = ['due_date']

    def __str__(self):
        return f"{self.title} - {self.student.computer_code}"

class FeePayment(models.Model):
    invoice = models.ForeignKey(FeeInvoice, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Fee Payment"
        verbose_name_plural = "Fee Payments"
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment {self.transaction_id} for {self.invoice.title}"

class LeaveApplication(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    )
    student = models.ForeignKey(CollegeUser, on_delete=models.CASCADE, limit_choices_to={'user_type': 'student'}, related_name='leave_applications')
    reason = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    document = models.FileField(upload_to='leaves/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    applied_on = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(CollegeUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_leaves')

    class Meta:
        verbose_name = "Leave Application"
        verbose_name_plural = "Leave Applications"
        ordering = ['-applied_on']

    def __str__(self):
        return f"{self.student.computer_code} - {self.start_date} to {self.end_date} [{self.status}]"