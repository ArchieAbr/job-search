"""
scraper.py — wraps python-jobspy.

Each site is scraped independently so that a failure on one (e.g. LinkedIn
blocking the request) does not prevent results from the others.
"""

import logging
import pandas as pd
from jobspy import scrape_jobs

SUPPORTED_SITES = ["indeed", "linkedin", "glassdoor"]

EXPERIENCE_KEYWORDS = {
    "junior": ["junior", "entry", "graduate", "jr.", "jr "],
    "mid": ["mid", "intermediate", "mid-level"],
    "senior": ["senior", "sr.", "sr ", "lead", "principal", "staff"],
}

VALID_JOB_TYPES = {"fulltime", "parttime", "contract", "internship"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scrape(
    query,
    location="",
    sites=None,
    job_type=None,
    is_remote=False,
    results_wanted=50,
    hours_old=72,
    salary_min=None,
    salary_max=None,
    experience_level=None,
):
    """Scrape jobs from the given sites.

    Each site is scraped individually so a failure on one site does not
    block results from the others.

    Returns:
        tuple: (jobs: list[dict], site_errors: list[dict])
    """
    if sites is None:
        sites = SUPPORTED_SITES

    jobspy_job_type = job_type if job_type in VALID_JOB_TYPES else None

    all_jobs = []
    site_errors = []

    for site in sites:
        result = _scrape_single_site(
            site=site,
            query=query,
            location=location,
            job_type=jobspy_job_type,
            is_remote=is_remote,
            results_wanted=results_wanted,
            hours_old=hours_old,
        )
        if result["status"] == "ok":
            all_jobs.extend(result["jobs"])
        else:
            site_errors.append({"site": site, "error": result["error"]})

    all_jobs = _apply_salary_filter(all_jobs, salary_min, salary_max)
    all_jobs = _apply_experience_filter(all_jobs, experience_level)

    return all_jobs, site_errors


def scrape_site(site, query="software engineer", location="London", results_wanted=5):
    """Probe a single site and return a health-check summary dict.

    Returns:
        dict with keys: site, status ('ok'|'no_results'|'error'), count, error
    """
    result = _scrape_single_site(
        site=site,
        query=query,
        location=location,
        job_type=None,
        is_remote=False,
        results_wanted=results_wanted,
        hours_old=168,  # wider window for health checks
    )
    return {
        "site": site,
        "status": result["status"],
        "count": len(result.get("jobs", [])),
        "error": result["error"],
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _scrape_single_site(site, query, location, job_type, is_remote, results_wanted, hours_old):
    """Call jobspy for one site. Returns dict: {status, jobs, error}."""
    try:
        # jobspy creates loggers named "JobSpy:<site>" with propagate=False, so
        # they bypass any root-logger filters. logging.disable() is a global
        # module-level short-circuit that silences them regardless of hierarchy.
        logging.disable(logging.ERROR)
        try:
            df = scrape_jobs(
                site_name=[site],
                search_term=query,
                location=location,
                results_wanted=results_wanted,
                hours_old=hours_old,
                is_remote=is_remote,
                job_type=job_type,
            )
        finally:
            logging.disable(logging.NOTSET)
    except Exception as exc:
        return {"status": "error", "jobs": [], "error": str(exc)}

    if df is None or df.empty:
        return {"status": "no_results", "jobs": [], "error": None}

    return {"status": "ok", "jobs": _dataframe_to_list(df), "error": None}


def _dataframe_to_list(df):
    jobs = []
    for _, row in df.iterrows():
        jobs.append(
            {
                "title": _str(row, "title"),
                "company": _str(row, "company"),
                "location": _str(row, "location"),
                "salary_min": _float(row, "min_amount"),
                "salary_max": _float(row, "max_amount"),
                "salary_interval": _str(row, "interval"),
                "job_type": _str(row, "job_type"),
                "description_snippet": _str(row, "description")[:500],
                "url": _str(row, "job_url"),
                "site": _str(row, "site"),
                "date_posted": _str(row, "date_posted"),
            }
        )
    return jobs


def _str(row, col):
    try:
        val = row.get(col)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return ""
        return str(val)
    except (TypeError, ValueError):
        return ""


def _float(row, col):
    try:
        val = row.get(col)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        return float(val)
    except (TypeError, ValueError):
        return None


def _apply_salary_filter(jobs, salary_min, salary_max):
    if salary_min is None and salary_max is None:
        return jobs
    filtered = []
    for job in jobs:
        jmin = job.get("salary_min")
        jmax = job.get("salary_max")
        # Keep jobs with no salary data — don't exclude unknowns
        if jmin is None and jmax is None:
            filtered.append(job)
            continue
        # Use the best available salary value for comparison
        val = jmax if jmax is not None else jmin
        if salary_min is not None and val < salary_min:
            continue
        if salary_max is not None and val > salary_max:
            continue
        filtered.append(job)
    return filtered


def _apply_experience_filter(jobs, experience_level):
    if not experience_level:
        return jobs
    keywords = EXPERIENCE_KEYWORDS.get(experience_level.lower(), [])
    if not keywords:
        return jobs
    filtered = []
    for job in jobs:
        combined = (
            job.get("title", "").lower() + " " + job.get("description_snippet", "").lower()
        )
        if any(kw in combined for kw in keywords):
            filtered.append(job)
    return filtered
