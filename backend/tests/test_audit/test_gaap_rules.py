"""
Tests for GAAP Rules Engine.
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audit.gaap_rules import GAAPRulesEngine
from core.schemas import (
    GeneralLedger, JournalEntry, TrialBalance, TrialBalanceRow,
    ChartOfAccounts, Account, AccountingBasis, FindingCategory
)


class TestGAAPRulesEngineBasics:
    """Test basic GAAP rules engine functionality."""
    
    @pytest.fixture
    def engine(self):
        return GAAPRulesEngine()
    
    @pytest.mark.asyncio
    async def test_check_compliance_returns_list(self, engine, sample_gl, sample_tb, sample_coa):
        """Test that check_compliance returns a list."""
        findings = await engine.check_compliance(
            gl=sample_gl,
            tb=sample_tb,
            coa=sample_coa,
            basis=AccountingBasis.ACCRUAL
        )
        assert isinstance(findings, list)
    
    @pytest.mark.asyncio
    async def test_findings_have_required_fields(self, engine, sample_gl, sample_tb, sample_coa):
        """Test that all findings have required fields."""
        findings = await engine.check_compliance(
            gl=sample_gl,
            tb=sample_tb,
            coa=sample_coa,
            basis=AccountingBasis.ACCRUAL
        )
        
        for finding in findings:
            assert "finding_id" in finding
            assert "category" in finding
            assert "severity" in finding
            assert "issue" in finding


class TestApprovalControls:
    """Test approval control checks."""
    
    @pytest.fixture
    def engine(self):
        return GAAPRulesEngine()
    
    def test_flags_high_value_transactions(self, engine, sample_company_id):
        """Test that high-value transactions are flagged."""
        entries = [
            JournalEntry(entry_id="HV1", date="2024-04-15", account_code="6000", account_name="Expense",
                        debit=15000.00, credit=0, description="Large payment", vendor_or_customer="Vendor"),
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = engine._check_approval_controls(gl)
        
        # Should flag high-value transaction
        assert len(findings) > 0
        assert any("High-Value" in f.get("issue", "") for f in findings)
    
    def test_ignores_low_value_transactions(self, engine, sample_company_id):
        """Test that low-value transactions are not flagged."""
        entries = [
            JournalEntry(entry_id="LV1", date="2024-04-15", account_code="6000", account_name="Expense",
                        debit=100.00, credit=0, description="Small payment", vendor_or_customer="Vendor"),
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = engine._check_approval_controls(gl)
        
        # Should not flag low-value transaction
        assert len(findings) == 0


class TestExpenseClassification:
    """Test expense classification checks."""
    
    @pytest.fixture
    def engine(self):
        return GAAPRulesEngine()
    
    def test_detects_travel_misclassification(self, engine, sample_company_id):
        """Test detection of travel expenses coded to wrong account."""
        entries = [
            JournalEntry(entry_id="TRV1", date="2024-04-15", account_code="6900", account_name="Miscellaneous",
                        debit=500.00, credit=0, description="Delta Airlines flight to NYC", vendor_or_customer="Delta"),
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = engine._check_expense_classification(gl)
        
        # Should detect travel misclassification
        assert len(findings) > 0
        assert any("Misclassification" in f.get("issue", "") for f in findings)
    
    def test_accepts_proper_travel_classification(self, engine, sample_company_id):
        """Test that properly classified travel is not flagged."""
        entries = [
            JournalEntry(entry_id="TRV1", date="2024-04-15", account_code="6600", account_name="Travel Expense",
                        debit=500.00, credit=0, description="Delta Airlines flight to NYC", vendor_or_customer="Delta"),
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = engine._check_expense_classification(gl)
        
        # Should not flag properly classified expense
        assert len(findings) == 0


class TestRevenueRecognition:
    """Test revenue recognition checks."""
    
    @pytest.fixture
    def engine(self):
        return GAAPRulesEngine()
    
    def test_flags_large_period_end_revenue(self, engine, sample_company_id):
        """Test flagging of large revenue entries at period end."""
        entries = [
            JournalEntry(entry_id="REV1", date="2024-06-30", account_code="4000", account_name="Revenue",
                        debit=0, credit=50000.00, description="Large sale", vendor_or_customer="Customer"),
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = engine._check_revenue_recognition(gl)
        
        # Should flag large period-end revenue
        assert len(findings) > 0
        assert any("Period-End Revenue" in f.get("issue", "") for f in findings)


class TestMatchingPrinciple:
    """Test matching principle checks."""
    
    @pytest.fixture
    def engine(self):
        return GAAPRulesEngine()
    
    def test_detects_unamortized_prepaids(self, engine, sample_company_id):
        """Test detection of prepaid expenses without amortization."""
        entries = [
            JournalEntry(entry_id="PP1", date="2024-04-01", account_code="1200", account_name="Prepaid Expenses",
                        debit=12000.00, credit=0, description="Annual insurance premium", vendor_or_customer="Insurance Co"),
            JournalEntry(entry_id="PP1", date="2024-04-01", account_code="1000", account_name="Cash",
                        debit=0, credit=12000.00, description="Payment", vendor_or_customer="Insurance Co"),
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        tb_rows = [
            TrialBalanceRow(account_code="1200", account_name="Prepaid Expenses", debit=12000, credit=0, ending_balance=12000),
        ]
        
        tb = TrialBalance(
            company_id=sample_company_id,
            period_end="2024-06-30",
            rows=tb_rows,
            total_debits=12000,
            total_credits=0,
            is_balanced=False
        )
        
        findings = engine._check_matching_principle(gl, tb)
        
        # Should detect unamortized prepaid
        assert len(findings) > 0
        assert any("Prepaid" in f.get("issue", "") or "amortiz" in f.get("issue", "").lower() for f in findings)


class TestCashBasisCompliance:
    """Test cash basis compliance checks."""
    
    @pytest.fixture
    def engine(self):
        return GAAPRulesEngine()
    
    def test_detects_ar_under_cash_basis(self, engine, sample_company_id):
        """Test detection of AR entries under cash basis."""
        entries = [
            JournalEntry(entry_id="AR1", date="2024-04-15", account_code="1100", account_name="Accounts Receivable",
                        debit=5000.00, credit=0, description="Credit sale", vendor_or_customer="Customer"),
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = engine._check_cash_basis_compliance(gl)
        
        # Should detect AR under cash basis
        assert len(findings) > 0
        assert any("Accrual Entry Under Cash Basis" in f.get("issue", "") for f in findings)
    
    def test_detects_ap_under_cash_basis(self, engine, sample_company_id):
        """Test detection of AP entries under cash basis."""
        entries = [
            JournalEntry(entry_id="AP1", date="2024-04-15", account_code="2000", account_name="Accounts Payable",
                        debit=0, credit=5000.00, description="Credit purchase", vendor_or_customer="Vendor"),
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = engine._check_cash_basis_compliance(gl)
        
        # Should detect AP under cash basis
        assert len(findings) > 0


class TestBasisSpecificRules:
    """Test that correct rules apply based on accounting basis."""
    
    @pytest.fixture
    def engine(self):
        return GAAPRulesEngine()
    
    @pytest.mark.asyncio
    async def test_accrual_specific_rules_applied(self, engine, sample_gl, sample_tb, sample_coa):
        """Test that accrual-specific rules are applied for accrual basis."""
        # This test verifies the engine runs accrual rules
        findings = await engine.check_compliance(
            gl=sample_gl,
            tb=sample_tb,
            coa=sample_coa,
            basis=AccountingBasis.ACCRUAL
        )
        
        # Accrual-specific checks should run (revenue recognition, matching)
        # We can't guarantee findings, but the method should complete without error
        assert isinstance(findings, list)
    
    @pytest.mark.asyncio
    async def test_cash_specific_rules_applied(self, engine, sample_company_id):
        """Test that cash-specific rules are applied for cash basis."""
        # Create GL with AR entry (which should be flagged under cash basis)
        entries = [
            JournalEntry(entry_id="AR1", date="2024-04-15", account_code="1100", account_name="AR",
                        debit=5000.00, credit=0, description="Sale", vendor_or_customer="Customer"),
            JournalEntry(entry_id="AR1", date="2024-04-15", account_code="4000", account_name="Revenue",
                        debit=0, credit=5000.00, description="Sale", vendor_or_customer="Customer"),
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        tb = TrialBalance(
            company_id=sample_company_id,
            period_end="2024-06-30",
            rows=[],
            total_debits=5000,
            total_credits=5000,
            is_balanced=True
        )
        
        coa = ChartOfAccounts(
            company_id=sample_company_id,
            accounts=[
                Account(code="1100", name="AR", type="asset", normal_balance="debit"),
                Account(code="4000", name="Revenue", type="revenue", normal_balance="credit"),
            ]
        )
        
        findings = await engine.check_compliance(
            gl=gl,
            tb=tb,
            coa=coa,
            basis=AccountingBasis.CASH
        )
        
        # Should have finding for AR under cash basis
        ar_findings = [f for f in findings if "Cash Basis" in f.get("issue", "")]
        assert len(ar_findings) > 0
