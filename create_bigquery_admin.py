import getpass
import os
from datetime import datetime

from google.cloud import bigquery
from werkzeug.security import generate_password_hash


PROJECT = os.environ.get('BIGQUERY_PROJECT', 'mis-gempundit')
DATASET = os.environ.get('BIGQUERY_DATASET', 'Content_FMS')


def main():
    username = input('Admin username: ').strip()
    email = input('Admin email: ').strip()
    password = getpass.getpass('Admin password: ')
    if not username or not email or not password:
        raise SystemExit('Username, email, and password are required.')

    client = bigquery.Client(project=PROJECT)
    now = datetime.utcnow().isoformat()
    row = {
        'user_id': int(datetime.utcnow().timestamp() * 1000),
        'username': username,
        'email': email,
        'password_hash': generate_password_hash(password, method='pbkdf2:sha256'),
        'role': 'admin',
        'is_active': True,
        'created_at': now,
        'updated_at': now,
    }
    table = f'{PROJECT}.{DATASET}.Users'
    errors = client.insert_rows_json(table, [row])
    if errors:
        raise SystemExit(f'BigQuery insert failed: {errors}')
    print(f'Admin {username!r} created in {table}.')


if __name__ == '__main__':
    main()