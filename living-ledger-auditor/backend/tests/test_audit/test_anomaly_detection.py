"""
Tests for Anomaly Detection module.
"""
import pytest
import sys
from pathlib import Path
import random
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audit.anomaly_detection import AnomalyDetector
from core.schemas import GeneralLedger, JournalEntry, FindingCategory


class TestAnomalyDetectorBasics:
    """Test basic anomaly detection functionality."""
    
    @pytest.fixture
    def detector(self):
        return AnomalyDetector()
    
    def test_detect_anomalies_returns_list(self, detector, sample_gl):
        """Test that detect_anomalies returns a list."""
        findings = detector.detect_anomalies(sample_gl)
        assert isinstance(findings, list)
    
    def test_findings_have_required_fields(self, detector, large_gl):
        """Test that all findings have required fields."""
        findings = detector.detect_anomalies(large_gl)
        
        for finding in findings:
            assert "finding_id" in finding
            assert "category" in finding
            assert "severity" in finding
            assert "issue" in finding
            assert "details" in finding
            assert "recommendation" in finding
            assert "confidence" in finding


class TestBenfordsLaw:
    """Test Benford's Law analysis."""
    
    @pytest.fixture
    def detector(self):
        return AnomalyDetector()
    
    def test_benford_needs_minimum_data(self, detector, sample_company_id):
        """Test that Benford analysis requires minimum data points."""
        # Create GL with too few entries
        entries = [
            JournalEntry(entry_id="E1", date="2024-04-15", account_code="1000", account_name="Cash", debit=100, credit=0, description="Test"),
        ]
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = detector._benfords_law_analysis(gl)
        
        # Should return empty - not enough data
        assert len(findings) == 0
    
    def test_benford_detects_fabricated_numbers(self, detector, sample_company_id):
        """Test that Benford's Law can detect fabricated numbers."""
        # Create entries with suspicious first digit distribution
        # All starting with 9 (should be rare in natural data)
        entries = []
        for i in range(100):
            amount = 9000 + random.randint(0, 999)
            entries.append(JournalEntry(
                entry_id=f"E{i}",
                date="2024-04-15",
                account_code="6000",
                account_name="Expense",
                debit=float(amount),
                credit=0,
                description="Fabricated"
            ))
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = detector._benfords_law_analysis(gl)
        
        # Should detect deviation from Benford's law
        assert len(findings) > 0
        assert any("Benford" in f.get("issue", "") for f in findings)


class TestStatisticalOutliers:
    """Test statistical outlier detection."""
    
    @pytest.fixture
    def detector(self):
        return AnomalyDetector()
    
    def test_detects_large_outliers(self, detector, sample_company_id):
        """Test detection of statistical outliers."""
        # Create entries with one extreme outlier
        entries = []
        
        # Normal entries around $1000
        for i in range(50):
            amount = 1000 + random.uniform(-200, 200)
            entries.append(JournalEntry(
                entry_id=f"E{i}",
                date="2024-04-15",
                account_code="6000",
                account_name="Expense",
                debit=round(amount, 2),
                credit=0,
                description="Normal expense"
            ))
        
        # Add extreme outlier
        entries.append(JournalEntry(
            entry_id="OUTLIER",
            date="2024-04-15",
            account_code="6000",
            account_name="Expense",
            debit=100000.00,  # Extreme outlier
            credit=0,
            description="Suspicious large payment"
        ))
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = detector._statistical_outliers(gl)
        
        # Should detect the outlier
        assert len(findings) > 0
        outlier_findings = [f for f in findings if "OUTLIER" in f.get("affected_transactions", [])]
        assert len(outlier_findings) > 0
    
    def test_no_outliers_in_uniform_data(self, detector, sample_company_id):
        """Test that uniform data produces no outlier findings."""
        # Create entries with very uniform amounts
        entries = []
        for i in range(50):
            entries.append(JournalEntry(
                entry_id=f"E{i}",
                date="2024-04-15",
                account_code="6000",
                account_name="Expense",
                debit=1000.00,  # All same amount
                credit=0,
                description="Uniform expense"
            ))
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = detector._statistical_outliers(gl)
        
        # Uniform data should not trigger outlier detection
        assert len(findings) == 0


class TestTimingAnomalies:
    """Test timing anomaly detection."""
    
    @pytest.fixture
    def detector(self):
        return AnomalyDetector()
    
    def test_detects_activity_spikes(self, detector, sample_company_id):
        """Test detection of unusual activity spikes."""
        entries = []
        
        # Normal activity - 2 entries per day
        for day in range(1, 28):
            for i in range(2):
                entries.append(JournalEntry(
                    entry_id=f"E{day}_{i}",
                    date=f"2024-04-{day:02d}",
                    account_code="6000",
                    account_name="Expense",
                    debit=1000.00,
                    credit=0,
                    description="Normal"
                ))
        
        # Spike on one day - 20 entries
        for i in range(20):
            entries.append(JournalEntry(
                entry_id=f"SPIKE_{i}",
                date="2024-04-28",
                account_code="6000",
                account_name="Expense",
                debit=1000.00,
                credit=0,
                description="Spike day"
            ))
        
        gl = GeneralLedger(
            company_id=sample_company_id,
            entries=entries,
            period_start="2024-04-01",
            period_end="2024-06-30"
        )
        
        findings = detector._timing_anomalies(gl)
        
        # Should detect the spike
        assert len(findings) > 0
        spike_findings = [f for f in findings if "2024-04-28" in f.get("details", "")]
        assert len(spike_findings) > 0


class TestAnomalyConfidence:
    """Test anomaly confidence scoring."""
    
    @pytest.fixture
    def detector(self):
        return AnomalyDetector()
    
    def test_confidence_within_bounds(self, detector, large_gl):
        """Test that confidence scores are within valid bounds."""
        findings = detector.detect_anomalies(large_gl)
        
        for finding in findings:
            confidence = finding.get("confidence", 0)
            assert 0 <= confidence <= 1, f"Confidence {confidence} out of bounds"
