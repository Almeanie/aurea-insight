"""
Pydantic Schemas for Aurea Insight
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


# ============================================
# Enums
# ============================================

class AccountingBasis(str, Enum):
    CASH = "cash"
    ACCRUAL = "accrual"


class Industry(str, Enum):
    SAAS = "saas"
    AGENCY = "agency"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    CONSULTING = "consulting"
    ECOMMERCE = "ecommerce"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FindingCategory(str, Enum):
    STRUCTURAL = "structural"
    TIMING = "timing"
    CLASSIFICATION = "classification"
    DOCUMENTATION = "documentation"
    BALANCE = "balance"
    FRAUD = "fraud"


# ============================================
# Company Schemas
# ============================================

class CompanyMetadata(BaseModel):
    """Company metadata for a synthetic or real company."""
    id: str
    name: str
    industry: Industry
    jurisdiction: str = "US-based"
    accounting_basis: AccountingBasis
    reporting_period: str  # e.g., "Q2 2024"
    currency: str = "USD"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_synthetic: bool = True


class CompanyGenerateRequest(BaseModel):
    """Request to generate a synthetic company."""
    industry: Optional[Industry] = None
    accounting_basis: Optional[AccountingBasis] = None
    num_transactions: int = Field(default=50, ge=30, le=100)
    issue_count: int = Field(default=8, ge=5, le=15)


class CompanyUploadRequest(BaseModel):
    """Request to upload real company data."""
    company_name: str
    industry: Industry
    accounting_basis: AccountingBasis
    reporting_period: str


# ============================================
# Chart of Accounts Schemas
# ============================================

class Account(BaseModel):
    """A single account in the Chart of Accounts."""
    code: str  # e.g., "1000"
    name: str  # e.g., "Cash"
    type: Literal["asset", "liability", "equity", "revenue", "expense"]
    subtype: Optional[str] = None  # e.g., "current_asset", "operating_expense"
    normal_balance: Literal["debit", "credit"]
    description: Optional[str] = None


class ChartOfAccounts(BaseModel):
    """Complete Chart of Accounts."""
    company_id: str
    accounts: list[Account]
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# General Ledger Schemas
# ============================================

class JournalEntry(BaseModel):
    """A single journal entry in the General Ledger."""
    entry_id: str
    date: str  # YYYY-MM-DD
    account_code: str
    account_name: str
    debit: float = 0
    credit: float = 0
    description: str
    vendor_or_customer: Optional[str] = None
    reference: Optional[str] = None  # e.g., invoice number
    created_by: str = "system"


class GeneralLedger(BaseModel):
    """Complete General Ledger."""
    company_id: str
    entries: list[JournalEntry]
    period_start: str
    period_end: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# Trial Balance Schemas
# ============================================

class TrialBalanceRow(BaseModel):
    """A single row in the Trial Balance."""
    account_code: str
    account_name: str
    debit: float = 0
    credit: float = 0
    ending_balance: float = 0


class TrialBalance(BaseModel):
    """Complete Trial Balance (derived from GL)."""
    company_id: str
    period_end: str
    rows: list[TrialBalanceRow]
    total_debits: float
    total_credits: float
    is_balanced: bool
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# Audit Finding Schemas
# ============================================

class AuditFinding(BaseModel):
    """A single audit finding."""
    finding_id: str
    category: str  # Using str to allow dynamic categories
    severity: str  # Using str to allow dynamic severities
    issue: str
    details: str
    affected_transactions: list[str] = []  # Entry IDs
    affected_accounts: list[str] = []  # Account codes
    gaap_principle: Optional[str] = None
    recommendation: str
    confidence: float = Field(default=0.8, ge=0, le=1)  # AI confidence score
    evidence: list[str] = []  # Supporting evidence
    
    # AI Reasoning fields
    ai_explanation: Optional[str] = None  # AI-generated explanation of the finding
    ai_risk_analysis: Optional[str] = None  # AI analysis of business risk
    ai_remediation_steps: Optional[list[str]] = None  # AI-suggested steps to fix
    detection_method: Optional[str] = None  # How this was detected (rule, AI, statistical)
    
    class Config:
        extra = "allow"  # Allow additional fields from the audit engine


class AuditFindingsResponse(BaseModel):
    """Response containing all audit findings."""
    audit_id: str
    company_id: str
    findings: list[AuditFinding]
    total_count: int
    by_severity: dict[str, int]
    by_category: dict[str, int]


# ============================================
# AJE (Adjusting Journal Entry) Schemas
# ============================================

class AJEEntry(BaseModel):
    """A single line in an AJE."""
    account_code: str
    account_name: str
    debit: float = 0
    credit: float = 0


class AdjustingJournalEntry(BaseModel):
    """A complete Adjusting Journal Entry."""
    aje_id: str
    date: str
    entries: list[AJEEntry]
    total_debits: float
    total_credits: float
    description: str
    finding_reference: str  # The finding ID this corrects
    is_balanced: bool
    
    # AI Reasoning fields
    ai_explanation: Optional[str] = None  # AI explanation of why this entry is needed
    ai_basis: Optional[str] = None  # GAAP/regulatory basis for the adjustment
    ai_impact: Optional[str] = None  # Expected impact of this adjustment
    
    class Config:
        extra = "allow"  # Allow additional fields


class AJEResponse(BaseModel):
    """Response containing all AJEs."""
    audit_id: str
    company_id: str
    ajes: list[AdjustingJournalEntry]
    total_count: int


# ============================================
# Risk Score Schemas
# ============================================

class RiskScore(BaseModel):
    """Overall risk assessment."""
    audit_id: str
    company_id: str
    overall_score: float = Field(ge=0, le=100)
    risk_level: Literal["low", "medium", "high", "critical"]
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    category_breakdown: dict[str, float]
    requires_immediate_action: bool
    interpretation: str


# ============================================
# Ownership Schemas
# ============================================

class EntityNode(BaseModel):
    """A node in the ownership graph."""
    id: str
    name: str
    type: Literal["company", "individual", "unknown", "boilerplate"]
    jurisdiction: Optional[str] = None
    status: Optional[str] = None
    registration_date: Optional[str] = None
    address: Optional[str] = None
    red_flags: list[str] = []
    api_source: Optional[str] = None  # Where this data came from
    is_mock: bool = False  # True if demo/mock data
    is_boilerplate: bool = False  # True if detected as template/placeholder name


class OwnershipEdge(BaseModel):
    """An edge in the ownership graph."""
    source: str
    target: str
    relationship: str  # "owns", "directs", "same_address", etc.
    percentage: Optional[float] = None
    relationship_type: Optional[str] = None  # "direct_parent", "ultimate_parent", etc.


class OwnershipGraph(BaseModel):
    """Complete ownership graph."""
    nodes: list[EntityNode]
    edges: list[OwnershipEdge]
    statistics: dict


class DataSourceSummary(BaseModel):
    """Summary of data sources used in discovery."""
    sources_used: list[str]  # e.g., ["opencorporates", "sec_edgar", "mock_demo"]
    entities_by_source: dict[str, int]
    total_from_real_apis: int
    total_mock: int


class OwnershipDiscoveryRequest(BaseModel):
    """Request to discover ownership network."""
    seed_entities: list[str]  # Company/vendor names to start from
    depth: int = Field(default=2, ge=1, le=3)


class OwnershipDiscoveryResponse(BaseModel):
    """Response from ownership discovery."""
    graph_id: str
    entities_discovered: int
    node_count: int
    edge_count: int
    findings_count: int
    data_sources: DataSourceSummary
    real_data_percentage: float  # % of data from real APIs vs mock


# ============================================
# Chat Schemas
# ============================================

class ChatMessage(BaseModel):
    """A single chat message."""
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """Request to the auditor chatbot."""
    message: str
    audit_id: Optional[str] = None
    company_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from the auditor chatbot."""
    message: str
    citations: list[str] = []  # References to findings, transactions, etc.
    confidence: float = Field(ge=0, le=1)


# ============================================
# Export Schemas
# ============================================

class ExportRequest(BaseModel):
    """Request to export data."""
    format: Literal["pdf", "csv", "json"]
    include_findings: bool = True
    include_ajes: bool = True
    include_audit_trail: bool = False
