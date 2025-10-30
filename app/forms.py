from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, DateField, SubmitField, IntegerField, ValidationError, BooleanField, TimeField, FloatField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange
from datetime import date

class LoginForm(FlaskForm):
    """User login form"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=80, message='Username must be between 3 and 80 characters')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required')
    ])
    submit = SubmitField('Sign In')


class CreateTaskForm(FlaskForm):
    """Task creation form with content-specific fields"""
    # Basic fields
    title = StringField('Task Title', validators=[
        DataRequired(message='Task title is required'),
        Length(min=5, max=200, message='Title must be between 5 and 200 characters')
    ])
    description = TextAreaField('Comments/Notes', validators=[
        Optional(),
        Length(max=5000, message='Comments must not exceed 5000 characters')
    ])
    assigned_to = SelectField('Assign To', coerce=int, validators=[
        DataRequired(message='Please assign the task to someone')
    ])
    plan_date = DateField('Planned Completion Date', validators=[
        DataRequired(message='Planned completion date is required')
    ], format='%Y-%m-%d')

    # SECTION 1: Basic Information
    category_type = SelectField('Content Type', choices=[
        ('', 'Select Content Type'),
        ('Category', 'Category'),
        ('Blog', 'Blog')
    ], validators=[DataRequired(message='Content type is required')])

    # Note: Content Metrics (type, keyword, search_volume) and Linking Data
    # (internal_linking_keywords, internal_link_urls, internal_linking_keywords_sv)
    # are now handled as dynamic arrays via JavaScript tables in the template

    title_field = StringField('Meta Title', validators=[
        DataRequired(message='Meta Title is required'),
        Length(min=10, max=200, message='Meta Title must be between 10 and 200 characters')
    ])
    meta_description = TextAreaField('Meta Description', validators=[DataRequired(message='Meta description is required')])
    faqs = TextAreaField('FAQs', validators=[DataRequired(message='FAQs is required')])

    # SECTION 2: Category-Specific Fields (conditionally required)
    page_type = StringField('Page Type', validators=[Optional()])
    category_name = StringField('Category Name', validators=[Optional()])
    url = StringField('URL', validators=[Optional()])
    page_sv = StringField('Page SV', validators=[Optional()])
    gemstone_category = SelectField('Gemstone Category', choices=[
        ('', 'Select Gemstone Category'),
        ('0-ultraprecious', '0-ultraprecious'),
        ('1-precious', '1-precious'),
        ('2-midPrecious', '2-midPrecious'),
        ('4-semiPrecious', '4-semiPrecious')
    ], validators=[Optional()])
    recommended_density = StringField('Recommended Density', validators=[Optional()])
    word_count = IntegerField('Word Count', validators=[Optional()])
    astro_non_astro = SelectField('Astro/Non-Astro', choices=[
        ('', 'Select Type'),
        ('Astro', 'Astro'),
        ('Non-Astro', 'Non-Astro')
    ], validators=[Optional()])

    # SECTION 3: Blog-Specific Fields (conditionally required)
    blog_url = StringField('Blog URL', validators=[Optional()])
    keyword_sv = StringField('Keyword SV', validators=[Optional()])
    h1 = StringField('H1', validators=[Optional()])
    meta_title = StringField('Meta Title', validators=[Optional()])
    content_structure_recommended = TextAreaField('Content Structure - Recommended', validators=[Optional()])

    submit = SubmitField('Create Task')

    def validate(self, extra_validators=None):
        """Custom validation to handle conditional required fields based on category_type"""
        if not super(CreateTaskForm, self).validate(extra_validators=extra_validators):
            return False

        # Get the category type
        category_type = self.category_type.data

        # If category type is 'Category', validate all Category-specific fields
        if category_type == 'Category':
            category_fields = [
                (self.page_type, 'Page Type'),
                (self.category_name, 'Category Name'),
                (self.url, 'URL'),
                (self.page_sv, 'Page SV'),
                (self.gemstone_category, 'Gemstone Category'),
                (self.recommended_density, 'Recommended Density'),
                (self.word_count, 'Word Count'),
                (self.astro_non_astro, 'Astro/Non-Astro')
            ]

            for field, field_name in category_fields:
                if not field.data or (isinstance(field.data, str) and not field.data.strip()):
                    field.errors.append(f'{field_name} is required for Category type')
                    return False

        # If category type is 'Blog', validate all Blog-specific fields
        elif category_type == 'Blog':
            blog_fields = [
                (self.blog_url, 'Blog URL'),
                (self.keyword_sv, 'Keyword SV'),
                (self.h1, 'H1'),
                (self.meta_title, 'Meta Title'),
                (self.content_structure_recommended, 'Content Structure - Recommended')
            ]

            for field, field_name in blog_fields:
                if not field.data or (isinstance(field.data, str) and not field.data.strip()):
                    field.errors.append(f'{field_name} is required for Blog type')
                    return False

        return True


class UpdateTaskForm(FlaskForm):
    """Task update form"""
    title = StringField('Task Title', validators=[
        DataRequired(message='Task title is required'),
        Length(min=5, max=200, message='Title must be between 5 and 200 characters')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=5000, message='Description must not exceed 5000 characters')
    ])
    plan_date = DateField('Planned Completion Date', validators=[
        Optional()
    ], format='%Y-%m-%d')
    submit = SubmitField('Update Task')


class TaskActionForm(FlaskForm):
    """Form for task status transitions"""
    notes = TextAreaField('Notes', validators=[
        Optional(),
        Length(max=1000, message='Notes must not exceed 1000 characters')
    ])
    submit = SubmitField('Submit')


class AuditForm(FlaskForm):
    """Audit action form"""
    audit_notes = TextAreaField('Audit Notes', validators=[
        DataRequired(message='Audit notes are required'),
        Length(min=10, max=1000, message='Notes must be between 10 and 1000 characters')
    ])
    action = SelectField('Audit Decision', choices=[
        ('audit_passed', 'Pass Audit'),
        ('audit_failed', 'Fail Audit')
    ], validators=[DataRequired()])
    new_completion_date = DateField('New Completion Date (if rejected)', validators=[
        Optional()
    ], format='%Y-%m-%d')
    submit = SubmitField('Submit Audit')


class CreateUserForm(FlaskForm):
    """User creation form (Admin only)"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=80, message='Username must be between 3 and 80 characters')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Invalid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=8, message='Password must be at least 8 characters')
    ])
    role = SelectField('Role', choices=[
        ('assignee', 'Assignee'),
        ('manager', 'Manager'),
        ('admin', 'Admin')
    ], validators=[DataRequired()])
    submit = SubmitField('Create User')


class UpdatePasswordForm(FlaskForm):
    """Password update form (Admin only)"""
    new_password = PasswordField('New Password', validators=[
        DataRequired(message='New password is required'),
        Length(min=8, message='Password must be at least 8 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm the password'),
        Length(min=8, message='Password must be at least 8 characters')
    ])
    submit = SubmitField('Update Password')

    def validate_confirm_password(self, field):
        """Validate that passwords match"""
        if field.data != self.new_password.data:
            raise ValidationError('Passwords must match')


class HolidayForm(FlaskForm):
    """Holiday management form (Admin only)"""
    date = DateField('Holiday Date', validators=[
        DataRequired(message='Holiday date is required')
    ], format='%Y-%m-%d')
    name = StringField('Holiday Name', validators=[
        DataRequired(message='Holiday name is required'),
        Length(min=2, max=200, message='Name must be between 2 and 200 characters')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500, message='Description must not exceed 500 characters')
    ])
    is_recurring = BooleanField('Recurring Yearly', default=False)
    submit = SubmitField('Save Holiday')


class BusinessHoursForm(FlaskForm):
    """Business hours configuration form (Admin only)"""
    day_of_week = SelectField('Day of Week', coerce=int, choices=[
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday')
    ], validators=[DataRequired()])
    start_time = TimeField('Start Time', validators=[
        DataRequired(message='Start time is required')
    ], format='%H:%M')
    end_time = TimeField('End Time', validators=[
        DataRequired(message='End time is required')
    ], format='%H:%M')
    is_working_day = BooleanField('Is Working Day', default=True)
    submit = SubmitField('Save Business Hours')

    def validate_end_time(self, field):
        """Validate that end time is after start time"""
        if self.is_working_day.data and field.data <= self.start_time.data:
            raise ValidationError('End time must be after start time')


class StepTemplateForm(FlaskForm):
    """Workflow step template form (Admin only)"""
    name = StringField('Step Name', validators=[
        DataRequired(message='Step name is required'),
        Length(min=2, max=200, message='Name must be between 2 and 200 characters')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500, message='Description must not exceed 500 characters')
    ])
    step_order = IntegerField('Step Order', validators=[
        DataRequired(message='Step order is required'),
        NumberRange(min=1, message='Step order must be at least 1')
    ])
    tat_hours = FloatField('TAT (Hours)', validators=[
        DataRequired(message='TAT is required'),
        NumberRange(min=0.5, max=720, message='TAT must be between 0.5 and 720 hours (30 days)')
    ])
    requires_audit = BooleanField('Requires Audit', default=True)
    is_active = BooleanField('Is Active', default=True)
    submit = SubmitField('Save Step Template')
