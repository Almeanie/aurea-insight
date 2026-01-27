"""
Tests for Issue Injector.
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from generators.issue_injector import IssueInjector, ISSUE_POOL, IssueType
from generators.coa_generator import COAGenerator
from generators.gl_generator import GLGenerator
from core.schemas import Industry, AccountingBasis, FindingCategory, Severity


class TestIssuePool:
    """Test issue pool configuration."""
    
    def test_issue_pool_not_empty(self):
        """Test that issue pool has issues defined."""
        assert len(ISSUE_POOL) > 0
    
    def test_all_categories_represented(self):
        """Test that all finding categories have issues."""
        categories = {issue.category for issue in ISSUE_POOL}
        expected = set(FindingCategory)
        assert categories == expected, f"Missing categories: {expected - categories}"
    
    def test_all_severities_represented(self):
        """Test that various severities are represented."""
        severities = {issue.severity for issue in ISSUE_POOL}
        # Should have at least critical, high, and medium
        assert Severity.CRITICAL in severities
        assert Severity.HIGH in severities
        assert Severity.MEDIUM in severities
    
    def test_issue_probabilities_valid(self):
        """Test that issue probabilities are valid (0-1)."""
        for issue in ISSUE_POOL:
            assert 0 < issue.probability <= 1, f"Invalid probability for {issue.name}: {issue.probability}"


class TestIssueType:
    """Test IssueType class."""
    
    def test_issue_type_creation(self):
        """Test creating an IssueType."""
        issue = IssueType(
            category=FindingCategory.FRAUD,
            name="Test Issue",
            description="Test description",
            severity=Severity.HIGH,
            gaap_principle="Test Principle",
            probability=0.1
        )
        
        assert issue.name == "Test Issue"
        assert issue.category == FindingCategory.FRAUD
        assert issue.severity == Severity.HIGH


class TestIssueInjectorBasics:
    """Test basic issue injection functionality."""
    
    @pytest.fixture
    def injector(self):
        return IssueInjector()
    
    @pytest.fixture
    def coa_generator(self):
        return COAGenerator()
    
    @pytest.fixture
    def gl_generator(self):
        return GLGenerator()
    
    @pytest.mark.asyncio
    async def test_inject_issues(self, injector, coa_generator, gl_generator, sample_company_id):
        """Test basic issue injection."""
        coa = await coa_generator.generate(
            company_id=sample_company_id,
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL
        )
        
        gl = await gl_generator.generate(
            company_id=sample_company_id,
            coa=coa,
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL,
            num_transactions=50,
            reporting_period="Q2 2024"
        )
        
        original_entry_count = len(gl.entries)
        
        modified_gl, injected_issues = await injector.inject(
            gl=gl,
            coa=coa,
            issue_count=5,
            accounting_basis=AccountingBasis.ACCRUAL
        )
        
        assert modified_gl is not None
        assert len(injected_issues) > 0
        assert len(injected_issues) <= 5
    
    @pytest.mark.asyncio
    async def test_injected_issues_have_metadata(self, injector, sample_gl, sample_coa):
        """Test that injected issues have proper metadata."""
        modified_gl, injected_issues = await injector.inject(
            gl=sample_gl,
            coa=sample_coa,
            issue_count=5,
            accounting_basis=AccountingBasis.ACCRUAL
        )
        
        for issue in injected_issues:
            assert "issue_type" in issue
            assert "category" in issue
            assert "severity" in issue
            assert "description" in issue


class TestIssueDiversity:
    """Test issue category diversity."""
    
    @pytest.fixture
    def injector(self):
        return IssueInjector()
    
    def test_select_diverse_issues(self, injector):
        """Test that issue selection provides category diversity."""
        # Select enough issues to cover all categories
        selected = injector._select_diverse_issues(10)
        
        categories = {issue.category for issue in selected}
        
        # Should have issues from multiple categories
        assert len(categories) >= 4, "Should have issues from at least 4 categories"
    
    def test_select_respects_count(self, injector):
        """Test that selection respects requested count."""
        for count in [3, 5, 8, 12]:
            selected = injector._select_diverse_issues(count)
            assert len(selected) <= count


class TestSpecificInjections:
    """Test specific issue injection methods."""
    
    @pytest.fixture
    def injector(self):
        return IssueInjector()
    
    def test_inject_wrong_account(self, injector, sample_journal_entries):
        """Test wrong account injection."""
        entries = list(sample_journal_entries)
        result = injector._inject_wrong_account(entries)
        
        assert "entries" in result
        assert "affected_entries" in result
    
    def test_inject_cutoff_error(self, injector, sample_journal_entries):
        """Test cutoff error injection."""
        entries = list(sample_journal_entries)
        result = injector._inject_cutoff_error(entries)
        
        assert "entries" in result
        assert "affected_entries" in result
    
    def test_inject_personal_expense(self, injector, sample_journal_entries):
        """Test personal expense injection."""
        entries = list(sample_journal_entries)
        original_count = len(entries)
        
        result = injector._inject_personal_expense(entries)
        
        # Should add new entries
        assert len(result["entries"]) > original_count
        assert len(result["affected_entries"]) > 0
    
    def test_inject_duplicate(self, injector, sample_journal_entries):
        """Test duplicate payment injection."""
        entries = list(sample_journal_entries)
        original_count = len(entries)
        
        result = injector._inject_duplicate(entries)
        
        # Should add duplicate entries
        assert len(result["entries"]) > original_count
    
    def test_inject_round_number(self, injector, sample_journal_entries):
        """Test round number transaction injection."""
        entries = list(sample_journal_entries)
        original_count = len(entries)
        
        result = injector._inject_round_number(entries)
        
        # Should add round number entries
        assert len(result["entries"]) > original_count
        
        # Find the injected round number entries
        new_entries = result["entries"][original_count:]
        amounts = [e.debit for e in new_entries if e.debit > 0]
        
        # At least one should be a round number
        round_amounts = [1000, 2500, 5000, 10000]
        assert any(amt in round_amounts for amt in amounts)
    
    def test_inject_structuring(self, injector, sample_journal_entries):
        """Test structuring injection."""
        entries = list(sample_journal_entries)
        original_count = len(entries)
        
        result = injector._inject_structuring(entries)
        
        # Should add multiple transactions under threshold
        assert len(result["entries"]) > original_count
        assert len(result["affected_entries"]) >= 3  # At least 3 structuring entries


class TestInjectionIntegrity:
    """Test that injections maintain GL integrity."""
    
    @pytest.fixture
    def injector(self):
        return IssueInjector()
    
    @pytest.fixture
    def coa_generator(self):
        return COAGenerator()
    
    @pytest.fixture
    def gl_generator(self):
        return GLGenerator()
    
    @pytest.mark.asyncio
    async def test_gl_remains_valid(self, injector, coa_generator, gl_generator, sample_company_id):
        """Test that GL remains valid after injection."""
        coa = await coa_generator.generate(
            company_id=sample_company_id,
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL
        )
        
        gl = await gl_generator.generate(
            company_id=sample_company_id,
            coa=coa,
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL,
            num_transactions=50,
            reporting_period="Q2 2024"
        )
        
        modified_gl, _ = await injector.inject(
            gl=gl,
            coa=coa,
            issue_count=10,
            accounting_basis=AccountingBasis.ACCRUAL
        )
        
        # All entries should still have required fields
        for entry in modified_gl.entries:
            assert entry.entry_id is not None
            assert entry.date is not None
            assert entry.account_code is not None
            assert entry.debit >= 0
            assert entry.credit >= 0
