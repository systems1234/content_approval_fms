# Quick Start Guide - TaskFlow CRM

Get your TaskFlow CRM up and running in 5 minutes!

## Method 1: Automated Setup (Recommended)

### Windows
1. Open Command Prompt or PowerShell
2. Navigate to project directory
3. Run:
   ```bash
   setup.bat
   ```

### Linux/Mac
1. Open Terminal
2. Navigate to project directory
3. Make script executable and run:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

### After Automated Setup
```bash
# Seed demo data (optional but recommended)
python seed_data.py

# Start the application
flask run
```

Visit: http://localhost:5000

---

## Method 2: Manual Setup

### Step 1: Environment Setup
```bash
# Create virtual environment
python -m venv crm_env

# Activate it
# Windows:
crm_env\Scripts\activate
# Linux/Mac:
source crm_env/bin/activate
```

### Step 2: Install Dependencies
```bash
# Python packages
pip install -r requirements.txt

# Node.js packages
npm install

# Build Tailwind CSS
npm run build:css
```

### Step 3: Database Setup
```bash
# Initialize migrations
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Seed demo data (optional)
python seed_data.py
```

### Step 4: Run Application
```bash
flask run
```

Open http://localhost:5000 in your browser

---

## Method 3: Docker (No Local Setup Required)

### Using Docker Compose
```bash
# Start everything
docker-compose up --build

# Application runs on http://localhost:5000
```

### Using Docker Only
```bash
# Build image
docker build -t flask-crm:latest .

# Run container
docker run -d -p 5000:8080 \
  -e SECRET_KEY=your-secret-key \
  -e DATABASE_URL=sqlite:///crm.db \
  flask-crm:latest
```

---

## Demo Credentials

After running `seed_data.py`, use these credentials:

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Manager | `manager` | `manager123` |
| Auditor | `auditor` | `auditor123` |
| Assignee | `user` | `user123` |

---

## First Steps After Login

### As Admin
1. Navigate to **Users** from the top menu
2. Create additional users as needed
3. View all tasks and system overview

### As Manager
1. Click **Create New Task** button
2. Fill in task details and assign to a user
3. Monitor task progress on the dashboard

### As Assignee
1. View tasks assigned to you on the dashboard
2. Click a task to view details
3. Start working and update task status

### As Auditor
1. Navigate to **Audit Dashboard**
2. Review tasks pending audit
3. Approve or reject completed work

---

## Task Workflow Example

1. **Manager creates task** → Status: `Assigned`
2. **Assignee starts work** → Status: `In Progress`
3. **Assignee completes task** → Status: `Completed` (auto-moves to `Under Audit`)
4. **Auditor reviews** → Status: `Audit Passed` or `Audit Failed`
   - If failed: Returns to `In Progress` for revision

---

## Troubleshooting

### Port Already in Use
```bash
# Change port in run command
flask run --port 5001
```

### CSS Not Loading
```bash
# Rebuild Tailwind CSS
npm run build:css
```

### Database Errors
```bash
# Reset database
rm crm.db
flask db upgrade
python seed_data.py
```

### Module Not Found Errors
```bash
# Ensure virtual environment is activated
# Reinstall dependencies
pip install -r requirements.txt
```

---

## Development Tips

### Watch CSS Changes (for development)
```bash
npm run watch:css
```

### Enable Debug Mode
In `.env`:
```env
FLASK_ENV=development
```

### View Database
```bash
# Using Flask shell
flask shell
>>> from app.models import User, Task
>>> User.query.all()
>>> Task.query.all()
```

---

## Next Steps

- Read [README_UPDATED.md](README_UPDATED.md) for detailed features
- Check [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- Customize templates in `app/templates/`
- Modify styles in `app/static/src/input.css`

---

## Getting Help

- Check existing documentation files
- Review error messages in terminal
- Check browser console for frontend issues
- Ensure all dependencies are installed

---

**Happy Task Managing! 🚀**
