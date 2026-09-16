"""Create the first admin so somebody can sign in.

    python scripts/bootstrap_admin.py sourabh@gempundit.com "Sourabh Singh"

Needs the same BigQuery credentials as the app (GOOGLE_APPLICATION_CREDENTIALS_JSON
or an authenticated gcloud session).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    email = sys.argv[1].strip().lower()
    name = sys.argv[2] if len(sys.argv) > 2 else email.split('@')[0]

    app = create_app()
    with app.app_context():
        store = app.extensions['store']
        existing = store.user_by_email(email)
        store.save_user(username=name, email=email, role='admin', is_active=True,
                        user_id=existing.id if existing else None)
        print(f'{email} is now an admin.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
