import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS quizzes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    slug          TEXT UNIQUE NOT NULL,
    title_ar      TEXT NOT NULL,
    pdf_filename  TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    fun_facts_json TEXT NOT NULL DEFAULT '[]'
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
    points_awarded INTEGER NOT NULL,
    retries        INTEGER NOT NULL DEFAULT 0,
    hint_used      INTEGER NOT NULL DEFAULT 0,
    -- The learner moved on without solving it (issue #29): zero points, breaks
    -- the streak, and the report shows it as not answered correctly.
    skipped        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS badges (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    contestant_id INTEGER NOT NULL REFERENCES contestants(telegram_user_id),
    code          TEXT NOT NULL,
    earned_at     TEXT NOT NULL,
    UNIQUE(contestant_id, code)
);

CREATE TABLE IF NOT EXISTS issue_reports (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id   INTEGER,
    username           TEXT,
    first_name         TEXT,
    last_name          TEXT,
    language_code      TEXT,
    is_premium         INTEGER,
    allows_write_to_pm INTEGER,
    auth_date          TEXT,
    chat_type          TEXT,
    chat_instance      TEXT,
    query_id           TEXT,
    start_param        TEXT,
    platform           TEXT,
    app_version        TEXT,
    text               TEXT NOT NULL,
    raw_json           TEXT,
    created_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS duels (
    token            TEXT PRIMARY KEY,
    question_id      INTEGER NOT NULL,
    creator_id       INTEGER NOT NULL,
    creator_correct  INTEGER NOT NULL,
    creator_time_ms  INTEGER NOT NULL,
    opponent_id      INTEGER,
    opponent_correct INTEGER,
    opponent_time_ms INTEGER,
    status           TEXT NOT NULL DEFAULT 'open',
    created_at       TEXT NOT NULL
);
-- Small key/value store. Holds `content_sha:<slug>` so a deploy reseeds only
-- the quizzes whose JSON changed (reseeding deletes that quiz's attempts).
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
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
