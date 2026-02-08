# Aurea Insight

**AI-Powered Financial Audit Platform** -- Built for the Gemini 3 Hackathon 2026

---

## Overview

Aurea Insight is a full-stack AI audit platform that leverages Google Gemini 3 to automate and enhance financial auditing. It performs real-time GAAP/IFRS compliance checks, multi-vector fraud detection, anomaly analysis, and beneficial ownership discovery -- all with a complete, cryptographically verifiable audit trail.

The platform streams audit progress and findings to the frontend in real time via Server-Sent Events, so auditors can review issues as they are discovered rather than waiting for the full pipeline to complete.

---

## Key Capabilities

- **Dual Accounting Standard Support**: Audit against US GAAP or IFRS rules, selectable at runtime
- **Real-Time Streaming Audit**: Findings, AJEs, and risk scores stream live to the UI as they are generated
- **Multi-Vector Fraud Detection**: Benford's Law, structuring/smurfing, duplicate payments, round-tripping, shell company indicators
- **Beneficial Ownership Discovery**: Real public registry lookups (SEC EDGAR, GLEIF) with AI-assisted classification
- **Adjusting Journal Entries (AJEs)**: Automatically generated correcting entries linked to specific findings
- **AI Auditor Assistant**: Conversational chatbot to ask questions about audit results
- **Full Audit Trail**: Complete prompt/response logging, reasoning chains, and cryptographic integrity hashes
- **Flexible Data Input**: Upload Excel/CSV files (multi-sheet, large file support) or use built-in demo scenarios
- **Export**: PDF audit reports, CSV and Excel exports for findings, AJEs, and financial data

---

## Features

### Fraud Detection
- Benford's Law analysis for fabricated numbers
- Structuring / smurfing detection (transactions split to avoid thresholds)
- Duplicate payment identification
- Round-tripping detection
- Shell company indicators
- Weekend/holiday transaction flagging
- Vendor-customer overlap analysis

### GAAP & IFRS Compliance
- Cash vs. Accrual basis awareness
- Revenue recognition timing (ASC 606 / IFRS 15)
- Expense classification validation
- Prepaid amortization checks
- Internal control verification
- Period-end cutoff analysis

### Beneficial Ownership Discovery
- SEC EDGAR integration (US public company filings)
- GLEIF integration (Legal Entity Identifiers)
- Gemini-powered web search fallback for entities not in registries
- Interactive ownership graph visualization (D3.js force-directed graph)
- Circular ownership detection
- Common controller identification
- Secrecy jurisdiction flagging
- Auto-enrichment workflow to resolve red flags

```
API Lookup --> Gemini Classification --> Auto-Enrichment --> Red Flags?
                                                              |
                                          Resolvable --> Web Search --> Parse --> Update --> Remove Flag
                                          Not Resolvable --> Keep Flag
```

### AI Auditability
- Complete Gemini prompt/response logging with token counts
- Step-by-step reasoning chain capture
- Cryptographic integrity hash for audit records
- Regulator-ready audit trails
- Interactive dialogs to inspect each AI interaction

### Real-Time Progress
- Server-Sent Events (SSE) for live audit streaming
- Step-by-step progress bar with named phases
- Findings appear individually as they are discovered
- AJEs stream in as they are generated (with loading indicator for pending ones)
- Live audit console with color-coded log entries

---

## System Architecture

### Design Philosophy

A critical design decision in Aurea Insight is the **strict separation between detection and explanation**. The audit engine does not use AI to decide what is wrong. All detection -- compliance violations, anomalies, fraud patterns -- is performed by deterministic, rule-based, and statistical algorithms. AI (Gemini) is used downstream to explain findings, generate corrective entries, parse uploaded files, and power the chatbot.

This means audit results are **reproducible and explainable**: the same input always produces the same findings, regardless of AI model behavior. Every Gemini interaction is logged in the audit trail for regulatory transparency.

### High-Level Flow

```
                                    +-------------------+
                                    |   Frontend        |
                                    |   (Next.js 16)    |
                                    +--------+----------+
                                             |
                                       SSE Stream + REST
                                             |
                                    +--------v----------+
                                    |   FastAPI Backend  |
                                    +--------+----------+
                                             |
              +------------------------------+------------------------------+
              |                              |                              |
     +--------v--------+         +----------v----------+         +---------v---------+
     |  Audit Engine    |         | Ownership Discovery |         | Auditor Assistant |
     |  (Deterministic) |         | (APIs + AI parsing) |         | (AI Chatbot)      |
     +---------+--------+         +----------+----------+         +---------+---------+
               |                             |                              |
   +-----------+-----------+        +--------+--------+             +-------v-------+
   |     |     |     |     |        |        |        |             |   Gemini 3    |
   v     v     v     v     v        v        v        v             | (Q&A only)    |
 GAAP  IFRS  Anom  Fraud Risk    SEC      GLEIF   Gemini           +---------------+
 Rules Rules  Det   Det  Score   EDGAR     API    (classify
  |     |     |     |     |                        + parse)
  |     |     |     |     |
  +--+--+--+--+--+--+     |
     |              |      |
     v              v      v
  Findings     AI Enhance  Risk
  (raw)        (Gemini)    Score
     |
     v
  AJE Generator
  (Gemini + fallback)
```

### The 7-Step Audit Pipeline

The audit engine runs a sequential pipeline. Steps 2-4 execute in parallel for performance.

| Step | Name | Method | Uses AI? |
|------|------|--------|----------|
| 1 | **Data Validation** | Structural checks (balance verification, data types) | No |
| 2 | **GAAP/IFRS Compliance** | Rule-based pattern matching against accounting standards | No |
| 3 | **Anomaly Detection** | Statistical algorithms (Benford's Law, Z-scores) | No |
| 4 | **Fraud Detection** | Pattern matching (duplicates, structuring, round-tripping) | No |
| 5 | **AI Enhancement** | Gemini generates human-readable explanations for each finding | Yes |
| 6 | **AJE Generation** | Gemini generates correcting journal entries (deterministic fallback) | Yes (with fallback) |
| 7 | **Risk Scoring** | Weighted formula: Critical=10, High=5, Medium=2, Low=1 | No |

Steps 2-4 run concurrently via `asyncio.gather()` and produce raw findings. Step 5 enhances those findings with AI explanations. Step 6 generates AJEs. Step 7 computes the final risk score.

### What the Audit Engine Does (No AI)

**GAAP Compliance** (`gaap_rules.py`):
- Approval control checks (transactions > $5,000 without approval)
- Expense classification validation (keyword matching)
- Revenue recognition timing (period-end large entries, ASC 606)
- Matching principle violations (unamortized prepaids)
- Cash basis compliance checks

**IFRS Compliance** (`ifrs_rules.py`):
- LIFO prohibition detection (LIFO not allowed under IFRS)
- Inventory NRV write-down/reversal checks
- PPE revaluation detection (allowed under IFRS)
- Impairment reversal analysis (IAS 36)
- Development cost capitalization criteria (IAS 38)
- Provision validation (IAS 37)
- Lease recognition checks (IFRS 16)
- Related party transaction flagging

**Anomaly Detection** (`anomaly_detection.py`):
- Benford's Law analysis (chi-square test on first-digit distribution)
- Statistical outlier detection (Z-score, flags |z| > 3)
- Timing anomalies (Z-score on daily transaction volume)

**Fraud Detection** (`fraud_detection.py`):
- Duplicate payment detection (same vendor + amount + date proximity)
- Structuring/smurfing (clusters of transactions just under $10,000)
- Suspiciously round amounts ($1,000, $5,000, etc.)
- Shell company indicators (generic vendor names)
- Round-tripping (circular payment-receipt patterns)
- Weekend/holiday transactions (temporal anomalies)
- Vendor-customer overlap (same entity on both sides)

**Risk Scorer** (`risk_scorer.py`):
- Weighted severity scoring normalized to 0-100
- Risk levels: Critical (>=75 or >=2 critical findings), High (>=50), Medium (>=25), Low (<25)

### What Gemini AI Does

AI is used in five specific areas, always with fallback mechanisms:

| Area | Purpose | Fallback |
|------|---------|----------|
| **Finding Explanations** | Generate clear, professional explanations for each audit finding | Finding is returned without explanation |
| **AJE Generation** | Create context-aware correcting journal entries from findings + chart of accounts | 10 deterministic rule templates |
| **File Parsing** | Detect column mappings when users upload arbitrary Excel/CSV files | Heuristic column name matching |
| **Ownership Classification** | Classify entities discovered from public registries, parse complex filings | Entity stored with "unknown" classification |
| **Auditor Assistant** | Answer natural-language questions about audit results | Keyword-based pattern matching on common questions |

Every Gemini call is:
- Logged with full prompt and response text
- Hashed for integrity verification
- Visible in the Audit Trail tab
- Rate-limited (15 req/min with exponential backoff)
- Protected by quota detection (graceful degradation when limits hit)

### Streaming Architecture

The platform uses Server-Sent Events (SSE) to stream audit progress to the frontend in real time.

```
Backend                              Frontend
+------------------+                 +------------------+
| Audit Engine     |                 | React State      |
|   |               |                 |   |               |
|   +--stream_data()-+-> Progress --> SSE --> EventSource  |
|   |  (finding)    |    Tracker     Stream   onmessage   |
|   +--stream_data()-+-> (Queue)              |            |
|   |  (aje)        |                         v            |
|   +--stream_data()-+               | setFindings()      |
|      (risk_score) |                | setAjes()          |
+------------------+                 | setRiskScore()     |
                                     +------------------+
```

1. The audit engine calls `stream_data()` after each individual finding, AJE, or score
2. The `ProgressTracker` pushes events to subscriber queues
3. The SSE endpoint reads from the queue and yields JSON events
4. The frontend `EventSource` processes each event and updates React state immediately
5. Findings appear one-by-one as they are discovered, not in a batch at the end

### Ownership Discovery Architecture

Ownership discovery follows a "real data first, AI for parsing" approach:

```
Vendor List (from GL)
        |
        v
+-------+--------+      +----------+      +-----------+
| SEC EDGAR API  |----->| Raw API  |----->| Gemini    |-----> Classified
| GLEIF API      |      | Response |      | Classify  |      Entity Node
+----------------+      +----------+      +-----------+
        |
        | (if not found)
        v
+----------------+      +----------+      +-----------+
| Gemini Web     |----->| Search   |----->| Gemini    |-----> Enriched
| Search         |      | Results  |      | Parse     |      Entity Node
+----------------+      +----------+      +-----------+
                                                |
                                                v
                                    +---------------------+
                                    | Graph Analysis      |
                                    | (NetworkX)          |
                                    | - Circular ownership|
                                    | - Common controllers|
                                    | - Secrecy juris.    |
                                    +---------------------+
```

1. For each vendor in the General Ledger, the system queries real public registries (SEC EDGAR, GLEIF)
2. If found, Gemini classifies the entity (type, risk level, jurisdiction) from the API response
3. If not found in registries, Gemini performs a web search and parses the results
4. Ownership relationships are built into a graph and streamed to the frontend node-by-node
5. NetworkX runs algorithmic fraud pattern detection on the graph (circular ownership, common controllers, secrecy jurisdictions)

---

## Tech Stack

### Frontend
| Component | Technology |
|-----------|------------|
| Framework | Next.js 16 (App Router) with React 19 |
| Language | TypeScript 5 |
| UI Library | shadcn/ui (Radix primitives) |
| Styling | Tailwind CSS 4 |
| Icons | Lucide React |
| Graphs | D3.js 7 (force-directed ownership visualization) |
| Notifications | Sonner (toast system) |
| Design | Dark-mode, Palantir-inspired financial UI |

### Backend
| Component | Technology |
|-----------|------------|
| Framework | FastAPI (Python 3.12) |
| AI Engine | Google Gemini 3 (`gemini-3-flash-preview`) |
| Data Processing | Pandas, OpenPyXL |
| Graph Analysis | NetworkX |
| HTTP Client | httpx (for registry API calls) |
| PDF Export | xhtml2pdf |
| Logging | Loguru |
| Validation | Pydantic 2 |
| Database | PostgreSQL + SQLAlchemy 2 (optional -- runs in-memory for demos) |

### Infrastructure
| Component | Technology |
|-----------|------------|
| Deployment | Google Cloud Run (backend + frontend) |
| CI/CD | GitHub Actions |
| Containers | Docker (multi-stage builds) |
| Orchestration | docker-compose (local dev) |

---

## Getting Started

### Prerequisites
- Node.js 20+
- Python 3.12+
- A Gemini API key ([get one here](https://aistudio.google.com/app/apikey))
- PostgreSQL (optional -- not required for demo mode)

### Quick Start (Recommended)

```bash
# Clone the repository
git clone https://github.com/Almeanie/aurea-insight.git
cd aurea-insight

# Install root dependencies
npm install

# Set up the backend environment
cd backend
cp .env.example .env   # Linux/Mac
copy .env.example .env  # Windows

# Edit .env and set your Gemini API key:
#   GEMINI_API_KEY=your_key_here

# Install Python dependencies
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
pip install -r requirements.txt
cd ..

# Install frontend dependencies
cd frontend
npm install
cd ..

# Run both frontend and backend concurrently
npm run dev
```

### Docker Setup (Alternative)

```bash
docker-compose up --build
```

This starts PostgreSQL, the backend, and the frontend together.

### Access Points
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8888 |
| API Documentation | http://localhost:8888/docs |
| Health Check | http://localhost:8888/health |

---

## Usage

1. **Choose a Data Source**: Select a built-in demo scenario (e.g., "Suspicious Corp" for fraud training) or upload your own Excel/CSV files containing General Ledger data.

2. **Select Accounting Standard**: Choose between US GAAP and IFRS from the header dropdown before running the audit.

3. **Run Audit**: Click "Run Audit" to execute the full pipeline. Watch findings stream in live on the Findings tab and monitor progress in the Live Audit Console.

4. **Review Findings**: Click any finding row to see its full AI explanation, affected transactions, applicable accounting standards, and confidence score.

5. **Inspect AJEs**: Switch to the Data > AJEs tab to see auto-generated correcting journal entries, each linked to the finding that triggered it.

6. **Discover Ownership**: On the Ownership tab, click "Discover Ownership" to search public registries for vendor ownership structures. The graph builds in real time.

7. **Ask the Assistant**: Use the Auditor Assistant chat panel (right side) to ask natural-language questions about the audit results.

8. **Review the Audit Trail**: The Audit Trail tab shows every reasoning step and every Gemini AI interaction, with full prompt/response details available on click.

9. **Export**: Download a PDF audit report, or export findings and AJEs as CSV/Excel from the Export menu.

---

## Project Structure

```
aurea-insight/
|-- frontend/                   # Next.js 16 application
|   |-- src/
|       |-- app/                # App Router pages (home, company/[id])
|       |-- components/
|       |   |-- audit/          # Finding dialogs, AJE cards, reasoning steps
|       |   |-- chat/           # Auditor Assistant chat widget
|       |   |-- ownership/      # D3 ownership graph visualization
|       |   |-- ui/             # shadcn/ui base components
|       |-- lib/                # API client, utilities
|
|-- backend/                    # FastAPI application
|   |-- api/
|   |   |-- routes/             # REST + SSE endpoints
|   |       |-- audit.py        # Audit execution and streaming
|   |       |-- company.py      # Company CRUD, scenarios, uploads
|   |       |-- ownership.py    # Ownership discovery and graph
|   |       |-- chat.py         # Auditor assistant chatbot
|   |       |-- export.py       # PDF/CSV/Excel exports
|   |       |-- settings.py     # Runtime configuration
|   |-- audit/                  # Audit engine modules
|   |   |-- engine.py           # Main audit orchestrator
|   |   |-- gaap_rules.py       # US GAAP compliance checks
|   |   |-- ifrs_rules.py       # IFRS compliance checks
|   |   |-- anomaly_detection.py
|   |   |-- fraud_detection.py
|   |   |-- aje_generator.py    # Adjusting journal entry generation
|   |   |-- risk_scorer.py      # Composite risk scoring
|   |-- ownership/              # Beneficial ownership discovery
|   |   |-- discovery.py        # Network discovery orchestrator
|   |   |-- entity_extractor.py
|   |   |-- registries/         # Public registry API clients
|   |       |-- sec_edgar.py    # SEC EDGAR API
|   |       |-- gleif_api.py    # GLEIF LEI lookups
|   |-- core/                   # Shared infrastructure
|   |   |-- gemini_client.py    # Gemini API wrapper with retry logic
|   |   |-- schemas.py          # Pydantic models
|   |   |-- audit_trail.py      # Audit record and integrity hashing
|   |   |-- progress.py         # SSE progress tracker with checkpoints
|   |-- generators/             # Synthetic data generation
|   |-- parsers/                # File parsing and AI-powered normalization
|   |-- chatbot/                # Auditor assistant logic
|   |-- exports/                # PDF/CSV/Excel report generation
|   |-- example_data/           # Built-in demo scenarios
|   |-- tests/                  # pytest test suite
|
|-- .github/workflows/
|   |-- deploy.yml              # CI/CD to Google Cloud Run
|-- docker-compose.yml          # Local dev orchestration
|-- Dockerfile (in each service)
```

---

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | (in-memory) | PostgreSQL connection string |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated or JSON array) |
| `DEBUG` | `true` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `HOST` | `0.0.0.0` | Backend host |
| `PORT` | `8000` | Backend port |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL (set at frontend build time) |
| `UK_COMPANIES_HOUSE_API_KEY` | -- | UK Companies House API key (enhances ownership discovery) |
| `OPENCORPORATES_API_KEY` | -- | OpenCorporates API key (enhances ownership discovery) |

---

## Deployment

The project deploys to **Google Cloud Run** via GitHub Actions. On every push to `main`:

1. The backend is built and deployed as a Cloud Run service (`aurea-insight-backend`)
2. The frontend is built (with `NEXT_PUBLIC_API_URL` baked in) and deployed as a separate Cloud Run service (`aurea-insight-frontend`)

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `GCP_SA_KEY` | Google Cloud service account key (JSON) |
| `GEMINI_API_KEY` | Gemini API key for the deployed backend |
| `CORS_ORIGINS` | Allowed origins for the deployed backend |
| `NEXT_PUBLIC_API_URL` | Backend Cloud Run URL for the frontend build |

### Cloud Run Configuration

| Setting | Backend | Frontend |
|---------|---------|----------|
| Memory | 1 Gi | 512 Mi |
| CPU | 1 | 1 |
| Port | 8000 | 8080 |
| Timeout | 900s (15 min) | 60s |

---

## Known Limitations

This is a hackathon demonstration with the following limitations:

1. Uses synthetic/simulated data for demos (real data upload is supported)
2. Simplified accounting assumptions for rule-based checks
3. Not a substitute for a professional audit engagement
4. Not legal or accounting advice
5. Human judgment is always required for final decisions
6. Public registry data may be incomplete or delayed
7. Fraud detection has inherent false positive risk
8. Gemini API quota limits may affect long-running ownership discoveries

---

## License

MIT License -- Hackathon Demonstration Project

---

## Team

Built for the Gemini 3 Hackathon 2026

---

**Disclaimer**: This is a demonstration project. It should not be used for actual financial audits or compliance purposes. Always consult qualified professionals for financial and legal matters.
