"""Unit tests for database.py — uses an in-memory SQLite DB to avoid touching jobs.db."""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import database


# ---------------------------------------------------------------------------
# Fixture: a fresh temp database for each test
# ---------------------------------------------------------------------------
@pytest.fixture
def db(tmp_path):
    db_file = str(tmp_path / "test.db")
    database.init_db(db_path=db_file)
    return db_file


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
def test_init_creates_tables(db):
    conn = database.get_connection(db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()
    assert "searches" in tables
    assert "jobs" in tables


# ---------------------------------------------------------------------------
# Searches
# ---------------------------------------------------------------------------
def test_insert_and_get_search(db):
    search_id = database.insert_search("python developer", "London", "fulltime", "senior", False, db_path=db)
    assert isinstance(search_id, int)
    searches = database.get_searches(db_path=db)
    assert len(searches) == 1
    s = searches[0]
    assert s["query"] == "python developer"
    assert s["location"] == "London"
    assert s["job_type"] == "fulltime"
    assert s["experience_level"] == "senior"
    assert s["is_remote"] == 0


def test_multiple_searches(db):
    database.insert_search("engineer", "London", None, None, False, db_path=db)
    database.insert_search("designer", "Manchester", None, None, True, db_path=db)
    searches = database.get_searches(db_path=db)
    assert len(searches) == 2
    # Most recent first
    assert searches[0]["query"] == "designer"


# ---------------------------------------------------------------------------
# Jobs: insert & query
# ---------------------------------------------------------------------------
SAMPLE_JOB = {
    "title": "Software Engineer",
    "company": "Acme Corp",
    "location": "London",
    "salary_min": 50000.0,
    "salary_max": 70000.0,
    "salary_interval": "yearly",
    "job_type": "fulltime",
    "description_snippet": "A great role for a software engineer.",
    "url": "https://example.com/job/1",
    "site": "indeed",
    "date_posted": "2024-01-15",
}


def test_insert_job_and_retrieve(db):
    search_id = database.insert_search("engineer", "London", None, None, False, db_path=db)
    inserted, skipped = database.insert_jobs(search_id, [SAMPLE_JOB], db_path=db)

    assert inserted == 1
    assert skipped == 0

    jobs = database.get_jobs(db_path=db)
    assert len(jobs) == 1
    j = jobs[0]
    assert j["title"] == "Software Engineer"
    assert j["company"] == "Acme Corp"
    assert j["salary_min"] == 50000.0
    assert j["site"] == "indeed"


def test_get_job_by_id(db):
    search_id = database.insert_search("engineer", "London", None, None, False, db_path=db)
    database.insert_jobs(search_id, [SAMPLE_JOB], db_path=db)

    jobs = database.get_jobs(db_path=db)
    job_id = jobs[0]["id"]

    job = database.get_job(job_id, db_path=db)
    assert job is not None
    assert job["title"] == "Software Engineer"


def test_get_job_not_found(db):
    assert database.get_job(9999, db_path=db) is None


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------
def test_duplicate_url_is_skipped(db):
    search_id = database.insert_search("engineer", "London", None, None, False, db_path=db)

    inserted1, skipped1 = database.insert_jobs(search_id, [SAMPLE_JOB], db_path=db)
    inserted2, skipped2 = database.insert_jobs(search_id, [SAMPLE_JOB], db_path=db)

    assert inserted1 == 1 and skipped1 == 0
    assert inserted2 == 0 and skipped2 == 1
    assert len(database.get_jobs(db_path=db)) == 1


def test_different_urls_both_inserted(db):
    search_id = database.insert_search("engineer", "London", None, None, False, db_path=db)
    job2 = {**SAMPLE_JOB, "url": "https://example.com/job/2", "title": "Backend Engineer"}
    inserted, skipped = database.insert_jobs(search_id, [SAMPLE_JOB, job2], db_path=db)
    assert inserted == 2
    assert skipped == 0


# ---------------------------------------------------------------------------
# Filters on get_jobs
# ---------------------------------------------------------------------------
def test_filter_by_site(db):
    search_id = database.insert_search("dev", "", None, None, False, db_path=db)
    li_job = {**SAMPLE_JOB, "url": "https://linkedin.com/job/1", "site": "linkedin"}
    database.insert_jobs(search_id, [SAMPLE_JOB, li_job], db_path=db)

    indeed_jobs = database.get_jobs(filters={"site": "indeed"}, db_path=db)
    assert len(indeed_jobs) == 1
    assert indeed_jobs[0]["site"] == "indeed"

    linkedin_jobs = database.get_jobs(filters={"site": "linkedin"}, db_path=db)
    assert len(linkedin_jobs) == 1


def test_filter_by_search_id(db):
    s1 = database.insert_search("dev", "London", None, None, False, db_path=db)
    s2 = database.insert_search("designer", "Remote", None, None, False, db_path=db)
    job2 = {**SAMPLE_JOB, "url": "https://example.com/job/2"}
    database.insert_jobs(s1, [SAMPLE_JOB], db_path=db)
    database.insert_jobs(s2, [job2], db_path=db)

    s1_jobs = database.get_jobs(filters={"search_id": s1}, db_path=db)
    assert len(s1_jobs) == 1
    assert s1_jobs[0]["search_id"] == s1


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
def test_delete_job(db):
    search_id = database.insert_search("engineer", "", None, None, False, db_path=db)
    database.insert_jobs(search_id, [SAMPLE_JOB], db_path=db)

    job_id = database.get_jobs(db_path=db)[0]["id"]
    assert database.delete_job(job_id, db_path=db) is True
    assert database.get_job(job_id, db_path=db) is None
    assert len(database.get_jobs(db_path=db)) == 0


def test_delete_nonexistent_job(db):
    assert database.delete_job(9999, db_path=db) is False
