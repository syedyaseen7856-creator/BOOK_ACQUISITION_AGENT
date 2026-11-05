/**
 * SyllExtract Acquisition Agent — Modern Discovery Client Application
 * Handles unified search, explainable identity ranking, genuine reading access,
 * and compliant acquisition workflows.
 */

// Application State
let currentCandidates = [];
let selectedCandidate = null;
let activeSearchRequestId = 0;
let approvedMap = new Map(); // candidate_id -> approvalRecord

// DOM Elements
const searchForm = document.getElementById("search-form");
const mainSearchInput = document.getElementById("main-search-input");
const btnClearSearch = document.getElementById("btn-clear-search");
const btnToggleFilters = document.getElementById("btn-toggle-filters");
const advancedFiltersPanel = document.getElementById("advanced-filters-panel");

// Filter Inputs
const filterAuthor = document.getElementById("filter-author");
const filterIsbn = document.getElementById("filter-isbn");
const filterEdition = document.getElementById("filter-edition");
const filterYear = document.getElementById("filter-year");
const filterSubject = document.getElementById("filter-subject");
const toggleMockMode = document.getElementById("toggle-mock-mode");

// Results Elements
const resultsSection = document.getElementById("results-section");
const resultsToolbar = document.getElementById("results-toolbar");
const resultsCountText = document.getElementById("results-count-text");
const sortSelect = document.getElementById("sort-select");
const booksGrid = document.getElementById("books-grid");

// State Containers
const stateLoading = document.getElementById("state-loading");
const stateEmpty = document.getElementById("state-empty");
const emptyStateTitle = document.getElementById("empty-state-title");
const emptyStateDesc = document.getElementById("empty-state-desc");

// Provider Status Dropdown
const btnProviderStatus = document.getElementById("btn-provider-status");
const providerStatusWrapper = document.getElementById("provider-status-wrapper");
const providerStatusPopover = document.getElementById("provider-status-popover");
const providerStatusList = document.getElementById("provider-status-list");
const providerSummaryDot = document.getElementById("provider-summary-dot");
const providerSummaryText = document.getElementById("provider-summary-text");

// Header Elements
const statusDot = document.getElementById("status-dot");
const statusLabel = document.getElementById("status-label");
const btnOpenAudit = document.getElementById("btn-open-audit");
const auditBadgeCount = document.getElementById("audit-badge-count");

// Modals
const readerModal = document.getElementById("reader-modal");
const readerModalTitle = document.getElementById("reader-modal-title");
const readerModalAuthor = document.getElementById("reader-modal-author");
const readerTypePill = document.getElementById("reader-type-pill");
const readerIframe = document.getElementById("reader-iframe");
const btnReaderExternal = document.getElementById("btn-reader-external");
const btnCloseReader = document.getElementById("btn-close-reader");

const detailsModal = document.getElementById("details-modal");
const detailsModalTitle = document.getElementById("details-modal-title");
const detailsModalBody = document.getElementById("details-modal-body");
const btnCloseDetails = document.getElementById("btn-close-details");

const approvalModal = document.getElementById("approval-modal");
const approvalForm = document.getElementById("approval-form");
const approvalSummaryCard = document.getElementById("approval-summary-card");
const approvalUserId = document.getElementById("approval-user-id");
const approvalPurpose = document.getElementById("approval-purpose");
const approvalNotes = document.getElementById("approval-notes");
const affirmationCheckbox = document.getElementById("affirmation-checkbox");
const btnCancelApproval = document.getElementById("btn-cancel-approval");
const btnCloseApproval = document.getElementById("btn-close-approval");

const downloadModal = document.getElementById("download-modal");
const btnCloseDownload = document.getElementById("btn-close-download");
const btnCancelDownload = document.getElementById("btn-cancel-download");
const btnExecuteDownload = document.getElementById("btn-execute-download");
const simulateDownloadToggle = document.getElementById("simulate-download-toggle");
const downloadResultBox = document.getElementById("download-result-box");
const downloadPreflightInfo = document.getElementById("download-preflight-info");

// Audit Drawer
const auditDrawer = document.getElementById("audit-drawer");
const btnCloseAudit = document.getElementById("btn-close-audit");
const auditItemsList = document.getElementById("audit-items-list");

// Toast Container
const toastContainer = document.getElementById("toast-container");

// ===================================================================
// Initialization & Event Wiring
// ===================================================================
document.addEventListener("DOMContentLoaded", async () => {
  setupEventListeners();
  await checkBackendHealth();
  await loadAuditHistory();
});

function setupEventListeners() {
  // Search Submission
  searchForm.addEventListener("submit", (e) => {
    e.preventDefault();
    executeSearch();
  });

  // Clear button for main search
  mainSearchInput.addEventListener("input", () => {
    btnClearSearch.style.display = mainSearchInput.value ? "block" : "none";
  });
  btnClearSearch.addEventListener("click", () => {
    mainSearchInput.value = "";
    btnClearSearch.style.display = "none";
    mainSearchInput.focus();
  });

  // Advanced Filters Toggle
  btnToggleFilters.addEventListener("click", () => {
    const isExpanded = advancedFiltersPanel.style.display !== "none";
    advancedFiltersPanel.style.display = isExpanded ? "none" : "block";
    btnToggleFilters.setAttribute("aria-expanded", String(!isExpanded));
    btnToggleFilters.classList.toggle("active", !isExpanded);
  });

  // Quick Suggestion Chips
  document.querySelectorAll(".suggestion-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const q = chip.getAttribute("data-query") || "";
      const a = chip.getAttribute("data-author") || "";
      mainSearchInput.value = q;
      btnClearSearch.style.display = "block";
      if (filterAuthor) filterAuthor.value = a;
      executeSearch();
    });
  });

  // Sorting Control
  sortSelect.addEventListener("change", () => {
    sortAndRenderCandidates(sortSelect.value);
  });

  // Provider Status Popover Toggle
  btnProviderStatus.addEventListener("click", (e) => {
    e.stopPropagation();
    const isOpen = providerStatusPopover.style.display !== "none";
    providerStatusPopover.style.display = isOpen ? "none" : "block";
    btnProviderStatus.setAttribute("aria-expanded", String(!isOpen));
  });
  document.addEventListener("click", (e) => {
    if (!providerStatusWrapper.contains(e.target)) {
      providerStatusPopover.style.display = "none";
      btnProviderStatus.setAttribute("aria-expanded", "false");
    }
  });

  // Modal Close buttons
  btnCloseReader.addEventListener("click", () => readerModal.close());
  btnCloseDetails.addEventListener("click", () => detailsModal.close());
  btnCloseApproval.addEventListener("click", () => approvalModal.close());
  btnCancelApproval.addEventListener("click", () => approvalModal.close());
  btnCloseDownload.addEventListener("click", () => downloadModal.close());
  btnCancelDownload.addEventListener("click", () => downloadModal.close());

  // Backdrop clicks for native dialogs
  [readerModal, detailsModal, approvalModal, downloadModal].forEach((dialog) => {
    dialog.addEventListener("click", (e) => {
      const rect = dialog.getBoundingClientRect();
      const inBounds = (
        rect.top <= e.clientY &&
        e.clientY <= rect.top + rect.height &&
        rect.left <= e.clientX &&
        e.clientX <= rect.left + rect.width
      );
      if (!inBounds) dialog.close();
    });
  });

  // Audit Drawer open/close
  btnOpenAudit.addEventListener("click", () => {
    auditDrawer.classList.add("open");
    auditDrawer.setAttribute("aria-hidden", "false");
    loadAuditHistory();
  });
  btnCloseAudit.addEventListener("click", () => {
    auditDrawer.classList.remove("open");
    auditDrawer.setAttribute("aria-hidden", "true");
  });

  // Approval Form Submit
  approvalForm.addEventListener("submit", handleApprovalSubmit);

  // Download Action Execute
  btnExecuteDownload.addEventListener("click", handleDownloadExecute);
}

// ===================================================================
// Search Execution with Stale-Response Protection
// ===================================================================
async function executeSearch() {
  const q = mainSearchInput.value.trim();
  const author = filterAuthor.value.trim();
  const isbn = filterIsbn.value.trim();
  const edition = filterEdition.value.trim();
  const yearStr = filterYear.value.trim();
  const year = yearStr ? parseInt(yearStr, 10) : null;
  const subject = filterSubject.value.trim();
  const useMock = toggleMockMode.checked;

  if (!q && !author && !isbn && !subject) {
    showToast("Please enter a title, author, or ISBN to search.", "warning");
    return;
  }

  // Increment request ID to ignore stale responses
  const currentRequestId = ++activeSearchRequestId;

  // Set Loading UI
  stateEmpty.style.display = "none";
  booksGrid.innerHTML = "";
  resultsToolbar.style.display = "none";
  stateLoading.style.display = "flex";

  const payload = {
    q: q || null,
    title: (author || isbn || edition || year || subject) ? (q || null) : null,
    author: author || null,
    isbn: isbn || null,
    edition: edition || null,
    year: year || null,
    subject: subject || null,
    use_mock_data: useMock
  };

  try {
    const data = await API.searchCandidates(payload);

    // Stale-response protection: if a newer request began, discard this result
    if (currentRequestId !== activeSearchRequestId) {
      return;
    }

    stateLoading.style.display = "none";
    currentCandidates = data.candidates || [];

    // Render Provider Statuses
    updateProviderStatusPill(data.provider_statuses || []);

    if (currentCandidates.length === 0) {
      stateEmpty.style.display = "flex";
      emptyStateTitle.textContent = "No Matching Books Found";
      emptyStateDesc.textContent = useMock
        ? "No candidates matched your query in the offline reference catalog."
        : `Zero records matched "${q || author || isbn}". Try searching by exact ISBN or title.`;
      return;
    }

    // Show Results Toolbar
    resultsToolbar.style.display = "flex";
    resultsCountText.textContent = `${currentCandidates.length} book${currentCandidates.length === 1 ? '' : 's'} discovered`;

    // Render cards using current sort
    sortAndRenderCandidates(sortSelect.value);

  } catch (err) {
    if (currentRequestId !== activeSearchRequestId) return;
    stateLoading.style.display = "none";
    stateEmpty.style.display = "flex";
    emptyStateTitle.textContent = "Search Failed";
    emptyStateDesc.textContent = err.message || "An error occurred while connecting to metadata repositories.";
    showToast(`Search error: ${err.message}`, "error");
  }
}

// ===================================================================
// Provider Status Pill & Popover
// ===================================================================
function updateProviderStatusPill(statuses) {
  providerStatusList.innerHTML = "";
  if (!statuses || statuses.length === 0) {
    providerStatusWrapper.style.display = "none";
    return;
  }

  providerStatusWrapper.style.display = "block";
  let hasSuccess = false;
  let hasLimited = false;

  statuses.forEach((s) => {
    if (s.status === "SUCCESS") hasSuccess = true;
    if (s.status === "RATE_LIMITED" || s.status === "UNAVAILABLE") hasLimited = true;

    const li = document.createElement("li");
    li.className = "provider-status-item";

    let tagClass = "tag-no-results";
    let tagText = s.status;
    if (s.status === "SUCCESS") {
      tagClass = "tag-success";
      tagText = `${s.results_count} found`;
    } else if (s.status === "RATE_LIMITED") {
      tagClass = "tag-limited";
      tagText = "Quota 429";
    } else if (s.status === "UNAVAILABLE") {
      tagClass = "tag-unavailable";
      tagText = "Offline";
    } else if (s.status === "NO_RESULTS") {
      tagClass = "tag-no-results";
      tagText = "0 found";
    }

    li.innerHTML = `
      <span class="provider-name">${escapeHtml(s.provider_name)}</span>
      <span class="provider-tag ${tagClass}">${tagText}</span>
    `;
    providerStatusList.appendChild(li);
  });

  if (hasSuccess) {
    providerSummaryDot.className = "provider-status-dot status-online";
    providerSummaryText.textContent = "Sources Queried";
  } else if (hasLimited) {
    providerSummaryDot.className = "provider-status-dot status-offline";
    providerSummaryText.textContent = "Sources Limited";
  } else {
    providerSummaryDot.className = "provider-status-dot";
    providerSummaryText.textContent = "Sources Ready";
  }
}

// ===================================================================
// Sorting & Candidate Grid Rendering
// ===================================================================
function sortAndRenderCandidates(sortKey) {
  const sorted = [...currentCandidates];

  if (sortKey === "relevance") {
    sorted.sort((a, b) => {
      const sA = a.confidence ? a.confidence.total_score : 0;
      const sB = b.confidence ? b.confidence.total_score : 0;
      return sB - sA;
    });
  } else if (sortKey === "year-desc") {
    sorted.sort((a, b) => (b.published_year || 0) - (a.published_year || 0));
  } else if (sortKey === "year-asc") {
    sorted.sort((a, b) => (a.published_year || 9999) - (b.published_year || 9999));
  } else if (sortKey === "title") {
    sorted.sort((a, b) => (a.title || "").localeCompare(b.title || ""));
  }

  renderCandidateGrid(sorted);
}

function renderCandidateGrid(candidates) {
  booksGrid.innerHTML = "";

  candidates.forEach((c) => {
    const card = document.createElement("article");
    card.className = "book-card";
    card.setAttribute("data-id", c.candidate_id);

    // Score Tier & Badge
    const scoreVal = c.confidence ? c.confidence.total_score : null;
    let scoreBadgeClass = "score-low";
    let scoreLabel = scoreVal !== null ? `${scoreVal}% Match` : "Score N/A";
    if (c.is_approximate_suggestion) {
      scoreBadgeClass = "score-approximate";
      scoreLabel = `${scoreVal}% Suggestion`;
    } else if (scoreVal >= 90) {
      scoreBadgeClass = "score-strong";
    } else if (scoreVal >= 75) {
      scoreBadgeClass = "score-plausible";
    }

    // License Badge
    const lic = c.licensing || {};
    let licBadgeClass = "lic-review";
    let licLabel = "Needs Review";
    if (lic.status === "VERIFIED_FOR_PERMITTED_DOWNLOAD") {
      licBadgeClass = "lic-verified";
      licLabel = lic.license_name || "Verified Permitted";
    } else if (lic.status === "COMMERCIAL_RESTRICTED") {
      licBadgeClass = "lic-restricted";
      licLabel = "Commercial In-Copyright";
    } else if (lic.status === "NOT_ELIGIBLE") {
      licBadgeClass = "lic-not-eligible";
      licLabel = "Not Eligible";
    }

    // Authors string
    const authorsStr = (c.authors && c.authors.length) ? c.authors.join(", ") : "Unknown Author";

    // Media Cover
    const coverHtml = c.thumbnail_url
      ? `<img src="${escapeHtml(c.thumbnail_url)}" alt="${escapeHtml(c.title)} Cover" class="card-cover-img" loading="lazy" onerror="this.onerror=null; this.parentElement.innerHTML='<div class=\\'card-cover-placeholder\\'><svg width=\\'36\\' height=\\'36\\' viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'currentColor\\'><path d=\\'M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z\\'/><path d=\\'M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z\\'/></svg><span>Cover Unavailable</span></div>';">`
      : `<div class="card-cover-placeholder">
           <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor">
             <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
             <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
           </svg>
           <span>Cover Unavailable</span>
         </div>`;

    // Download Button (Only if legally downloadable)
    const isDownloadable = Boolean(lic.is_legally_downloadable);
    const downloadBtnHtml = isDownloadable
      ? `<button type="button" class="btn btn-action-download btn-sm" onclick="initiateApproval('${escapeHtml(c.candidate_id)}')">
           <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
             <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
             <polyline points="7 10 12 15 17 10"></polyline>
             <line x1="12" y1="15" x2="12" y2="3"></line>
           </svg>
           Download
         </button>`
      : "";

    card.innerHTML = `
      <div class="card-cover-container">
        ${coverHtml}
        <div class="card-badges-top">
          <span class="badge-source">${escapeHtml(c.source_name)}</span>
          <span class="badge-score ${scoreBadgeClass}">${scoreLabel}</span>
        </div>
      </div>
      <div class="card-body">
        <h3 class="card-title" title="${escapeHtml(c.title)}">${escapeHtml(c.title)}</h3>
        <p class="card-authors">${escapeHtml(authorsStr)}</p>

        <div class="card-meta-row">
          ${c.published_year ? `<span class="card-meta-pill">${c.published_year}</span>` : ''}
          ${c.edition ? `<span class="card-meta-pill">${escapeHtml(c.edition)}</span>` : ''}
          ${c.page_count ? `<span class="card-meta-pill">${c.page_count} pp.</span>` : ''}
          <span class="card-meta-pill pill-access">${escapeHtml(c.access_type === 'FULL_TEXT' ? 'Full Text' : (c.access_type === 'PREVIEW' ? 'Preview' : 'Publisher Record'))}</span>
        </div>

        <div class="card-license-row">
          <span class="badge-license ${licBadgeClass}">${escapeHtml(licLabel)}</span>
        </div>

        <p class="card-description">${escapeHtml(c.description || 'Bibliographic record cataloged in repository.')}</p>

        <div class="card-actions">
          <button type="button" class="btn btn-secondary btn-sm" onclick="showBookDetails('${escapeHtml(c.candidate_id)}')">
            View Details
          </button>
          <button type="button" class="btn btn-action-read btn-sm" onclick="openReadOnline('${escapeHtml(c.candidate_id)}')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
              <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
            </svg>
            Open / Read Online
          </button>
          ${downloadBtnHtml}
        </div>
      </div>
    `;

    booksGrid.appendChild(card);
  });
}

// ===================================================================
// Book Details Modal View
// ===================================================================
window.showBookDetails = function(candidateId) {
  const c = currentCandidates.find((item) => item.candidate_id === candidateId);
  if (!c) return;

  selectedCandidate = c;
  detailsModalTitle.textContent = c.title;

  const conf = c.confidence || {};
  const lic = c.licensing || {};
  const authorsStr = (c.authors && c.authors.length) ? c.authors.join(", ") : "Unknown";
  const isbnsStr = (c.isbns && c.isbns.length) ? c.isbns.join(", ") : "None Cataloged";

  const coverImgHtml = c.thumbnail_url 
    ? `<img src="${escapeHtml(c.thumbnail_url)}" alt="${escapeHtml(c.title)}" class="details-cover" onerror="this.style.display='none';">` 
    : "";

  detailsModalBody.innerHTML = `
    <div class="details-grid">
      <div class="details-hero">
        ${coverImgHtml}
        <div class="details-main-info">
          <h3 class="details-title">${escapeHtml(c.title)}</h3>
          ${c.subtitle ? `<p style="color: var(--text-secondary); font-size: 0.9rem;">${escapeHtml(c.subtitle)}</p>` : ''}
          <p class="details-authors">By ${escapeHtml(authorsStr)}</p>
          <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem;">
            Source: <a href="${escapeHtml(c.source_url)}" target="_blank" rel="noopener noreferrer" style="color: var(--accent-cyan); text-decoration: underline;">${escapeHtml(c.source_name)}</a>
          </p>
        </div>
      </div>

      <table class="details-table">
        <tbody>
          <tr><th>Publisher</th><td>${escapeHtml(c.publisher || 'Not Specified')}</td></tr>
          <tr><th>Publication Year</th><td>${c.published_year || 'Unknown'}</td></tr>
          <tr><th>Edition</th><td>${escapeHtml(c.edition || 'Standard Edition')}</td></tr>
          <tr><th>ISBN(s)</th><td>${escapeHtml(isbnsStr)}</td></tr>
          <tr><th>Pages & Language</th><td>${c.page_count ? c.page_count + ' pages' : 'Unknown'} • ${escapeHtml((c.language || 'en').toUpperCase())}</td></tr>
          <tr><th>Categories</th><td>${escapeHtml((c.categories || []).join(', ') || 'General / Unclassified')}</td></tr>
        </tbody>
      </table>

      <!-- Confidence Breakdown Card -->
      <div class="score-breakdown-card">
        <div class="score-breakdown-title">
          <span>Deterministic Match Confidence</span>
          <span style="font-family: var(--font-mono); color: var(--accent-cyan);">${conf.total_score || 0}/100 pts (${conf.confidence_tier || 'LOW'})</span>
        </div>
        <ul class="score-factors-list">
          <li class="score-factor-item"><span>Title Match</span><span>${conf.title_score || 0}/30 pts</span></li>
          <li class="score-factor-item"><span>Author Match</span><span>${conf.author_score || 0}/25 pts</span></li>
          <li class="score-factor-item"><span>ISBN Verification</span><span>${conf.isbn_score || 0}/20 pts</span></li>
          <li class="score-factor-item"><span>Edition & Year</span><span>${conf.edition_year_score || 0}/15 pts</span></li>
          <li class="score-factor-item"><span>Publisher Evidence</span><span>${conf.publisher_score || 0}/10 pts</span></li>
        </ul>
        ${(conf.mismatches_and_uncertainty && conf.mismatches_and_uncertainty.length) ? `
          <div style="margin-top: 0.65rem; padding: 0.5rem; background: var(--color-danger-bg); border-radius: var(--radius-sm); font-size: 0.78rem; color: var(--color-danger);">
            <strong>Discrepancies:</strong> ${escapeHtml(conf.mismatches_and_uncertainty.join("; "))}
          </div>
        ` : ''}
      </div>

      <!-- Licensing Evidence Card -->
      <div class="score-breakdown-card">
        <div class="score-breakdown-title">
          <span>Licensing & Acquisition Eligibility</span>
          <span style="font-size: 0.78rem; color: ${lic.is_legally_downloadable ? 'var(--color-success)' : 'var(--color-danger)'}; font-weight: 700;">
            ${lic.is_legally_downloadable ? 'VERIFIED PERMITTED' : 'NOT ELIGIBLE FOR DIRECT DOWNLOAD'}
          </span>
        </div>
        <table class="details-table" style="margin-top: 0.5rem;">
          <tbody>
            <tr><th>Designation</th><td>${escapeHtml(lic.license_name || 'In-Copyright')}</td></tr>
            <tr><th>Rights Statement</th><td>${escapeHtml(lic.rights_statement || 'Standard institutional copyright rules apply.')}</td></tr>
            <tr><th>Verified At</th><td>${escapeHtml(lic.verified_at || 'Just now')}</td></tr>
          </tbody>
        </table>
      </div>

      <div class="modal-footer" style="padding-top: 0.5rem;">
        <button type="button" class="btn btn-secondary" onclick="detailsModal.close()">Close</button>
        <button type="button" class="btn btn-primary" onclick="detailsModal.close(); openBookReader('${escapeHtml(c.candidate_id)}');">
          Open Book ↗
        </button>
      </div>
    </div>
  `;

  detailsModal.showModal();
};

// ===================================================================
// Rule 3 — Open / Read Online Workflow
// ===================================================================
window.openReadOnline = function(candidateId) {
  const c = currentCandidates.find((item) => item.candidate_id === candidateId);
  if (!c) {
    showToast("Candidate record not found in active session.", "error");
    return;
  }

  const accessType = c.access_type || "UNAVAILABLE";
  const accessMsg = c.access_message || "";
  const readerUrl = c.reader_url;
  const previewUrl = c.preview_url;
  const pdfUrl = c.pdf_url;
  const sourceUrl = c.source_url;

  // Case 1: Full text verified
  if (accessType === "FULL_TEXT" && (readerUrl || pdfUrl || sourceUrl)) {
    const target = readerUrl || pdfUrl || sourceUrl;
    if (c.can_embed && c.reader_type === "HTML_READER") {
      readerModalTitle.textContent = c.title;
      readerModalAuthor.textContent = (c.authors || []).join(", ") || c.source_name;
      readerTypePill.textContent = "Full-Text Verified";
      btnReaderExternal.href = target;
      readerIframe.src = target;
      readerModal.showModal();
      showToast(`Launching verified full-text reader for "${c.title}"`, "success");
      return;
    }
    window.open(target, "_blank", "noopener,noreferrer");
    showToast(`Opening verified full text for "${c.title}" in a new tab.`, "success");
    return;
  }

  // Case 2: Preview copy
  if (accessType === "PREVIEW" && (previewUrl || readerUrl || sourceUrl)) {
    const target = previewUrl || readerUrl || sourceUrl;
    window.open(target, "_blank", "noopener,noreferrer");
    showToast(`Opening preview edition (${accessMsg || 'Limited preview'}) for "${c.title}" in a new tab.`, "warning");
    return;
  }

  // Case 3: Official Publisher / Repository Page
  if ((accessType === "PUBLISHER_PAGE" || accessType === "UNAVAILABLE") && (sourceUrl || readerUrl)) {
    const target = sourceUrl || readerUrl;
    window.open(target, "_blank", "noopener,noreferrer");
    showToast(`Direct in-app reader not cataloged. Opening repository landing page for "${c.title}".`, "info");
    return;
  }

  // Case 4: Access Unavailable
  showToast("No online reader, preview, or repository URL is available for this volume.", "error");
};
window.openBookReader = window.openReadOnline;

// ===================================================================
// Phase 6 — Explicit Approval & Compliant Download Workflow
// ===================================================================
window.initiateApproval = function(candidateId) {
  const c = currentCandidates.find((item) => item.candidate_id === candidateId);
  if (!c) return;

  selectedCandidate = c;
  const lic = c.licensing || {};

  approvalSummaryCard.innerHTML = `
    <h4 style="color: var(--text-primary); font-size: 1rem; margin-bottom: 0.35rem;">${escapeHtml(c.title)}</h4>
    <p style="color: var(--text-secondary); font-size: 0.82rem; margin-bottom: 0.5rem;">
      By ${(c.authors || []).join(", ")} • ${c.published_year || 'Unknown year'} • Source: ${escapeHtml(c.source_name)}
    </p>
    <div style="font-size: 0.78rem; color: var(--color-success); font-weight: 600;">
      Verified License: ${escapeHtml(lic.license_name || 'Open Access')}
    </div>
  `;

  approvalUserId.value = "academic-curator@syllextract.local";
  approvalNotes.value = `Verified open educational licensing from ${c.source_name}.`;
  affirmationCheckbox.checked = false;

  approvalModal.showModal();
};

async function handleApprovalSubmit(e) {
  e.preventDefault();
  if (!selectedCandidate) return;

  if (!affirmationCheckbox.checked) {
    showToast("You must affirm compliance before recording approval.", "warning");
    return;
  }

  const payload = {
    approved_by: approvalUserId.value.trim(),
    intended_use_case: approvalPurpose.value,
    affirmation_confirmed: true,
    notes: approvalNotes.value.trim()
  };

  try {
    const approvalRecord = await API.approveCandidate(selectedCandidate.candidate_id, payload);
    approvedMap.set(selectedCandidate.candidate_id, approvalRecord);
    approvalModal.close();
    showToast("Approval formally recorded in persistent SQLite ledger.", "success");
    await loadAuditHistory();

    // Proceed to download preflight modal
    openDownloadModal(selectedCandidate, approvalRecord);

  } catch (err) {
    showToast(`Approval failed: ${err.message}`, "error");
  }
}

function openDownloadModal(candidate, approvalRecord) {
  selectedCandidate = candidate;
  downloadPreflightInfo.style.display = "block";
  downloadResultBox.style.display = "none";
  btnExecuteDownload.style.display = "inline-flex";
  btnExecuteDownload.disabled = false;
  btnExecuteDownload.textContent = "Execute Compliant Download";
  downloadModal.showModal();
}

async function handleDownloadExecute() {
  if (!selectedCandidate) return;

  btnExecuteDownload.disabled = true;
  btnExecuteDownload.textContent = "Validating & Downloading...";

  const simulate = simulateDownloadToggle.checked;
  const payload = {
    simulate: simulate,
    user_id: approvalUserId.value.trim() || "academic-curator@syllextract.local"
  };

  try {
    const job = await API.requestDownload(selectedCandidate.candidate_id, payload);
    
    downloadPreflightInfo.style.display = "none";
    downloadResultBox.style.display = "block";
    downloadResultBox.innerHTML = `
      <div style="padding: 1rem; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);">
        <h4 style="color: var(--color-success); margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
          Acquisition ${simulate ? 'Simulation Completed' : 'Completed Successfully'}
        </h4>
        <p style="font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 0.5rem;">
          Status: <strong>${job.status}</strong> • Format: <strong>${job.format || 'PDF'}</strong>
        </p>
        <p style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted); word-break: break-all;">
          SHA-256: ${job.file_hash || 'SHA-256 Calculated upon quarantine validation'}
        </p>
      </div>
    `;

    btnExecuteDownload.style.display = "none";
    showToast("Acquisition job completed and recorded.", "success");
    await loadAuditHistory();

  } catch (err) {
    btnExecuteDownload.disabled = false;
    btnExecuteDownload.textContent = "Retry Download";
    showToast(`Download failed: ${err.message}`, "error");
  }
}

// ===================================================================
// Audit History Loader
// ===================================================================
async function loadAuditHistory() {
  try {
    const approvals = await API.getApprovals();
    auditBadgeCount.textContent = approvals.length;

    auditItemsList.innerHTML = "";
    if (approvals.length === 0) {
      auditItemsList.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 2rem 0; font-size: 0.85rem;">
          No human acquisition approvals recorded yet.
        </div>
      `;
      return;
    }

    approvals.forEach((a) => {
      const card = document.createElement("div");
      card.className = "audit-card";
      card.innerHTML = `
        <div class="audit-card-title">${escapeHtml(a.title || a.candidate_id)}</div>
        <div class="audit-meta-row">
          <span>By ${escapeHtml(a.approved_by || 'curator')}</span>
          <span>${formatDate(a.timestamp)}</span>
        </div>
        <div style="font-size: 0.75rem; color: var(--color-success);">
          ${escapeHtml(a.status || 'APPROVED')} • Scope: ${escapeHtml(a.intended_use_case || 'Educational')}
        </div>
        ${a.file_hash ? `
          <div style="font-family: var(--font-mono); font-size: 0.68rem; color: var(--text-muted); margin-top: 0.4rem; word-break: break-all;">
            Hash: ${a.file_hash.substring(0, 24)}...
          </div>
        ` : ''}
      `;
      auditItemsList.appendChild(card);
    });

  } catch (err) {
    console.warn("Could not refresh audit list:", err);
  }
}

// ===================================================================
// System Health Status Check
// ===================================================================
async function checkBackendHealth() {
  try {
    const health = await API.getHealth();
    if (health && health.status === "healthy") {
      statusDot.className = "status-dot status-online";
      statusLabel.textContent = "Backend Connected";
    } else {
      statusDot.className = "status-dot status-unknown";
      statusLabel.textContent = "Degraded";
    }
  } catch (err) {
    statusDot.className = "status-dot status-offline";
    statusLabel.textContent = "Offline";
  }
}

// ===================================================================
// Utilities (Toast, HTML Escaping, Date Formatting)
// ===================================================================
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(8px)";
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatDate(isoStr) {
  if (!isoStr) return "";
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch (e) {
    return isoStr;
  }
}
