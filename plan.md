# Plan: Job Search Scraper App

## Summary
A local, personal job search aggregator built with Python/Flask + Vanilla JS + SQLite.
Uses `python-jobspy` to scrape Indeed, LinkedIn, and Glassdoor. User enters keyword/job title and filters; results are saved to SQLite for deduplication and history.

## Stack
- Backend: Python + Flask
- Frontend: Vanilla JS + HTML/CSS (served by Flask static folder)
- Database: SQLite (via Python's built-in `sqlite3` module)
- Scraping: `python-jobspy`

## Project Structure
```
job-search/
├── app.py               # Flask app + API routes
├── database.py          # SQLite init and query helpers
├── scraper.py           # python-jobspy wrapper
├── requirements.txt
├── jobs.db              # created at runtime
└── static/
    ├── index.html       # single-page app
    ├── style.css
    └── app.js           # fetch calls + DOM manipulation
```

## Data Model (SQLite)
### `searches` table
- id, query (text), location, job_type, experience_level, date_run

### `jobs` table
- id, search_id (FK), title, company, location, salary_min, salary_max, salary_interval, job_type, description_snippet, url (UNIQUE), site (indeed/linkedin/glassdoor), date_posted, date_scraped

## API Endpoints (Flask)
- `POST /api/search` — run a new search with filters, return job results
- `GET /api/jobs` — retrieve all saved jobs (optional query params for filtering)
- `GET /api/jobs/<id>` — get single job details
- `DELETE /api/jobs/<id>` — delete a job from history
- `GET /api/searches` — list past searches

## Key Implementation Details
- `python-jobspy` params: search_term, location, results_wanted, hours_old, is_remote, job_type (fulltime/parttime/contract/internship)
- Salary and experience level are post-filters (jobspy doesn't natively support them)
- Deduplication by `url` UNIQUE constraint in SQLite
- Flask serves `static/index.html` at root `/`
- CORS not needed (same origin, Flask serves frontend)

## Phases

### Phase 1: Backend foundation
1. Create `requirements.txt` (flask, python-jobspy, pandas)
2. Create `database.py` — init SQLite, create tables, insert/query helpers
3. Create `scraper.py` — wrap jobspy, apply post-filters (salary, experience_level)
4. Create `app.py` — Flask app with all API routes

### Phase 2: Frontend
5. Create `static/index.html` — search form + results display area
6. Create `static/style.css` — clean, readable styling
7. Create `static/app.js` — fetch calls, render job cards, handle filters

### Phase 3: Polish
8. Deduplication feedback (tell user X new / Y already seen)
9. Search history sidebar
10. Expand/collapse job description

## Verification
1. Run `pip install -r requirements.txt` and confirm no errors
2. Start Flask: `python app.py` — confirm server starts
3. POST /api/search with {"query": "software engineer", "location": "London"} — confirm jobs returned
4. Check jobs.db has populated `jobs` table
5. Re-run same search — confirm duplicates not inserted again
6. Open browser at http://localhost:5000 — confirm UI loads and search works end-to-end

## Decisions
- Local only — no cloud hosting
- Single user — no auth
- On-demand search — no scheduling
- python-jobspy for scraping (user is aware of ToS implications)
- Salary/experience filters handled as post-filters on results
