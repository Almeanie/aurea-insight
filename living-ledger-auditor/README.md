# Living Ledger Auditor

AI-Powered Financial Audit Platform - Powered by Gemini 3

## Overview

Living Ledger Auditor is a full-stack AI audit platform that:

- Generates complete synthetic companies with realistic accounting structures
- Supports real data upload (General Ledger, Trial Balance, receipts)
- Discovers beneficial ownership via public registries
- Detects complex fraud patterns including shell companies and round-tripping
- Generates correcting journal entries (AJEs)
- Maintains full audit trail for regulatory compliance
- Explains all findings with traceable AI reasoning

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
- Public registry integration (OpenCorporates, SEC EDGAR)
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

# Copy environment file
copy .env.example .env  # Windows
cp .env.example .env  # Linux/Mac

# Add your Gemini API key to .env
# GEMINI_API_KEY=your_key_here

# Run the server
python main.py
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### Access the Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Usage

1. **Generate a Demo Company**: Click "Generate Demo Company" to create a synthetic company with realistic accounting data and planted issues.

2. **Run Audit**: Click "Run Audit" to execute the full audit pipeline:
   - GAAP compliance checks
   - Anomaly detection
   - Fraud pattern analysis
   - AI-enhanced findings
   - AJE generation

3. **Review Findings**: Examine audit findings by severity and category.

4. **Explore Data**: View the Chart of Accounts, General Ledger, and Trial Balance.

5. **Export Reports**: Download PDF reports or CSV data.

## Project Structure

```
living-ledger-auditor/
|-- frontend/           # Next.js application
|   |-- src/
|   |   |-- app/       # App router pages
|   |   |-- components/ # React components
|
|-- backend/            # FastAPI application
|   |-- api/           # API routes
|   |-- core/          # Core modules (Gemini, audit trail)
|   |-- generators/    # Synthetic data generation
|   |-- parsers/       # File parsing
|   |-- audit/         # Audit engine
|   |-- ownership/     # Ownership discovery
|   |-- chatbot/       # Auditor assistant
|   |-- exports/       # PDF/CSV export
```

## Known Limitations

This system is a hackathon demonstration and has the following limitations:

1. Uses synthetic/simulated data
2. Simplified accounting assumptions
3. Not a substitute for professional audit
4. Not legal or accounting advice
5. Human judgment always required
6. Registry data may be incomplete
7. Fraud detection has false positive risk

## Demo Video

[Link to demo video - to be added]

## License

MIT License - Hackathon Demonstration Project

## Team

Built for the Gemini 3 Hackathon 2026

---

**Disclaimer**: This is a demonstration project. It should not be used for actual financial audits or compliance purposes. Always consult qualified professionals for financial and legal matters.
