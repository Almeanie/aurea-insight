"""Pytest configuration and fixtures."""
import pytest
import asyncio
import uuid
import random
from typing import Generator
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.schemas import (
    GeneralLedger, JournalEntry, TrialBalance, TrialBalanceRow,
    ChartOfAccounts, Account, AccountingBasis
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_company_id():
    """Generate a sample company ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_coa(sample_company_id):
    """Create a sample Chart of Accounts."""
    accounts = [
        Account(code="1000", name="Cash", type="asset", normal_balance="debit", description="Cash on hand"),
        Account(code="1100", name="Accounts Receivable", type="asset", normal_balance="debit", description="AR"),
        Account(code="1200", name="Prepaid Expenses", type="asset", normal_balance="debit", description="Prepaids"),
        Account(code="2000", name="Accounts Payable", type="liability", normal_balance="credit", description="AP"),
        Account(code="3000", name="Retained Earnings", type="equity", normal_balance="credit", description="RE"),
        Account(code="4000", name="Service Revenue", type="revenue", normal_balance="credit", description="Revenue"),
        Account(code="6000", name="Operating Expense", type="expense", normal_balance="debit", description="OpEx"),
        Account(code="6100", name="Utilities", type="expense", normal_balance="debit", description="Utilities"),
        Account(code="6600", name="Travel & Entertainment", type="expense", normal_balance="debit", description="T&E"),
    ]
    return ChartOfAccounts(company_id=sample_company_id, accounts=accounts)


@pytest.fixture
def sample_gl(sample_company_id):
    """Create a sample General Ledger with basic entries."""
    entries = [
        # Cash receipt from customer
        JournalEntry(
            entry_id="JE001",
            date="2024-04-15",
            account_code="1000",
            account_name="Cash",
            debit=10000.00,
            credit=0,
            description="Customer payment",
            vendor_or_customer="Acme Corp"
        ),
        JournalEntry(
            entry_id="JE001",
            date="2024-04-15",
            account_code="4000",
            account_name="Service Revenue",
            debit=0,
            credit=10000.00,
            description="Customer payment",
            vendor_or_customer="Acme Corp"
        ),
        # Expense payment
        JournalEntry(
            entry_id="JE002",
            date="2024-04-20",
            account_code="6000",
            account_name="Operating Expense",
            debit=2500.00,
            credit=0,
            description="Office supplies",
            vendor_or_customer="Office Depot"
        ),
        JournalEntry(
            entry_id="JE002",
            date="2024-04-20",
            account_code="1000",
            account_name="Cash",
            debit=0,
            credit=2500.00,
            description="Office supplies",
            vendor_or_customer="Office Depot"
        ),
    ]
    return GeneralLedger(
        company_id=sample_company_id,
        entries=entries,
        period_start="2024-04-01",
        period_end="2024-06-30"
    )


@pytest.fixture
def sample_tb(sample_company_id):
    """Create a sample Trial Balance."""
    rows = [
        TrialBalanceRow(account_code="1000", account_name="Cash", beginning_balance=50000, debits=10000, credits=2500, ending_balance=57500),
        TrialBalanceRow(account_code="1100", account_name="Accounts Receivable", beginning_balance=5000, debits=0, credits=0, ending_balance=5000),
        TrialBalanceRow(account_code="2000", account_name="Accounts Payable", beginning_balance=10000, debits=0, credits=0, ending_balance=10000),
        TrialBalanceRow(account_code="3000", account_name="Retained Earnings", beginning_balance=45000, debits=0, credits=0, ending_balance=45000),
        TrialBalanceRow(account_code="4000", account_name="Service Revenue", beginning_balance=0, debits=0, credits=10000, ending_balance=10000),
        TrialBalanceRow(account_code="6000", account_name="Operating Expense", beginning_balance=0, debits=2500, credits=0, ending_balance=2500),
    ]
    return TrialBalance(
        company_id=sample_company_id,
        rows=rows,
        period_start="2024-04-01",
        period_end="2024-06-30",
        is_balanced=True,
        total_debits=67500,
        total_credits=67500
    )


@pytest.fixture
def large_gl(sample_company_id):
    """Create a larger General Ledger for comprehensive testing."""
    entries = []
    vendors = ["Vendor A", "Vendor B", "Vendor C", "Office Depot", "Amazon", "Microsoft", "Consulting Services LLC"]
    customers = ["Customer 1", "Customer 2", "Customer 3", "Enterprise Co", "Acme Corp"]
    
    # Generate 100 entries with realistic variation
    for i in range(100):
        entry_id = f"JE{i:04d}"
        day = 1 + (i % 28)
        date = f"2024-04-{day:02d}"
        
        if i % 3 == 0:
            # Revenue entries
            amount = round(random.uniform(1000, 15000), 2)
            customer = random.choice(customers)
            entries.append(JournalEntry(
                entry_id=entry_id,
                date=date,
                account_code="1000",
                account_name="Cash",
                debit=amount,
                credit=0,
                description=f"Payment from {customer}",
                vendor_or_customer=customer
            ))
            entries.append(JournalEntry(
                entry_id=entry_id,
                date=date,
                account_code="4000",
                account_name="Service Revenue",
                debit=0,
                credit=amount,
                description=f"Payment from {customer}",
                vendor_or_customer=customer
            ))
        else:
            # Expense entries
            amount = round(random.uniform(100, 5000), 2)
            vendor = random.choice(vendors)
            entries.append(JournalEntry(
                entry_id=entry_id,
                date=date,
                account_code="6000",
                account_name="Operating Expense",
                debit=amount,
                credit=0,
                description=f"Payment to {vendor}",
                vendor_or_customer=vendor
            ))
            entries.append(JournalEntry(
                entry_id=entry_id,
                date=date,
                account_code="1000",
                account_name="Cash",
                debit=0,
                credit=amount,
                description=f"Payment to {vendor}",
                vendor_or_customer=vendor
            ))
    
    return GeneralLedger(
        company_id=sample_company_id,
        entries=entries,
        period_start="2024-04-01",
        period_end="2024-06-30"
    )


@pytest.fixture
def sample_findings_list():
    """Create a sample list of findings for testing."""
    return [
        {
            "finding_id": "F001",
            "category": "fraud",
            "severity": "critical",
            "issue": "Potential Structuring",
            "details": "Multiple transactions just under threshold",
            "recommendation": "Investigate further"
        },
        {
            "finding_id": "F002", 
            "category": "classification",
            "severity": "high",
            "issue": "Expense Misclassification",
            "details": "Travel expense in wrong account",
            "recommendation": "Reclassify expense"
        },
        {
            "finding_id": "F003",
            "category": "documentation",
            "severity": "medium",
            "issue": "Missing Receipt",
            "details": "Receipt not attached",
            "recommendation": "Obtain receipt"
        },
        {
            "finding_id": "F004",
            "category": "timing",
            "severity": "low",
            "issue": "Weekend Transaction",
            "details": "Transaction posted on Saturday",
            "recommendation": "Verify authorization"
        }
    ]
