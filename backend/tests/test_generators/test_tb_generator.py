"""Tests for Trial Balance generator."""
import pytest

from generators.tb_generator import TBGenerator
from core.schemas import GeneralLedger, JournalEntry, ChartOfAccounts, Account


class TestTBGenerator:
    """Tests for TB derivation from GL."""
    
    @pytest.fixture
    def generator(self):
        return TBGenerator()
    
    @pytest.fixture
    def sample_coa(self):
        return ChartOfAccounts(
            company_id="test-123",
            accounts=[
                Account(code="1000", name="Cash", type="asset", normal_balance="debit"),
                Account(code="4000", name="Revenue", type="revenue", normal_balance="credit"),
                Account(code="6000", name="Rent Expense", type="expense", normal_balance="debit"),
            ]
        )
    
    @pytest.fixture
    def sample_gl(self):
        return GeneralLedger(
            company_id="test-123",
            entries=[
                JournalEntry(entry_id="1", date="2024-06-01", account_code="1000", account_name="Cash", debit=10000, credit=0, description="Initial deposit"),
                JournalEntry(entry_id="1", date="2024-06-01", account_code="4000", account_name="Revenue", debit=0, credit=10000, description="Sales"),
                JournalEntry(entry_id="2", date="2024-06-15", account_code="6000", account_name="Rent", debit=2000, credit=0, description="Rent payment"),
                JournalEntry(entry_id="2", date="2024-06-15", account_code="1000", account_name="Cash", debit=0, credit=2000, description="Rent payment"),
            ],
            period_start="2024-06-01",
            period_end="2024-06-30"
        )
    
    def test_derive_tb_from_gl(self, generator, sample_gl, sample_coa):
        """Test deriving trial balance from general ledger."""
        tb = generator.derive_from_gl(
            company_id="test-123",
            gl=sample_gl,
            coa=sample_coa,
            reporting_period="Q2 2024"
        )
        
        assert tb.company_id == "test-123"
        assert tb.is_balanced == True
        assert tb.total_debits == tb.total_credits
        
        # Check balances
        cash_row = next(r for r in tb.rows if r.account_code == "1000")
        assert cash_row.ending_balance == 8000  # 10000 - 2000
        
        revenue_row = next(r for r in tb.rows if r.account_code == "4000")
        assert revenue_row.ending_balance == 10000
