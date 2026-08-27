"""Local development entrypoint.

Start PostgreSQL first:

    docker compose up -d postgres

Then:

    .venv\\Scripts\\activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8000

API docs: http://localhost:8000/api/docs

Demo users (same passwords as the Angular login hint):
- admin@demo-business.com / admin123
- manager@demo-business.com / manager123
- finance@demo-business.com / finance123
- operator@demo-business.com / operator123
- viewer@demo-business.com / viewer123

Organization id in JWT: 00000000-0000-0000-0000-000000000001
"""
