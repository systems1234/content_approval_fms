# FMS (Flow Management System) Implementation Status

## 📊 Overall Progress: ~70% Complete

---

## ✅ COMPLETED FEATURES

### 1. **Database Models** (100% Complete)
**Location:** `app/models.py`

#### New Models Created:
- ✅ **Holiday** - Holiday calendar with recurring support
  - Fields: date, name, description, is_recurring, created_by_id
  - Relationships: creator (User)

- ✅ **BusinessHours** - Working hours configuration per day of week
  - Fields: day_of_week (0-6), start_time, end_time, is_working_day
  - Indexed by day_of_week for performance

- ✅ **StepTemplate** - Workflow step templates with TAT
  - Fields: name, description, step_order, tat_hours, requires_audit, is_active
  - Relationships: creator (User), step_instances (WorkflowStep)

- ✅ **WorkflowStep** - Individual step instances for tasks
  - Fields: step_name, step_order, tat_hours
  - Dates: planned_ptp, planned_atp, started_at, completed_at, audit_completed_at
  - Assignment: assigned_to_id, auditor_id
  - Status: pending, in_progress, completed, under_audit, audit_passed, audit_failed
  - Document submission support
  - Methods: `is_delayed()`, `is_on_time()`, `get_status_badge_class()`

#### Task Model Enhancements:
- ✅ Added methods:
  - `generate_workflow_steps(step_assignments)` - Creates workflow steps from templates
  - `get_current_step()` - Returns active workflow step
  - `get_all_steps()` - Returns all workflow steps ordered
  - `is_workflow_complete()` - Checks if all steps passed
  - `update_task_status_from_workflow()` - Syncs task status with workflow

---

### 2. **Date/Time Calculation Utilities** (100% Complete)
**Location:** `app/utils.py`

#### Functions Implemented:
- ✅ `get_holidays()` - Retrieves holiday dates including recurring
- ✅ `get_business_hours()` - Gets business hours config with defaults
- ✅ `is_working_day(check_date, holidays, business_config)` - Validates working days
- ✅ `add_business_hours(start_datetime, hours_to_add)` - Adds business hours accounting for holidays/weekends
- ✅ `calculate_planned_ptp(task_start, step_order, prev_planned, tat)` - Plan-to-Plan calculation
- ✅ `calculate_planned_atp(prev_actual, tat)` - Actual-to-Plan calculation
- ✅ `calculate_business_hours_between(start, end)` - Duration calculation
- ✅ `initialize_default_business_hours()` - Creates Mon-Fri 9-6 PM default
- ✅ `format_duration_hours(hours)` - Human-readable duration formatting

---

### 3. **Admin Configuration System** (100% Complete)

#### **Holiday Management**
**Routes:** `app/routes.py` lines 662-754
- ✅ `/admin/holidays` - List all holidays
- ✅ `/admin/holidays/create` - Create new holiday
- ✅ `/admin/holidays/<id>/edit` - Edit existing holiday
- ✅ `/admin/holidays/<id>/delete` - Delete holiday

**Forms:** `app/forms.py` lines 205-219
- ✅ `HolidayForm` - Date, name, description, is_recurring

**Templates:** `app/templates/admin/`
- ✅ `holidays.html` - Holiday list with actions
- ✅ `create_holiday.html` - Create form
- ✅ `edit_holiday.html` - Edit form

#### **Business Hours Configuration**
**Routes:** `app/routes.py` lines 757-795
- ✅ `/admin/business-hours` - List all business hours config
- ✅ `/admin/business-hours/<id>/edit` - Edit day configuration

**Forms:** `app/forms.py` lines 222-245
- ✅ `BusinessHoursForm` - Day selector, start/end time, is_working_day

**Templates:** `app/templates/admin/`
- ✅ `business_hours.html` - Config list with calculated hours/day
- ✅ `edit_business_hours.html` - Edit form with validation

#### **Step Templates Management**
**Routes:** `app/routes.py` lines 798-898
- ✅ `/admin/step-templates` - List all templates
- ✅ `/admin/step-templates/create` - Create new template
- ✅ `/admin/step-templates/<id>/edit` - Edit template
- ✅ `/admin/step-templates/<id>/delete` - Delete template (with usage check)

**Forms:** `app/forms.py` lines 248-268
- ✅ `StepTemplateForm` - Name, description, step_order, tat_hours, requires_audit, is_active

**Templates:** `app/templates/admin/`
- ✅ `step_templates.html` - Template list with TAT display
- ✅ `create_step_template.html` - Create form with TAT helper text
- ✅ `edit_step_template.html` - Edit form with usage warning

---

### 4. **Navigation Updates** (100% Complete)
**Location:** `app/templates/base.html`

- ✅ Desktop navigation: Added "FMS Config" dropdown with Alpine.js
  - Holidays, Business Hours, Step Templates links
- ✅ Mobile navigation: Added FMS Config section with all admin links
- ✅ Only visible to admin users

---

### 5. **Task Creation with Workflow** (80% Complete)
**Location:** `app/routes.py` lines 125-265

#### Completed:
- ✅ Modified create_task route to detect `use_workflow` flag
- ✅ Collects step assignments from form data
- ✅ Calls `task.generate_workflow_steps(step_assignments)`
- ✅ Updates task status based on workflow
- ✅ Passes `step_templates` and `all_users` to template

#### Remaining:
- ⏳ **Update `create_task.html` template** to show workflow step assignment UI
  - Add toggle for "Use Multi-Step Workflow"
  - Display step template list with user assignment dropdowns
  - Show TAT for each step

---

## 🔄 IN PROGRESS / REMAINING FEATURES

### 6. **Create Task Template Enhancement** (20% Complete)
**Location:** `app/templates/create_task.html`

**Required Changes:**
Add after line ~35 (after basic task fields section):

```html
<!-- WORKFLOW STEP ASSIGNMENT SECTION -->
{% if step_templates %}
<div class="card mt-6" x-data="{ useWorkflow: false }">
    <div class="card-header bg-purple-50 border-b border-purple-200">
        <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-purple-900">Multi-Step Workflow (FMS)</h3>
            <label class="flex items-center cursor-pointer">
                <input type="checkbox" name="use_workflow" value="yes" x-model="useWorkflow" class="form-checkbox h-5 w-5 text-purple-600">
                <span class="ml-2 text-sm text-gray-700">Enable Workflow</span>
            </label>
        </div>
    </div>

    <div x-show="useWorkflow" x-transition class="card-body">
        <p class="text-sm text-gray-600 mb-4">
            Assign users to each workflow step. TAT is calculated automatically based on business hours.
        </p>

        <div class="space-y-4">
            {% for template in step_templates %}
            <div class="border border-gray-200 rounded-lg p-4 bg-gray-50">
                <div class="flex items-start justify-between mb-3">
                    <div>
                        <h4 class="font-medium text-gray-900">
                            <span class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-purple-100 text-purple-800 text-xs font-bold mr-2">
                                {{ template.step_order }}
                            </span>
                            {{ template.name }}
                        </h4>
                        {% if template.description %}
                        <p class="text-sm text-gray-600 mt-1 ml-8">{{ template.description }}</p>
                        {% endif %}
                    </div>
                    <div class="text-right">
                        <span class="text-sm font-medium text-purple-700">TAT: {{ template.tat_hours }}h</span>
                        <span class="text-xs text-gray-500 block">({{ (template.tat_hours / 24)|round(1) }} days)</span>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 ml-8">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">
                            Assignee <span class="text-red-500">*</span>
                        </label>
                        <select name="step_{{ template.step_order }}_assigned_to" class="form-select w-full" required>
                            <option value="">Select Assignee</option>
                            {% for user in all_users %}
                            <option value="{{ user.id }}">{{ user.username }} ({{ user.role }})</option>
                            {% endfor %}
                        </select>
                    </div>

                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">
                            Auditor {% if template.requires_audit %}<span class="text-red-500">*</span>{% endif %}
                        </label>
                        <select name="step_{{ template.step_order }}_auditor" class="form-select w-full" {% if template.requires_audit %}required{% endif %}>
                            <option value="">Select Auditor</option>
                            {% for user in all_users if user.is_auditor() %}
                            <option value="{{ user.id }}">{{ user.username }} ({{ user.role }})</option>
                            {% endfor %}
                        </select>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>

        <div class="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p class="text-sm text-blue-800">
                <strong>Note:</strong> Planned dates will be calculated automatically based on TAT, business hours, and holidays.
                Users will only see steps assigned to them.
            </p>
        </div>
    </div>
</div>
{% endif %}
```

---

### 7. **Step Completion & Audit Workflow** (0% Complete)
**Location:** `app/routes.py` - New routes needed

**Required Routes:**

```python
@main_bp.route('/workflow-step/<int:step_id>/start', methods=['POST'])
@login_required
def start_workflow_step(step_id):
    """Start a workflow step"""
    step = WorkflowStep.query.get_or_404(step_id)

    # Check permissions
    if step.assigned_to_id != current_user.id:
        abort(403)

    if step.status != 'pending':
        flash('This step has already been started.', 'warning')
        return redirect(url_for('main.task_detail', task_id=step.task_id))

    # Start the step
    step.status = 'in_progress'
    step.started_at = datetime.utcnow()

    # Update task status
    step.task.update_task_status_from_workflow()

    db.session.commit()

    flash(f'Started step: {step.step_name}', 'success')
    return redirect(url_for('main.task_detail', task_id=step.task_id))


@main_bp.route('/workflow-step/<int:step_id>/complete', methods=['POST'])
@login_required
def complete_workflow_step(step_id):
    """Complete a workflow step (submit work)"""
    step = WorkflowStep.query.get_or_404(step_id)

    # Check permissions
    if step.assigned_to_id != current_user.id:
        abort(403)

    if step.status not in ['in_progress', 'audit_failed']:
        flash('Cannot complete this step in its current state.', 'danger')
        return redirect(url_for('main.task_detail', task_id=step.task_id))

    # Handle document/sheet submission
    submission_type = request.form.get('submission_type')

    if submission_type == 'document':
        # Handle file upload (reuse existing logic)
        if 'document_file' not in request.files:
            flash('Please upload a document.', 'danger')
            return redirect(url_for('main.task_detail', task_id=step.task_id))

        file = request.files['document_file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, f"{step.task.ticket_id}_step{step.step_order}_{filename}")
            file.save(filepath)

            step.submission_type = 'document'
            step.document_file_path = filepath
            step.document_file_name = filename

    elif submission_type == 'sheet_link':
        sheet_url = request.form.get('sheet_url', '').strip()
        if not validate_google_sheet_url(sheet_url):
            flash('Please provide a valid Google Sheets URL.', 'danger')
            return redirect(url_for('main.task_detail', task_id=step.task_id))

        step.submission_type = 'sheet_link'
        step.sheet_url = sheet_url

    # Mark step as completed
    step.status = 'completed'
    step.completed_at = datetime.utcnow()

    # If requires audit, move to under_audit
    if step.step_template and step.step_template.requires_audit:
        step.status = 'under_audit'
    else:
        # No audit required, mark as passed
        step.status = 'audit_passed'
        step.audit_completed_at = datetime.utcnow()

        # Calculate planned_atp for next step
        from app.utils import calculate_planned_atp
        next_step = WorkflowStep.query.filter_by(
            task_id=step.task_id
        ).filter(
            WorkflowStep.step_order > step.step_order
        ).order_by(WorkflowStep.step_order).first()

        if next_step:
            next_step.planned_atp = calculate_planned_atp(step.audit_completed_at, next_step.tat_hours)

    # Update task status
    step.task.update_task_status_from_workflow()

    db.session.commit()

    flash(f'Step "{step.step_name}" completed successfully!', 'success')
    return redirect(url_for('main.task_detail', task_id=step.task_id))


@main_bp.route('/workflow-step/<int:step_id>/audit', methods=['POST'])
@login_required
def audit_workflow_step(step_id):
    """Audit a workflow step (pass/fail)"""
    step = WorkflowStep.query.get_or_404(step_id)

    # Check permissions
    if step.auditor_id != current_user.id and not current_user.is_manager():
        abort(403)

    if step.status != 'under_audit':
        flash('This step is not ready for audit.', 'warning')
        return redirect(url_for('main.task_detail', task_id=step.task_id))

    action = request.form.get('action')
    audit_notes = request.form.get('audit_notes', '').strip()

    if action == 'pass':
        step.status = 'audit_passed'
        step.audit_completed_at = datetime.utcnow()
        step.audit_notes = audit_notes

        # Calculate planned_atp for next step
        from app.utils import calculate_planned_atp
        next_step = WorkflowStep.query.filter_by(
            task_id=step.task_id
        ).filter(
            WorkflowStep.step_order > step.step_order
        ).order_by(WorkflowStep.step_order).first()

        if next_step:
            next_step.planned_atp = calculate_planned_atp(step.audit_completed_at, next_step.tat_hours)
            next_step.status = 'pending'  # Activate next step

        flash(f'Step "{step.step_name}" passed audit!', 'success')

    elif action == 'fail':
        step.status = 'audit_failed'
        step.revision_count += 1
        step.audit_notes = audit_notes

        flash(f'Step "{step.step_name}" failed audit. Sent back for revision.', 'warning')

    # Update task status
    step.task.update_task_status_from_workflow()

    db.session.commit()

    return redirect(url_for('main.task_detail', task_id=step.task_id))
```

---

### 8. **User Dashboard with Pending/Delayed Tabs** (0% Complete)
**Location:** `app/routes.py` - Update dashboard route

**Required Changes to `/dashboard` route:**

```python
@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with FMS features"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status_filter = request.args.get('status', None)
    search_query = request.args.get('search', '').strip()
    tab = request.args.get('tab', 'all')  # all, pending, delayed

    # ... existing code ...

    # FMS: Get user's assigned workflow steps
    if current_user.role not in ['admin', 'manager']:
        # All pending steps assigned to user
        pending_steps = WorkflowStep.query.filter_by(
            assigned_to_id=current_user.id
        ).filter(
            WorkflowStep.status.in_(['pending', 'in_progress', 'audit_failed'])
        ).order_by(WorkflowStep.planned_atp, WorkflowStep.planned_ptp).all()

        # Delayed steps (past planned date)
        delayed_steps = [step for step in pending_steps if step.is_delayed()]

        pending_count = len(pending_steps)
        delayed_count = len(delayed_steps)
    else:
        pending_steps = []
        delayed_steps = []
        pending_count = 0
        delayed_count = 0

    # ... existing pagination code ...

    return render_template('dashboard.html',
                         tasks=tasks,
                         stats=stats,
                         pending_steps=pending_steps,
                         delayed_steps=delayed_steps,
                         pending_count=pending_count,
                         delayed_count=delayed_count,
                         tab=tab,
                         # ... existing vars ...
                         )
```

**Update `dashboard.html` template:**
Add tabs UI after the search/filter section:

```html
<!-- FMS: User Workflow Steps Panel -->
{% if current_user.role not in ['admin', 'manager'] %}
<div class="mt-6 bg-white shadow-sm rounded-lg border border-gray-200">
    <div class="border-b border-gray-200">
        <nav class="-mb-px flex">
            <a href="{{ url_for('main.dashboard', tab='all') }}"
               class="px-6 py-3 border-b-2 font-medium text-sm {% if tab == 'all' %}border-blue-500 text-blue-600{% else %}border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300{% endif %}">
                All Tasks
            </a>
            <a href="{{ url_for('main.dashboard', tab='pending') }}"
               class="px-6 py-3 border-b-2 font-medium text-sm {% if tab == 'pending' %}border-blue-500 text-blue-600{% else %}border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300{% endif %}">
                My Pending Steps
                {% if pending_count > 0 %}
                <span class="ml-2 px-2 py-1 text-xs font-bold rounded-full bg-blue-100 text-blue-800">{{ pending_count }}</span>
                {% endif %}
            </a>
            <a href="{{ url_for('main.dashboard', tab='delayed') }}"
               class="px-6 py-3 border-b-2 font-medium text-sm {% if tab == 'delayed' %}border-red-500 text-red-600{% else %}border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300{% endif %}">
                Delayed Steps
                {% if delayed_count > 0 %}
                <span class="ml-2 px-2 py-1 text-xs font-bold rounded-full bg-red-100 text-red-800">{{ delayed_count }}</span>
                {% endif %}
            </a>
        </nav>
    </div>

    {% if tab == 'pending' or tab == 'delayed' %}
    <div class="p-6">
        {% set display_steps = delayed_steps if tab == 'delayed' else pending_steps %}
        {% if display_steps %}
        <div class="space-y-4">
            {% for step in display_steps %}
            <div class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition {% if step.is_delayed() %}border-l-4 border-l-red-500{% endif %}">
                <div class="flex justify-between items-start">
                    <div class="flex-1">
                        <a href="{{ url_for('main.task_detail', task_id=step.task_id) }}" class="font-medium text-blue-600 hover:text-blue-800">
                            {{ step.task.ticket_id }} - {{ step.task.title }}
                        </a>
                        <p class="text-sm text-gray-600 mt-1">
                            Step {{ step.step_order }}: {{ step.step_name }}
                        </p>
                        <div class="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                            <span>TAT: {{ step.tat_hours }}h</span>
                            {% if step.planned_atp %}
                            <span>Planned: {{ step.planned_atp.strftime('%Y-%m-%d %H:%M') }}</span>
                            {% elif step.planned_ptp %}
                            <span>Planned: {{ step.planned_ptp.strftime('%Y-%m-%d %H:%M') }}</span>
                            {% endif %}
                            {% if step.is_delayed() %}
                            <span class="text-red-600 font-medium">⚠ DELAYED</span>
                            {% endif %}
                        </div>
                    </div>
                    <div>
                        <span class="px-3 py-1 text-xs font-medium rounded-full {{ step.get_status_badge_class() }}">
                            {{ step.status.replace('_', ' ').title() }}
                        </span>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <p class="text-gray-500 text-center py-8">No {{ 'delayed' if tab == 'delayed' else 'pending' }} steps.</p>
        {% endif %}
    </div>
    {% endif %}
</div>
{% endif %}
```

---

### 9. **Task Detail View with Planned vs Actual Table** (0% Complete)
**Location:** `app/templates/task_detail.html`

**Add after task information section:**

```html
<!-- FMS: Workflow Steps - Planned vs Actual -->
{% set workflow_steps = task.get_all_steps() %}
{% if workflow_steps %}
<div class="card mb-6">
    <div class="card-header bg-purple-50 border-b border-purple-200">
        <h3 class="text-lg font-semibold text-purple-900">Workflow Progress</h3>
    </div>
    <div class="card-body p-0">
        <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Step</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Assignee</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">TAT</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Planned (PTP)</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Planned (ATP)</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actual</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    {% for step in workflow_steps %}
                    <tr class="{% if step.is_delayed() %}bg-red-50{% elif step.status == 'audit_passed' %}bg-green-50{% endif %}">
                        <td class="px-4 py-3 whitespace-nowrap">
                            <span class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-purple-100 text-purple-800 text-xs font-bold">
                                {{ step.step_order }}
                            </span>
                        </td>
                        <td class="px-4 py-3 text-sm font-medium">{{ step.step_name }}</td>
                        <td class="px-4 py-3 text-sm">
                            {% if step.assignee %}{{ step.assignee.username }}{% else %}<span class="text-gray-400">Not assigned</span>{% endif %}
                        </td>
                        <td class="px-4 py-3 text-sm whitespace-nowrap">{{ step.tat_hours }}h</td>
                        <td class="px-4 py-3 text-sm whitespace-nowrap">
                            {% if step.planned_ptp %}{{ step.planned_ptp.strftime('%Y-%m-%d %H:%M') }}{% else %}<span class="text-gray-400">-</span>{% endif %}
                        </td>
                        <td class="px-4 py-3 text-sm whitespace-nowrap">
                            {% if step.planned_atp %}{{ step.planned_atp.strftime('%Y-%m-%d %H:%M') }}{% else %}<span class="text-gray-400">-</span>{% endif %}
                        </td>
                        <td class="px-4 py-3 text-sm whitespace-nowrap {% if step.is_on_time() == False %}text-red-600 font-medium{% elif step.is_on_time() == True %}text-green-600 font-medium{% endif %}">
                            {% if step.audit_completed_at %}
                                {{ step.audit_completed_at.strftime('%Y-%m-%d %H:%M') }}
                                {% if step.is_on_time() == True %}✓{% elif step.is_on_time() == False %}⚠{% endif %}
                            {% else %}<span class="text-gray-400">-</span>{% endif %}
                        </td>
                        <td class="px-4 py-3">
                            <span class="px-2 py-1 text-xs font-medium rounded-full {{ step.get_status_badge_class() }}">
                                {{ step.status.replace('_', ' ').title() }}
                            </span>
                        </td>
                        <td class="px-4 py-3 text-sm">
                            {% if step.assigned_to_id == current_user.id %}
                                {% if step.status == 'pending' %}
                                <form method="POST" action="{{ url_for('main.start_workflow_step', step_id=step.id) }}" class="inline">
                                    <button type="submit" class="text-blue-600 hover:text-blue-800 text-xs">Start</button>
                                </form>
                                {% elif step.status == 'in_progress' %}
                                <button onclick="showCompleteModal({{ step.id }})" class="text-green-600 hover:text-green-800 text-xs">Complete</button>
                                {% endif %}
                            {% endif %}
                            {% if (step.auditor_id == current_user.id or current_user.is_manager()) and step.status == 'under_audit' %}
                            <button onclick="showAuditModal({{ step.id }})" class="text-yellow-600 hover:text-yellow-800 text-xs">Audit</button>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endif %}
```

---

### 10. **Performance Reporting** (0% Complete)
**Location:** New route and template needed

**Create route:**
```python
@main_bp.route('/my-performance')
@login_required
def my_performance():
    """User performance report"""
    # Get all completed steps for user
    completed_steps = WorkflowStep.query.filter_by(
        assigned_to_id=current_user.id,
        status='audit_passed'
    ).all()

    # Calculate stats
    total_completed = len(completed_steps)
    on_time = sum(1 for step in completed_steps if step.is_on_time())
    late = total_completed - on_time

    # Performance score (on-time percentage)
    performance_score = (on_time / total_completed * 100) if total_completed > 0 else 0

    # Group by month for chart
    from collections import defaultdict
    monthly_stats = defaultdict(lambda: {'total': 0, 'on_time': 0})

    for step in completed_steps:
        if step.audit_completed_at:
            month_key = step.audit_completed_at.strftime('%Y-%m')
            monthly_stats[month_key]['total'] += 1
            if step.is_on_time():
                monthly_stats[month_key]['on_time'] += 1

    return render_template('my_performance.html',
                         total_completed=total_completed,
                         on_time=on_time,
                         late=late,
                         performance_score=round(performance_score, 1),
                         monthly_stats=dict(monthly_stats),
                         completed_steps=completed_steps)


@main_bp.route('/my-performance/export')
@login_required
def export_performance():
    """Export performance report as CSV"""
    import csv
    from io import StringIO
    from flask import make_response

    completed_steps = WorkflowStep.query.filter_by(
        assigned_to_id=current_user.id,
        status='audit_passed'
    ).all()

    # Generate CSV
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Task ID', 'Step Name', 'Planned Date', 'Actual Date', 'TAT (hours)', 'On Time'])

    for step in completed_steps:
        planned = step.planned_atp or step.planned_ptp
        writer.writerow([
            step.task.ticket_id,
            step.step_name,
            planned.strftime('%Y-%m-%d %H:%M') if planned else '',
            step.audit_completed_at.strftime('%Y-%m-%d %H:%M') if step.audit_completed_at else '',
            step.tat_hours,
            'Yes' if step.is_on_time() else 'No'
        ])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=performance_{current_user.username}.csv"
    output.headers["Content-type"] = "text/csv"
    return output
```

---

### 11. **Database Migration** (0% Complete)

**Create migration:**
```bash
flask db migrate -m "Add FMS workflow tables"
flask db upgrade
```

**Initialize default data:**
```python
# Add to app/__init__.py or create init script
from app.utils import initialize_default_business_hours

with app.app_context():
    initialize_default_business_hours()
```

---

## 📝 TESTING CHECKLIST

### Admin Configuration
- [ ] Create holidays (one-time and recurring)
- [ ] Edit and delete holidays
- [ ] Configure business hours for each day
- [ ] Create step templates with different TATs
- [ ] Edit and delete step templates

### Workflow Creation
- [ ] Create task with multi-step workflow enabled
- [ ] Assign different users to each step
- [ ] Verify workflow steps are created correctly
- [ ] Check planned_ptp dates are calculated

### Step Execution
- [ ] User sees only their assigned steps in dashboard
- [ ] Start a workflow step
- [ ] Complete step with document upload
- [ ] Complete step with Google Sheets URL
- [ ] Verify planned_atp is calculated after completion

### Audit Process
- [ ] Auditor sees steps under audit
- [ ] Pass a step audit
- [ ] Fail a step audit (send back for revision)
- [ ] Verify revision count increments
- [ ] Verify next step becomes active after audit pass

### Dashboard & Reporting
- [ ] "All Pending" tab shows user's active steps
- [ ] "Delayed Pending" tab shows overdue steps
- [ ] Steps marked as delayed when past planned date
- [ ] Performance report shows on-time vs late stats
- [ ] CSV export works correctly

### Business Hours & Holidays
- [ ] TAT respects business hours (no counting after 6 PM)
- [ ] TAT skips weekends
- [ ] TAT skips configured holidays
- [ ] Recurring holidays apply to future years

---

## 🚀 DEPLOYMENT NOTES

1. **Run migrations:**
   ```bash
   flask db migrate -m "Add FMS workflow tables"
   flask db upgrade
   ```

2. **Initialize business hours:**
   ```python
   from app.utils import initialize_default_business_hours
   initialize_default_business_hours()
   ```

3. **Create initial step templates** (via admin UI or script):
   - Step 1: Content Writing (TAT: 48h)
   - Step 2: Internal Review (TAT: 24h)
   - Step 3: Final Approval (TAT: 12h)

4. **Test workflow end-to-end** with sample task

---

## 📚 KEY CONCEPTS

### Planned Date Calculations
- **PTP (Plan-to-Plan)**: Based on previous step's planned date + TAT
  - Used for initial planning
  - Calculated when workflow is created

- **ATP (Actual-to-Plan)**: Based on previous step's actual completion + TAT
  - More accurate, reflects real progress
  - Calculated after previous step completes

### Business Hours Logic
- Only counts hours during configured working times
- Automatically skips non-working days
- Respects holidays (one-time and recurring)
- Example: 24h TAT on Friday 5 PM = Tuesday 9 AM (skips weekend)

### Step States
1. **Pending** - Step created, waiting to start
2. **In Progress** - Assignee is working on it
3. **Completed** - Work submitted, waiting for audit
4. **Under Audit** - Auditor reviewing
5. **Audit Passed** - Approved, moves to next step
6. **Audit Failed** - Rejected, goes back to assignee

---

## 🎯 NEXT IMMEDIATE STEPS

1. ✅ **Add workflow step assignment UI to create_task.html** (snippet provided above)
2. ✅ **Implement step completion routes** (code provided above)
3. ✅ **Update dashboard with pending/delayed tabs** (code provided above)
4. ✅ **Add workflow progress table to task_detail.html** (code provided above)
5. ✅ **Create performance reporting** (routes provided above)
6. ⏳ **Run database migrations**
7. ⏳ **Test end-to-end workflow**

---

## 📞 SUPPORT

If you need clarification on any feature or encounter issues:
1. Check this status document first
2. Review the code comments in models.py and utils.py
3. Test with small data first (1-2 tasks, 2-3 steps)

**Remember:** The system supports both legacy (single-step) and new (multi-step) workflows. Tasks without workflow steps use the old system, tasks with workflow steps use FMS.

---

**Document Last Updated:** 2025-01-28
**Implementation Progress:** ~70% Complete
**Estimated Time to Complete:** 4-6 hours for remaining features + testing
