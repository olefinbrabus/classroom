import os
import sqlite3
import subprocess
import sys


def test_dev_seed_reset_creates_stable_manual_test_data(tmp_path):
    database_path = tmp_path / "seed.db"
    env = {
        **os.environ,
        "PYTHONPATH": ".",
        "CLASSROOM_DATABASE_PATH": str(database_path),
    }

    result = subprocess.run(
        [sys.executable, "-m", "scripts.dev_seed", "--reset"],
        cwd=os.getcwd(),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout

    connection = sqlite3.connect(database_path)
    try:
        users = connection.execute(
            "SELECT id, email, is_superuser, is_teacher FROM classroom_user ORDER BY id"
        ).fetchall()
        courses = connection.execute("SELECT id, title FROM course").fetchall()
        enrollments = connection.execute(
            "SELECT course_id, user_id, role, status FROM enrollment ORDER BY id"
        ).fetchall()
        lessons = connection.execute(
            "SELECT id, title, is_published FROM lesson ORDER BY id"
        ).fetchall()
        assignments = connection.execute(
            "SELECT id, lesson_id, is_published FROM assignment"
        ).fetchall()
        submissions = connection.execute(
            "SELECT id, assignment_id, student_id, status FROM submission"
        ).fetchall()
        alembic_version = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
    finally:
        connection.close()

    assert users == [
        (1, "admin@admin.com", 1, 1),
        (2, "student@example.com", 0, 0),
        (3, "outsider@example.com", 0, 0),
    ]
    assert courses == [(1, "Seeded LMS Course")]
    assert enrollments == [
        (1, 1, "TEACHER", "ACTIVE"),
        (1, 2, "STUDENT", "ACTIVE"),
    ]
    assert lessons == [
        (1, "Seeded published lesson", 1),
        (2, "Seeded draft lesson", 0),
    ]
    assert assignments == [(1, 1, 1)]
    assert submissions == [(1, 1, 2, "SUBMITTED")]
    assert alembic_version == ("20260501_remove_class",)
