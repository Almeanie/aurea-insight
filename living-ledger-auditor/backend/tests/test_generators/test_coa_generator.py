"""Tests for Chart of Accounts generator."""
import pytest

from generators.coa_generator import COAGenerator
from core.schemas import Industry, AccountingBasis


class TestCOAGenerator:
    """Tests for COA generation."""
    
    @pytest.fixture
    def generator(self):
        return COAGenerator()
    
    @pytest.mark.asyncio
    async def test_generate_coa_saas(self, generator):
        """Test generating COA for SaaS company."""
        coa = await generator.generate(
            company_id="test-123",
            industry=Industry.SAAS,
            accounting_basis=AccountingBasis.ACCRUAL
        )
        
        assert coa.company_id == "test-123"
        assert len(coa.accounts) > 30  # Should have many accounts
        
        # Check for required accounts
        codes = [a.code for a in coa.accounts]
        assert "1000" in codes  # Cash
        assert "1100" in codes  # AR (accrual)
        assert "4000" in codes  # Revenue
    
    @pytest.mark.asyncio
    async def test_generate_coa_cash_basis(self, generator):
        """Test COA for cash basis excludes accrual accounts."""
        coa = await generator.generate(
            company_id="test-123",
            industry=Industry.CONSULTING,
            accounting_basis=AccountingBasis.CASH
        )
        
        codes = [a.code for a in coa.accounts]
        
        # Cash basis should not have AR/AP
        assert "1100" not in codes  # No AR
        assert "2200" not in codes  # No Deferred Revenue
