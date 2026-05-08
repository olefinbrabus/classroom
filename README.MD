# Classroom

Classroom is a FastAPI LMS backend for courses, lessons, materials, assignments,
submissions, grades, announcements, and user access management.

## Stack

- Python 3.13
- FastAPI
- FastAPI Users
- SQLAlchemy async
- SQLite for local development
- Alembic
- Pydantic
- Starlette Admin
- Pytest

## Install

```bash
git clone https://github.com/olefinbrabus/classroom
cd Classroom
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Database

The local database defaults to:

```text
classroom_database.db
```

The path is resolved from the project root, not from the current working
directory. For tests or temporary runs, override it with:

```bash
CLASSROOM_DATABASE_PATH=/tmp/classroom.db
```

Run migrations:

```bash
PYTHONPATH=. .venv/bin/alembic upgrade head
```

## Dev Seed

Reset and seed the local development database:

```bash
PYTHONPATH=. .venv/bin/python -m scripts.dev_seed --reset
```

Seeded users:

```text
Teacher/admin: admin@admin.com / Administrate_12345
Student:       student@example.com / Student_12345
Outsider:      outsider@example.com / Outsider_12345
```

Stable seed ids:

```text
course=1
lesson=1
assignment=1
submission=1
```

## Run

```bash
PYTHONPATH=. .venv/bin/uvicorn main:app --reload
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## File Uploads

Uploaded files are stored on disk and referenced from the database by metadata.
The default upload root is:

```text
uploads/
```

Override it for local experiments or tests with:

```bash
CLASSROOM_UPLOAD_ROOT=/tmp/classroom-uploads
```

The upload endpoint is:

```text
POST /classroom/files/upload/
```

Use `multipart/form-data` with a `file` field. Admin file preview reads from the
stored file path first, with database binary content kept only as a fallback for
development records.

## Admin Panel

Starlette Admin is mounted at:

```text
http://127.0.0.1:8000/admin
```

Only active superusers can log in. Use the seeded admin account after running
the dev seed command:

```text
admin@admin.com / Administrate_12345
```

The admin panel exposes the main LMS models:

- Users
- Courses
- Enrollments
- Lessons
- Materials
- Assignments
- Submissions
- Grades
- Uploaded files
- Announcements

Safety rules:

- Users cannot be created or deleted from the admin panel, so password hashing
  stays under `fastapi-users`.
- Duplicate enrollments and duplicate submissions are rejected.
- Assignment max score and grade score are validated.
- Admin access is separate from regular LMS student/teacher access and requires
  `is_superuser=true`.

## Manual HTTP Checks

Use `test_main.http` in JetBrains HTTP Client.

Recommended flow:

```bash
PYTHONPATH=. .venv/bin/python -m scripts.dev_seed --reset
PYTHONPATH=. .venv/bin/uvicorn main:app --reload
```

Then run the request groups in `test_main.http`.

## Tests

```bash
PYTHONPATH=. .venv/bin/pytest -q
```
