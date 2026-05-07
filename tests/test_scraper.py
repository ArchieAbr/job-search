"""
tests/test_scraper.py — Site health checks.

Run as a standalone diagnostic script:
    python tests/test_scraper.py

Run via pytest (live network — skipped by default):
    pytest tests/test_scraper.py -m live -v
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import scraper

SITES       = ["indeed", "linkedin", "glassdoor"]
TEST_QUERY  = "software engineer"
TEST_LOCATION = "London"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _check_and_print(site):
    print(f"\n  Checking {site}...", end=" ", flush=True)
    result = scraper.scrape_site(
        site=site,
        query=TEST_QUERY,
        location=TEST_LOCATION,
        results_wanted=3,
    )
    status = result["status"]
    count  = result["count"]
    error  = result["error"]

    if status == "ok":
        print(f"OK  ({count} results returned)")
    elif status == "no_results":
        print(f"WARNING  — 0 results (possibly blocked or a slow day)")
    else:
        print(f"FAILED  — {error}")

    return result


# ---------------------------------------------------------------------------
# Live pytest tests (require real network — not run by default)
# ---------------------------------------------------------------------------
@pytest.mark.live
@pytest.mark.parametrize("site", SITES)
def test_site_health(site):
    """Live test: makes a real network request to each job site.

    Run with:  pytest tests/test_scraper.py -m live -v
    """
    result = _check_and_print(site)
    if result["status"] == "error":
        pytest.fail(
            f"{site} scraping raised an exception: {result['error']}\n"
            "This may be a temporary block. Try again or check your network."
        )


@pytest.mark.live
def test_scrape_returns_expected_fields(site="indeed"):
    """Spot-check that the job dicts returned have the expected keys."""
    from scraper import scrape
    jobs, errors = scrape(
        query=TEST_QUERY,
        location=TEST_LOCATION,
        sites=["indeed"],
        results_wanted=3,
    )
    if errors:
        pytest.skip(f"indeed unavailable: {errors[0]['error']}")

    assert len(jobs) > 0, "Expected at least one job result from Indeed"
    job = jobs[0]
    for field in ("title", "company", "location", "url", "site"):
        assert field in job, f"Missing field: {field}"
    assert job["site"] == "indeed"


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 55)
    print("  Job Site Health Check")
    print(f"  Query: '{TEST_QUERY}' | Location: '{TEST_LOCATION}'")
    print("=" * 55)

    results = [_check_and_print(site) for site in SITES]

    print("\n" + "=" * 55)
    print("  Summary")
    print("=" * 55)
    for r in results:
        icon = "✓" if r["status"] == "ok" else ("⚠" if r["status"] == "no_results" else "✗")
        count_str = f"({r['count']} results)" if r["status"] == "ok" else ""
        print(f"  {icon}  {r['site']:<12} {r['status']}  {count_str}")

    failed = [r for r in results if r["status"] == "error"]
    warned = [r for r in results if r["status"] == "no_results"]

    print()
    if failed:
        print(f"  {len(failed)} site(s) failed with errors.")
        for r in failed:
            print(f"    • {r['site']}: {r['error']}")
        print("\n  Tips:")
        print("  - LinkedIn actively blocks scrapers; failures here are common.")
        print("  - Try again later or reduce request frequency.")
        sys.exit(1)
    elif warned:
        print(f"  {len(warned)} site(s) returned 0 results (possible soft block).")
        sys.exit(0)
    else:
        print("  All sites returned results successfully.")
        sys.exit(0)
