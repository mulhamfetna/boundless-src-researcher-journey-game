"""`python -m app.migrate` must work against a brand-new database.

A first deploy starts from an empty Docker volume, so the deploy job runs
migrate before any schema exists. migrate() itself assumes the tables are
there (it ALTERs `attempts`), so main() creates the schema first. Without
that, the very first deploy fails with "no such table: attempts".
"""
import subprocess
import sys


def test_migrate_module_succeeds_on_an_empty_database(tmp_path):
    db = tmp_path / "fresh.db"
    result = subprocess.run(
        [sys.executable, "-m", "app.migrate"],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "QUIZ_DB_PATH": str(db), "PYTHONPATH": "."},
    )
    assert result.returncode == 0, f"migrate failed on a fresh DB:\n{result.stderr}"
    assert db.exists()


def test_migrate_is_idempotent_when_run_twice(tmp_path):
    db = tmp_path / "twice.db"
    env = {"PATH": "/usr/bin:/bin", "QUIZ_DB_PATH": str(db), "PYTHONPATH": "."}
    first = subprocess.run(
        [sys.executable, "-m", "app.migrate"], capture_output=True, text=True, env=env
    )
    second = subprocess.run(
        [sys.executable, "-m", "app.migrate"], capture_output=True, text=True, env=env
    )
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert "already current" in second.stdout
