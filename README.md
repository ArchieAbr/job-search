# Job Search

A local, personal job listing aggregator that scrapes Indeed, LinkedIn, and Glassdoor. Search by keyword, let AI expand your query, or upload your CV and let Gemini find roles that match your experience — all saved to a local database so you never see the same listing twice.

Built with Python and vanilla JavaScript. Runs entirely on your own machine — no accounts, no cloud hosting, no subscription.

> **Built with assistance from [GitHub Copilot](https://github.com/features/copilot), powered by Claude Sonnet 4.6.**
> Styled with [Pico CSS](https://picocss.com/) (MIT licence).

---

## Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running the App](#running-the-app)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Known Limitations](#known-limitations)
- [Licence](#licence)

---

## Features

- **Three search modes** — Standard (exact keyword), AI (natural language expansion), and CV (upload your CV and let Gemini find matching roles)
- **Multi-site search** — queries Indeed, LinkedIn, and Glassdoor simultaneously; a failure on one site does not block the others
- **AI query expansion** — describe what you're looking for in plain English and Gemini 2.5 Flash generates up to 5 targeted job title searches
- **CV-powered search** — upload a PDF, DOCX, or TXT CV; Gemini extracts your skills, experience level, and up to 6 relevant job titles, then searches all selected sites for matching roles
- **Filters** — location, job type (full-time, part-time, contract, internship), experience level, minimum salary, and remote-only toggle
- **Deduplication** — job listings are stored by URL; re-running the same search never inserts duplicates
- **Results table** — all results in a sortable table showing job title (with link), company, location, salary, type, date posted, and source site
- **Search history** — every search is saved in the sidebar; click any entry to reload its results instantly
- **Delete history** — remove individual searches with their saved jobs, or wipe all history with "Clear all"
- **Remove listings** — delete individual jobs from saved results
- **Site error reporting** — clear per-site warnings if a job board blocks or returns nothing
- **Progress bar** — animated, stage-by-stage progress feedback during search
- **Runs locally** — no data leaves your machine (except calls to the Gemini API when using AI or CV mode)

---

## How It Works

```
Browser (Vanilla JS)
       │
       │  HTTP (fetch API)
       ▼
Flask API (app.py)
       │
       ├──► expander.py  ──► Gemini 2.5 Flash ──► job title expansion (AI / CV mode)
       │
       ├──► cv_parser.py ──► pdfplumber / python-docx ──► plain text extraction
       │
       ├──► scraper.py   ──► python-jobspy ──► Indeed / LinkedIn / Glassdoor
       │         │
       │         └── post-filters: salary, experience level
       │
       └──► database.py  ──► SQLite (jobs.db)
```

### Standard mode

The query is sent directly to each selected job board as-is. No AI call is made.

### AI mode

The query is sent to Gemini 2.5 Flash, which returns up to 5 specific, searchable job titles plus an auto-detected seniority level. The app then runs a separate scrape for each title and deduplicates results by URL before saving.

### CV mode

The uploaded file is parsed server-side to plain text (PDF via `pdfplumber`, DOCX via `python-docx`, TXT directly). The text is sent to Gemini, which returns:

- Up to 6 relevant job titles
- Up to 8 top skills
- Detected seniority level
- A 1–2 sentence professional summary

The app then searches each job board for every extracted title. An optional additional keyword can be appended to the CV-derived terms.

### Components

| File                | Responsibility                                                            |
| ------------------- | ------------------------------------------------------------------------- |
| `app.py`            | Flask application — API routes and static file serving                    |
| `scraper.py`        | Wraps `python-jobspy`; per-site error isolation; post-filters             |
| `database.py`       | SQLite schema, insert helpers, deduplication, query and delete helpers    |
| `expander.py`       | Gemini 2.5 Flash integration — query expansion and CV analysis            |
| `cv_parser.py`      | Extracts plain text from PDF, DOCX, or TXT files                          |
| `static/index.html` | Single-page UI — mode toggle, search form, results table, history sidebar |
| `static/app.js`     | Frontend logic — fetch calls, CV upload, progress bar, DOM rendering      |
| `static/style.css`  | Styling layered on Pico CSS — layout, progress bar, CV dropzone, badges   |
| `tests/`            | Unit, integration, and site health-check tests                            |

---

## Project Structure

```
job-search/
├── app.py                  # Flask app and API routes
├── database.py             # SQLite helpers
├── scraper.py              # python-jobspy wrapper
├── expander.py             # Gemini query expansion and CV analysis
├── cv_parser.py            # CV text extraction (PDF, DOCX, TXT)
├── requirements.txt        # Python dependencies
├── .env.example            # Template for environment variables
├── pytest.ini              # pytest configuration
├── run_tests.sh            # Test runner script
├── jobs.db                 # Created automatically on first run
├── static/
│   ├── index.html          # Web UI
│   ├── style.css           # Stylesheet
│   └── app.js              # Frontend JavaScript
└── tests/
    ├── test_database.py    # Database unit tests
    ├── test_api.py         # Flask API integration tests
    └── test_scraper.py     # Per-site health checks (live network)
```

---

## Requirements

- Python 3.9 or later
- pip
- A **Gemini API key** (free tier available) — required for AI mode and CV mode only

No other system dependencies are required. The app uses SQLite via Python's built-in `sqlite3` module.

---

## Installation

**1. Clone the repository**

```bash
git clone <repository-url>
cd job-search
```

**2. Create and activate a virtual environment** _(recommended)_

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Set up your Gemini API key** _(required for AI and CV modes)_

```bash
cp .env.example .env
```

Edit `.env` and add your key:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

Get a free key at [aistudio.google.com](https://aistudio.google.com/). The app works without a key in Standard mode — AI and CV modes will show an error if the key is missing.

---

## Running the App

```bash
python3 app.py
```

Then open your browser at:

```
http://localhost:5000
```

Flask runs in debug mode by default, so the server reloads automatically if you edit Python files.

---

## Usage

### Choosing a search mode

Use the **Standard / ✦ AI / 📄 CV** toggle at the top of the search form.

| Mode     | When to use                                                                |
| -------- | -------------------------------------------------------------------------- |
| Standard | You know the exact job title or keyword you want to search                 |
| ✦ AI     | You want to describe your intent in plain English; Gemini finds the titles |
| 📄 CV    | You want Gemini to read your CV and find roles that match your experience  |

### Standard mode

1. Enter a **job title or keyword** (required).
2. Optionally enter a **location**.
3. Select **job sites**, apply filters, and click **Search Jobs**.

### AI mode

1. Describe what you're looking for in plain English — e.g. _"creative industry"_, _"graduate computer science student"_, _"data-focused marketing role"_.
2. Gemini returns up to 5 specific job titles and an auto-detected seniority level.
3. All titles are searched in parallel and results are deduplicated.
4. After the search, the **AI expansion panel** shows which titles were searched and what Gemini understood.

### CV mode

1. Switch to **📄 CV** mode.
2. Drop your CV onto the upload area or click to browse. PDF, DOCX, and TXT are supported (max 5 MB).
3. Gemini analyses the CV and displays:
   - A professional summary
   - Detected seniority level
   - Extracted skills (green pills)
   - Job titles it will search for
4. Optionally add an extra keyword in the query field.
5. Click **Search Jobs**.

### Filters

| Filter           | Options                                             |
| ---------------- | --------------------------------------------------- |
| Location         | Free text — city, region, or "Remote"               |
| Job type         | Full-time, part-time, contract, internship          |
| Experience level | Junior, mid-level, senior                           |
| Min salary       | Annual figure in GBP                                |
| Remote only      | Checkbox — restricts to remote positions            |
| Max results      | Number of listings to request per site (default 50) |

### Results table

Results are shown in a table with: job title (linked), company, location, salary, type, date posted, source badge, and a remove button.

### Search history

All past searches appear in the sidebar. Click any entry to reload its saved results. Each entry has an **✕** button to delete it (this also deletes all saved jobs from that search). Use **Clear all** to wipe the entire history.

### Progress bar

During a search, an animated progress bar tracks the current stage — AI interpretation, site-by-site scraping, and compilation — with a percentage and descriptive text.

---

## API Reference

### `POST /api/search`

Run a new search and save results to the database.

**Request body (JSON):**

```json
{
  "query": "Python developer",
  "location": "London",
  "sites": ["indeed", "linkedin"],
  "job_type": "fulltime",
  "experience_level": "senior",
  "is_remote": false,
  "results_wanted": 50,
  "hours_old": 72,
  "salary_min": 50000,
  "use_ai": false,
  "use_cv": false,
  "cv_terms": ["Software Engineer", "Backend Developer"],
  "cv_experience_level": "mid"
}
```

| Field                 | Type    | Required | Description                                                               |
| --------------------- | ------- | -------- | ------------------------------------------------------------------------- |
| `query`               | string  | Yes\*    | Job title, keyword, or natural language description. Optional in CV mode. |
| `location`            | string  | No       | City or region                                                            |
| `sites`               | array   | No       | `["indeed", "linkedin", "glassdoor"]` (default: indeed + linkedin)        |
| `job_type`            | string  | No       | `fulltime`, `parttime`, `contract`, `internship`                          |
| `experience_level`    | string  | No       | `junior`, `mid`, `senior`                                                 |
| `is_remote`           | boolean | No       | `true` to filter remote-only                                              |
| `results_wanted`      | integer | No       | Max results per site (default: 50)                                        |
| `hours_old`           | integer | No       | Max age of listings in hours (default: 72)                                |
| `salary_min`          | number  | No       | Minimum annual salary in GBP                                              |
| `use_ai`              | boolean | No       | `true` to expand query with Gemini before searching                       |
| `use_cv`              | boolean | No       | `true` to use `cv_terms` instead of expanding the query                   |
| `cv_terms`            | array   | CV mode  | Job titles from a prior `/api/analyze-cv` call                            |
| `cv_experience_level` | string  | No       | Experience level detected from CV analysis                                |

**Response:**

```json
{
  "search_id": 3,
  "total_found": 12,
  "new": 8,
  "already_seen": 4,
  "jobs": [ ... ],
  "site_errors": [
    { "site": "glassdoor", "error": "Error encountered in API response" }
  ],
  "expansion": {
    "terms": ["Python Developer", "Backend Engineer"],
    "experience_level_detected": "senior",
    "summary": "A senior Python developer role in backend engineering.",
    "used_ai": true
  }
}
```

---

### `POST /api/analyze-cv`

Upload a CV file and receive Gemini-generated job search terms and a profile summary. Must be called before using CV mode in `/api/search`.

**Request:** `multipart/form-data` with a `cv` field containing the file (PDF, DOCX, or TXT, max 5 MB).

```bash
curl -X POST http://localhost:5000/api/analyze-cv \
  -F "cv=@/path/to/my-cv.pdf"
```

**Response:**

```json
{
  "terms": [
    "Data Analyst",
    "Business Intelligence Developer",
    "Reporting Analyst"
  ],
  "skills": ["SQL", "Python", "Power BI", "Excel", "Tableau"],
  "experience_level": "mid",
  "summary": "A mid-level data professional with strong SQL and BI tooling skills.",
  "analyzed": true
}
```

---

### `GET /api/jobs`

Retrieve saved jobs. Supports optional query parameters:

| Parameter   | Description                                        |
| ----------- | -------------------------------------------------- |
| `site`      | Filter by site (`indeed`, `linkedin`, `glassdoor`) |
| `job_type`  | Filter by job type                                 |
| `search_id` | Return only jobs from a specific search            |

---

### `GET /api/jobs/<id>`

Retrieve a single job by its database ID.

---

### `DELETE /api/jobs/<id>`

Delete a single job from the database.

---

### `GET /api/searches`

Return all past searches, most recent first.

---

### `DELETE /api/searches/<id>`

Delete a single search and all its associated jobs.

---

### `DELETE /api/searches`

Delete all searches and all saved jobs.

---

## Testing

### Unit and integration tests

These run without making any network requests (the scraper is mocked):

```bash
bash run_tests.sh
```

Or directly with pytest:

```bash
pytest tests/ -v -m "not live"
```

The test suite includes:

- **`test_database.py`** — covers schema creation, insert, query, deduplication, filtering, and deletion
- **`test_api.py`** — covers all API endpoints using Flask's test client

### Live site health checks

To test whether each job board is reachable and returning results:

```bash
python3 tests/test_scraper.py
```

This makes real network requests and prints a per-site summary. You can also run via pytest:

```bash
pytest tests/test_scraper.py -m live -v
```

---

## Known Limitations

### Glassdoor

Glassdoor's internal API currently rejects requests from `python-jobspy` with `"Error encountered in API response"`. This appears to be bot detection. Glassdoor is unchecked by default but can still be selected — results will appear if the block is lifted.

### LinkedIn

LinkedIn does not offer an official public job search API. `python-jobspy` accesses it without authentication, which works until LinkedIn detects and throttles the requests. Failures are intermittent.

### Rate limiting

Running very frequent or high-volume searches increases the likelihood of being temporarily blocked. If you see consistent failures, wait a few hours before trying again.

### CV parsing

CV text extraction works best with text-based PDFs. Scanned image PDFs (where the content is a photograph rather than selectable text) cannot be parsed. If extraction fails, the app returns a clear error and suggests using a DOCX or TXT file instead.

### Terms of Service

Scraping job boards may conflict with their Terms of Service. This tool is intended for personal, non-commercial use only. Use responsibly.

---

## Licence

MIT

---

_Built with assistance from [GitHub Copilot](https://github.com/features/copilot), powered by **Claude Sonnet 4.6**. Styled with [Pico CSS](https://picocss.com/) (MIT licence)._

---

## Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running the App](#running-the-app)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Known Limitations](#known-limitations)
- [Licence](#licence)

---

## Features

- **Multi-site search** — queries Indeed, LinkedIn, and Glassdoor simultaneously (each site scraped independently, so a failure on one does not affect the others)
- **Keyword & job title search** — free-text search term passed directly to each job board
- **Filters** — location, job type (full-time, part-time, contract, internship), experience level (junior, mid-level, senior), salary range, and remote-only toggle
- **Deduplication** — job listings are stored by URL; re-running the same search will never insert duplicate rows
- **Search history** — every search is saved and accessible from the sidebar; click any past search to reload its results
- **Site error reporting** — if a job board blocks the request or returns no results, a clear warning is shown in the UI
- **Remove listings** — delete individual job cards from your saved results
- **Runs locally** — no external services, no authentication, no data leaves your machine

---

## How It Works

```
Browser (Vanilla JS)
       │
       │  HTTP (fetch API)
       ▼
Flask API (app.py)
       │
       ├──► scraper.py  ──► python-jobspy ──► Indeed / LinkedIn / Glassdoor
       │         │
       │         └── post-filters: salary range, experience level
       │
       └──► database.py ──► SQLite (jobs.db)
```

1. The browser sends a `POST /api/search` request with the user's search parameters.
2. Flask hands the request to `scraper.py`, which calls `python-jobspy` for each selected site individually. Any site that fails is reported as an error without blocking the others.
3. Optional salary and experience-level filters are applied server-side to the returned results (these are not natively supported by jobspy).
4. The search parameters and all results are written to `jobs.db` (SQLite). Duplicate URLs are silently skipped.
5. The response includes the job listings, a count of new vs. already-seen results, and any per-site errors.
6. The frontend renders job cards and updates the search history sidebar.

### Components

| File                | Responsibility                                                |
| ------------------- | ------------------------------------------------------------- |
| `app.py`            | Flask application — API routes and static file serving        |
| `scraper.py`        | Wraps `python-jobspy`; per-site error isolation; post-filters |
| `database.py`       | SQLite schema, insert helpers, deduplication, query helpers   |
| `static/index.html` | Single-page UI — search form, results grid, history sidebar   |
| `static/app.js`     | Frontend logic — fetch calls, DOM rendering, job cards        |
| `static/style.css`  | Styling — card layout, responsive design                      |
| `tests/`            | Unit, integration, and site health-check tests                |

---

## Project Structure

```
job-search/
├── app.py                  # Flask app and API routes
├── database.py             # SQLite helpers
├── scraper.py              # python-jobspy wrapper
├── requirements.txt        # Python dependencies
├── pytest.ini              # pytest configuration
├── run_tests.sh            # Test runner script
├── jobs.db                 # Created automatically on first run
├── static/
│   ├── index.html          # Web UI
│   ├── style.css           # Stylesheet
│   └── app.js              # Frontend JavaScript
└── tests/
    ├── test_database.py    # Database unit tests
    ├── test_api.py         # Flask API integration tests
    └── test_scraper.py     # Per-site health checks (live network)
```

---

## Requirements

- Python 3.9 or later
- pip

No other system dependencies are required. The app uses SQLite via Python's built-in `sqlite3` module.

---

## Installation

**1. Clone the repository**

```bash
git clone <repository-url>
cd job-search
```

**2. Create and activate a virtual environment** _(recommended)_

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

---

## Running the App

```bash
python3 app.py
```

Then open your browser at:

```
http://localhost:5000
```

Flask runs in debug mode by default, so the server will reload automatically if you edit any Python files.

---

## Usage

### Searching for jobs

1. Enter a **job title or keyword** in the search box (required).
2. Optionally enter a **location** (e.g. "London", "Manchester", "Remote").
3. Select which **job sites** to search (Indeed and LinkedIn are checked by default; Glassdoor is available but currently unreliable — see [Known Limitations](#known-limitations)).
4. Apply optional filters:
   - **Job type** — full-time, part-time, contract, or internship
   - **Experience level** — junior, mid-level, or senior (applied as a keyword filter on titles and descriptions)
   - **Salary range** — minimum and/or maximum annual salary in GBP
   - **Remote only** — tick to restrict results to remote positions
   - **Max results** — number of results to request per site (default: 50)
5. Click **Search Jobs**.

Searching typically takes 15–30 seconds depending on how many sites are selected.

### Reading results

Each job card shows:

- Job title, company, and location
- Site badge (colour-coded by source)
- Job type and date posted
- Salary range (where available)
- A snippet of the job description (click **Show more** to expand)
- A **View listing** button linking directly to the original posting
- A **Remove** button to delete the card from your saved results

### Deduplication feedback

After each search, the status bar reports:

> Found **12** jobs — **8** new, **4** already seen.

"Already seen" means those URLs were already in your local database from a previous search.

### Search history

All past searches appear in the sidebar on the left. Click any entry to reload the saved results for that search without making new network requests.

### Site error warnings

If a job board rejects the request or returns no results, a yellow warning banner appears listing the affected sites and their error messages. Results from successful sites are still displayed.

---

## API Reference

The Flask backend exposes a JSON API that the frontend uses. You can also call it directly (e.g. with `curl` or a REST client).

### `POST /api/search`

Run a new search and save results to the database.

**Request body (JSON):**

```json
{
  "query": "Python developer",
  "location": "London",
  "sites": ["indeed", "linkedin"],
  "job_type": "fulltime",
  "experience_level": "senior",
  "is_remote": false,
  "results_wanted": 50,
  "hours_old": 72,
  "salary_min": 50000,
  "salary_max": 90000
}
```

| Field              | Type    | Required | Description                                                        |
| ------------------ | ------- | -------- | ------------------------------------------------------------------ |
| `query`            | string  | Yes      | Job title or keyword                                               |
| `location`         | string  | No       | City or region                                                     |
| `sites`            | array   | No       | `["indeed", "linkedin", "glassdoor"]` (default: indeed + linkedin) |
| `job_type`         | string  | No       | `fulltime`, `parttime`, `contract`, `internship`                   |
| `experience_level` | string  | No       | `junior`, `mid`, `senior`                                          |
| `is_remote`        | boolean | No       | `true` to filter remote-only                                       |
| `results_wanted`   | integer | No       | Max results per site (default: 50)                                 |
| `hours_old`        | integer | No       | Max age of listings in hours (default: 72)                         |
| `salary_min`       | number  | No       | Minimum salary                                                     |
| `salary_max`       | number  | No       | Maximum salary                                                     |

**Response:**

```json
{
  "search_id": 3,
  "total_found": 12,
  "new": 8,
  "already_seen": 4,
  "jobs": [ ... ],
  "site_errors": [
    { "site": "glassdoor", "error": "Error encountered in API response" }
  ]
}
```

---

### `GET /api/jobs`

Retrieve all saved jobs. Supports optional query parameters:

| Parameter   | Description                                        |
| ----------- | -------------------------------------------------- |
| `site`      | Filter by site (`indeed`, `linkedin`, `glassdoor`) |
| `job_type`  | Filter by job type                                 |
| `search_id` | Return only jobs from a specific search            |

---

### `GET /api/jobs/<id>`

Retrieve a single job by its database ID.

---

### `DELETE /api/jobs/<id>`

Delete a job from the database.

---

### `GET /api/searches`

Return all past searches, most recent first.

---

## Testing

### Unit and integration tests

These run without making any network requests (the scraper is mocked):

```bash
bash run_tests.sh
```

Or directly with pytest:

```bash
pytest tests/ -v -m "not live"
```

The test suite includes:

- **`test_database.py`** — 12 tests covering schema creation, insert, query, deduplication, filtering, and deletion
- **`test_api.py`** — 14 tests covering all API endpoints using Flask's test client

### Live site health checks

To test whether each job board is actually reachable and returning results:

```bash
python3 tests/test_scraper.py
```

This makes real network requests and prints a per-site summary:

```
=======================================================
  Job Site Health Check
  Query: 'software engineer' | Location: 'London'
=======================================================

  Checking indeed... OK  (3 results returned)
  Checking linkedin... OK  (3 results returned)
  Checking glassdoor... WARNING  — 0 results (possibly blocked or a slow day)

=======================================================
  Summary
=======================================================
  ✓  indeed       ok  (3 results)
  ✓  linkedin     ok  (3 results)
  ⚠  glassdoor    no_results
```

You can also run the live tests via pytest:

```bash
pytest tests/test_scraper.py -m live -v
```

---

## Known Limitations

### Glassdoor

Glassdoor's internal GraphQL API is currently rejecting requests from `python-jobspy` with `"Error encountered in API response"`. This appears to be a bot-detection measure on Glassdoor's side. As of `python-jobspy` v1.1.82 (the latest release), there is no workaround available.

Glassdoor is unchecked by default in the UI. You can still select it — results will appear if the block is lifted — but expect zero results in most cases.

### LinkedIn

LinkedIn does not provide an official public job search API. `python-jobspy` accesses LinkedIn without authentication, which works until LinkedIn detects and blocks the requests. Failures are intermittent and typically resolve on their own.

### Rate limiting and blocks

Running very frequent or high-volume searches increases the likelihood of being temporarily blocked by any of the job boards. If you encounter consistent failures, wait a few hours before searching again.

### Terms of Service

Scraping job boards may conflict with their Terms of Service. This tool is intended for personal, non-commercial use only. Use responsibly.

---

## Licence

MIT

---

_Built with assistance from [GitHub Copilot](https://github.com/features/copilot), powered by **Claude Sonnet 4.6**. Styled with [Pico CSS](https://picocss.com/) (MIT licence)._
