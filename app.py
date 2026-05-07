from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else reads env vars

from flask import Flask, jsonify, request, send_from_directory

import database
import expander
import scraper

app = Flask(__name__, static_folder="static")

# init_db() is NOT called at module level so tests can inject their own DB path.
# Call database.init_db() before app.run() (see __main__ block below).


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/search", methods=["POST"])
def search():
    data = request.get_json(force=True) or {}

    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400

    location = (data.get("location") or "").strip()
    sites = data.get("sites") or ["indeed", "linkedin"]
    job_type = data.get("job_type") or None
    is_remote = bool(data.get("is_remote", False))
    experience_level = data.get("experience_level") or None

    try:
        results_wanted = int(data.get("results_wanted", 50))
        hours_old = int(data.get("hours_old", 72))
    except (TypeError, ValueError):
        return jsonify({"error": "results_wanted and hours_old must be integers"}), 400

    salary_min = None
    try:
        if data.get("salary_min") not in (None, ""):
            salary_min = float(data["salary_min"])
    except (TypeError, ValueError):
        return jsonify({"error": "salary_min must be a number"}), 400

    # --- AI query expansion ---
    expansion = expander.expand_query(query)
    terms = expansion["terms"]

    # Use AI-detected seniority only if the user didn't explicitly choose one
    effective_experience = experience_level or expansion["experience_level"]

    # --- Scrape each expanded term, deduplicate by URL ---
    all_jobs = []
    all_site_errors = []
    seen_urls = set()

    for term in terms:
        jobs, errors = scraper.scrape(
            query=term,
            location=location,
            sites=sites,
            job_type=job_type,
            is_remote=is_remote,
            results_wanted=results_wanted,
            hours_old=hours_old,
            salary_min=salary_min,
            salary_max=None,
            experience_level=effective_experience,
        )
        for job in jobs:
            url = job.get("url", "")
            if url and url in seen_urls:
                continue
            seen_urls.add(url)
            all_jobs.append(job)

        # Collect site errors without duplicating per-site entries
        for err in errors:
            if not any(e["site"] == err["site"] for e in all_site_errors):
                all_site_errors.append(err)

    search_id = database.insert_search(
        query=query,
        location=location,
        job_type=job_type,
        experience_level=effective_experience,
        is_remote=is_remote,
    )
    inserted, skipped = database.insert_jobs(search_id, all_jobs)

    return jsonify(
        {
            "search_id": search_id,
            "total_found": len(all_jobs),
            "new": inserted,
            "already_seen": skipped,
            "jobs": all_jobs,
            "site_errors": all_site_errors,
            "expansion": {
                "terms": terms,
                "experience_level_detected": expansion["experience_level"],
                "summary": expansion["summary"],
                "used_ai": expansion["expanded"],
            },
        }
    )


@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    filters = {}
    if request.args.get("site"):
        filters["site"] = request.args["site"]
    if request.args.get("job_type"):
        filters["job_type"] = request.args["job_type"]
    if request.args.get("search_id"):
        try:
            filters["search_id"] = int(request.args["search_id"])
        except ValueError:
            return jsonify({"error": "search_id must be an integer"}), 400
    return jsonify(database.get_jobs(filters))


@app.route("/api/jobs/<int:job_id>", methods=["GET"])
def get_job(job_id):
    job = database.get_job(job_id)
    if not job:
        return jsonify({"error": "not found"}), 404
    return jsonify(job)


@app.route("/api/jobs/<int:job_id>", methods=["DELETE"])
def delete_job(job_id):
    if not database.delete_job(job_id):
        return jsonify({"error": "not found"}), 404
    return jsonify({"deleted": True})


@app.route("/api/searches", methods=["GET"])
def get_searches():
    return jsonify(database.get_searches())


if __name__ == "__main__":
    database.init_db()
    app.run(debug=True, port=5000)
