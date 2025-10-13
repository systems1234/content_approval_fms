from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, DateField, SubmitField, IntegerField, ValidationError
from wtforms.validators import DataRequired, Email, Length, Optional
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
    category_type = SelectField('Category Type', choices=[
        ('', 'Select Category Type'),
        ('Category', 'Category'),
        ('Blog', 'Blog')
    ], validators=[DataRequired(message='Category type is required')])
    keyword = StringField('Keyword', validators=[DataRequired(message='Keyword is required')])
    search_volume = StringField('Search Volume', validators=[DataRequired(message='Search volume is required')])
    meta_description = TextAreaField('Meta Description', validators=[DataRequired(message='Meta description is required')])
    faqs = TextAreaField('FAQs', validators=[DataRequired(message='FAQs is required')])
    internal_linking_keywords = TextAreaField('Internal Linking Keywords', validators=[DataRequired(message='Internal linking keywords is required')])
    internal_link_urls = TextAreaField('Internal Link URLs', validators=[DataRequired(message='Internal link URLs is required')])

    # SECTION 2: Category-Specific Fields (conditionally required)
    page_type = StringField('Page Type', validators=[Optional()])
    category_name = StringField('Category Name', validators=[Optional()])
    url = StringField('URL', validators=[Optional()])
    page_sv = StringField('Page SV', validators=[Optional()])
    gemstone_category = StringField('Gemstone Category', validators=[Optional()])
    type_field = StringField('Type', validators=[Optional()])
    recommended_density = StringField('Recommended Density', validators=[Optional()])
    word_count = IntegerField('Word Count', validators=[Optional()])
    title_field = StringField('Title', validators=[Optional()])
    astro_non_astro = SelectField('Astro/Non-Astro', choices=[
        ('', 'Select Type'),
        ('Astro', 'Astro'),
        ('Non-Astro', 'Non-Astro')
    ], validators=[Optional()])
    internal_linking_keywords_sv = StringField('Internal Linking Keywords SV', validators=[Optional()])

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
                (self.type_field, 'Type'),
                (self.recommended_density, 'Recommended Density'),
                (self.word_count, 'Word Count'),
                (self.title_field, 'Title'),
                (self.astro_non_astro, 'Astro/Non-Astro'),
                (self.internal_linking_keywords_sv, 'Internal Linking Keywords SV')
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
