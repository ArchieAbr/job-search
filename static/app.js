/* ============================================================
   app.js — Job Search front-end logic
   ============================================================ */

const form = document.getElementById("search-form");
const searchBtn = document.getElementById("search-btn");
const statusBar = document.getElementById("status-bar");
const progressContainer = document.getElementById("progress-container");
const progressMsg = document.getElementById("progress-msg");
const progressSub = document.getElementById("progress-sub");
const progressFill = document.getElementById("progress-fill");
const progressPct = document.getElementById("progress-pct");
const expansionPanel = document.getElementById("expansion-panel");
const siteErrorsEl = document.getElementById("site-errors");
const resultsTableContainer = document.getElementById(
  "results-table-container",
);
const emptyState = document.getElementById("empty-state");
const historyList = document.getElementById("history-list");

// ---------------------------------------------------------------
// Mode toggle
// ---------------------------------------------------------------
let currentMode = "standard"; // "standard" | "ai" | "cv"
let cvAnalysis = null; // Stores the last successful CV analysis result

const modeHint = document.getElementById("mode-hint");
const queryInput = document.getElementById("query");
const queryLabel = document.querySelector('label[for="query"]');
const cvUploadArea = document.getElementById("cv-upload-area");
const cvFileInput = document.getElementById("cv-file-input");
const cvStatusEl = document.getElementById("cv-status");
const cvDropzone = document.getElementById("cv-dropzone");

document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document
      .querySelectorAll(".mode-btn")
      .forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentMode = btn.dataset.mode;

    if (currentMode === "ai") {
      queryInput.placeholder =
        "e.g. creative industry, graduate computer science";
      queryInput.required = true;
      queryLabel.innerHTML =
        'Job title / keyword <span class="required">*</span>';
      modeHint.textContent =
        "Describe what you're looking for — AI will find the best matching roles";
      cvUploadArea.classList.add("hidden");
    } else if (currentMode === "cv") {
      queryInput.placeholder = "Optional — leave blank to use only your CV";
      queryInput.required = false;
      queryLabel.innerHTML =
        'Additional keywords <span class="mode-optional">(optional)</span>';
      modeHint.textContent =
        "Upload your CV — Gemini will find roles that match your experience";
      cvUploadArea.classList.remove("hidden");
    } else {
      queryInput.placeholder = "e.g. Python Developer";
      queryInput.required = true;
      queryLabel.innerHTML =
        'Job title / keyword <span class="required">*</span>';
      modeHint.textContent = "Enter a specific job title or keyword";
      cvUploadArea.classList.add("hidden");
    }
  });
});

// ---------------------------------------------------------------
// CV file upload + analysis
// ---------------------------------------------------------------

// Drag-and-drop visual feedback
cvDropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  cvDropzone.classList.add("cv-dragover");
});
cvDropzone.addEventListener("dragleave", () =>
  cvDropzone.classList.remove("cv-dragover"),
);
cvDropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  cvDropzone.classList.remove("cv-dragover");
  const file = e.dataTransfer.files[0];
  if (file) handleCvFile(file);
});

cvFileInput.addEventListener("change", () => {
  if (cvFileInput.files[0]) handleCvFile(cvFileInput.files[0]);
});

async function handleCvFile(file) {
  cvAnalysis = null;
  cvDropzone.classList.remove("cv-analyzed");

  // Show loading state
  cvStatusEl.className = "cv-status cv-status-loading";
  cvStatusEl.innerHTML =
    '<span class="cv-spinner"></span> Analysing your CV with Gemini…';
  cvStatusEl.classList.remove("hidden");
  cvDropzone.querySelector(".cv-drop-primary").textContent = `📄 ${file.name}`;

  const formData = new FormData();
  formData.append("cv", file);

  try {
    const res = await fetch("/api/analyze-cv", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (!res.ok) {
      cvStatusEl.className = "cv-status cv-status-error";
      cvStatusEl.innerHTML = `⚠ ${escapeHtml(data.error || "Analysis failed.")}`;
      return;
    }

    cvAnalysis = data;
    cvDropzone.classList.add("cv-analyzed");

    const skillPills = (data.skills || [])
      .map((s) => `<span class="expansion-term">${escapeHtml(s)}</span>`)
      .join(" ");
    const levelBadge = data.experience_level
      ? ` · <strong>${escapeHtml(data.experience_level)}</strong> level`
      : "";
    const summary = data.summary
      ? `<p class="cv-summary">${escapeHtml(data.summary)}</p>`
      : "";

    cvStatusEl.className = "cv-status cv-status-ok";
    cvStatusEl.innerHTML = `
      <div class="cv-result-header">✦ CV analysed${levelBadge}</div>
      ${summary}
      <div class="cv-skills-row">${skillPills}</div>
      <p class="cv-will-search">Will search for: ${(data.terms || []).map((t) => `<em>${escapeHtml(t)}</em>`).join(", ")}</p>`;
  } catch (err) {
    cvStatusEl.className = "cv-status cv-status-error";
    cvStatusEl.innerHTML = "⚠ Could not reach the server.";
    console.error(err);
  }
}

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

  // In CV mode the query is optional but we need a CV analysis
  if (currentMode === "cv") {
    if (!cvAnalysis) {
      showStatus(
        "Please upload and analyse your CV before searching.",
        "error",
      );
      return;
    }
  } else {
    if (!query) {
      showStatus("Please enter a job title or keyword.", "error");
      return;
    }
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

  // Build payload — in CV mode inject the CV-derived terms
  let payload;
  if (currentMode === "cv") {
    payload = {
      query: query || cvAnalysis.terms[0] || "",
      cv_terms: cvAnalysis.terms,
      cv_experience_level: cvAnalysis.experience_level,
      location: document.getElementById("location").value.trim() || "",
      sites,
      job_type: document.getElementById("job_type").value || null,
      experience_level:
        document.getElementById("experience_level").value ||
        cvAnalysis.experience_level ||
        null,
      is_remote: document.getElementById("is_remote").checked,
      results_wanted: resultsWanted,
      salary_min: parseNumberOrNull("salary_min"),
      use_ai: false,
      use_cv: true,
    };
  } else {
    payload = {
      query,
      location: document.getElementById("location").value.trim() || "",
      sites,
      job_type: document.getElementById("job_type").value || null,
      experience_level:
        document.getElementById("experience_level").value || null,
      is_remote: document.getElementById("is_remote").checked,
      results_wanted: resultsWanted,
      salary_min: parseNumberOrNull("salary_min"),
      use_ai: currentMode === "ai",
      use_cv: false,
    };
  }

  searchBtn.disabled = true;
  searchBtn.textContent = "Searching…";
  startProgress(sites, currentMode !== "standard");
  clearExpansion();
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
      stopProgress(false);
      showStatus(data.error || "Search failed.", "error");
      return;
    }

    stopProgress();
    showStatus(buildSearchSummary(data));

    if (currentMode === "cv" && cvAnalysis) {
      showCvExpansion(cvAnalysis, data.expansion);
    } else {
      showExpansion(data.expansion);
    }

    if (data.site_errors && data.site_errors.length > 0) {
      showSiteErrors(data.site_errors);
    }

    renderJobs(data.jobs);
    await loadHistory();
  } catch (err) {
    stopProgress(false);
    showStatus("Could not reach the server. Is Flask running?", "error");
    console.error(err);
  } finally {
    searchBtn.disabled = false;
    searchBtn.textContent = "Search Jobs";
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
    const clearAllBtn = document.getElementById("clear-all-btn");

    if (!Array.isArray(searches) || searches.length === 0) {
      historyList.innerHTML = '<li class="empty-item">No searches yet.</li>';
      if (clearAllBtn) clearAllBtn.disabled = true;
      return;
    }

    if (clearAllBtn) clearAllBtn.disabled = false;
    historyList.innerHTML = "";
    searches.forEach((s) => {
      const li = document.createElement("li");
      li.dataset.searchId = s.id;
      li.innerHTML = `
        <div class="hist-text">
          <span class="hist-query">${escapeHtml(s.query)}</span>
          <span class="hist-meta">${s.location ? escapeHtml(s.location) + " · " : ""}${formatDate(s.date_run)}</span>
        </div>
        <button class="btn-delete-search" title="Delete this search" aria-label="Delete search">✕</button>
      `;
      li.querySelector(".hist-text").addEventListener("click", () =>
        loadHistoryResults(s.id, li),
      );
      li.querySelector(".btn-delete-search").addEventListener("click", (e) => {
        e.stopPropagation();
        deleteSearch(s.id, li);
      });
      historyList.appendChild(li);
    });
  } catch (err) {
    console.error("Failed to load history:", err);
  }
}

async function deleteSearch(searchId, li) {
  try {
    const res = await fetch(`/api/searches/${searchId}`, { method: "DELETE" });
    if (res.ok) {
      li.remove();
      if (historyList.children.length === 0) {
        historyList.innerHTML = '<li class="empty-item">No searches yet.</li>';
        const clearAllBtn = document.getElementById("clear-all-btn");
        if (clearAllBtn) clearAllBtn.disabled = true;
      }
      // If the deleted search's results are currently showing, clear them
      renderJobs([]);
      clearSiteErrors();
      clearExpansion();
      statusBar.classList.add("hidden");
    }
  } catch (err) {
    console.error("Failed to delete search:", err);
  }
}

document.getElementById("clear-all-btn").addEventListener("click", async () => {
  if (!confirm("Delete all search history and saved jobs?")) return;
  try {
    await fetch("/api/searches", { method: "DELETE" });
    historyList.innerHTML = '<li class="empty-item">No searches yet.</li>';
    document.getElementById("clear-all-btn").disabled = true;
    renderJobs([]);
    clearSiteErrors();
    clearExpansion();
    statusBar.classList.add("hidden");
  } catch (err) {
    console.error("Failed to clear history:", err);
  }
});

async function loadHistoryResults(searchId, li) {
  document
    .querySelectorAll("#history-list li")
    .forEach((el) => el.classList.remove("active-item"));
  li.classList.add("active-item");

  try {
    const res = await fetch(`/api/jobs?search_id=${searchId}`);
    const jobs = await res.json();
    clearSiteErrors();
    clearExpansion();
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

// --- Progress tracker ---
let _progressTimers = [];

function buildStages(sites, useAi) {
  // Timings (ms from search start) are estimates based on real jobspy behaviour.
  // Gemini call: ~1–3s. Per-site scrape: ~15–25s each.
  const stages = useAi
    ? [
        {
          pct: 5,
          msg: "Asking AI to interpret your search…",
          sub: "Sending your query to Gemini 2.5 Flash",
          at: 300,
        },
        {
          pct: 20,
          msg: "Expanding to related job titles…",
          sub: "Identifying the most relevant roles to search for",
          at: 2800,
        },
      ]
    : [
        {
          pct: 10,
          msg: "Preparing search…",
          sub: "Using your query directly",
          at: 300,
        },
      ];

  // Per-site scraping stages — spread 25 % → 88 % across all chosen sites
  const siteStart = useAi ? 25 : 20;
  const siteEnd = 88;
  const pctStep =
    sites.length > 1
      ? (siteEnd - siteStart) / sites.length
      : siteEnd - siteStart;
  const timePerSite = 18000; // 18 s per site estimate
  const siteTimeOffset = useAi ? 4000 : 1000;

  sites.forEach((site, i) => {
    stages.push({
      pct: Math.round(siteStart + i * pctStep),
      msg: `Searching ${capitalise(site)}…`,
      sub: "Scraping live job listings — please wait",
      at: siteTimeOffset + i * timePerSite,
    });
  });

  stages.push({
    pct: 92,
    msg: "Compiling results…",
    sub: "Deduplicating listings across all sources",
    at: siteTimeOffset + sites.length * timePerSite,
  });

  return stages;
}

function setProgress(pct, msg, sub) {
  // rAF ensures the CSS transition fires correctly after width is set
  requestAnimationFrame(() => {
    progressFill.style.width = `${pct}%`;
    progressPct.textContent = `${pct}%`;
    progressMsg.textContent = msg;
    progressSub.textContent = sub || "";
  });
}

function startProgress(sites, useAi = false) {
  statusBar.classList.add("hidden");
  progressContainer.classList.remove("hidden");
  setProgress(2, "Preparing search…", "");

  const stages = buildStages(sites, useAi);
  _progressTimers = stages.map(({ pct, msg, sub, at }) =>
    setTimeout(() => setProgress(pct, msg, sub), at),
  );
}

function stopProgress(success = true) {
  _progressTimers.forEach(clearTimeout);
  _progressTimers = [];

  if (success) {
    setProgress(100, "Done!", "");
    setTimeout(() => progressContainer.classList.add("hidden"), 600);
  } else {
    progressContainer.classList.add("hidden");
  }
}

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

function showExpansion(expansion) {
  if (!expansion || !expansion.used_ai) {
    clearExpansion();
    return;
  }
  const termPills = expansion.terms
    .map((t) => `<span class="expansion-term">${escapeHtml(t)}</span>`)
    .join(" ");
  const levelNote = expansion.experience_level_detected
    ? ` · Auto-detected level: <strong>${escapeHtml(expansion.experience_level_detected)}</strong>`
    : "";
  const summary = expansion.summary
    ? `<p class="expansion-summary">${escapeHtml(expansion.summary)}</p>`
    : "";
  expansionPanel.innerHTML = `
    <span class="expansion-icon">✦</span>
    ${summary}
    <div class="expansion-terms-row">Searched for: ${termPills}${levelNote}</div>`;
  expansionPanel.classList.remove("hidden");
}

function showCvExpansion(analysis, expansion) {
  const termPills = (analysis.terms || [])
    .map((t) => `<span class="expansion-term">${escapeHtml(t)}</span>`)
    .join(" ");
  const skillPills = (analysis.skills || [])
    .map(
      (s) => `<span class="expansion-term skill-pill">${escapeHtml(s)}</span>`,
    )
    .join(" ");
  const levelNote = analysis.experience_level
    ? ` · <strong>${escapeHtml(analysis.experience_level)}</strong> level`
    : "";
  const summary = analysis.summary
    ? `<p class="expansion-summary">${escapeHtml(analysis.summary)}</p>`
    : "";
  expansionPanel.innerHTML = `
    <span class="expansion-icon">📄</span>
    ${summary}
    <div class="expansion-terms-row">Roles searched: ${termPills}${levelNote}</div>
    ${skillPills ? `<div class="expansion-terms-row cv-skills-row-panel">Skills detected: ${skillPills}</div>` : ""}`;
  expansionPanel.classList.remove("hidden");
}

function clearExpansion() {
  expansionPanel.classList.add("hidden");
  expansionPanel.innerHTML = "";
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
