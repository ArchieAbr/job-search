"""
expander.py — Natural language query expansion using Gemini 2.5 Flash.

Takes a free-text job search intent (e.g. "graduate computer science student"
or "creative industry") and returns specific, searchable job titles plus an
auto-detected seniority level.

If GEMINI_API_KEY is not set, or if the google-genai package is not installed,
the module falls back silently: the raw query is returned unchanged and the app
continues to work without AI expansion.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a job search assistant helping someone find jobs on UK job boards (Indeed, LinkedIn, Glassdoor).

A user has described what they are looking for in natural language. Your tasks:

1. Return up to 5 specific, concise job titles that best capture their intent and will return relevant results on a job board. Titles should be realistic search terms (e.g. "UX Designer", "Graduate Software Engineer"), not vague descriptions.
2. Detect the seniority level ONLY if clearly indicated:
   - "junior" for: graduate, entry-level, junior, new to the field, recently graduated
   - "mid" for: mid-level, 2-5 years experience, intermediate
   - "senior" for: senior, lead, principal, staff, head of
   - null if not specified or ambiguous
3. Do NOT embed seniority words inside the job title strings — capture it only in experience_level.
4. Write a one-sentence summary of what you understood the user to be looking for.

Respond ONLY with valid JSON. No markdown fences, no explanation outside the JSON.

Format:
{
  "terms": ["Job Title 1", "Job Title 2", "Job Title 3"],
  "experience_level": "junior" | "mid" | "senior" | null,
  "summary": "One sentence explaining what was understood."
}"""


# ---------------------------------------------------------------------------
# Lazy client initialisation
# ---------------------------------------------------------------------------

_client = None


def _get_client():
    """Return a Gemini client, or None if the SDK/key is unavailable."""
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        from google import genai  # google-genai package

        _client = genai.Client(api_key=api_key)
        return _client
    except ImportError:
        logger.warning(
            "google-genai is not installed; query expansion disabled. "
            "Run: pip install google-genai"
        )
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def expand_query(query: str) -> dict:
    """Expand a natural-language job search query into specific job titles.

    Returns a dict:
        terms           list[str]   — job titles to search (1–5 items)
        experience_level str|None   — "junior" | "mid" | "senior" | None
        summary         str|None    — human-readable explanation from Gemini
        expanded        bool        — True if Gemini was used; False = fallback
    """
    client = _get_client()

    if client is None:
        return {
            "terms": [query],
            "experience_level": None,
            "summary": None,
            "expanded": False,
        }

    try:
        from google.genai import types

        prompt = f'{_SYSTEM_PROMPT}\n\nUser query: "{query}"'

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )

        data = json.loads(response.text)

        terms = [t for t in (data.get("terms") or []) if isinstance(t, str) and t.strip()]
        if not terms:
            terms = [query]

        return {
            "terms": terms[:5],
            "experience_level": data.get("experience_level") or None,
            "summary": data.get("summary") or None,
            "expanded": True,
        }

    except Exception as exc:
        logger.warning("Gemini expansion failed, falling back to raw query: %s", exc)
        return {
            "terms": [query],
            "experience_level": None,
            "summary": None,
            "expanded": False,
        }


# ---------------------------------------------------------------------------
# CV analysis
# ---------------------------------------------------------------------------

_CV_SYSTEM_PROMPT = """You are a career advisor and job search assistant helping someone in the UK find jobs that match their CV.

You will be given the full text of a person's CV (resume). Your tasks:

1. Identify up to 6 specific, searchable job titles that this person is well-suited for based on their experience, skills, and qualifications. These should be realistic job board search terms (e.g. "Marketing Manager", "Data Analyst", "UX Designer").
2. Extract a concise list of their top 8 skills (technical skills, tools, languages, or domain expertise).
3. Detect their seniority level:
   - "junior" — student, graduate, 0-2 years experience
   - "mid" — 2-5 years experience
   - "senior" — 5+ years, lead/manager/head roles
4. Write a 1-2 sentence professional summary of who this person is and what roles suit them.

Respond ONLY with valid JSON. No markdown fences, no explanation.

Format:
{
  "terms": ["Job Title 1", "Job Title 2"],
  "skills": ["Skill 1", "Skill 2"],
  "experience_level": "junior" | "mid" | "senior" | null,
  "summary": "A brief professional summary."
}"""


def analyze_cv(cv_text: str) -> dict:
    """Analyse CV text using Gemini and return job search terms + profile info.

    Returns a dict:
        terms            list[str]   — job titles to search (1–6 items)
        skills           list[str]   — extracted top skills
        experience_level str|None   — "junior" | "mid" | "senior" | None
        summary          str|None   — professional summary from Gemini
        analyzed         bool        — True if Gemini was used; False = fallback
    """
    client = _get_client()

    if client is None:
        return {
            "terms": [],
            "skills": [],
            "experience_level": None,
            "summary": None,
            "analyzed": False,
            "error": "GEMINI_API_KEY is not set. CV analysis requires a Gemini API key.",
        }

    try:
        from google.genai import types

        prompt = f"{_CV_SYSTEM_PROMPT}\n\nCV text:\n\"\"\"\n{cv_text}\n\"\"\""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        data = json.loads(response.text)

        terms = [t for t in (data.get("terms") or []) if isinstance(t, str) and t.strip()]
        skills = [s for s in (data.get("skills") or []) if isinstance(s, str) and s.strip()]

        return {
            "terms": terms[:6],
            "skills": skills[:8],
            "experience_level": data.get("experience_level") or None,
            "summary": data.get("summary") or None,
            "analyzed": True,
        }

    except Exception as exc:
        logger.warning("Gemini CV analysis failed: %s", exc)
        return {
            "terms": [],
            "skills": [],
            "experience_level": None,
            "summary": None,
            "analyzed": False,
            "error": f"CV analysis failed: {exc}",
        }

