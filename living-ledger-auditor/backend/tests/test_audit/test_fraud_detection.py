"""
Tests for Fraud Detection module.
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audit.fraud_detection import FraudDetector
from core.schemas import GeneralLedger, JournalEntry, FindingCategory, Severity


class TestFraudDetectorBasics:
    """Test basic fraud detection functionality."""
    
    @pytest.fixture
    def detector(self):
        return FraudDetector()
    
    def test_detect_fraud_patterns_returns_list(self, detector, sample_gl):
        """Test that detect_fraud_patterns returns a list."""
        findings = detector.detect_fraud_patterns(sample_gl)
        assert isinstance(findings, list)
    
    def test_findings_have_required_fields(self, detector, sample_gl):
        """Test that all findings have required fields."""
        findings = detector.detect_fraud_patterns(sample_gl)
        
        for finding in findings:
            assert "finding_id" in finding
            assert "category" in finding
            assert "severity" in finding
            assert "issue" in finding
            assert "details" in finding
            assert "recommendation" in finding


class TestDuplicatePaymentDetection:
    """Test duplicate payment detection."""
    
    @pytest.fixture
    def detector(self):
        return FraudDetector()
    
    def test_detects_duplicate_payments(self, detector, sample_company_id):
        """Test detection of duplicate payments."""
        # Create entries with duplicate payment
        entries = [
            # First payment
            JournalEntry(entry_id="PAY1", date="2024-04-15", account_code="6000", account_name="Expense",
                        debit=5000.00, credit=0, description="Payment to Vendor A", vendor_or_customer="Vendor A"),
            JournalEntry(entry_id="PAY1", date="2024-04-15", account_code="1000", account_name="Cash",
                        debit=0, credit=5000.00, description="Payment to Vendor A", vendor_or_customer="Vendor A"),
            # Duplicate payment (same vendor, same amount, within 7 days)
            JournalEntry(entry_id="PAY2", date="2024-04-18", account_code="6000", account_name="Expense",
                        debit=5000.00, credit=0, description="Payment to Vendor A", vendor_or_customer="Vendor A"),
            JournalEntry(entry_id="PAY2", date="2024-04-18", account_code="1000", account_name="Cash",
                        debit=0, credit=5000.00, description="Payment to Vendor A", vendor_or_customer="Vendor A"),
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = detector._detect_duplicate_payments(gl)
        
        # Should detect duplicate
        assert len(findings) > 0
        dup_findings = [f for f in findings if "Duplicate" in f.get("issue", "")]
        assert len(dup_findings) > 0
    
    def test_ignores_different_amounts(self, detector, sample_company_id):
        """Test that different amounts to same vendor are not flagged as duplicates."""
        entries = [
            JournalEntry(entry_id="PAY1", date="2024-04-15", account_code="6000", account_name="Expense",
                        debit=5000.00, credit=0, description="Payment", vendor_or_customer="Vendor A"),
            JournalEntry(entry_id="PAY2", date="2024-04-18", account_code="6000", account_name="Expense",
                        debit=3000.00, credit=0, description="Payment", vendor_or_customer="Vendor A"),  # Different amount
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = detector._detect_duplicate_payments(gl)
        
        # Should not detect duplicate for different amounts
        assert len(findings) == 0


class TestStructuringDetection:
    """Test structuring (smurfing) detection."""
    
    @pytest.fixture
    def detector(self):
        return FraudDetector()
    
    def test_detects_structuring(self, detector, sample_company_id):
        """Test detection of structuring patterns."""
        # Create entries just under $10k threshold
        entries = []
        for i in range(4):
            amount = 9500 + (i * 100)  # $9500, $9600, $9700, $9800
            entries.append(JournalEntry(
                entry_id=f"STR{i}",
                date=f"2024-04-{15+i}",
                account_code="6000",
                account_name="Expense",
                debit=float(amount),
                credit=0,
                description="Cash withdrawal",
                vendor_or_customer="Bank Withdrawal"
            ))
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = detector._detect_structuring(gl)
        
        # Should detect structuring
        assert len(findings) > 0
        struct_findings = [f for f in findings if "Structuring" in f.get("issue", "")]
        assert len(struct_findings) > 0
        
        # Should be critical severity
        assert struct_findings[0].get("severity") == Severity.CRITICAL.value
    
    def test_ignores_normal_transactions(self, detector, sample_company_id):
        """Test that normal transactions below threshold are not flagged."""
        entries = [
            JournalEntry(entry_id="E1", date="2024-04-15", account_code="6000", account_name="Expense",
                        debit=1000.00, credit=0, description="Normal", vendor_or_customer="Vendor"),
            JournalEntry(entry_id="E2", date="2024-04-16", account_code="6000", account_name="Expense",
                        debit=2000.00, credit=0, description="Normal", vendor_or_customer="Vendor"),
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = detector._detect_structuring(gl)
        
        # Should not detect structuring for amounts well below threshold
        assert len(findings) == 0


class TestRoundNumberDetection:
    """Test round number transaction detection."""
    
    @pytest.fixture
    def detector(self):
        return FraudDetector()
    
    def test_detects_multiple_round_numbers(self, detector, sample_company_id):
        """Test detection of suspicious round number transactions."""
        entries = [
            JournalEntry(entry_id="R1", date="2024-04-15", account_code="6000", account_name="Expense",
                        debit=5000.00, credit=0, description="Consulting", vendor_or_customer="Consultant"),
            JournalEntry(entry_id="R2", date="2024-04-18", account_code="6000", account_name="Expense",
                        debit=10000.00, credit=0, description="Services", vendor_or_customer="Service Co"),
            JournalEntry(entry_id="R3", date="2024-04-20", account_code="6000", account_name="Expense",
                        debit=2500.00, credit=0, description="Advisory", vendor_or_customer="Advisor"),
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = detector._detect_round_numbers(gl)
        
        # Should detect round numbers
        assert len(findings) > 0
    
    def test_ignores_single_round_number(self, detector, sample_company_id):
        """Test that single round number is not suspicious."""
        entries = [
            JournalEntry(entry_id="R1", date="2024-04-15", account_code="6000", account_name="Expense",
                        debit=5000.00, credit=0, description="Normal", vendor_or_customer="Vendor"),
            JournalEntry(entry_id="R2", date="2024-04-18", account_code="6000", account_name="Expense",
                        debit=1234.56, credit=0, description="Normal", vendor_or_customer="Vendor"),
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = detector._detect_round_numbers(gl)
        
        # Single round number should not trigger finding
        assert len(findings) == 0


class TestVendorAnomalies:
    """Test vendor anomaly detection."""
    
    @pytest.fixture
    def detector(self):
        return FraudDetector()
    
    def test_detects_generic_vendor_names(self, detector, sample_company_id):
        """Test detection of generic vendor names (shell company indicators)."""
        entries = [
            JournalEntry(entry_id="V1", date="2024-04-15", account_code="6000", account_name="Expense",
                        debit=25000.00, credit=0, description="Services",
                        vendor_or_customer="Global Management Consulting Solutions"),  # Multiple generic terms
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = detector._detect_vendor_anomalies(gl)
        
        # Should detect suspicious vendor name
        assert len(findings) > 0
        vendor_findings = [f for f in findings if "Generic Vendor" in f.get("issue", "")]
        assert len(vendor_findings) > 0
    
    def test_ignores_normal_vendors(self, detector, sample_company_id):
        """Test that normal vendor names are not flagged."""
        entries = [
            JournalEntry(entry_id="V1", date="2024-04-15", account_code="6000", account_name="Expense",
                        debit=5000.00, credit=0, description="Rent",
                        vendor_or_customer="Metro Commercial Properties"),
            JournalEntry(entry_id="V2", date="2024-04-18", account_code="6000", account_name="Expense",
                        debit=3000.00, credit=0, description="Software",
                        vendor_or_customer="Microsoft"),
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = detector._detect_vendor_anomalies(gl)
        
        # Normal vendors should not trigger findings
        assert len(findings) == 0


class TestFraudCategory:
    """Test that fraud findings have correct category."""
    
    @pytest.fixture
    def detector(self):
        return FraudDetector()
    
    def test_all_findings_are_fraud_category(self, detector, large_gl):
        """Test that all fraud detection findings have fraud category."""
        findings = detector.detect_fraud_patterns(large_gl)
        
        for finding in findings:
            assert finding.get("category") == FindingCategory.FRAUD.value
