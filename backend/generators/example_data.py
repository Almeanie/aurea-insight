"""
Example Data - Pre-generated fixed data for testing.
This data is deterministic and doesn't require AI calls.
Loads from CSV files in the example_data folder.
"""
import csv
import json
from pathlib import Path
from loguru import logger

from core.schemas import (
    CompanyMetadata, ChartOfAccounts, Account,
    GeneralLedger, JournalEntry, TrialBalance, TrialBalanceRow,
    Industry, AccountingBasis
)

# Pre-defined example company ID
EXAMPLE_COMPANY_ID = "example-company-001"

# Path to example data folder
EXAMPLE_DATA_PATH = Path(__file__).parent.parent / "example_data"


def load_general_ledger_from_csv() -> list[JournalEntry]:
    """Load general ledger entries from CSV file."""
    gl_path = EXAMPLE_DATA_PATH / "general_ledger.csv"
    entries = []
    
    logger.info(f"[load_general_ledger_from_csv] Loading from {gl_path}")
    
    with open(gl_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                entry = JournalEntry(
                    entry_id=row['entry_id'],
                    date=row['date'],  # Keep as string YYYY-MM-DD
                    account_code=row['account_code'],
                    account_name=row['account_name'],
                    description=row['description'],
                    debit=float(row['debit']) if row['debit'] else 0.0,
                    credit=float(row['credit']) if row['credit'] else 0.0,
                    vendor_or_customer=row.get('vendor_or_customer')
                )
                entries.append(entry)
            except Exception as e:
                logger.warning(f"[load_general_ledger_from_csv] Error parsing row: {e}")
    
    logger.info(f"[load_general_ledger_from_csv] Loaded {len(entries)} entries")
    return entries


def load_chart_of_accounts_from_csv() -> list[Account]:
    """Load chart of accounts from CSV file."""
    coa_path = EXAMPLE_DATA_PATH / "chart_of_accounts.csv"
    accounts = []
    
    logger.info(f"[load_chart_of_accounts_from_csv] Loading from {coa_path}")
    
    with open(coa_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                account = Account(
                    code=row['code'],
                    name=row['name'],
                    type=row['type'],
                    subtype=row.get('subtype'),
                    normal_balance=row['normal_balance'],
                    description=row.get('description')
                )
                accounts.append(account)
            except Exception as e:
                logger.warning(f"[load_chart_of_accounts_from_csv] Error parsing row: {e}")
    
    logger.info(f"[load_chart_of_accounts_from_csv] Loaded {len(accounts)} accounts")
    return accounts


def load_trial_balance_from_csv() -> list[TrialBalanceRow]:
    """Load trial balance from CSV file."""
    tb_path = EXAMPLE_DATA_PATH / "trial_balance.csv"
    rows = []
    
    logger.info(f"[load_trial_balance_from_csv] Loading from {tb_path}")
    
    with open(tb_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                tb_row = TrialBalanceRow(
                    account_code=row['account_code'],
                    account_name=row['account_name'],
                    debit=float(row['period_debits']) if row['period_debits'] else 0.0,
                    credit=float(row['period_credits']) if row['period_credits'] else 0.0
                )
                rows.append(tb_row)
            except Exception as e:
                logger.warning(f"[load_trial_balance_from_csv] Error parsing row: {e}")
    
    logger.info(f"[load_trial_balance_from_csv] Loaded {len(rows)} rows")
    return rows


def load_known_issues() -> list[dict]:
    """Load known issues from JSON file."""
    json_path = EXAMPLE_DATA_PATH / "company.json"
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get('known_issues', [])


def get_example_company() -> dict:
    """
    Returns pre-generated example company data loaded from CSV files.
    This data is fixed and reproducible - ideal for testing and demos.
    """
    logger.info("[get_example_company] Loading example company data from files")
    
    # Company Metadata
    metadata = CompanyMetadata(
        id=EXAMPLE_COMPANY_ID,
        name="Acme Software Solutions Inc.",
        industry=Industry.SAAS,
        accounting_basis=AccountingBasis.ACCRUAL,
        reporting_period="2024-Q4",
        is_synthetic=True
    )
    
    # Load from CSV files
    accounts = load_chart_of_accounts_from_csv()
    gl_entries = load_general_ledger_from_csv()
    tb_rows = load_trial_balance_from_csv()
    
    # Create Chart of Accounts
    coa = ChartOfAccounts(
        company_id=EXAMPLE_COMPANY_ID,
        accounts=accounts
    )
    
    # Create General Ledger
    gl = GeneralLedger(
        company_id=EXAMPLE_COMPANY_ID,
        period_start="2024-10-01",
        period_end="2024-12-31",
        entries=gl_entries
    )
    
    # Calculate totals for TB
    total_debits = sum(row.debit for row in tb_rows)
    total_credits = sum(row.credit for row in tb_rows)
    
    # Create Trial Balance
    tb = TrialBalance(
        company_id=EXAMPLE_COMPANY_ID,
        period_end="2024-12-31",
        rows=tb_rows,
        total_debits=total_debits,
        total_credits=total_credits,
        is_balanced=abs(total_debits - total_credits) < 0.01
    )
    
    # Load known issues for audit validation
    injected_issues = load_known_issues()
    
    logger.info(f"[get_example_company] Loaded company: {metadata.name}")
    logger.info(f"[get_example_company] Accounts: {len(accounts)}, GL entries: {len(gl_entries)}, TB rows: {len(tb_rows)}")
    logger.info(f"[get_example_company] Known issues: {len(injected_issues)}")
    
    return {
        "metadata": metadata,
        "coa": coa,
        "gl": gl,
        "tb": tb,
        "injected_issues": injected_issues,
        "is_example": True
    }
