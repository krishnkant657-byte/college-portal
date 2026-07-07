from django.contrib import admin
from django import forms
from django.contrib.auth.hashers import make_password
from .models import StudentProfile, ExamFormRecord, Student, Faculty, Coordinator, CollegeUser, Batch, FirstYearBranch, SecondYearBranch, ThirdYearBranch, FourthYearBranch, Subject, SubjectAllocation, MSTMark, AttendanceRecord, StudentAttendance, Assignment, AssignmentSubmission, ClassSchedule, FeeInvoice, FeePayment, LeaveApplication

import csv
from django.urls import path
from django.shortcuts import render
from django.contrib import messages
from django.http import HttpResponseRedirect

# --- 1. STUDENT PROFILE INLINE ---

class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make specific fields compulsory as requested
        self.fields['address'].required = True
        self.fields['mobile'].required = True
        self.fields['father_name'].required = True
        self.fields['mother_name'].required = True
        # Disable browser autofill globally for this form using aggressive tags
        for field in self.fields.values():
            field.widget.attrs['autocomplete'] = 'new-password'
            field.widget.attrs['data-lpignore'] = 'true'
            field.widget.attrs['spellcheck'] = 'false'

class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    form = StudentProfileForm
    can_delete = False
    verbose_name_plural = 'Student Full Information (Mandatory & Optional)'

class ExamFormRecordInline(admin.TabularInline):
    model = ExamFormRecord
    extra = 0
    can_delete = True
    verbose_name_plural = 'Exam Forms (Set status to "Forwarded by Institution" to allow student submission)'
    readonly_fields = ('is_verified_by_student', 'submitted_at')


# --- 2. CUSTOM ADMIN FORMS WITH PASSWORD HASHING ---

class BaseUserAdminForm(forms.ModelForm):
    # Use TextInput with CSS masking instead of PasswordInput to defeat the browser's password manager generator
    password = forms.CharField(
        widget=forms.TextInput(attrs={'style': '-webkit-text-security: disc;'}), 
        required=False, 
        help_text="Leave blank to keep the current password."
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        # Disable browser autofill globally for this form using aggressive tags
        for field in self.fields.values():
            field.widget.attrs['autocomplete'] = 'off'
            field.widget.attrs['data-lpignore'] = 'true'
            field.widget.attrs['spellcheck'] = 'false'

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not password and not self.instance.pk:
            raise forms.ValidationError("Password is required for new users.")
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        # If editing and password is blank, keep the old password
        if not self.cleaned_data.get('password') and self.instance.pk:
            user.password = self.instance.__class__.objects.get(pk=self.instance.pk).password
        return super().save(commit)

class StudentAdminForm(BaseUserAdminForm):
    class Meta:
        model = Student
        fields = ('computer_code', 'password', 'first_name', 'last_name', 'email', 'is_active')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.utils.safestring import mark_safe
        self.fields['computer_code'].help_text = mark_safe('<a href="javascript:history.back()" style="background:#6c757d;color:#fff;padding:6px 12px;border-radius:4px;text-decoration:none;display:inline-block;margin-top:8px;">&laquo; Go Back to Batch</a>')

class FacultyAdminForm(BaseUserAdminForm):
    class Meta:
        model = Faculty
        fields = ('computer_code', 'password', 'first_name', 'last_name', 'email', 'is_active')
        
class CoordinatorAdminForm(BaseUserAdminForm):
    class Meta:
        model = Coordinator
        fields = ('computer_code', 'password', 'first_name', 'last_name', 'email', 'is_active')


# --- 3. PROXY ADMIN CLASSES ---

class StudentAdmin(admin.ModelAdmin):
    form = StudentAdminForm
    inlines = [StudentProfileInline, ExamFormRecordInline]
    list_display = ('computer_code', 'first_name', 'last_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('computer_code', 'first_name', 'last_name')
    
    def has_module_permission(self, request):
        # Hides the Student tab from the sidebar as requested
        return False
        
    def get_queryset(self, request):
        return super().get_queryset(request).filter(user_type='student')
        
    def save_model(self, request, obj, form, change):
        if not change or 'password' in form.changed_data:
            if obj.password and not obj.password.startswith('pbkdf2_'):
                obj.password = make_password(obj.password)
        obj.user_type = 'student'
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, StudentProfile):
                batch_id = request.GET.get('batch_id')
                if batch_id:
                    instance.batch_id = batch_id
            instance.save()
        formset.save_m2m()

    def response_add(self, request, obj, post_url_continue=None):
        from django.http import HttpResponseRedirect
        if '_continue' not in request.POST and '_addanother' not in request.POST:
            try:
                if obj.studentprofile and obj.studentprofile.batch:
                    return HttpResponseRedirect(f'/admin/portal/batch/{obj.studentprofile.batch.id}/change/')
            except Exception:
                pass
            return HttpResponseRedirect('/admin/') # Fallback to dashboard if no batch
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        from django.http import HttpResponseRedirect
        if '_continue' not in request.POST and '_addanother' not in request.POST:
            try:
                if obj.studentprofile and obj.studentprofile.batch:
                    return HttpResponseRedirect(f'/admin/portal/batch/{obj.studentprofile.batch.id}/change/')
            except Exception:
                pass
            return HttpResponseRedirect('/admin/') # Fallback to dashboard if no batch
        return super().response_change(request, obj)


class FacultyAdmin(admin.ModelAdmin):
    form = FacultyAdminForm
    list_display = ('computer_code', 'first_name', 'last_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('computer_code', 'first_name', 'last_name')
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(user_type='faculty')
        
    def save_model(self, request, obj, form, change):
        if not change or 'password' in form.changed_data:
            if obj.password and not obj.password.startswith('pbkdf2_'):
                obj.password = make_password(obj.password)
        obj.user_type = 'faculty'
        super().save_model(request, obj, form, change)


class CoordinatorAdmin(admin.ModelAdmin):
    form = CoordinatorAdminForm
    list_display = ('computer_code', 'first_name', 'last_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('computer_code', 'first_name', 'last_name')
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(user_type='coordinator')
        
    def save_model(self, request, obj, form, change):
        if not change or 'password' in form.changed_data:
            if obj.password and not obj.password.startswith('pbkdf2_'):
                obj.password = make_password(obj.password)
        obj.user_type = 'coordinator'
        obj.is_staff = True
        obj.is_superuser = True
        super().save_model(request, obj, form, change)

# --- 4. HIERARCHY ADMIN CONFIGURATION ---

from .models import Branch, Batch, FirstYearBranch, SecondYearBranch, ThirdYearBranch, FourthYearBranch
from django.utils.html import format_html
from django.urls import reverse

from django.utils.safestring import mark_safe

class BatchStudentProfileInline(admin.TabularInline):
    model = StudentProfile
    fields = ('student_link', 'first_name', 'last_name', 'enrollment_number')
    readonly_fields = ('student_link', 'first_name', 'last_name', 'enrollment_number')
    extra = 0
    can_delete = True
    verbose_name_plural = mark_safe(
        'Students in this Batch '
        '&nbsp;&nbsp;&nbsp; '
        '<a href="javascript:void(0)" onclick="window.location.href=\'/admin/portal/student/add/?batch_id=\' + window.location.pathname.split(\'/\')[4]" style="background:var(--primary, #417690);color:#fff;padding:4px 10px;border-radius:4px;text-decoration:none;font-size:0.8rem;">+ Add Student</a>'
        '&nbsp;&nbsp;&nbsp; '
        '<a href="javascript:void(0)" onclick="window.location.href=window.location.pathname.replace(\'/change/\', \'/upload-csv/\')" style="background:#28a745;color:#fff;padding:4px 10px;border-radius:4px;text-decoration:none;font-size:0.8rem;">&#128193; Upload CSV</a>'
    )
    
    def has_add_permission(self, request, obj=None):
        return False
        
    def student_link(self, obj):
        if obj.user_id:
            url = reverse('admin:portal_student_change', args=[obj.user_id])
            return format_html('<a href="{}" target="_blank" style="font-weight:bold; color:var(--primary, #417690);">{}</a>', url, obj.user.computer_code)
        return "-"
    student_link.short_description = "Computer Code"

    def first_name(self, obj):
        return obj.user.first_name if obj.user else "-"
    first_name.short_description = "First Name"
    
    def last_name(self, obj):
        return obj.user.last_name if obj.user else "-"
    last_name.short_description = "Last Name"

class BatchAdmin(admin.ModelAdmin):
    fields = ('batch_info',)
    readonly_fields = ('batch_info',)
    inlines = [BatchStudentProfileInline]
    
    def has_module_permission(self, request):
        return False
        
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:batch_id>/upload-csv/', self.admin_site.admin_view(self.upload_csv), name='batch-upload-csv'),
        ]
        return custom_urls + urls
        
    def upload_csv(self, request, batch_id):
        batch = self.get_object(request, str(batch_id))
        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            if not csv_file or not csv_file.name.endswith('.csv'):
                messages.warning(request, 'Please upload a valid CSV file.')
                return HttpResponseRedirect(request.path_info)
            
            file_data = csv_file.read().decode("utf-8")
            csv_data = csv.reader(file_data.splitlines())
            next(csv_data, None) # Skip header
            
            created_count = 0
            for row in csv_data:
                if len(row) >= 4:
                    code, fname, lname, enroll = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()
                    pwd = row[4].strip() if len(row) > 4 else None
                    if not code: continue
                    
                    user, created = CollegeUser.objects.get_or_create(
                        computer_code=code,
                        defaults={
                            'first_name': fname, 'last_name': lname, 'user_type': 'student',
                            'password': make_password(pwd) if pwd else make_password('123456')
                        }
                    )
                    profile, _ = StudentProfile.objects.get_or_create(user=user)
                    if enroll: profile.enrollment_number = enroll
                    profile.batch = batch
                    profile.save()
                    if created: created_count += 1
            
            messages.success(request, f"Successfully uploaded! Created {created_count} new students.")
            return HttpResponseRedirect(f"/admin/portal/batch/{batch.id}/change/")
            
        return render(request, "admin/upload_students.html", {"batch": batch})
        
    def batch_info(self, obj):
        if not obj: return ""
        return format_html(
            '<div style="display:flex;gap:40px;background:#f8f9fa;padding:15px;border-radius:5px;border:1px solid #dee2e6;">'
            '<div><span style="color:#6c757d;font-size:0.75rem;text-transform:uppercase;font-weight:bold;">Batch</span><br><strong style="font-size:1.1rem;color:#343a40;">{}</strong></div>'
            '<div><span style="color:#6c757d;font-size:0.75rem;text-transform:uppercase;font-weight:bold;">Branch</span><br><strong style="font-size:1.1rem;color:#343a40;">{}</strong></div>'
            '<div><span style="color:#6c757d;font-size:0.75rem;text-transform:uppercase;font-weight:bold;">Year</span><br><strong style="font-size:1.1rem;color:#343a40;">{}</strong></div>'
            '</div>',
            obj.name, obj.branch.name, obj.branch.get_year_display()
        )
    batch_info.short_description = ""

class BatchInline(admin.TabularInline):
    model = Batch
    extra = 1
    fields = ('name', 'manage_students')
    readonly_fields = ('manage_students',)
    
    def manage_students(self, obj):
        if obj.pk:
            url = reverse('admin:portal_batch_change', args=[obj.pk])
            return format_html('<a href="{}" style="background:var(--primary, #417690);color:#fff;padding:4px 10px;border-radius:4px;text-decoration:none;font-size:0.8rem;">Manage Students</a>', url)
        return "Save Batch first to manage students."
    manage_students.short_description = "Students"

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'name':
            field.widget.attrs['autocomplete'] = 'off'
        return field

class BaseBranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'year', 'delete_button')
    list_filter = ('name',)
    search_fields = ('name',)
    inlines = [BatchInline]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'name':
            field.widget.attrs['autocomplete'] = 'off'
        return field

    def delete_button(self, obj):
        model_name = obj._meta.model_name
        url = reverse(f'admin:portal_{model_name}_delete', args=[obj.pk])
        return format_html('<a href="{}" style="color: white; background: #dc3545; padding: 4px 10px; border-radius: 4px; text-decoration: none; font-size: 0.8rem;">Delete</a>', url)
    delete_button.short_description = 'Action'

class FirstYearBranchAdmin(BaseBranchAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(year=1)
    def save_model(self, request, obj, form, change):
        obj.year = 1
        super().save_model(request, obj, form, change)

class SecondYearBranchAdmin(BaseBranchAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(year=2)
    def save_model(self, request, obj, form, change):
        obj.year = 2
        super().save_model(request, obj, form, change)

class ThirdYearBranchAdmin(BaseBranchAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(year=3)
    def save_model(self, request, obj, form, change):
        obj.year = 3
        super().save_model(request, obj, form, change)

class FourthYearBranchAdmin(BaseBranchAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(year=4)
    def save_model(self, request, obj, form, change):
        obj.year = 4
        super().save_model(request, obj, form, change)

# --- 5. REGISTRATION ---
admin.site.register(Student, StudentAdmin)
admin.site.register(Faculty, FacultyAdmin)
admin.site.register(Coordinator, CoordinatorAdmin)

admin.site.register(Batch, BatchAdmin)
admin.site.register(FirstYearBranch, FirstYearBranchAdmin)
admin.site.register(SecondYearBranch, SecondYearBranchAdmin)
admin.site.register(ThirdYearBranch, ThirdYearBranchAdmin)
admin.site.register(FourthYearBranch, BaseBranchAdmin)

# --- 5. ACADEMIC ADMIN CONFIGURATION ---

class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch')
    list_filter = ('branch',)
    search_fields = ('name',)
    
    def has_module_permission(self, request):
        # Only coordinators should manage subjects
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or getattr(request.user, 'user_type', None) == 'coordinator'

class SubjectAllocationAdmin(admin.ModelAdmin):
    list_display = ('faculty', 'subject', 'batch')
    list_filter = ('faculty', 'batch', 'subject')
    search_fields = ('faculty__first_name', 'faculty__last_name', 'faculty__computer_code', 'subject__name', 'batch__name')
    
    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or getattr(request.user, 'user_type', None) == 'coordinator'

admin.site.register(Subject, SubjectAdmin)
admin.site.register(SubjectAllocation, SubjectAllocationAdmin)

class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('batch', 'subject', 'faculty', 'date')
    list_filter = ('date', 'batch', 'subject', 'faculty')

class StudentAttendanceAdmin(admin.ModelAdmin):
    list_display = ('record', 'student', 'is_present')
    list_filter = ('is_present', 'record__date')

admin.site.register(AttendanceRecord, AttendanceRecordAdmin)
admin.site.register(StudentAttendance, StudentAttendanceAdmin)

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'batch', 'faculty', 'due_date', 'points')
    list_filter = ('subject', 'batch')
    search_fields = ('title', 'faculty__computer_code')

@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'student', 'submitted_at', 'marks_awarded')
    list_filter = ('assignment',)
    search_fields = ('student__computer_code', 'student__first_name')

@admin.register(ClassSchedule)
class ClassScheduleAdmin(admin.ModelAdmin):
    list_display = ('batch', 'subject', 'faculty', 'day_of_week', 'start_time', 'end_time')
    list_filter = ('batch', 'day_of_week', 'faculty')
    search_fields = ('subject__name', 'faculty__first_name', 'batch__name')

@admin.register(FeeInvoice)
class FeeInvoiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'amount', 'due_date', 'is_paid')
    list_filter = ('is_paid', 'due_date')
    search_fields = ('student__computer_code', 'title')

@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'invoice', 'amount_paid', 'payment_date')
    search_fields = ('transaction_id', 'invoice__title', 'invoice__student__computer_code')

@admin.register(LeaveApplication)
class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display = ('student', 'start_date', 'end_date', 'status', 'applied_on')
    list_filter = ('status', 'start_date')
    search_fields = ('student__computer_code', 'reason')