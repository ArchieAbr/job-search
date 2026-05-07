#!/usr/bin/env bash
# run_tests.sh — runs unit and API tests (skips live network tests)
set -e

echo "Running unit and API tests (live site tests excluded)..."
python3 -m pytest tests/ -v -m "not live"
echo ""
echo "To run live site health checks:"
echo "  python3 -m pytest tests/test_scraper.py -m live -v"
echo "  # or run standalone:"
echo "  python3 tests/test_scraper.py"
