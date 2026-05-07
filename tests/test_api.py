"""
API integration tests — uses Flask's test client and mocks scraper.scrape
so no real network requests are made.
"""

import sys
import os
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

SAMPLE_JOBS = [
    {
        "title": "Python Developer",
        "company": "TechCorp",
        "location": "London",
        "salary_min": 50000.0,
        "salary_max": 70000.0,
        "salary_interval": "yearly",
        "job_type": "fulltime",
        "description_snippet": "Exciting Python role in London.",
        "url": "https://example.com/job/100",
        "site": "indeed",
        "date_posted": "2024-01-01",
    },
    {
        "title": "Backend Engineer",
        "company": "StartupCo",
        "location": "Remote",
        "salary_min": None,
        "salary_max": None,
        "salary_interval": None,
        "job_type": "fulltime",
        "description_snippet": "Remote backend position.",
        "url": "https://example.com/job/101",
        "site": "linkedin",
        "date_posted": "2024-01-02",
    },
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Redirect all database calls to a fresh temp DB for each test."""
    db_path = str(tmp_path / "test_api.db")
    monkeypatch.setattr("database.DB_PATH", db_path)

    import database
    database.init_db(db_path=db_path)
    return db_path


@pytest.fixture
def client():
    import app as flask_app
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# POST /api/search
# ---------------------------------------------------------------------------
def test_search_returns_jobs(client):
    with patch("scraper.scrape", return_value=(SAMPLE_JOBS, [])):
        rv = client.post("/api/search", json={"query": "python developer", "location": "London"})

    assert rv.status_code == 200
    data = rv.get_json()
    assert data["total_found"] == 2
    assert data["new"] == 2
    assert data["already_seen"] == 0
    assert len(data["jobs"]) == 2
    assert data["site_errors"] == []


def test_search_reports_deduplication(client):
    with patch("scraper.scrape", return_value=(SAMPLE_JOBS, [])):
        client.post("/api/search", json={"query": "python", "location": "London"})
        rv = client.post("/api/search", json={"query": "python", "location": "London"})

    data = rv.get_json()
    assert rv.status_code == 200
    assert data["new"] == 0
    assert data["already_seen"] == 2


def test_search_missing_query(client):
    rv = client.post("/api/search", json={})
    assert rv.status_code == 400
    assert "error" in rv.get_json()


def test_search_empty_query_string(client):
    rv = client.post("/api/search", json={"query": "   "})
    assert rv.status_code == 400


def test_search_reports_site_errors(client):
    errors = [{"site": "linkedin", "error": "blocked"}]
    with patch("scraper.scrape", return_value=([SAMPLE_JOBS[0]], errors)):
        rv = client.post("/api/search", json={"query": "engineer"})

    data = rv.get_json()
    assert rv.status_code == 200
    assert len(data["site_errors"]) == 1
    assert data["site_errors"][0]["site"] == "linkedin"


def test_search_no_results(client):
    with patch("scraper.scrape", return_value=([], [])):
        rv = client.post("/api/search", json={"query": "zzz_unlikely_job"})

    data = rv.get_json()
    assert rv.status_code == 200
    assert data["total_found"] == 0
    assert data["jobs"] == []


# ---------------------------------------------------------------------------
# GET /api/jobs
# ---------------------------------------------------------------------------
def test_get_all_jobs(client):
    with patch("scraper.scrape", return_value=(SAMPLE_JOBS, [])):
        client.post("/api/search", json={"query": "python", "location": "London"})

    rv = client.get("/api/jobs")
    assert rv.status_code == 200
    jobs = rv.get_json()
    assert len(jobs) == 2


def test_get_jobs_filter_by_site(client):
    with patch("scraper.scrape", return_value=(SAMPLE_JOBS, [])):
        client.post("/api/search", json={"query": "python", "location": "London"})

    rv = client.get("/api/jobs?site=indeed")
    assert rv.status_code == 200
    jobs = rv.get_json()
    assert all(j["site"] == "indeed" for j in jobs)


def test_get_jobs_filter_by_search_id(client):
    with patch("scraper.scrape", return_value=(SAMPLE_JOBS, [])):
        rv = client.post("/api/search", json={"query": "python", "location": "London"})
    search_id = rv.get_json()["search_id"]

    jobs = client.get(f"/api/jobs?search_id={search_id}").get_json()
    assert len(jobs) == 2
    assert all(j["search_id"] == search_id for j in jobs)


# ---------------------------------------------------------------------------
# GET /api/jobs/<id>
# ---------------------------------------------------------------------------
def test_get_single_job(client):
    with patch("scraper.scrape", return_value=(SAMPLE_JOBS, [])):
        client.post("/api/search", json={"query": "python", "location": "London"})

    jobs   = client.get("/api/jobs").get_json()
    job_id = jobs[0]["id"]

    rv = client.get(f"/api/jobs/{job_id}")
    assert rv.status_code == 200
    assert rv.get_json()["id"] == job_id


def test_get_single_job_not_found(client):
    rv = client.get("/api/jobs/99999")
    assert rv.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/jobs/<id>
# ---------------------------------------------------------------------------
def test_delete_job(client):
    with patch("scraper.scrape", return_value=(SAMPLE_JOBS, [])):
        client.post("/api/search", json={"query": "python", "location": "London"})

    job_id = client.get("/api/jobs").get_json()[0]["id"]

    rv = client.delete(f"/api/jobs/{job_id}")
    assert rv.status_code == 200
    assert rv.get_json()["deleted"] is True

    assert client.get(f"/api/jobs/{job_id}").status_code == 404


def test_delete_nonexistent_job(client):
    rv = client.delete("/api/jobs/99999")
    assert rv.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/searches
# ---------------------------------------------------------------------------
def test_get_searches(client):
    with patch("scraper.scrape", return_value=(SAMPLE_JOBS, [])):
        client.post("/api/search", json={"query": "python", "location": "London"})
        client.post("/api/search", json={"query": "designer", "location": "Remote"})

    rv = client.get("/api/searches")
    assert rv.status_code == 200
    searches = rv.get_json()
    assert len(searches) == 2
    # Most recent first
    assert searches[0]["query"] == "designer"
