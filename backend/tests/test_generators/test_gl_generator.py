"""
Tests for General Ledger Generator.
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from generators.gl_generator import GLGenerator, VENDORS, CUSTOMERS
from generators.coa_generator import COAGenerator
from core.schemas import Industry, AccountingBasis


class TestGLGeneratorBasics:
    """Test basic GL generation functionality."""
    
    @pytest.fixture
    def generator(self):
        return GLGenerator()
    
    @pytest.fixture
    def coa_generator(self):
        return COAGenerator()
    
    @pytest.mark.asyncio
    async def test_generate_gl(self, generator, coa_generator, sample_company_id):
        """Test basic GL generation."""
        coa = await coa_generator.generate(
            company_id=sample_company_id,
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL
        )
        
        gl = await generator.generate(
            company_id=sample_company_id,
            coa=coa,
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL,
            num_transactions=50,
            reporting_period="Q2 2024"
        )
        
        assert gl.company_id == sample_company_id
        assert len(gl.entries) > 0
        assert gl.period_start == "2024-04-01"
        assert gl.period_end == "2024-06-30"
    
    @pytest.mark.asyncio
    async def test_gl_entries_have_required_fields(self, generator, coa_generator, sample_company_id):
        """Test that all GL entries have required fields."""
        coa = await coa_generator.generate(
            company_id=sample_company_id,
            industry=Industry.CONSULTING,
            accounting_basis=AccountingBasis.ACCRUAL
        )
        
        gl = await generator.generate(
            company_id=sample_company_id,
            coa=coa,
            industry=Industry.CONSULTING,
            accounting_basis=AccountingBasis.ACCRUAL,
            num_transactions=30,
            reporting_period="Q1 2024"
        )
        
        for entry in gl.entries:
            assert entry.entry_id is not None
            assert entry.date is not None
            assert entry.account_code is not None
            assert entry.account_name is not None
            assert entry.description is not None
            # Either debit or credit should be non-zero
            assert entry.debit >= 0
            assert entry.credit >= 0
            assert entry.debit > 0 or entry.credit > 0


class TestGLBalance:
    """Test GL balance and double-entry accounting."""
    
    @pytest.fixture
    def generator(self):
        return GLGenerator()
    
    @pytest.fixture
    def coa_generator(self):
        return COAGenerator()
    
    @pytest.mark.asyncio
    async def test_gl_entries_balanced(self, generator, coa_generator, sample_company_id):
        """Test that GL entries are balanced (debits = credits)."""
        coa = await coa_generator.generate(
            company_id=sample_company_id,
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL
        )
        
        gl = await generator.generate(
            company_id=sample_company_id,
            coa=coa,
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL,
            num_transactions=50,
            reporting_period="Q2 2024"
        )
        
        total_debits = sum(e.debit for e in gl.entries)
        total_credits = sum(e.credit for e in gl.entries)
        
        # Should be balanced within rounding tolerance
        assert abs(total_debits - total_credits) < 0.01, f"Imbalance: {total_debits} debits vs {total_credits} credits"
    
    @pytest.mark.asyncio
    async def test_entries_grouped_by_entry_id_balance(self, generator, coa_generator, sample_company_id):
        """Test that entries with same entry_id are balanced."""
        coa = await coa_generator.generate(
            company_id=sample_company_id,
            industry=Industry.AGENCY,
            accounting_basis=AccountingBasis.ACCRUAL
        )
        
        gl = await generator.generate(
            company_id=sample_company_id,
            coa=coa,
            industry=Industry.AGENCY,
            accounting_basis=AccountingBasis.ACCRUAL,
            num_transactions=30,
            reporting_period="Q3 2024"
        )
        
        # Group by entry_id
        entry_groups = {}
        for entry in gl.entries:
            if entry.entry_id not in entry_groups:
                entry_groups[entry.entry_id] = []
            entry_groups[entry.entry_id].append(entry)
        
        # Each group should be balanced
        for entry_id, entries in entry_groups.items():
            group_debits = sum(e.debit for e in entries)
            group_credits = sum(e.credit for e in entries)
            assert abs(group_debits - group_credits) < 0.01, f"Entry {entry_id} is not balanced"


class TestGLDateRanges:
    """Test GL date generation."""
    
    @pytest.fixture
    def generator(self):
        return GLGenerator()
    
    @pytest.fixture
    def coa_generator(self):
        return COAGenerator()
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("quarter,start,end", [
        ("Q1 2024", "2024-01-01", "2024-03-31"),
        ("Q2 2024", "2024-04-01", "2024-06-30"),
        ("Q3 2024", "2024-07-01", "2024-09-30"),
        ("Q4 2024", "2024-10-01", "2024-12-31"),
    ])
    async def test_quarter_date_ranges(self, generator, coa_generator, sample_company_id, quarter, start, end):
        """Test that quarter date ranges are correct."""
        coa = await coa_generator.generate(
            company_id=sample_company_id,
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL
        )
        
        gl = await generator.generate(
            company_id=sample_company_id,
            coa=coa,
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL,
            num_transactions=30,
            reporting_period=quarter
        )
        
        assert gl.period_start == start
        assert gl.period_end == end
    
    @pytest.mark.asyncio
    async def test_entries_within_period(self, generator, coa_generator, sample_company_id):
        """Test that entry dates are within the reporting period."""
        coa = await coa_generator.generate(
            company_id=sample_company_id,
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL
        )
        
        gl = await generator.generate(
            company_id=sample_company_id,
            coa=coa,
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL,
            num_transactions=50,
            reporting_period="Q2 2024"
        )
        
        period_start = datetime.strptime(gl.period_start, "%Y-%m-%d")
        period_end = datetime.strptime(gl.period_end, "%Y-%m-%d")
        
        for entry in gl.entries:
            entry_date = datetime.strptime(entry.date, "%Y-%m-%d")
            assert period_start <= entry_date <= period_end, f"Entry {entry.entry_id} date {entry.date} outside period"


class TestGLEntriesSorted:
    """Test GL entry sorting."""
    
    @pytest.fixture
    def generator(self):
        return GLGenerator()
    
    @pytest.fixture
    def coa_generator(self):
        return COAGenerator()
    
    @pytest.mark.asyncio
    async def test_entries_sorted_by_date(self, generator, coa_generator, sample_company_id):
        """Test that GL entries are sorted by date."""
        coa = await coa_generator.generate(
            company_id=sample_company_id,
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL
        )
        
        gl = await generator.generate(
            company_id=sample_company_id,
            coa=coa,
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL,
            num_transactions=50,
            reporting_period="Q2 2024"
        )
        
        dates = [e.date for e in gl.entries]
        assert dates == sorted(dates)


class TestGLAccrualEntries:
    """Test accrual-specific entries."""
    
    @pytest.fixture
    def generator(self):
        return GLGenerator()
    
    @pytest.fixture
    def coa_generator(self):
        return COAGenerator()
    
    @pytest.mark.asyncio
    async def test_accrual_basis_has_adjusting_entries(self, generator, coa_generator, sample_company_id):
        """Test that accrual basis includes adjusting entries."""
        coa = await coa_generator.generate(
            company_id=sample_company_id,
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL
        )
        
        gl = await generator.generate(
            company_id=sample_company_id,
            coa=coa,
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL,
            num_transactions=50,
            reporting_period="Q2 2024"
        )
        
        # Should have some ADJ entries (accrued wages, depreciation)
        adj_entries = [e for e in gl.entries if e.entry_id.startswith("ADJ-")]
        assert len(adj_entries) > 0, "Accrual basis should have adjusting entries"


class TestVendorsAndCustomers:
    """Test vendor and customer data."""
    
    def test_vendors_defined(self):
        """Test that vendor categories are defined."""
        assert len(VENDORS) > 0
        for category, vendors in VENDORS.items():
            assert len(vendors) > 0, f"Category {category} has no vendors"
    
    def test_customers_defined(self):
        """Test that customers list is defined."""
        assert len(CUSTOMERS) > 0
