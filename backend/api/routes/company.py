"""
Company API Routes
Handles company generation, upload, and retrieval.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import uuid
from loguru import logger

from core.schemas import (
    CompanyMetadata, CompanyGenerateRequest, CompanyUploadRequest,
    ChartOfAccounts, GeneralLedger, TrialBalance, Industry, AccountingBasis
)

router = APIRouter()

# In-memory storage (replace with database in production)
companies: dict[str, dict] = {}


@router.post("/generate", response_model=CompanyMetadata)
async def generate_company(request: CompanyGenerateRequest):
    """
    Generate a complete synthetic company with:
    - Company metadata
    - Chart of Accounts
    - General Ledger with transactions
    - Trial Balance (derived from GL)
    - Planted issues for audit testing
    """
    logger.info("[generate_company] Starting company generation")
    logger.info(f"[generate_company] Request params: industry={request.industry}, basis={request.accounting_basis}, transactions={request.num_transactions}, issues={request.issue_count}")
    
    try:
        from generators.company_generator import CompanyGenerator
        
        generator = CompanyGenerator()
        logger.info("[generate_company] CompanyGenerator initialized")
        
        company_data = await generator.generate(
            industry=request.industry,
            accounting_basis=request.accounting_basis,
            num_transactions=request.num_transactions,
            issue_count=request.issue_count
        )
        
        company_id = company_data["metadata"].id
        companies[company_id] = company_data
        
        logger.info(f"[generate_company] Company generated successfully: id={company_id}, name={company_data['metadata'].name}")
        logger.info(f"[generate_company] COA accounts: {len(company_data['coa'].accounts) if company_data.get('coa') else 0}")
        logger.info(f"[generate_company] GL entries: {len(company_data['gl'].entries) if company_data.get('gl') else 0}")
        logger.info(f"[generate_company] Injected issues: {len(company_data.get('injected_issues', []))}")
        
        return company_data["metadata"]
        
    except Exception as e:
        logger.error(f"[generate_company] Error generating company: {str(e)}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Error generating company: {str(e)}")


@router.post("/upload", response_model=CompanyMetadata)
async def upload_company(
    company_name: str = Form(...),
    industry: Industry = Form(...),
    accounting_basis: AccountingBasis = Form(...),
    reporting_period: str = Form(...),
    gl_file: UploadFile = File(...),
    tb_file: Optional[UploadFile] = File(None),
    coa_file: Optional[UploadFile] = File(None),
):
    """
    Upload real company data for audit.
    Uses AI-powered parsing to normalize data from any format.
    All AI decisions are logged in the audit trail.
    """
    from core.audit_trail import audit_trail
    from parsers.normalizer import DataNormalizer
    
    logger.info(f"[upload_company] Uploading company: {company_name}")
    logger.info(f"[upload_company] Industry: {industry}, Basis: {accounting_basis}, Period: {reporting_period}")
    
    # Create company ID early for audit trail
    company_id = str(uuid.uuid4())
    
    # Create audit record for file upload
    audit_record = audit_trail.create_record(
        audit_id=f"upload-{company_id}",
        company_id=company_id,
        created_by="file_upload"
    )
    audit_record.input_type = "uploaded"
    
    try:
        normalizer = DataNormalizer()
        
        # Parse uploaded files with AI-powered normalization
        logger.info(f"[upload_company] Parsing GL file: {gl_file.filename}")
        audit_record.add_reasoning_step("Starting file upload processing", {
            "company_name": company_name,
            "gl_file": gl_file.filename,
            "tb_file": tb_file.filename if tb_file else None,
            "coa_file": coa_file.filename if coa_file else None
        })
        
        gl_content = await gl_file.read()
        gl_data = await normalizer.parse_file(gl_content, gl_file.filename, "general_ledger", audit_record)
        logger.info(f"[upload_company] GL parsed: {len(gl_data.entries) if gl_data else 0} entries")
        
        tb_data = None
        if tb_file:
            logger.info(f"[upload_company] Parsing TB file: {tb_file.filename}")
            tb_content = await tb_file.read()
            tb_data = await normalizer.parse_file(tb_content, tb_file.filename, "trial_balance", audit_record)
        
        coa_data = None
        if coa_file:
            logger.info(f"[upload_company] Parsing COA file: {coa_file.filename}")
            coa_content = await coa_file.read()
            coa_data = await normalizer.parse_file(coa_content, coa_file.filename, "chart_of_accounts", audit_record)
        
        # Create company metadata
        metadata = CompanyMetadata(
            id=company_id,
            name=company_name,
            industry=industry,
            accounting_basis=accounting_basis,
            reporting_period=reporting_period,
            is_synthetic=False
        )
        
        audit_record.add_reasoning_step("File upload completed successfully", {
            "gl_entries": len(gl_data.entries) if gl_data else 0,
            "tb_rows": len(tb_data.rows) if tb_data else 0,
            "coa_accounts": len(coa_data.accounts) if coa_data else 0
        })
        
        # Finalize audit record
        audit_trail.finalize_record(audit_record.audit_id)
        
        companies[company_id] = {
            "metadata": metadata,
            "coa": coa_data,
            "gl": gl_data,
            "tb": tb_data,
            "upload_audit": audit_record.to_dict()
        }
        
        logger.info(f"[upload_company] Company uploaded successfully: id={company_id}")
        return metadata
        
    except Exception as e:
        logger.error(f"[upload_company] Error uploading company: {str(e)}")
        logger.exception(e)
        audit_record.add_reasoning_step("Upload failed with error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Error uploading company: {str(e)}")


@router.get("/")
async def list_companies():
    """List all companies."""
    logger.info(f"[list_companies] Listing {len(companies)} companies")
    
    return [
        {
            "id": company_id,
            "name": data["metadata"].name,
            "industry": data["metadata"].industry,
            "is_synthetic": data["metadata"].is_synthetic
        }
        for company_id, data in companies.items()
    ]


@router.get("/scenarios")
async def list_scenarios():
    """List all available demo scenarios."""
    import json
    from pathlib import Path
    
    logger.info("[list_scenarios] Listing available scenarios")
    
    try:
        scenarios_path = Path(__file__).parent.parent.parent / "example_data" / "scenarios" / "index.json"
        with open(scenarios_path, 'r') as f:
            data = json.load(f)
        return data["scenarios"]
    except Exception as e:
        logger.error(f"[list_scenarios] Error: {e}")
        return []


@router.get("/{company_id}", response_model=CompanyMetadata)
async def get_company(company_id: str):
    """Get company metadata by ID."""
    logger.info(f"[get_company] Fetching company: {company_id}")
    
    if company_id not in companies:
        logger.warning(f"[get_company] Company not found: {company_id}")
        raise HTTPException(status_code=404, detail="Company not found")
    
    logger.info(f"[get_company] Returning company: {companies[company_id]['metadata'].name}")
    return companies[company_id]["metadata"]


@router.get("/{company_id}/coa", response_model=ChartOfAccounts)
async def get_chart_of_accounts(company_id: str):
    """Get Chart of Accounts for a company."""
    logger.info(f"[get_chart_of_accounts] Fetching COA for company: {company_id}")
    
    if company_id not in companies:
        logger.warning(f"[get_chart_of_accounts] Company not found: {company_id}")
        raise HTTPException(status_code=404, detail="Company not found")
    
    coa = companies[company_id].get("coa")
    if not coa:
        logger.warning(f"[get_chart_of_accounts] COA not available for company: {company_id}")
        raise HTTPException(status_code=404, detail="Chart of Accounts not available")
    
    logger.info(f"[get_chart_of_accounts] Returning {len(coa.accounts)} accounts")
    return coa


@router.get("/{company_id}/gl", response_model=GeneralLedger)
async def get_general_ledger(company_id: str):
    """Get General Ledger for a company."""
    logger.info(f"[get_general_ledger] Fetching GL for company: {company_id}")
    
    if company_id not in companies:
        logger.warning(f"[get_general_ledger] Company not found: {company_id}")
        raise HTTPException(status_code=404, detail="Company not found")
    
    gl = companies[company_id].get("gl")
    if not gl:
        logger.warning(f"[get_general_ledger] GL not available for company: {company_id}")
        raise HTTPException(status_code=404, detail="General Ledger not available")
    
    logger.info(f"[get_general_ledger] Returning {len(gl.entries)} entries")
    return gl


@router.get("/{company_id}/tb", response_model=TrialBalance)
async def get_trial_balance(company_id: str):
    """Get Trial Balance for a company."""
    logger.info(f"[get_trial_balance] Fetching TB for company: {company_id}")
    
    if company_id not in companies:
        logger.warning(f"[get_trial_balance] Company not found: {company_id}")
        raise HTTPException(status_code=404, detail="Company not found")
    
    tb = companies[company_id].get("tb")
    if not tb:
        # Try to derive from GL if available
        gl = companies[company_id].get("gl")
        coa = companies[company_id].get("coa")
        if gl and coa:
            logger.info(f"[get_trial_balance] deriving TB from GL for company: {company_id}")
            from generators.tb_generator import TBGenerator
            generator = TBGenerator()
            tb = generator.derive_from_gl(
                company_id=company_id,
                gl=gl,
                coa=coa,
                reporting_period=companies[company_id]["metadata"].reporting_period
            )
            # Save it
            companies[company_id]["tb"] = tb
        else:
            logger.warning(f"[get_trial_balance] TB not available and cannot derive (missing GL/COA) for company: {company_id}")
            raise HTTPException(status_code=404, detail="Trial Balance not available")
    
    logger.info(f"[get_trial_balance] Returning TB with {len(tb.rows)} rows, balanced={tb.is_balanced}")
    return tb


@router.post("/example", response_model=CompanyMetadata)
async def load_example_company(scenario_id: Optional[str] = None):
    """
    Load pre-generated example company data.
    This data is fixed and reproducible - ideal for testing and demos.
    Does not require AI API calls.
    
    Args:
        scenario_id: Optional scenario to load. Options: acme_saas, startup_growth, fraud_indicators, clean_retail
    """
    logger.info(f"[load_example_company] Loading example company data, scenario={scenario_id}")
    
    try:
        if scenario_id and scenario_id != "acme_saas":
            # Load specific scenario
            return await load_scenario(scenario_id)
        
        from generators.example_data import get_example_company, EXAMPLE_COMPANY_ID
        
        # Check if already loaded
        if EXAMPLE_COMPANY_ID in companies:
            logger.info(f"[load_example_company] Example company already loaded")
            return companies[EXAMPLE_COMPANY_ID]["metadata"]
        
        # Load example data
        company_data = get_example_company()
        companies[EXAMPLE_COMPANY_ID] = company_data
        
        logger.info(f"[load_example_company] Example company loaded: {company_data['metadata'].name}")
        logger.info(f"[load_example_company] Injected issues: {len(company_data.get('injected_issues', []))}")
        
        return company_data["metadata"]
        
    except Exception as e:
        logger.error(f"[load_example_company] Error loading example: {str(e)}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Error loading example: {str(e)}")


async def load_scenario(scenario_id: str) -> CompanyMetadata:
    """Load a specific scenario by ID from pre-written files."""
    import json
    import csv
    from pathlib import Path
    from datetime import datetime
    
    logger.info(f"[load_scenario] Loading scenario: {scenario_id}")
    
    scenarios_dir = Path(__file__).parent.parent.parent / "example_data" / "scenarios"
    index_path = scenarios_dir / "index.json"
    
    with open(index_path, 'r') as f:
        scenarios = json.load(f)["scenarios"]
    
    scenario = next((s for s in scenarios if s["id"] == scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    
    def resolve_path(file_ref: str) -> Path:
        """Resolve file path relative to scenarios dir."""
        if file_ref.startswith("../"):
            return scenarios_dir.parent / file_ref[3:]
        return scenarios_dir / file_ref
    
    # Load GL file
    gl_file = scenario.get("gl_file", "")
    gl_path = resolve_path(gl_file)
    
    from core.schemas import JournalEntry, GeneralLedger, ChartOfAccounts, Account, TrialBalance, TrialBalanceRow
    
    gl_entries = []
    with open(gl_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            gl_entries.append(JournalEntry(
                entry_id=row['entry_id'],
                date=row['date'],
                account_code=row['account_code'],
                account_name=row['account_name'],
                description=row['description'],
                debit=float(row['debit']) if row['debit'] else 0.0,
                credit=float(row['credit']) if row['credit'] else 0.0,
                vendor_or_customer=row.get('vendor_or_customer')
            ))
    logger.info(f"[load_scenario] Loaded GL with {len(gl_entries)} entries")
    
    # Load COA file
    coa_file = scenario.get("coa_file", "")
    coa = None
    if coa_file:
        coa_path = resolve_path(coa_file)
        if coa_path.exists():
            accounts = []
            with open(coa_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    accounts.append(Account(
                        code=row['code'],
                        name=row['name'],
                        type=row['type'],
                        normal_balance=row.get('normal_balance', 'debit'),
                        subtype=row.get('subtype'),
                        description=row.get('description', '')
                    ))
            coa = ChartOfAccounts(company_id="", accounts=accounts)
            logger.info(f"[load_scenario] Loaded COA with {len(accounts)} accounts")
    
    # Load TB file
    tb_file = scenario.get("tb_file", "")
    tb = None
    if tb_file:
        tb_path = resolve_path(tb_file)
        if tb_path.exists():
            tb_rows = []
            total_debit = 0.0
            total_credit = 0.0
            with open(tb_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    debit = float(row['debit']) if row['debit'] else 0.0
                    credit = float(row['credit']) if row['credit'] else 0.0
                    total_debit += debit
                    total_credit += credit
                    
                    beginning_balance = 0.0
                    # Formula: Beginning Balance + Debit - Credit
                    ending_balance = beginning_balance + debit - credit
                    
                    tb_rows.append(TrialBalanceRow(
                        account_code=row['account_code'],
                        account_name=row['account_name'],
                        beginning_balance=beginning_balance,
                        debit=debit,
                        credit=credit,
                        ending_balance=ending_balance
                    ))
            period_end_date = max(e.date for e in gl_entries) if gl_entries else str(datetime.now().date())
            tb = TrialBalance(
                company_id="",
                period_end=period_end_date,
                rows=tb_rows,
                total_debits=round(total_debit, 2),
                total_credits=round(total_credit, 2),
                is_balanced=abs(total_debit - total_credit) < 0.01
            )
            logger.info(f"[load_scenario] Loaded TB with {len(tb_rows)} rows, balanced={tb.is_balanced}")
    
    # Create company
    company_id = f"scenario-{scenario_id}-{uuid.uuid4().hex[:6]}"
    
    industry_map = {
        "saas": Industry.SAAS,
        "retail": Industry.RETAIL,
        "services": Industry.CONSULTING,
        "consulting": Industry.CONSULTING,
        "manufacturing": Industry.MANUFACTURING,
        "ecommerce": Industry.ECOMMERCE,
        "agency": Industry.AGENCY
    }
    
    metadata = CompanyMetadata(
        id=company_id,
        name=scenario["name"],
        industry=industry_map.get(scenario.get("industry", "saas"), Industry.SAAS),
        accounting_basis=AccountingBasis.ACCRUAL if scenario.get("accounting_basis") == "accrual" else AccountingBasis.CASH,
        reporting_period="Demo Scenario",
        is_synthetic=True
    )
    
    gl = GeneralLedger(
        company_id=company_id,
        period_start=min(e.date for e in gl_entries) if gl_entries else datetime.now().date(),
        period_end=max(e.date for e in gl_entries) if gl_entries else datetime.now().date(),
        entries=gl_entries
    )
    
    # Update company_id in COA and TB
    if coa:
        coa.company_id = company_id
    if tb:
        tb.company_id = company_id
    
    companies[company_id] = {
        "metadata": metadata,
        "gl": gl,
        "coa": coa,
        "tb": tb,
        "scenario": scenario
    }
    
    logger.info(f"[load_scenario] Loaded scenario '{scenario['name']}' with GL={len(gl_entries)}, COA={len(coa.accounts) if coa else 0}, TB={len(tb.rows) if tb else 0}")
    return metadata


@router.post("/upload-smart", response_model=CompanyMetadata)
async def upload_company_smart(
    company_name: str = Form(...),
    gl_file: UploadFile = File(...),
    tb_file: Optional[UploadFile] = File(None),
    coa_file: Optional[UploadFile] = File(None),
):
    """
    Smart upload with AI-powered data normalization.
    Gemini analyzes and normalizes uploaded files automatically.
    All AI decisions are logged in the audit trail.
    """
    from core.gemini_client import GeminiClient
    from core.audit_trail import audit_trail
    import json
    
    logger.info(f"[upload_company_smart] Smart upload for: {company_name}")
    
    company_id = str(uuid.uuid4())
    audit_record = audit_trail.create_record(
        audit_id=f"upload-{company_id}",
        company_id=company_id,
        created_by="file_upload"
    )
    audit_record.input_type = "uploaded"
    
    try:
        gemini = GeminiClient()
        
        # Read GL file
        gl_content = await gl_file.read()
        gl_text = gl_content.decode('utf-8', errors='ignore')[:10000]  # Limit for prompt
        
        audit_record.add_reasoning_step("Starting smart file upload", {
            "file_name": gl_file.filename,
            "file_size": len(gl_content),
            "content_preview": gl_text[:500]
        })
        
        # Use AI to understand and normalize the data
        result = await gemini.generate_json(
            prompt=f"""Analyze this financial data and extract structured General Ledger entries.

File name: {gl_file.filename}
Content preview:
{gl_text}

Extract and return a JSON object with:
{{
    "company_name": "detected company name or use '{company_name}'",
    "industry": "one of: saas, retail, manufacturing, healthcare, services",
    "accounting_basis": "accrual or cash",
    "entries": [
        {{
            "entry_id": "unique id",
            "date": "YYYY-MM-DD",
            "account_code": "account number",
            "account_name": "account name",
            "description": "transaction description",
            "debit": 0.00,
            "credit": 0.00,
            "vendor_or_customer": "name if any"
        }}
    ],
    "detected_issues": ["list of any data quality issues noticed"]
}}

If you cannot parse the data, return {{"error": "description of the problem"}}
""",
            purpose="file_normalization"
        )
        
        if result.get("audit"):
            audit_record.add_gemini_interaction(result["audit"])
        
        if result.get("error"):
            if "quota" in str(result.get("error", "")).lower():
                audit_record.add_reasoning_step("AI normalization failed - quota exceeded")
                raise HTTPException(
                    status_code=429, 
                    detail="AI quota exceeded. Please use 'Generate Data' or 'Use Example' instead."
                )
            raise HTTPException(status_code=400, detail=f"AI parsing error: {result.get('error')}")
        
        parsed = result.get("parsed", {})
        
        if parsed.get("error"):
            raise HTTPException(status_code=400, detail=parsed["error"])
        
        # Create GL from parsed data
        from datetime import datetime
        from core.schemas import GLEntry, GeneralLedger
        
        gl_entries = []
        for entry in parsed.get("entries", []):
            try:
                gl_entries.append(GLEntry(
                    entry_id=entry.get("entry_id", f"UP-{uuid.uuid4().hex[:6]}"),
                    date=datetime.strptime(entry.get("date", "2024-01-01"), "%Y-%m-%d").date(),
                    account_code=str(entry.get("account_code", "0000")),
                    account_name=entry.get("account_name", "Unknown"),
                    description=entry.get("description", ""),
                    debit=float(entry.get("debit", 0)),
                    credit=float(entry.get("credit", 0)),
                    vendor_or_customer=entry.get("vendor_or_customer")
                ))
            except Exception as e:
                logger.warning(f"[upload_company_smart] Skipping entry: {e}")
        
        audit_record.add_reasoning_step(f"Parsed {len(gl_entries)} entries from uploaded file", {
            "entries_parsed": len(gl_entries),
            "detected_issues": parsed.get("detected_issues", [])
        })
        
        # Detect industry from AI response
        detected_industry = parsed.get("industry", "saas").lower()
        industry_map = {
            "saas": Industry.SAAS,
            "retail": Industry.RETAIL,
            "manufacturing": Industry.MANUFACTURING,
            "healthcare": Industry.CONSULTING,  # Map healthcare to consulting
            "services": Industry.CONSULTING,    # Map services to consulting
            "consulting": Industry.CONSULTING,
            "ecommerce": Industry.ECOMMERCE,
            "agency": Industry.AGENCY
        }
        industry = industry_map.get(detected_industry, Industry.SAAS)
        
        # Detect accounting basis
        detected_basis = parsed.get("accounting_basis", "accrual").lower()
        basis = AccountingBasis.ACCRUAL if detected_basis == "accrual" else AccountingBasis.CASH
        
        # Create metadata
        metadata = CompanyMetadata(
            id=company_id,
            name=parsed.get("company_name", company_name),
            industry=industry,
            accounting_basis=basis,
            reporting_period="Uploaded Data",
            is_synthetic=False
        )
        
        # Create GL
        gl = GeneralLedger(
            company_id=company_id,
            period_start=min(e.date for e in gl_entries) if gl_entries else datetime.now().date(),
            period_end=max(e.date for e in gl_entries) if gl_entries else datetime.now().date(),
            entries=gl_entries
        )
        
        companies[company_id] = {
            "metadata": metadata,
            "gl": gl,
            "coa": None,
            "tb": None,
            "upload_audit": audit_record.to_dict()
        }
        
        audit_trail.finalize_record(audit_record.audit_id)
        
        logger.info(f"[upload_company_smart] Company uploaded: {company_id} with {len(gl_entries)} entries")
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[upload_company_smart] Error: {str(e)}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Error processing upload: {str(e)}")
