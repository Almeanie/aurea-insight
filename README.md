# Aurea Insight

AI-Powered Financial Audit Platform - Built for the Gemini 3 Hackathon 2026

## Overview

Aurea Insight (Living Ledger Auditor) is a comprehensive AI audit platform that leverages Google's Gemini 3 to revolutionize financial auditing. The platform provides intelligent analysis, fraud detection, and regulatory compliance verification for financial data.

### Key Capabilities

- **Synthetic Company Generation**: Create realistic demo companies with complete accounting structures
- **Real Data Support**: Upload General Ledger, Trial Balance, and receipt data
- **Beneficial Ownership Discovery**: Integrate with public registries (SEC EDGAR, OpenCorporates, UK Companies House)
- **Complex Fraud Pattern Detection**: Identify shell companies, round-tripping, and structuring
- **Correcting Journal Entries (AJEs)**: Automatically generate adjustment entries
- **Full Audit Trail**: Maintain complete logs for regulatory compliance
- **AI-Powered Explanations**: Traceable reasoning for all findings

## Features

### Fraud Detection
- Benford's Law analysis for fabricated numbers
- Structuring/smurfing detection
- Duplicate payment identification
- Round-tripping detection
- Shell company indicators

### GAAP Compliance
- Cash vs Accrual basis awareness
- Revenue recognition timing (ASC 606)
- Expense classification validation
- Prepaid amortization checks
- Internal control verification

### Ownership Discovery
- Public registry integration
- Ownership graph visualization
- Circular ownership detection
- Common controller identification
- Secrecy jurisdiction flagging

### AI Auditability
- Complete prompt/response logging
- Reasoning chain capture
- Cryptographic integrity verification
- Regulator-ready audit trails

## Tech Stack

### Frontend
- Next.js 16 with React 19
- shadcn/ui components
- Tailwind CSS
- Dark mode Palantir-inspired design

### Backend
- Python 3.12 with FastAPI
- Google Gemini 3 API
- PostgreSQL database
- NetworkX for graph analysis

## Getting Started

### Prerequisites
- Node.js 20+
- Python 3.12+
- PostgreSQL (optional - can run without for demo)
- Gemini API key

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment file and add your Gemini API key
copy .env.example .env  # Windows
cp .env.example .env  # Linux/Mac

# Edit .env and add your Gemini API key:
# GEMINI_API_KEY=your_key_here

# Run the server
python -m uvicorn main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### Docker Setup (Alternative)

```bash
# From repository root
docker-compose up --build
```

### Access the Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Usage

1. **Generate a Demo Company**: Click "Generate Demo Company" to create a synthetic company with realistic accounting data and planted issues.

2. **Run Audit**: Execute the full audit pipeline including GAAP compliance, anomaly detection, fraud analysis, and AJE generation.

3. **Review Findings**: Examine audit findings categorized by severity and type.

4. **Explore Data**: View Chart of Accounts, General Ledger, and Trial Balance.

5. **Export Reports**: Download PDF reports or CSV data for further analysis.

## Project Structure

```
aurea-insight/
|-- frontend/               # Next.js application
|   |-- src/
|       |-- app/            # App router pages
|       |-- components/     # React components
|       |-- lib/            # Utilities
|
|-- backend/                # FastAPI application
|   |-- api/                # API routes
|   |-- core/               # Core modules (Gemini, audit trail)
|   |-- generators/         # Synthetic data generation
|   |-- parsers/            # File parsing
|   |-- audit/              # Audit engine
|   |-- ownership/          # Ownership discovery
|   |-- chatbot/            # Auditor assistant
|   |-- exports/            # PDF/CSV export
|   |-- tests/              # Test suite
|
|-- docker-compose.yml      # Docker orchestration
|-- README.md               # This file
```

## Known Limitations

This is a hackathon demonstration with the following limitations:

1. Uses synthetic/simulated data
2. Simplified accounting assumptions
3. Not a substitute for professional audit
4. Not legal or accounting advice
5. Human judgment always required
6. Registry data may be incomplete
7. Fraud detection has false positive risk

## License

MIT License - Hackathon Demonstration Project

## Team

Built for the Gemini 3 Hackathon 2026

---

**Disclaimer**: This is a demonstration project. It should not be used for actual financial audits or compliance purposes. Always consult qualified professionals for financial and legal matters.
