import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS quizzes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    slug          TEXT UNIQUE NOT NULL,
    title_ar      TEXT NOT NULL,
    pdf_filename  TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS questions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id       INTEGER NOT NULL REFERENCES quizzes(id),
    type          TEXT NOT NULL,
    prompt_ar     TEXT NOT NULL,
    base_points   INTEGER NOT NULL DEFAULT 100,
    explanation_ar TEXT NOT NULL DEFAULT '',
    source_page   INTEGER,
    data_json     TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS assets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id      INTEGER NOT NULL REFERENCES quizzes(id),
    question_id  INTEGER REFERENCES questions(id),
    file_path    TEXT NOT NULL,
    kind         TEXT NOT NULL DEFAULT 'image',
    source_url   TEXT NOT NULL DEFAULT '',
    anonymized   INTEGER NOT NULL DEFAULT 0,
    caption_ar   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS contestants (
    telegram_user_id INTEGER PRIMARY KEY,
    first_name       TEXT NOT NULL DEFAULT '',
    username         TEXT,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attempts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    contestant_id    INTEGER NOT NULL REFERENCES contestants(telegram_user_id),
    quiz_id          INTEGER NOT NULL REFERENCES quizzes(id),
    mode             TEXT NOT NULL DEFAULT 'async',
    total_score      INTEGER NOT NULL DEFAULT 0,
    accuracy         REAL NOT NULL DEFAULT 0,
    duration_ms      INTEGER NOT NULL DEFAULT 0,
    max_streak       INTEGER NOT NULL DEFAULT 0,
    started_at       TEXT,
    finished_at      TEXT
);

CREATE TABLE IF NOT EXISTS answers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id    INTEGER NOT NULL REFERENCES attempts(id),
    question_id   INTEGER NOT NULL REFERENCES questions(id),
    given_json    TEXT NOT NULL,
    is_correct    INTEGER NOT NULL,
    time_ms       INTEGER NOT NULL,
    points_awarded INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS badges (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    contestant_id INTEGER NOT NULL REFERENCES contestants(telegram_user_id),
    code          TEXT NOT NULL,
    earned_at     TEXT NOT NULL,
    UNIQUE(contestant_id, code)
);
"""


def connect(db_path: str) -> sqlite3.Connection:
    # check_same_thread=False: the app holds one shared connection that the
    # web framework reuses across request worker threads.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
