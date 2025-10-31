import os
from app import create_app, db
from app.models import User, Task, TaskLog

app = create_app(os.getenv('FLASK_ENV') or 'production')

@app.shell_context_processor
def make_shell_context():
    """Make database models available in Flask shell"""
    return {
        'db': db,
        'User': User,
        'Task': Task,
        'TaskLog': TaskLog
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
