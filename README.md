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
