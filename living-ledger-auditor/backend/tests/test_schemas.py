"""Tests for Pydantic schemas."""
import pytest
from datetime import datetime

from core.schemas import (
    CompanyMetadata, Industry, AccountingBasis,
    Account, ChartOfAccounts,
    JournalEntry, GeneralLedger,
    TrialBalanceRow, TrialBalance,
    AuditFinding, Severity, FindingCategory
)


class TestCompanyMetadata:
    """Tests for CompanyMetadata schema."""
    
    def test_create_company_metadata(self):
        """Test creating company metadata."""
        metadata = CompanyMetadata(
            id="test-123",
            name="Test Company LLC",
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL,
            reporting_period="Q2 2024"
        )
        
        assert metadata.id == "test-123"
        assert metadata.name == "Test Company LLC"
        assert metadata.industry == Industry.SAAS
        assert metadata.accounting_basis == AccountingBasis.ACCRUAL
        assert metadata.is_synthetic == True
        assert metadata.currency == "USD"


class TestChartOfAccounts:
    """Tests for Chart of Accounts schema."""
    
    def test_create_account(self):
        """Test creating an account."""
        account = Account(
            code="1000",
            name="Cash",
            type="asset",
            normal_balance="debit"
        )
        
        assert account.code == "1000"
        assert account.name == "Cash"
        assert account.type == "asset"
        assert account.normal_balance == "debit"
    
    def test_create_coa(self):
        """Test creating Chart of Accounts."""
        accounts = [
            Account(code="1000", name="Cash", type="asset", normal_balance="debit"),
            Account(code="2000", name="Accounts Payable", type="liability", normal_balance="credit"),
            Account(code="4000", name="Revenue", type="revenue", normal_balance="credit"),
        ]
        
        coa = ChartOfAccounts(
            company_id="test-123",
            accounts=accounts
        )
        
        assert len(coa.accounts) == 3
        assert coa.company_id == "test-123"


class TestJournalEntry:
    """Tests for Journal Entry schema."""
    
    def test_create_journal_entry(self):
        """Test creating a journal entry."""
        entry = JournalEntry(
            entry_id="JE-001",
            date="2024-06-15",
            account_code="1000",
            account_name="Cash",
            debit=1000.00,
            credit=0,
            description="Customer payment received"
        )
        
        assert entry.entry_id == "JE-001"
        assert entry.debit == 1000.00
        assert entry.credit == 0


class TestTrialBalance:
    """Tests for Trial Balance schema."""
    
    def test_trial_balance_balanced(self):
        """Test balanced trial balance."""
        rows = [
            TrialBalanceRow(account_code="1000", account_name="Cash", debit=10000, credit=0, ending_balance=10000),
            TrialBalanceRow(account_code="3000", account_name="Equity", debit=0, credit=10000, ending_balance=10000),
        ]
        
        tb = TrialBalance(
            company_id="test-123",
            period_end="2024-06-30",
            rows=rows,
            total_debits=10000,
            total_credits=10000,
            is_balanced=True
        )
        
        assert tb.is_balanced == True
        assert tb.total_debits == tb.total_credits


class TestAuditFinding:
    """Tests for Audit Finding schema."""
    
    def test_create_finding(self):
        """Test creating an audit finding."""
        finding = AuditFinding(
            finding_id="FND-001",
            category=FindingCategory.FRAUD,
            severity=Severity.CRITICAL,
            issue="Potential structuring detected",
            details="Multiple transactions just under $10,000 threshold",
            recommendation="Investigate for BSA compliance",
            confidence=0.85
        )
        
        assert finding.severity == Severity.CRITICAL
        assert finding.category == FindingCategory.FRAUD
        assert finding.confidence == 0.85
