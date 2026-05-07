from flask import Flask, jsonify, request, send_from_directory

import database
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
    salary_max = None
    try:
        if data.get("salary_min") not in (None, ""):
            salary_min = float(data["salary_min"])
        if data.get("salary_max") not in (None, ""):
            salary_max = float(data["salary_max"])
    except (TypeError, ValueError):
        return jsonify({"error": "salary values must be numbers"}), 400

    jobs, site_errors = scraper.scrape(
        query=query,
        location=location,
        sites=sites,
        job_type=job_type,
        is_remote=is_remote,
        results_wanted=results_wanted,
        hours_old=hours_old,
        salary_min=salary_min,
        salary_max=salary_max,
        experience_level=experience_level,
    )

    search_id = database.insert_search(
        query=query,
        location=location,
        job_type=job_type,
        experience_level=experience_level,
        is_remote=is_remote,
    )
    inserted, skipped = database.insert_jobs(search_id, jobs)

    return jsonify(
        {
            "search_id": search_id,
            "total_found": len(jobs),
            "new": inserted,
            "already_seen": skipped,
            "jobs": jobs,
            "site_errors": site_errors,
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
