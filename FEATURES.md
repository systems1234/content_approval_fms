# TaskFlow CRM - Feature Guide

Complete guide to all features and capabilities of TaskFlow CRM.

## Table of Contents
1. [User Management](#user-management)
2. [Task Management](#task-management)
3. [Workflow & FSM](#workflow--fsm)
4. [Audit System](#audit-system)
5. [Dashboards](#dashboards)
6. [Security Features](#security-features)
7. [UI/UX Features](#uiux-features)

---

## User Management

### User Roles

#### Admin
**Capabilities:**
- Create and manage all users
- Activate/deactivate user accounts
- View all tasks in the system
- Create and assign tasks
- Audit tasks
- Full system access

**Dashboard View:**
- All tasks across all users
- System-wide statistics
- User management link

#### Manager
**Capabilities:**
- Create new tasks
- Assign tasks to any user
- View all tasks
- Cancel any task
- Monitor team progress

**Dashboard View:**
- All tasks in the system
- Team statistics
- Task creation button

#### Auditor
**Capabilities:**
- Review completed tasks
- Approve or reject work
- Provide audit feedback
- View assigned audits

**Dashboard View:**
- Tasks pending audit
- Audit statistics (total, pending, passed, failed)
- Audit dashboard link

#### Assignee
**Capabilities:**
- View assigned tasks
- Start working on tasks
- Complete tasks
- View task history

**Dashboard View:**
- Own assigned tasks
- Personal statistics
- Task status filters

### User Creation (Admin Only)
- Username (unique)
- Email address (unique)
- Secure password (min 8 characters)
- Role selection
- Automatic activation

### User Management
- View all users in table format
- See user details (email, role, status, creation date)
- Activate/deactivate accounts
- Cannot deactivate own account
- Color-coded role badges

---

## Task Management

### Task Creation (Manager/Admin)

**Required Fields:**
- Task Title (5-200 characters)
- Assigned To (select from active users)

**Optional Fields:**
- Description (rich text, up to 5000 characters)
- Planned Completion Date

**Auto-Generated:**
- Created By (current user)
- Status (assigned)
- Creation timestamp
- Unique task ID

### Task Details View

**Information Display:**
- Task title and status badge
- Full description
- Assigned user (with avatar)
- Creator information
- Auditor (if assigned)
- All relevant dates
- Revision count (if any)
- Audit notes (if failed)

**Activity Log:**
- Chronological list of all actions
- User attribution
- Timestamps
- Notes and comments
- Visual timeline

**Workflow Progress:**
- Visual progress indicator
- Current status highlighted
- Completed steps marked
- Upcoming steps shown

### Task Actions

**Assignee Actions:**
- Start Task (assigned → in_progress)
- Complete Task (in_progress → completed → under_audit)

**Auditor Actions:**
- Pass Audit (under_audit → audit_passed)
- Fail Audit (under_audit → audit_failed → in_progress)

**Manager Actions:**
- Cancel Task (any status → cancelled)

**All Actions Include:**
- Optional notes field
- Confirmation step
- Automatic logging
- State validation

---

## Workflow & FSM

### State Definitions

#### 1. Assigned
- Initial state when task is created
- Task is waiting to be started
- Can transition to: In Progress, Cancelled

#### 2. In Progress
- Assignee is actively working
- Started by assignee
- Can transition to: Completed, Cancelled

#### 3. Completed
- Work finished by assignee
- Automatically moves to Under Audit
- System assigns random auditor
- Can transition to: Under Audit, Cancelled

#### 4. Under Audit
- Auditor is reviewing the work
- Waiting for audit decision
- Can transition to: Audit Passed, Audit Failed, Cancelled

#### 5. Audit Passed
- Work approved by auditor
- Terminal state (complete)
- Task successfully finished
- No further transitions

#### 6. Audit Failed
- Work rejected by auditor
- Audit notes required
- Revision count incremented
- Automatically returns to In Progress
- Can be reworked and resubmitted

#### 7. Cancelled
- Task cancelled by manager
- Terminal state
- No further work possible
- Preserved for audit trail

### Automatic Behaviors

**On Task Completion:**
1. Status changes to "completed"
2. Completion date recorded
3. System assigns random auditor from available auditors
4. Status auto-transitions to "under_audit"
5. Activity log updated

**On Audit Failure:**
1. Audit date recorded
2. Revision count incremented
3. Audit notes saved
4. Status returns to "in_progress"
5. Assignee can rework

**On Audit Success:**
1. Audit date recorded
2. Status set to "audit_passed"
3. Task marked as complete
4. No further changes allowed

---

## Audit System

### Auditor Assignment
- **Automatic**: On task completion
- **Random Selection**: From available auditors
- **Exclusions**: Task assignee cannot be auditor
- **Roles Eligible**: Auditor, Manager, Admin

### Audit Process

**Step 1: Task Completion**
- Assignee marks task as complete
- System auto-assigns auditor
- Status changes to "under_audit"
- Auditor notified (via dashboard)

**Step 2: Review**
- Auditor views task details
- Reviews work description
- Checks completion quality
- Examines task history

**Step 3: Decision**
- **Pass**: Work meets requirements
  - Add approval notes (optional)
  - Task marked as passed
- **Fail**: Work needs revision
  - Add audit notes (required)
  - Specify what needs fixing
  - Task returns to assignee

**Step 4: Resolution**
- If passed: Task complete
- If failed: Assignee revises and resubmits

### Audit Dashboard

**Statistics Display:**
- Total audits assigned
- Pending audits count
- Passed audits count
- Failed audits count

**Task List:**
- Only tasks "under_audit"
- Sorted by completion date
- Quick review button
- Revision indicators

### Audit Trail
- All audits logged
- Previous audit notes visible
- Revision history tracked
- Auditor actions recorded

---

## Dashboards

### Main Dashboard (All Roles)

**Statistics Cards:**
1. **Total Tasks**: All tasks (role-dependent)
2. **Assigned**: Tasks waiting to start
3. **In Progress**: Active tasks
4. **Under Audit**: Tasks being reviewed
5. **Completed**: Successfully finished tasks

**Filters:**
- All tasks
- By status (assigned, in_progress, under_audit, passed)
- Applied via button clicks
- URL-based (bookmarkable)

**Task List:**
- Paginated (10 per page)
- Task cards with:
  - Title and status badge
  - Description preview
  - Assignee name
  - Auditor name (if assigned)
  - Creation date
  - Revision count
  - Click to view details

**Empty State:**
- Friendly message when no tasks
- Helpful suggestions
- Create task button (if manager)

### Audit Dashboard (Auditors)

**Key Features:**
- Focused on audit tasks only
- Pending audits highlighted
- Quick access to review
- Audit-specific statistics

**Task Display:**
- Task title and status
- Assignee information
- Completion date
- Revision history
- Review button

---

## Security Features

### Authentication
- **No Self-Signup**: Users pre-created by admin
- **Secure Login**: Username/password authentication
- **Session Management**: Flask-Login integration
- **Password Requirements**: Minimum 8 characters
- **Hash Algorithm**: PBKDF2 with SHA256
- **Salt**: Unique per password

### Authorization
- **Role-Based Access**: 4 distinct roles
- **Route Protection**: @login_required decorators
- **Action Validation**: Permission checks before operations
- **Data Isolation**: Users see only relevant data

### Data Protection
- **CSRF Tokens**: On all forms
- **XSS Prevention**: Jinja2 auto-escaping
- **SQL Injection**: SQLAlchemy ORM
- **Session Security**: HTTPOnly, Secure cookies
- **Environment Secrets**: .env for sensitive data

### Production Security
- **HTTPS Ready**: Cloud Run automatic SSL
- **Secret Manager**: GCP secrets integration
- **Database Encryption**: Cloud SQL encryption
- **Audit Logging**: Complete activity trail
- **Non-Root Container**: Docker security best practice

---

## UI/UX Features

### Design System

**Color Palette:**
- Primary: Blue (tasks, actions)
- Success: Green (completed, passed)
- Warning: Yellow (under audit)
- Danger: Red (failed, errors)
- Neutral: Gray (assigned, inactive)

**Status Badges:**
- Color-coded by status
- Rounded pill design
- Consistent sizing
- Readable text

**Cards:**
- Clean white background
- Subtle shadows
- Hover effects
- Rounded corners

### Responsive Design

**Breakpoints:**
- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px

**Mobile Optimizations:**
- Collapsible navigation
- Stack card layouts
- Touch-friendly buttons
- Readable font sizes

### Interactive Elements

**Buttons:**
- Clear action labels
- Loading states ready
- Hover animations
- Focus indicators

**Forms:**
- Inline validation
- Error messages
- Field hints
- Required indicators

**Navigation:**
- Role-based menu items
- Active page highlighting
- Breadcrumbs on details
- Back buttons

### Animations

**Page Transitions:**
- Fade-in on load
- Smooth page changes

**Interactions:**
- Button hover effects
- Card hover lift
- Alert slide-in
- Smooth scrolling

**Feedback:**
- Flash messages
- Success confirmations
- Error notifications
- Info alerts

### Accessibility

**Features:**
- Semantic HTML
- ARIA labels ready
- Keyboard navigation
- Focus indicators
- Color contrast compliance

---

## Advanced Features

### Pagination
- 10 items per page (configurable)
- Previous/Next navigation
- Page number display
- Maintains filters
- URL state preservation

### Search & Filter
- Status-based filtering
- Role-specific views
- Filter persistence
- Quick filter buttons

### Data Display
- Sortable columns (ready)
- Data tables
- List views
- Card views
- Empty states

### User Experience
- Intuitive workflows
- Consistent patterns
- Clear call-to-actions
- Helpful error messages
- Contextual help

---

## Tips & Best Practices

### For Managers
1. Write clear task descriptions
2. Set realistic due dates
3. Assign to appropriate users
4. Monitor task progress regularly
5. Use cancellation sparingly

### For Assignees
1. Start tasks promptly
2. Add notes when completing
3. Review audit feedback carefully
4. Communicate issues
5. Track your progress

### For Auditors
1. Review work thoroughly
2. Provide clear feedback
3. Be specific in audit notes
4. Be fair and consistent
5. Approve quality work promptly

### For Admins
1. Create users with appropriate roles
2. Monitor system usage
3. Deactivate inactive users
4. Review audit metrics
5. Maintain user balance

---

## Future Enhancements

Planned features for future releases:

- [ ] Email notifications
- [ ] File attachments on tasks
- [ ] Task comments/discussion
- [ ] Advanced search
- [ ] Export reports (PDF, Excel)
- [ ] Task templates
- [ ] Calendar view
- [ ] Time tracking
- [ ] Task dependencies
- [ ] Bulk operations
- [ ] REST API
- [ ] WebSocket updates
- [ ] Mobile app (PWA)
- [ ] Dashboard customization
- [ ] Custom fields
- [ ] Workflow builder

---

## Getting Help

- Read this feature guide
- Check QUICKSTART.md
- Review DEPLOYMENT.md
- Examine code comments
- Test in demo environment

---

**Enjoy using TaskFlow CRM!** 🚀
