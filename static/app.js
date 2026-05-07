/* ============================================================
   app.js — Job Search front-end logic
   ============================================================ */

const form = document.getElementById("search-form");
const searchBtn = document.getElementById("search-btn");
const statusBar = document.getElementById("status-bar");
const siteErrorsEl = document.getElementById("site-errors");
const resultsTableContainer = document.getElementById(
  "results-table-container",
);
const emptyState = document.getElementById("empty-state");
const historyList = document.getElementById("history-list");

// ---------------------------------------------------------------
// Initialise
// ---------------------------------------------------------------
loadHistory();

// ---------------------------------------------------------------
// Form submit
// ---------------------------------------------------------------
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const query = document.getElementById("query").value.trim();
  if (!query) {
    showStatus("Please enter a job title or keyword.", "error");
    return;
  }

  const sites = [
    ...document.querySelectorAll('input[name="sites"]:checked'),
  ].map((cb) => cb.value);
  if (sites.length === 0) {
    showStatus("Please select at least one site.", "error");
    return;
  }

  const resultsWanted =
    parseInt(document.getElementById("results_wanted").value, 10) || 50;

  const payload = {
    query,
    location: document.getElementById("location").value.trim() || "",
    sites,
    job_type: document.getElementById("job_type").value || null,
    experience_level: document.getElementById("experience_level").value || null,
    is_remote: document.getElementById("is_remote").checked,
    results_wanted: resultsWanted,
    salary_min: parseNumberOrNull("salary_min"),
  };

  const siteLabels = sites.map(capitalise).join(", ");

  setLoading(true);
  showStatus(
    `<span class="spinner"></span> Searching <strong>${siteLabels}</strong> — this may take 15–30 seconds…`,
  );
  clearSiteErrors();
  renderJobs([]);

  try {
    const res = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      showStatus(data.error || "Search failed.", "error");
      return;
    }

    showStatus(buildSearchSummary(data));

    if (data.site_errors && data.site_errors.length > 0) {
      showSiteErrors(data.site_errors);
    }

    renderJobs(data.jobs);
    await loadHistory();
  } catch (err) {
    showStatus("Could not reach the server. Is Flask running?", "error");
    console.error(err);
  } finally {
    setLoading(false);
  }
});

// ---------------------------------------------------------------
// Render results table
// ---------------------------------------------------------------
function renderJobs(jobs) {
  resultsTableContainer.innerHTML = "";

  if (!jobs || jobs.length === 0) {
    emptyState.textContent = "No jobs found. Try broadening your search.";
    emptyState.classList.remove("hidden");
    return;
  }

  emptyState.classList.add("hidden");

  const rows = jobs
    .map((job) => {
      const salary = formatSalary(job);
      const badgeCls = `badge-${(job.site || "other").toLowerCase()}`;
      const titleCell = job.url
        ? `<a href="${escapeHtml(job.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(job.title || "Untitled")}</a>`
        : escapeHtml(job.title || "Untitled");
      const snippet = (job.description_snippet || "").trim();

      return `
        <tr data-id="${job.id || ""}">
          <td class="col-title">
            ${titleCell}
            ${snippet ? `<p class="row-snippet">${escapeHtml(snippet.slice(0, 160))}${snippet.length > 160 ? "…" : ""}</p>` : ""}
          </td>
          <td>${cell(job.company)}</td>
          <td>${cell(job.location)}</td>
          <td class="col-salary">${salary ? escapeHtml(salary) : dash()}</td>
          <td>${cell(job.job_type)}</td>
          <td>${cell(job.date_posted)}</td>
          <td><span class="site-badge ${badgeCls}">${escapeHtml(job.site || "unknown")}</span></td>
          <td class="col-actions">
            ${job.id ? `<button class="btn-remove" onclick="removeJob(${job.id}, this)" aria-label="Remove">✕</button>` : ""}
          </td>
        </tr>`;
    })
    .join("");

  resultsTableContainer.innerHTML = `
    <div class="table-wrapper">
      <table class="results-table">
        <thead>
          <tr>
            <th>Job Title</th>
            <th>Company</th>
            <th>Location</th>
            <th>Salary</th>
            <th>Type</th>
            <th>Date Posted</th>
            <th>Source</th>
            <th></th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function cell(value) {
  return value && value.trim() !== "" ? escapeHtml(value) : dash();
}

function dash() {
  return '<span class="not-found" aria-label="Not available">—</span>';
}

function buildSearchSummary(data) {
  // Per-site counts computed client-side from the returned jobs list
  const counts = {};
  (data.jobs || []).forEach((j) => {
    const s = j.site || "unknown";
    counts[s] = (counts[s] || 0) + 1;
  });
  const badges = Object.entries(counts)
    .map(
      ([s, n]) =>
        `<span class="site-count-badge badge-${s}">${capitalise(s)}: ${n}</span>`,
    )
    .join(" ");

  return (
    `Found <strong>${data.total_found}</strong> job${data.total_found !== 1 ? "s" : ""}` +
    (badges ? ` &nbsp;${badges}` : "") +
    ` — <strong>${data.new}</strong> new, <strong>${data.already_seen}</strong> already seen.`
  );
}

// ---------------------------------------------------------------
// Remove a job
// ---------------------------------------------------------------
async function removeJob(jobId, btn) {
  try {
    const res = await fetch(`/api/jobs/${jobId}`, { method: "DELETE" });
    if (res.ok) {
      const row = btn.closest("tr");
      row.remove();
      const tbody = resultsTableContainer.querySelector("tbody");
      if (!tbody || tbody.children.length === 0) {
        resultsTableContainer.innerHTML = "";
        emptyState.textContent = "No jobs found. Try broadening your search.";
        emptyState.classList.remove("hidden");
      }
    }
  } catch (err) {
    console.error("Failed to remove job:", err);
  }
}

// ---------------------------------------------------------------
// History
// ---------------------------------------------------------------
async function loadHistory() {
  try {
    const res = await fetch("/api/searches");
    const searches = await res.json();

    if (!Array.isArray(searches) || searches.length === 0) {
      historyList.innerHTML = '<li class="empty-item">No searches yet.</li>';
      return;
    }

    historyList.innerHTML = "";
    searches.forEach((s) => {
      const li = document.createElement("li");
      li.dataset.searchId = s.id;
      li.innerHTML = `
        <span class="hist-query">${escapeHtml(s.query)}</span>
        <span class="hist-meta">${s.location ? escapeHtml(s.location) + " · " : ""}${formatDate(s.date_run)}</span>
      `;
      li.addEventListener("click", () => loadHistoryResults(s.id, li));
      historyList.appendChild(li);
    });
  } catch (err) {
    console.error("Failed to load history:", err);
  }
}

async function loadHistoryResults(searchId, li) {
  document
    .querySelectorAll("#history-list li")
    .forEach((el) => el.classList.remove("active-item"));
  li.classList.add("active-item");

  try {
    const res = await fetch(`/api/jobs?search_id=${searchId}`);
    const jobs = await res.json();
    clearSiteErrors();
    showStatus(
      `Showing saved results for search #${searchId} — ${jobs.length} job${jobs.length !== 1 ? "s" : ""}.`,
    );
    renderJobs(jobs);
  } catch (err) {
    console.error("Failed to load history results:", err);
  }
}

// ---------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------
function setLoading(loading) {
  searchBtn.disabled = loading;
  searchBtn.textContent = loading ? "Searching…" : "Search Jobs";
}

function showStatus(html, type = "info") {
  statusBar.innerHTML = html;
  statusBar.className = "status-bar" + (type === "error" ? " error" : "");
  statusBar.classList.remove("hidden");
}

function showSiteErrors(errors) {
  const items = errors
    .map(
      (e) =>
        `<li><strong>${escapeHtml(e.site)}</strong>: ${escapeHtml(e.error || "no results returned")}</li>`,
    )
    .join("");
  siteErrorsEl.innerHTML = `<strong>⚠ Some sites had issues:</strong><ul>${items}</ul>`;
  siteErrorsEl.classList.remove("hidden");
}

function clearSiteErrors() {
  siteErrorsEl.classList.add("hidden");
  siteErrorsEl.innerHTML = "";
}

function parseNumberOrNull(id) {
  const val = document.getElementById(id).value;
  const n = parseFloat(val);
  return val && !isNaN(n) ? n : null;
}

function formatSalary(job) {
  if (!job.salary_min && !job.salary_max) return "";
  const interval = job.salary_interval ? ` / ${job.salary_interval}` : "";
  if (job.salary_min && job.salary_max) {
    return `£${fmt(job.salary_min)} – £${fmt(job.salary_max)}${interval}`;
  }
  const val = job.salary_max || job.salary_min;
  return `£${fmt(val)}${interval}`;
}

function fmt(n) {
  return Number(n).toLocaleString("en-GB");
}

function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
    });
  } catch {
    return iso.slice(0, 10);
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function capitalise(str) {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}
