# TaskFlow CRM - Task Assignment & Audit System

A comprehensive Flask-based CRM system for managing task assignments with a full audit workflow. Features a beautiful, responsive UI built with Tailwind CSS and ready for production deployment on Google Cloud Platform.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38bdf8)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

### Core Functionality
- **User Authentication**: Secure login system with Flask-Login (no self-signup)
- **Role-Based Access Control**: Four user roles with distinct permissions
  - **Admin**: Full system access and user management
  - **Manager**: Create and manage tasks, view all tasks
  - **Auditor**: Review and approve/reject completed tasks
  - **Assignee**: Work on assigned tasks

### Task Management
- **FSM Workflow**: Finite State Machine for task lifecycle
  - Assigned → In Progress → Completed → Under Audit → Passed/Failed
- **Automatic Auditor Assignment**: Random auditor allocation on task completion
- **Revision Tracking**: Count and manage failed audit revisions
- **Comprehensive Audit Trail**: Detailed logs of all status changes

### User Interface
- **Beautiful Dashboard**: Modern, responsive design with Tailwind CSS
- **Real-time Statistics**: Visual metrics and progress indicators
- **Dynamic Forms**: Client-side validation with Alpine.js
- **Mobile Responsive**: Works seamlessly on all devices
- **Intuitive Navigation**: Role-specific menus and actions

### Technical Features
- **Database Flexibility**: SQLite for development, PostgreSQL for production
- **Database Migrations**: Managed with Flask-Migrate
- **Security**: PBKDF2 password hashing, CSRF protection
- **Docker Ready**: Multi-stage builds with non-root user
- **Cloud Deployment**: Complete GCP integration with Cloud Run and Cloud SQL

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd content_approval_fms
   ```

2. **Set up environment**
   ```bash
   python -m venv crm_env
   source crm_env/bin/activate  # On Windows: .\crm_env\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install Node dependencies and build CSS**
   ```bash
   npm install
   npm run build:css
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize database**
   ```bash
   flask db upgrade
   python seed_data.py  # Optional: Creates demo users
   ```

6. **Run the application**
   ```bash
   flask run
   ```

7. **Access the application**
   Open http://localhost:5000

### Demo Credentials
After running `seed_data.py`:
- **Admin**: `admin` / `admin123`
- **Manager**: `manager` / `manager123`
- **Auditor**: `auditor` / `auditor123`
- **Assignee**: `user` / `user123`

## Project Structure

```
content_approval_fms/
├── app/
│   ├── __init__.py           # Application factory
│   ├── models.py             # Database models (User, Task, TaskLog)
│   ├── routes.py             # Application routes/views
│   ├── forms.py              # WTForms definitions
│   ├── templates/            # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── create_task.html
│   │   ├── task_detail.html
│   │   ├── audit_dashboard.html
│   │   ├── users.html
│   │   └── create_user.html
│   └── static/
│       ├── src/
│       │   └── input.css     # Tailwind source
│       └── css/
│           └── output.css    # Compiled CSS
├── migrations/               # Database migrations
├── config.py                 # Configuration settings
├── run.py                    # Application entry point
├── seed_data.py             # Database seeding script
├── requirements.txt         # Python dependencies
├── package.json            # Node.js dependencies
├── tailwind.config.js      # Tailwind configuration
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose setup
├── cloudbuild.yaml         # GCP Cloud Build config
├── .env.example            # Environment variables template
└── README.md              # This file
```

## Database Models

### User Model
```python
- id: Primary key
- username: Unique username
- email: Unique email address
- password_hash: PBKDF2 hashed password
- role: admin, manager, auditor, assignee
- is_active: Account status
- created_at, updated_at: Timestamps
```

### Task Model
```python
- id: Primary key
- title: Task title
- description: Detailed description
- created_by_id: Creator (Manager/Admin)
- assigned_to_id: Assignee
- auditor_id: Auto-assigned auditor
- plan_date: Target completion date
- completed_date: Actual completion timestamp
- audit_date: Audit completion timestamp
- revision_count: Number of failed audits
- audit_notes: Auditor feedback
- status: FSM state
- created_at, updated_at: Timestamps
```

### TaskLog Model
```python
- id: Primary key
- task_id: Related task
- user_id: User who performed action
- action: Description of action
- previous_status: State before change
- new_status: State after change
- notes: Additional comments
- timestamp: Action timestamp
```

## FSM Workflow

```
┌─────────┐
│ ASSIGNED│
└────┬────┘
     │
     ▼
┌────────────┐
│IN PROGRESS │
└─────┬──────┘
      │
      ▼
┌──────────┐
│COMPLETED │
└────┬─────┘
     │ (Auto-assign auditor)
     ▼
┌────────────┐       ┌─────────────┐
│UNDER AUDIT │──────▶│ AUDIT PASSED│
└─────┬──────┘       └─────────────┘
      │
      ▼
┌─────────────┐
│ AUDIT FAILED│─────┐
└─────────────┘     │
                    │ (revision_count++)
                    │
                    ▼
              ┌────────────┐
              │IN PROGRESS │
              └────────────┘

(Managers can cancel tasks at any stage)
```

## API Routes

| Route | Method | Description | Access |
|-------|--------|-------------|--------|
| `/` | GET | Redirect to dashboard or login | Public |
| `/login` | GET, POST | User login | Public |
| `/logout` | GET | User logout | Authenticated |
| `/dashboard` | GET | Main task dashboard | Authenticated |
| `/create-task` | GET, POST | Create new task | Manager, Admin |
| `/task/<id>` | GET, POST | Task detail and actions | Task participants |
| `/audit-dashboard` | GET | Auditor dashboard | Auditor, Manager, Admin |
| `/users` | GET | User management | Admin |
| `/create-user` | GET, POST | Create new user | Admin |
| `/user/<id>/toggle-status` | POST | Activate/deactivate user | Admin |

## Development

### Watch Tailwind CSS Changes
```bash
npm run watch:css
```

### Database Migrations
```bash
# Create migration
flask db migrate -m "Description"

# Apply migration
flask db upgrade

# Rollback migration
flask db downgrade
```

### Running Tests
```bash
# Add your test commands here
pytest
```

## Docker Deployment

### Using Docker Compose
```bash
# Build and start
docker-compose up --build

# Stop
docker-compose down

# View logs
docker-compose logs -f web
```

### Standalone Docker
```bash
# Build image
docker build -t flask-crm:latest .

# Run container
docker run -d -p 5000:8080 \
  -e SECRET_KEY=your-key \
  -e DATABASE_URL=sqlite:///crm.db \
  flask-crm:latest
```

## Google Cloud Deployment

Comprehensive deployment guide available in [DEPLOYMENT.md](DEPLOYMENT.md)

### Quick Deploy
```bash
# Set project
export PROJECT_ID=your-project-id
gcloud config set project $PROJECT_ID

# Build and deploy
gcloud builds submit --config cloudbuild.yaml
```

## Configuration

### Environment Variables
See `.env.example` for all available configuration options.

### Key Settings
- `SECRET_KEY`: Flask secret key (change in production!)
- `DATABASE_URL`: Database connection string
- `FLASK_ENV`: `development` or `production`

## Security Considerations

1. **Password Security**: PBKDF2 hashing with salt
2. **CSRF Protection**: Enabled on all forms
3. **Session Security**: HTTPOnly, Secure cookies in production
4. **SQL Injection**: Protected by SQLAlchemy ORM
5. **XSS Protection**: Jinja2 auto-escaping

## Performance Optimization

- **Database Indexing**: Applied on frequently queried fields
- **Query Optimization**: Eager loading for relationships
- **Static Asset Caching**: Configured cache headers
- **Connection Pooling**: For production databases
- **Gunicorn Workers**: Multiple worker processes

## Browser Support

- Chrome/Edge (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Roadmap

- [ ] Email notifications for task assignments and audits
- [ ] Task comments and attachments
- [ ] Advanced filtering and search
- [ ] Export tasks to PDF/Excel
- [ ] Task templates
- [ ] Calendar view for planned dates
- [ ] Mobile app (PWA)
- [ ] REST API for third-party integrations
- [ ] Real-time updates with WebSockets
- [ ] Performance analytics dashboard

## Troubleshooting

See [DEPLOYMENT.md](DEPLOYMENT.md#troubleshooting) for common issues and solutions.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Flask framework and ecosystem
- Tailwind CSS for beautiful styling
- Alpine.js for reactive components
- Google Cloud Platform for hosting

## Support

For support, please:
1. Check the [DEPLOYMENT.md](DEPLOYMENT.md) guide
2. Review closed issues on GitHub
3. Open a new issue with detailed information

---

**Built with ❤️ using Flask, Tailwind CSS, and modern web technologies**

**Author**: Your Name
**Version**: 1.0.0
**Last Updated**: 2024
