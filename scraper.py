"""
scraper.py — wraps python-jobspy.

Each site is scraped independently so that a failure on one (e.g. LinkedIn
blocking the request) does not prevent results from the others.
"""

import logging
import pandas as pd
from jobspy import scrape_jobs

SUPPORTED_SITES = ["indeed", "linkedin", "glassdoor"]

# Words in a location string that indicate a non-UK country. If any of these
# appear the default UK country setting for Indeed is overridden.
_US_INDICATORS  = {"usa", "united states", "u.s.", "u.s.a"}
_AUS_INDICATORS = {"australia", "aus", "sydney", "melbourne", "brisbane"}
_CA_INDICATORS  = {"canada", "toronto", "vancouver", "montreal"}

# Words that are country/region names rather than city names — stripped when
# building the location post-filter tokens.
_COUNTRY_NOISE = {
    "uk", "u.k.", "united", "kingdom", "england", "scotland",
    "wales", "ireland", "great", "britain", "gb",
    "usa", "united", "states", "america",
    "australia", "canada",
}

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
    all_jobs = _apply_location_filter(all_jobs, location)

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


def _detect_country_indeed(location: str) -> str:
    """Return the country_indeed value appropriate for the given location string.

    Defaults to 'UK' (since this app is UK-focused / uses GBP salaries).
    Overrides to other countries when the location string contains clear indicators.
    """
    loc_lower = location.lower()
    if any(ind in loc_lower for ind in _US_INDICATORS):
        return "USA"
    if any(ind in loc_lower for ind in _AUS_INDICATORS):
        return "Australia"
    if any(ind in loc_lower for ind in _CA_INDICATORS):
        return "Canada"
    return "UK"


def _scrape_single_site(site, query, location, job_type, is_remote, results_wanted, hours_old):
    """Call jobspy for one site. Returns dict: {status, jobs, error}."""
    try:
        # jobspy creates loggers named "JobSpy:<site>" with propagate=False, so
        # they bypass any root-logger filters. logging.disable() is a global
        # module-level short-circuit that silences them regardless of hierarchy.
        logging.disable(logging.ERROR)
        try:
            kwargs = dict(
                site_name=[site],
                search_term=query,
                location=location,
                results_wanted=results_wanted,
                hours_old=hours_old,
                is_remote=is_remote,
                job_type=job_type,
            )
            # country_indeed tells jobspy which Indeed locale to hit.
            # Without this it defaults to the US, causing non-US locations
            # to match US cities with the same name (e.g. London, Ohio).
            if site == "indeed" and location:
                kwargs["country_indeed"] = _detect_country_indeed(location)

            df = scrape_jobs(**kwargs)
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


def _apply_location_filter(jobs, location: str):
    """Drop jobs whose returned location clearly doesn't match the requested one.

    Strategy:
    - Extract meaningful city/town tokens from the requested location (strip
      country-level noise words).
    - Keep a job if ANY of those tokens appears in the job's location field
      (case-insensitive).
    - Always keep jobs with an empty location field — we don't want to silently
      discard listings that just didn't populate the field.
    - Skip the filter entirely if the user didn't supply a location.
    """
    if not location or not location.strip():
        return jobs

    # Build the set of tokens to match against, e.g. "South London, UK" → {"south", "london"}
    raw_tokens = location.lower().replace(",", " ").split()
    match_tokens = [t for t in raw_tokens if t not in _COUNTRY_NOISE and len(t) > 2]

    if not match_tokens:
        return jobs

    filtered = []
    for job in jobs:
        job_loc = (job.get("location") or "").lower()
        if not job_loc:
            # No location data returned — keep it rather than over-filtering
            filtered.append(job)
            continue
        if any(token in job_loc for token in match_tokens):
            filtered.append(job)
    return filtered


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
