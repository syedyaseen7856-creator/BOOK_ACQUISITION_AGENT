# SyllExtract Book Acquisition Agent

An autonomous, independent, and compliant reference book acquisition service designed to discover academic and educational book candidates, calculate explainable 0–100 match confidence scores in Python, independently verify licensing evidence, and manage explicit per-book human approvals with strict security safeguards.

---

## 1. Core Architecture & Capabilities

1. **Multi-Source Bibliographic Discovery**:
   - Searches Google Books API and Open Library API for bibliographic metadata.
   - Connects to authorized repositories (Project Gutenberg, DOAB Open Access monographs).
   - Includes realistic offline mock datasets for deterministic verification and UI testing.
   - **Mandatory Rule**: Searching and previewing candidates never downloads book files.

2. **Deterministic 0–100 Python Book Match Score**:
   - Configurable points allocation totaling 100 points:
     - **Title match**: 30 points (handles subtitles and prefix containment)
     - **Author match**: 25 points (handles token and surname overlap)
     - **ISBN match**: 20 points (exact ISBN-10 / ISBN-13 verification)
     - **Edition and publication year**: 15 points (proximity decay)
     - **Publisher match**: 10 points
   - **Hard Mismatch Rule**: A conflicting ISBN or conflicting author triggers an automatic score cap (score capped at ≤ 64) and flags the candidate into the `LOW_CONFIDENCE` tier.
   - Presentation tiers:
     - `90–100`: **Strong identity match** (`STRONG_MATCH`)
     - `75–89`: **Plausible match requiring careful comparison** (`PLAUSIBLE_MATCH`)
     - `Below 75`: **Low-confidence candidate** (`LOW_CONFIDENCE`)
   - Complete transparency: exposes evidence used, missing query fields, and uncertainty breakdown.

3. **Independent 3-State Licensing Verification**:
   - **MANDATORY SAFEGUARD**: A high identity score (even 100/100) NEVER implies or grants a legal download license.
   - Independent verification states:
     - `VERIFIED_FOR_PERMITTED_DOWNLOAD`: Public domain (Gutenberg, pre-1929 statutory publication) or authorized Open Access (CC-BY, CC-BY-NC). Eligible for acquisition.
     - `NEEDS_REVIEW`: Ambiguous, partial, or unverified licensing metadata. Automated downloads strictly blocked until human review.
     - `NOT_ELIGIBLE`: Commercial copyright, retail bookstore paywalls, or Controlled Digital Lending (CDL) in-library loans. Downloading strictly prohibited.
   - Optional Google Gemini Flash API (`gemini-2.5-flash`) integration for nuanced rights analysis with deterministic heuristic fallback.

4. **Server-Side Approval Management & Expiration**:
   - Every acquisition requires explicit, per-book human approval with user affirmation (`user_affirmation: true`).
   - Server-side validation: only candidates with status `VERIFIED_FOR_PERMITTED_DOWNLOAD` can be approved (HTTP 403 otherwise).
   - Tamper-detection: stores a deterministic SHA-256 snapshot hash of critical candidate fields.
   - Expiration enforcement: approvals expire after a configurable window (default 24 hours).
   - If candidate source URL or details change, renewed approval is required.

5. **Safe Download Pipeline & File Validation**:
   - Re-checks approval validity, expiration, and licensing status at execution time.
   - **SSRF Defense**: Blocks localhost, loopback, private IPv4 (RFC 1918), link-local (`169.254.x.x`), IPv6 (`::1`, `fe80::`).
   - Repository domain allowlist enforcement (`gutenberg.org`, `archive.org`, `openlibrary.org`, `doabooks.org`, `wisc.edu`).
   - Size limit protection (50MB) and streamed download abort.
   - **PDF Verification via `pypdf`**: Validates `%PDF-` signature, structural integrity, non-encryption, and page count (≥ 1).
   - **SHA-256 Hashing & Duplicate Detection**: Computes file hash and detects duplicates against previously acquired books in SQLite.
   - **Quarantine Isolation**: Suspicious or corrupted files are immediately quarantined to `data/quarantine/`.
   - Never executes downloaded content.

6. **SQLite Local Persistence**:
   - Stores search requests, candidate evaluations, approvals, download jobs, and provenance records in `data/book_agent.db`.

7. **SyllExtract Integration Adapter**:
   - Standalone `import_adapter.py` that formats acquired book records with citation keys, SHA-256 hashes, page counts, and legal provenance for future ingestion by SyllExtract's `extractors/reference_book_indexer.py`.

---

## 2. API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/search` | Discovers and ranks candidate records only; **never downloads files**. |
| `GET` | `/api/candidates/{candidate_id}` | Returns candidate metadata, confidence score breakdown, and licensing evidence. |
| `POST` | `/api/candidates/{candidate_id}/approve` | Records server-side explicit human approval with snapshot hash and expiration. |
| `POST` | `/api/candidates/{candidate_id}/download` | Re-verifies approval and licensing, then executes secure download and validation. |
| `GET` | `/api/jobs/{job_id}` | Returns download job progress, outcome, validation results, and provenance. |
| `GET` | `/api/approvals` | Lists audit history of all recorded approvals. |
| `POST` | `/api/syllabus/upload` | Parses uploaded syllabus document (PDF/TXT) into structured citations. |
| `GET` | `/api/syllabus/{syllabus_id}` | Retrieves parsed syllabus record and extracted book citations. |
| `PUT` | `/api/syllabus/{syllabus_id}/books/{book_id}` | Updates metadata for an extracted syllabus book item. |
| `DELETE` | `/api/syllabus/{syllabus_id}/books/{book_id}` | Removes an extracted book from the syllabus list. |
| `POST` | `/api/syllabus/{syllabus_id}/search-batch` | Launches bounded concurrent multi-book search across all providers. |
| `GET` | `/api/batches/{batch_id}` | Polls real-time progress and candidate evaluations for a search batch. |
| `GET` | `/api/candidates/{candidate_id}/alternative` | Discovers open-access alternative textbooks (OpenStax, Gutenberg) for restricted titles. |
| `GET` | `/api/history` | Retrieves unified, immutable audit history across searches, approvals, and acquisitions. |
| `GET` | `/api/health` | Health check endpoint. |
| `GET` | `/api/system-status` | System status, database connection, model configuration, and statistics. |

---

## 3. Project Structure

```
d:\BOOK_ACQUISITION_AGENT\
├── .env.example                     # Environment template (API keys, ports, limits)
├── .env                             # Local configuration
├── requirements.txt                 # Python dependencies
├── README.md                        # Documentation & setup instructions
├── app/
│   ├── main.py                      # FastAPI app entrypoint, CORS, lifespan & static mount
│   ├── config.py                    # Pydantic BaseSettings configuration
│   ├── schemas.py                   # Pydantic domain models
│   ├── models/
│   │   └── syllabus.py              # Syllabus, Batch Search & Acquisition schemas
│   ├── db/
│   │   ├── session.py               # SQLite connection & schema initialization
│   │   └── repository.py            # SQLite CRUD for searches, candidates, approvals, jobs
│   ├── api/
│   │   ├── health.py                # Health & system status
│   │   ├── search.py                # POST /api/search
│   │   ├── candidates.py            # GET /api/candidates/{id}
│   │   ├── approvals.py             # POST /api/candidates/{id}/approve
│   │   ├── downloads.py             # POST /api/candidates/{id}/download
│   │   ├── jobs.py                  # GET /api/jobs/{id}
│   │   └── syllabus_routes.py       # Syllabus parsing, batch search & acquisition history
│   ├── services/
│   │   ├── syllabus_extractor.py    # Multi-format citation regexes (APA, Harvard, etc.) + LLM fallback
│   │   ├── batch_search_service.py  # Concurrency-controlled batch search runner
│   │   ├── openstax_search.py       # OpenStax OER textbook catalog & search provider
│   │   ├── alternative_finder.py    # Subject-based Open Access alternative textbook matcher
│   │   ├── acquisition_history_service.py # Lifecycle logging, audit logs & reporting
│   │   ├── confidence_scorer.py     # 0-100 deterministic scoring with hard mismatches
│   │   ├── licensing_verifier.py    # 3-state licensing verification
│   │   ├── gemini_service.py        # Gemini Flash bibliographic parser & query assistant
│   │   ├── google_books.py          # Google Books API connector
│   │   ├── open_library.py          # Open Library API connector
│   │   ├── authorized_repos.py      # Project Gutenberg & DOAB client
│   │   ├── metadata_aggregator.py   # Multi-source search coordinator (incl. OpenStax)
│   │   ├── approval_service.py      # Server-side approval manager & audit logger
│   │   ├── safe_downloader.py       # Secure download pipeline with SSRF checks
│   │   ├── file_validator.py        # PDF validation (pypdf), SHA-256 hashing, quarantine
│   │   ├── duplicate_detector.py    # SHA-256 duplicate book detector
│   │   └── import_adapter.py        # SyllExtract reference book indexer adapter
│   └── static/
│       ├── index.html               # Classic web interface
│       ├── css/style.css            # Dark mode, glassmorphism, responsive cards
│       └── js/                      # api.js and app.js UI logic
├── frontend/                        # Modern React + Vite application
│   ├── src/
│   │   ├── App.jsx                  # Main application container & tab router
│   │   └── components/
│   │       ├── SyllabusUploader.jsx # Drag-and-drop syllabus parser & batch actions bar
│   │       ├── AcquisitionsHistory.jsx # Acquisition audit tracker and filter UI
│   │       └── ...
├── data/
│   ├── book_agent.db                # SQLite database
│   ├── mock_candidates.json         # Realistic test datasets
│   ├── downloads/                   # Validated book downloads
│   └── quarantine/                  # Quarantined invalid/suspicious files
└── tests/                           # Pytest automated test suite (56 tests)
```

---

## 4. Local Setup & Execution (Windows PowerShell)

### Step 1: Open Windows PowerShell and navigate to the project
```powershell
Set-Location -Path "D:\BOOK_ACQUISITION_AGENT"
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Run the Complete Automated Test Suite (56 Tests)
```powershell
python -m pytest -v
```
All 56 tests pass covering:
- Deterministic 0-100 scoring & hard mismatch rules
- 3-state licensing verification (`VERIFIED_FOR_PERMITTED_DOWNLOAD`, `NEEDS_REVIEW`, `NOT_ELIGIBLE`)
- Server-side approval creation, expiration, and snapshot tampering detection
- SSRF prevention, scheme validation, and dangerous file extension blocking
- PDF structural validation with `pypdf`, page count checks, and quarantine isolation
- SHA-256 duplicate detection via SQLite
- Syllabus parsing across diverse citation formats (APA, Harvard, multi-author, ISBN)
- Multi-book batch acquisition pipeline lifecycle and progress tracking
- OpenStax Open Educational Resources provider search & alternative finder
- Full API integration tests across all required routes
- SyllExtract reference-book indexer import adapter compatibility

### Step 4: Run the Application
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 5: Open the Web Application
Open your web browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 5. Web Interface Walkthrough & Testing Scenarios

1. **`🟢 Public Domain (Frankenstein)`**:
   - Searches *Frankenstein* by Mary Shelley.
   - Python Match Score: **Strong Identity Match (90-100 pts)**.
   - Licensing Status: **`VERIFIED_FOR_PERMITTED_DOWNLOAD`**.
   - Click **Explain Identity Score (0-100) ▼** to view the factor-by-factor point breakdown.
   - Click **Review & Approve Candidate** to open the approval modal, review the legal warning, check the required affirmation, and record an immutable server-side audit log.
   - Triggers the validation download gate confirming that the approval is active and authorized.

2. **`🔵 Open Access (OSTEP)`**:
   - Searches *Operating Systems: Three Easy Pieces* by Remzi & Andrea Arpaci-Dusseau.
   - Licensing Status: **`VERIFIED_FOR_PERMITTED_DOWNLOAD`** (Creative Commons CC-BY-NC-ND).
   - Demonstrates an authorized open-access textbook acquisition.

3. **`🔴 Commercial / In-Copyright (AIMA)`**:
   - Searches *Artificial Intelligence: A Modern Approach* by Russell & Norvig (Pearson).
   - Python Match Score: High confidence (96 pts).
   - Licensing Status: **`NOT_ELIGIBLE`** (Commercial Copyright).
   - Demonstrates the **Mandatory Safeguard**: High confidence does **NOT** permit download. The approval button is replaced by **"Acquisition Prohibited"**, preventing unauthorized acquisition.

4. **`🟡 CDL Borrow-Only (Algorithms)`**:
   - Searches *Introduction to Algorithms* (CLRS).
   - Licensing Status: **`NOT_ELIGIBLE`** (Controlled Digital Lending - Borrow-Only).
   - Demonstrates library loan protection.

5. **Audit History**:
   - Click the **Audit History** button in the header at any time to open the audit drawer and inspect all approved records and their snapshot hashes.
