"""
Synthetic Company Generator
Creates complete, internally consistent company data.
"""
from typing import Optional
import uuid
import random
from datetime import datetime
from loguru import logger

from core.schemas import (
    CompanyMetadata, Industry, AccountingBasis,
    ChartOfAccounts, GeneralLedger, TrialBalance
)
from core.gemini_client import GeminiClient
from .coa_generator import COAGenerator
from .gl_generator import GLGenerator
from .tb_generator import TBGenerator
from .issue_injector import IssueInjector


# Company name components for generation
COMPANY_PREFIXES = [
    "Apex", "Nova", "Stellar", "Quantum", "Pinnacle", "Velocity", "Summit",
    "Horizon", "Catalyst", "Nexus", "Vertex", "Zenith", "Prime", "Atlas"
]

COMPANY_SUFFIXES = {
    Industry.SAAS: ["Software", "Tech", "Systems", "Cloud", "Digital", "Labs"],
    Industry.AGENCY: ["Creative", "Media", "Studios", "Group", "Partners", "Agency"],
    Industry.RETAIL: ["Goods", "Supply", "Trading", "Retail", "Commerce", "Mart"],
    Industry.MANUFACTURING: ["Manufacturing", "Industries", "Products", "Works", "Fabrication"],
    Industry.CONSULTING: ["Consulting", "Advisors", "Solutions", "Services", "Partners"],
    Industry.ECOMMERCE: ["Online", "Direct", "Digital", "Commerce", "Market", "Shop"],
}


class CompanyGenerator:
    """Generates complete synthetic companies."""
    
    def __init__(self):
        logger.info("[CompanyGenerator.__init__] Initializing company generator")
        self.gemini = GeminiClient()
        self.coa_generator = COAGenerator()
        self.gl_generator = GLGenerator()
        self.tb_generator = TBGenerator()
        self.issue_injector = IssueInjector()
        logger.info("[CompanyGenerator.__init__] All sub-generators initialized")
    
    async def generate(
        self,
        industry: Optional[Industry] = None,
        accounting_basis: Optional[AccountingBasis] = None,
        num_transactions: int = 50,
        issue_count: int = 8
    ) -> dict:
        """
        Generate a complete synthetic company.
        
        Returns dict with:
        - metadata: CompanyMetadata
        - coa: ChartOfAccounts
        - gl: GeneralLedger
        - tb: TrialBalance
        - injected_issues: list of planted issues (hidden from user)
        """
        logger.info("[generate] Starting synthetic company generation")
        
        # Random selections if not provided
        if industry is None:
            industry = random.choice(list(Industry))
            logger.info(f"[generate] Randomly selected industry: {industry}")
        if accounting_basis is None:
            accounting_basis = random.choice([AccountingBasis.CASH, AccountingBasis.ACCRUAL])
            logger.info(f"[generate] Randomly selected accounting basis: {accounting_basis}")
        
        # Generate company ID and name
        company_id = str(uuid.uuid4())
        company_name = self._generate_company_name(industry)
        logger.info(f"[generate] Generated company: id={company_id}, name={company_name}")
        
        # Generate reporting period
        current_year = datetime.now().year
        quarter = random.choice(["Q1", "Q2", "Q3", "Q4"])
        reporting_period = f"{quarter} {current_year}"
        logger.info(f"[generate] Reporting period: {reporting_period}")
        
        # Create metadata
        logger.info("[generate] Creating company metadata")
        metadata = CompanyMetadata(
            id=company_id,
            name=company_name,
            industry=industry,
            accounting_basis=accounting_basis,
            reporting_period=reporting_period,
            is_synthetic=True
        )
        
        # Generate Chart of Accounts
        logger.info("[generate] Generating Chart of Accounts")
        coa = await self.coa_generator.generate(
            company_id=company_id,
            industry=industry,
            accounting_basis=accounting_basis
        )
        logger.info(f"[generate] Generated {len(coa.accounts)} accounts in COA")
        
        # Generate General Ledger
        logger.info(f"[generate] Generating General Ledger with {num_transactions} transactions")
        gl = await self.gl_generator.generate(
            company_id=company_id,
            coa=coa,
            industry=industry,
            accounting_basis=accounting_basis,
            num_transactions=num_transactions,
            reporting_period=reporting_period
        )
        logger.info(f"[generate] Generated {len(gl.entries)} GL entries")
        
        # Inject issues into GL
        logger.info(f"[generate] Injecting {issue_count} issues into GL")
        gl, injected_issues = await self.issue_injector.inject(
            gl=gl,
            coa=coa,
            issue_count=issue_count,
            accounting_basis=accounting_basis
        )
        logger.info(f"[generate] Injected {len(injected_issues)} issues")
        for issue in injected_issues:
            logger.debug(f"[generate] Injected issue: {issue.get('type')} - {issue.get('description')}")
        
        # Derive Trial Balance from GL
        logger.info("[generate] Deriving Trial Balance from GL")
        tb = self.tb_generator.derive_from_gl(
            company_id=company_id,
            gl=gl,
            coa=coa,
            reporting_period=reporting_period
        )
        logger.info(f"[generate] Generated TB with {len(tb.rows)} rows, balanced={tb.is_balanced}")
        logger.info(f"[generate] TB totals: debits={tb.total_debits}, credits={tb.total_credits}")
        
        logger.info("[generate] Company generation complete")
        
        return {
            "metadata": metadata,
            "coa": coa,
            "gl": gl,
            "tb": tb,
            "injected_issues": injected_issues  # Hidden - for testing only
        }
    
    def _generate_company_name(self, industry: Industry) -> str:
        """Generate a plausible company name."""
        logger.debug(f"[_generate_company_name] Generating name for industry: {industry}")
        
        prefix = random.choice(COMPANY_PREFIXES)
        suffix = random.choice(COMPANY_SUFFIXES.get(industry, ["Inc"]))
        
        # Sometimes add a location or descriptor
        if random.random() > 0.7:
            descriptors = ["Global", "International", "American", "Pacific", "National"]
            prefix = f"{random.choice(descriptors)} {prefix}"
        
        name = f"{prefix} {suffix}"
        logger.debug(f"[_generate_company_name] Generated name: {name}")
        return name
