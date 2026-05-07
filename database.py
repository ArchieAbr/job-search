import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")


def get_connection(db_path=None):
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=None):
    conn = get_connection(db_path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS searches (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            query            TEXT NOT NULL,
            location         TEXT,
            job_type         TEXT,
            experience_level TEXT,
            is_remote        INTEGER DEFAULT 0,
            date_run         TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            search_id           INTEGER REFERENCES searches(id),
            title               TEXT,
            company             TEXT,
            location            TEXT,
            salary_min          REAL,
            salary_max          REAL,
            salary_interval     TEXT,
            job_type            TEXT,
            description_snippet TEXT,
            url                 TEXT UNIQUE,
            site                TEXT,
            date_posted         TEXT,
            date_scraped        TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


def insert_search(query, location, job_type, experience_level, is_remote, db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO searches (query, location, job_type, experience_level, is_remote, date_run)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            query,
            location,
            job_type,
            experience_level,
            1 if is_remote else 0,
            datetime.utcnow().isoformat(),
        ),
    )
    search_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return search_id


def insert_jobs(search_id, jobs, db_path=None):
    """Insert jobs, skipping duplicates by URL.

    Returns:
        tuple: (inserted_count, skipped_count)
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
    now = datetime.utcnow().isoformat()

    for job in jobs:
        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO jobs
                    (search_id, title, company, location, salary_min, salary_max,
                     salary_interval, job_type, description_snippet, url, site,
                     date_posted, date_scraped)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    search_id,
                    job.get("title"),
                    job.get("company"),
                    job.get("location"),
                    job.get("salary_min"),
                    job.get("salary_max"),
                    job.get("salary_interval"),
                    job.get("job_type"),
                    job.get("description_snippet"),
                    job.get("url"),
                    job.get("site"),
                    job.get("date_posted"),
                    now,
                ),
            )
            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except sqlite3.Error:
            skipped += 1

    conn.commit()
    conn.close()
    return inserted, skipped


def get_jobs(filters=None, db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    sql = "SELECT * FROM jobs"
    params = []
    clauses = []

    if filters:
        if filters.get("site"):
            clauses.append("site = ?")
            params.append(filters["site"])
        if filters.get("job_type"):
            clauses.append("job_type = ?")
            params.append(filters["job_type"])
        if filters.get("search_id"):
            clauses.append("search_id = ?")
            params.append(filters["search_id"])

    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY date_scraped DESC"

    cursor.execute(sql, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_job(job_id, db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_job(job_id, db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted > 0


def get_searches(db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM searches ORDER BY date_run DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def delete_search(search_id, db_path=None):
    """Delete a search and all its associated jobs."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE search_id = ?", (search_id,))
    cursor.execute("DELETE FROM searches WHERE id = ?", (search_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted > 0


def delete_all_searches(db_path=None):
    """Delete every search and every job."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs")
    cursor.execute("DELETE FROM searches")
    conn.commit()
    conn.close()
