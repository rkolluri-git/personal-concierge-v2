"""Smoke-test a built image against disposable PostgreSQL; no host ports or volumes.

Run: python3 tools/validate_container.py
Build first: docker build -t personal-concierge-v2:validation .
"""
import secrets
import subprocess
import time
from uuid import uuid4


def docker(*args, **kwargs):
    return subprocess.run(['docker', *args], check=True, text=True, **kwargs)


def main():
    suffix = uuid4().hex[:12]
    network = 'concierge-validation-' + suffix
    database = network + '-db'
    application = network + '-app'
    password = secrets.token_hex(24)
    network_created = False
    db_created = False
    try:
        docker('network', 'create', network, capture_output=True)
        network_created = True
        docker('run', '-d', '--name', database, '--network', network,
               '-e', 'POSTGRES_PASSWORD=' + password, '-e', 'POSTGRES_DB=concierge',
               'postgres:16', capture_output=True)
        db_created = True
        for attempt in range(60):
            ready = subprocess.run(['docker', 'exec', database, 'pg_isready', '-U', 'postgres'],
                                   capture_output=True)
            if ready.returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError('Disposable PostgreSQL did not become ready')
        code = '''
from fastapi.testclient import TestClient
from main import app
from access_control import access_key
# Enter twice to validate idempotent startup against an existing schema.
for run in range(2):
    with TestClient(app) as client:
        assert client.get('/health').status_code == 200
        assert client.get('/family-members').status_code == 401
        headers = {'Authorization': 'Bearer ' + access_key()}
        assert client.get('/settings/regional', headers=headers).json()['school_calendar'] == 'none'
        if run == 0:
            result = client.post('/family-members', headers=headers,
                                 json={'name': 'Example Adult', 'role': 'adult', 'age': 30})
            assert result.status_code == 201, result.text
            assert result.json()['age'] == 30
        members = client.get('/family-members', headers=headers).json()
        assert len(members) == 1 and members[0]['name'] == 'Example Adult'
print('PostgreSQL startup/restart, health, authentication, regional defaults, and encrypted member round-trip passed.')
'''
        docker('run', '--rm', '--name', application, '--network', network,
               '-e', f'DATABASE_URL=postgresql://postgres:{password}@{database}:5432/concierge',
               '-e', 'FAMILY_CONFIG_DIR=/tmp/concierge-config',
               'personal-concierge-v2:validation', 'python', '-c', code)
    finally:
        # Only remove the randomly named resources created by this run.
        subprocess.run(['docker', 'rm', '-f', application], capture_output=True)
        if db_created:
            subprocess.run(['docker', 'rm', '-f', '-v', database], check=True, capture_output=True)
        if network_created:
            docker('network', 'rm', network, capture_output=True)


if __name__ == '__main__':
    main()
