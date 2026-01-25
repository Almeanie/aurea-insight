"""
Tests for Risk Scorer module.
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audit.risk_scorer import RiskScorer
from core.schemas import Severity, FindingCategory


class TestRiskScorerBasics:
    """Test basic risk scoring functionality."""
    
    @pytest.fixture
    def scorer(self):
        return RiskScorer()
    
    def test_calculate_returns_dict(self, scorer, sample_findings_list):
        """Test that calculate returns a dictionary."""
        result = scorer.calculate(sample_findings_list)
        assert isinstance(result, dict)
    
    def test_result_has_required_fields(self, scorer, sample_findings_list):
        """Test that result has all required fields."""
        result = scorer.calculate(sample_findings_list)
        
        required_fields = [
            "overall_score", "risk_level", "total_findings",
            "critical_count", "high_count", "medium_count", "low_count",
            "category_breakdown", "requires_immediate_action", "interpretation"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing field: {field}"


class TestEmptyFindings:
    """Test scoring with no findings."""
    
    @pytest.fixture
    def scorer(self):
        return RiskScorer()
    
    def test_empty_findings_low_risk(self, scorer):
        """Test that empty findings result in low risk."""
        result = scorer.calculate([])
        
        assert result["overall_score"] == 0
        assert result["risk_level"] == "low"
        assert result["total_findings"] == 0
        assert result["requires_immediate_action"] is False
    
    def test_empty_findings_positive_interpretation(self, scorer):
        """Test that empty findings have positive interpretation."""
        result = scorer.calculate([])
        
        assert "No findings" in result["interpretation"]


class TestSeverityCounts:
    """Test severity counting."""
    
    @pytest.fixture
    def scorer(self):
        return RiskScorer()
    
    def test_counts_by_severity(self, scorer, sample_findings_list):
        """Test that severities are counted correctly."""
        result = scorer.calculate(sample_findings_list)
        
        assert result["critical_count"] == 1
        assert result["high_count"] == 1
        assert result["medium_count"] == 1
        assert result["low_count"] == 1
        assert result["total_findings"] == 4
    
    def test_handles_enum_and_string_severities(self, scorer):
        """Test that both enum values and strings work for severity."""
        findings = [
            {"severity": Severity.CRITICAL.value, "category": "fraud"},
            {"severity": "critical", "category": "fraud"},
        ]
        
        result = scorer.calculate(findings)
        
        assert result["critical_count"] == 2


class TestRiskLevelCalculation:
    """Test risk level determination."""
    
    @pytest.fixture
    def scorer(self):
        return RiskScorer()
    
    def test_critical_risk_level(self, scorer):
        """Test that multiple critical findings trigger critical risk."""
        findings = [
            {"severity": "critical", "category": "fraud"},
            {"severity": "critical", "category": "fraud"},
        ]
        
        result = scorer.calculate(findings)
        
        assert result["risk_level"] == "critical"
        assert result["requires_immediate_action"] is True
    
    def test_high_risk_level(self, scorer):
        """Test high risk level determination."""
        findings = [
            {"severity": "critical", "category": "fraud"},
            {"severity": "high", "category": "balance"},
            {"severity": "medium", "category": "classification"},
        ]
        
        result = scorer.calculate(findings)
        
        assert result["risk_level"] in ["critical", "high"]
        assert result["requires_immediate_action"] is True
    
    def test_medium_risk_level(self, scorer):
        """Test medium risk level determination."""
        findings = [
            {"severity": "medium", "category": "classification"},
            {"severity": "low", "category": "documentation"},
        ]
        
        result = scorer.calculate(findings)
        
        # With weighted score, this should be medium or low
        assert result["risk_level"] in ["medium", "low"]
    
    def test_low_risk_level(self, scorer):
        """Test low risk level determination."""
        findings = [
            {"severity": "low", "category": "documentation"},
        ]
        
        result = scorer.calculate(findings)
        
        assert result["risk_level"] == "low"
        assert result["requires_immediate_action"] is False


class TestScoreNormalization:
    """Test score normalization to 0-100 scale."""
    
    @pytest.fixture
    def scorer(self):
        return RiskScorer()
    
    def test_score_within_bounds(self, scorer, sample_findings_list):
        """Test that score is within 0-100."""
        result = scorer.calculate(sample_findings_list)
        
        assert 0 <= result["overall_score"] <= 100
    
    def test_all_critical_max_score(self, scorer):
        """Test that all critical findings approach max score."""
        findings = [
            {"severity": "critical", "category": "fraud"} for _ in range(10)
        ]
        
        result = scorer.calculate(findings)
        
        assert result["overall_score"] == 100  # All critical = 100%
    
    def test_all_low_min_score(self, scorer):
        """Test that all low findings result in low score."""
        findings = [
            {"severity": "low", "category": "documentation"} for _ in range(5)
        ]
        
        result = scorer.calculate(findings)
        
        # All low should result in 10% (5 * 1 / 5 * 10 = 10%)
        assert result["overall_score"] < 20


class TestCategoryBreakdown:
    """Test category score breakdown."""
    
    @pytest.fixture
    def scorer(self):
        return RiskScorer()
    
    def test_category_breakdown_calculated(self, scorer, sample_findings_list):
        """Test that category breakdown is calculated."""
        result = scorer.calculate(sample_findings_list)
        
        assert "category_breakdown" in result
        assert isinstance(result["category_breakdown"], dict)
    
    def test_category_scores_weighted(self, scorer):
        """Test that category scores use severity weights."""
        findings = [
            {"severity": "critical", "category": "fraud"},  # Weight 10
            {"severity": "low", "category": "documentation"},  # Weight 1
        ]
        
        result = scorer.calculate(findings)
        
        assert result["category_breakdown"]["fraud"] > result["category_breakdown"]["documentation"]


class TestInterpretation:
    """Test interpretation text generation."""
    
    @pytest.fixture
    def scorer(self):
        return RiskScorer()
    
    def test_critical_interpretation(self, scorer):
        """Test critical risk interpretation."""
        findings = [
            {"severity": "critical", "category": "fraud"},
            {"severity": "critical", "category": "fraud"},
        ]
        
        result = scorer.calculate(findings)
        
        assert "CRITICAL RISK" in result["interpretation"]
        assert "immediate" in result["interpretation"].lower()
    
    def test_high_interpretation(self, scorer):
        """Test high risk interpretation."""
        findings = [
            {"severity": "critical", "category": "fraud"},
            {"severity": "high", "category": "balance"},
        ]
        
        result = scorer.calculate(findings)
        
        # Could be CRITICAL or HIGH depending on score
        assert "RISK" in result["interpretation"]
    
    def test_low_interpretation(self, scorer):
        """Test low risk interpretation."""
        findings = [
            {"severity": "low", "category": "documentation"},
        ]
        
        result = scorer.calculate(findings)
        
        assert "LOW RISK" in result["interpretation"]
        assert "reliable" in result["interpretation"].lower()


class TestSeverityWeights:
    """Test severity weight configuration."""
    
    def test_weights_defined(self):
        """Test that severity weights are properly defined."""
        scorer = RiskScorer()
        
        assert scorer.SEVERITY_WEIGHTS["critical"] == 10
        assert scorer.SEVERITY_WEIGHTS["high"] == 5
        assert scorer.SEVERITY_WEIGHTS["medium"] == 2
        assert scorer.SEVERITY_WEIGHTS["low"] == 1
    
    def test_enum_value_weights_match(self):
        """Test that enum value weights match string weights."""
        scorer = RiskScorer()
        
        assert scorer.SEVERITY_WEIGHTS[Severity.CRITICAL.value] == scorer.SEVERITY_WEIGHTS["critical"]
        assert scorer.SEVERITY_WEIGHTS[Severity.HIGH.value] == scorer.SEVERITY_WEIGHTS["high"]
