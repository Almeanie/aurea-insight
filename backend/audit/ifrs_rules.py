import asyncio
import uuid
from loguru import logger

from core.schemas import (
    GeneralLedger, TrialBalance, ChartOfAccounts, 
    AccountingBasis, Severity, FindingCategory
)


class IFRSRulesEngine:
    """Checks IFRS (International Financial Reporting Standards) compliance."""
    
    async def check_compliance(
        self,
        gl: GeneralLedger,
        tb: TrialBalance,
        coa: ChartOfAccounts,
        basis: AccountingBasis
    ) -> list[dict]:
        """Run all IFRS compliance checks concurrently."""
        logger.info(f"[check_compliance] Starting IFRS compliance checks for {basis} basis")
        logger.info(f"[check_compliance] GL entries: {len(gl.entries) if gl else 0}, TB rows: {len(tb.rows) if tb else 0}")
        
        findings = []
        
        # Define tasks for common IFRS rules (apply regardless of basis)
        tasks = [
            # IAS 2 - Inventories
            asyncio.to_thread(self._check_lifo_prohibition, gl, tb),
            asyncio.to_thread(self._check_inventory_nrv, gl, tb),
            # IAS 16 - PPE Revaluation
            asyncio.to_thread(self._check_ppe_revaluation, gl, tb),
            # IAS 36 - Impairment
            asyncio.to_thread(self._check_impairment_reversal, gl, tb),
            # IAS 38 - Intangibles / Development Costs
            asyncio.to_thread(self._check_development_capitalization, gl, tb),
            # IAS 37 - Provisions
            asyncio.to_thread(self._check_provisions, gl, tb),
            # IAS 24 - Related Party
            asyncio.to_thread(self._check_related_party, gl),
            # IFRS 16 - Leases
            asyncio.to_thread(self._check_lease_recognition, gl, tb),
            # IAS 12 - Deferred Tax
            asyncio.to_thread(self._check_deferred_tax, gl, tb),
            # IAS 21 - Foreign Currency
            asyncio.to_thread(self._check_foreign_currency, gl),
            # IAS 10 - Subsequent Events
            asyncio.to_thread(self._check_subsequent_events, gl),
            # IAS 8 - Policy Changes
            asyncio.to_thread(self._check_policy_changes, gl),
            # Internal Controls (common)
            asyncio.to_thread(self._check_approval_controls, gl),
            asyncio.to_thread(self._check_expense_classification, gl),
        ]
        
        # Add tasks for basis-specific rules
        if basis == AccountingBasis.ACCRUAL:
            logger.info("[check_compliance] Adding accrual-specific IFRS checks")
            tasks.extend([
                # IFRS 15 - Revenue from Contracts
                asyncio.to_thread(self._check_revenue_recognition_ifrs15, gl),
                # IAS 1 - Accrual basis checks
                asyncio.to_thread(self._check_accrual_basis_presentation, gl, tb),
            ])
        else:
            logger.info("[check_compliance] Adding cash basis-specific checks")
            tasks.append(asyncio.to_thread(self._check_cash_basis_compliance, gl))
            
        # Run all checks in parallel
        results = await asyncio.gather(*tasks)
        
        # Aggregate findings
        for result in results:
            findings.extend(result)
        
        logger.info(f"[check_compliance] Total IFRS findings: {len(findings)}")
        return findings
    
    # =========================================================================
    # IAS 2 - INVENTORIES
    # =========================================================================
    
    def _check_lifo_prohibition(self, gl: GeneralLedger, tb: TrialBalance) -> list[dict]:
        """
        IFRS_002: IAS 2 - LIFO is PROHIBITED under IFRS.
        Detect any LIFO cost flow assumption usage.
        """
        findings = []
        
        # Check for LIFO keywords in inventory/COGS entries
        lifo_keywords = ["lifo", "last-in", "last in first out"]
        
        for entry in gl.entries:
            desc = entry.description.lower()
            # Check inventory (typically 1200-1299) and COGS (5000-5999)
            if entry.account_code.startswith(("12", "50")):
                if any(kw in desc for kw in lifo_keywords):
                    findings.append({
                        "finding_id": f"IFRS-INV-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.STRUCTURAL.value,
                        "severity": Severity.CRITICAL.value,
                        "issue": "LIFO Method Detected - Prohibited Under IFRS",
                        "details": f"Transaction description suggests LIFO inventory costing: '{entry.description}'. LIFO is explicitly prohibited under IAS 2.",
                        "affected_transactions": [entry.entry_id],
                        "transaction_details": [{
                            "entry_id": entry.entry_id,
                            "date": str(entry.date),
                            "account_code": entry.account_code,
                            "account_name": entry.account_name,
                            "description": entry.description,
                            "debit": entry.debit,
                            "credit": entry.credit,
                            "vendor": entry.vendor_or_customer
                        }],
                        "recommendation": "Switch to FIFO or weighted average cost method as required by IAS 2",
                        "confidence": 0.95,
                        "ifrs_standard": "IAS 2 Inventories",
                        "audit_rule": "IFRS_002_LIFO_PROHIBITION",
                        "rule_code": """
# IFRS_002: LIFO Prohibition Check
# Source: IAS 2 Inventories, Paragraph 25
# LIFO (Last-In, First-Out) is PROHIBITED under IFRS
# Allowed methods: FIFO, Weighted Average, Specific Identification

def check_lifo_prohibition(entry):
    LIFO_KEYWORDS = ['lifo', 'last-in', 'last in first out']
    desc_lower = entry.description.lower()
    
    if any(kw in desc_lower for kw in LIFO_KEYWORDS):
        return {
            'flagged': True,
            'severity': 'CRITICAL',
            'reason': 'LIFO method prohibited under IAS 2',
            'remedy': 'Use FIFO or weighted average'
        }
    return {'flagged': False}
"""
                    })
        
        return findings
    
    def _check_inventory_nrv(self, gl: GeneralLedger, tb: TrialBalance) -> list[dict]:
        """
        IFRS_002: IAS 2 - Inventory at lower of cost and NRV.
        Also note: IFRS ALLOWS reversal of write-downs (unlike GAAP).
        """
        findings = []
        
        # Look for inventory write-down or write-up entries
        writedown_keywords = ["write-down", "writedown", "nrv", "impairment", "obsolete"]
        reversal_keywords = ["reversal", "write-up", "recovery"]
        
        for entry in gl.entries:
            desc = entry.description.lower()
            
            if entry.account_code.startswith("12"):  # Inventory accounts
                # Detect write-downs for review
                if any(kw in desc for kw in writedown_keywords):
                    findings.append({
                        "finding_id": f"IFRS-NRV-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.BALANCE.value,
                        "severity": Severity.MEDIUM.value,
                        "issue": "Inventory NRV Adjustment Detected",
                        "details": f"Inventory write-down of ${entry.credit:,.2f} detected. Verify NRV calculation per IAS 2.",
                        "affected_transactions": [entry.entry_id],
                        "transaction_details": [{
                            "entry_id": entry.entry_id,
                            "date": str(entry.date),
                            "account_code": entry.account_code,
                            "account_name": entry.account_name,
                            "description": entry.description,
                            "debit": entry.debit,
                            "credit": entry.credit,
                            "vendor": entry.vendor_or_customer
                        }],
                        "recommendation": "Verify NRV = Estimated selling price - Costs to complete - Costs to sell",
                        "confidence": 0.80,
                        "ifrs_standard": "IAS 2 Inventories",
                        "audit_rule": "IFRS_002_INVENTORY_NRV",
                        "rule_code": """
# IFRS_002: Inventory NRV Check
# Source: IAS 2 Inventories, Paragraphs 28-33
# Inventory must be at lower of cost and NRV
# NRV = Estimated selling price - Costs to complete - Costs to sell
# NOTE: Unlike US GAAP, IFRS ALLOWS reversal of write-downs

def check_inventory_nrv(entry):
    if 'write-down' in entry.description.lower():
        return {
            'flagged': True,
            'reason': 'NRV adjustment requires verification',
            'note': 'IFRS allows reversal if conditions improve'
        }
    return {'flagged': False}
"""
                    })
                
                # Detect reversals (allowed under IFRS, would be prohibited under GAAP)
                if any(kw in desc for kw in reversal_keywords) and entry.debit > 0:
                    findings.append({
                        "finding_id": f"IFRS-NRVR-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.BALANCE.value,
                        "severity": Severity.LOW.value,
                        "issue": "Inventory Write-Down Reversal (Permitted Under IFRS)",
                        "details": f"Inventory write-down reversal of ${entry.debit:,.2f}. This is ALLOWED under IAS 2 but verify conditions.",
                        "affected_transactions": [entry.entry_id],
                        "transaction_details": [{
                            "entry_id": entry.entry_id,
                            "date": str(entry.date),
                            "account_code": entry.account_code,
                            "account_name": entry.account_name,
                            "description": entry.description,
                            "debit": entry.debit,
                            "credit": entry.credit,
                            "vendor": entry.vendor_or_customer
                        }],
                        "recommendation": "Verify reversal is due to increased NRV (e.g., selling price increase) and does not exceed original write-down",
                        "confidence": 0.85,
                        "ifrs_standard": "IAS 2 Inventories",
                        "audit_rule": "IFRS_002_NRV_REVERSAL",
                        "rule_code": """
# IFRS_002: Inventory Write-Down Reversal
# Source: IAS 2 Inventories, Paragraph 33
# Reversal of write-down IS ALLOWED under IFRS (prohibited under US GAAP)
# Reversal limited to amount of original write-down

def check_nrv_reversal(entry):
    if 'reversal' in entry.description.lower() and entry.debit > 0:
        return {
            'flagged': True,
            'note': 'Reversal PERMITTED under IFRS, verify conditions',
            'gaap_difference': 'Would be PROHIBITED under US GAAP'
        }
    return {'flagged': False}
"""
                    })
        
        return findings
    
    # =========================================================================
    # IAS 16 - PROPERTY, PLANT AND EQUIPMENT
    # =========================================================================
    
    def _check_ppe_revaluation(self, gl: GeneralLedger, tb: TrialBalance) -> list[dict]:
        """
        IFRS_003: IAS 16 - Revaluation model is ALLOWED under IFRS (not under GAAP).
        Detect revaluation entries and verify proper treatment.
        """
        findings = []
        
        revaluation_keywords = ["revaluation", "revalue", "fair value adjustment", "appraisal"]
        
        for entry in gl.entries:
            desc = entry.description.lower()
            
            # PPE accounts typically 1500-1599, Revaluation surplus in equity 3xxx
            if entry.account_code.startswith(("15", "16", "17")) or "revaluation" in desc:
                if any(kw in desc for kw in revaluation_keywords):
                    # Determine if upward or downward revaluation
                    direction = "upward" if entry.debit > 0 else "downward"
                    amount = entry.debit if entry.debit > 0 else entry.credit
                    
                    findings.append({
                        "finding_id": f"IFRS-REV-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.BALANCE.value,
                        "severity": Severity.MEDIUM.value,
                        "issue": f"PPE Revaluation Detected ({direction})",
                        "details": f"Property, Plant & Equipment {direction} revaluation of ${amount:,.2f}. Verify per IAS 16 revaluation model requirements.",
                        "affected_transactions": [entry.entry_id],
                        "transaction_details": [{
                            "entry_id": entry.entry_id,
                            "date": str(entry.date),
                            "account_code": entry.account_code,
                            "account_name": entry.account_name,
                            "description": entry.description,
                            "debit": entry.debit,
                            "credit": entry.credit,
                            "vendor": entry.vendor_or_customer
                        }],
                        "recommendation": "Verify: 1) Revaluation applied to entire asset class, 2) Surplus credited to OCI, 3) Depreciation recalculated on revalued amount",
                        "confidence": 0.85,
                        "ifrs_standard": "IAS 16 Property, Plant and Equipment",
                        "audit_rule": "IFRS_003_PPE_REVALUATION",
                        "rule_code": """
# IFRS_003: PPE Revaluation Model
# Source: IAS 16 Property, Plant and Equipment, Paragraphs 31-42
# Revaluation model ALLOWED under IFRS (NOT allowed under US GAAP)
# Requirements:
# 1. Must apply to entire class of assets
# 2. Revaluations must be regular (fair value not materially different)
# 3. Increases go to OCI (revaluation surplus)
# 4. Decreases go to P&L (unless reversing previous increase)

def check_ppe_revaluation(entry):
    if 'revaluation' in entry.description.lower():
        return {
            'flagged': True,
            'note': 'Revaluation PERMITTED under IFRS',
            'verify': ['Entire class revalued', 'OCI treatment correct', 'Depreciation recalculated'],
            'gaap_difference': 'NOT permitted under US GAAP'
        }
    return {'flagged': False}
"""
                    })
        
        return findings
    
    # =========================================================================
    # IAS 36 - IMPAIRMENT OF ASSETS
    # =========================================================================
    
    def _check_impairment_reversal(self, gl: GeneralLedger, tb: TrialBalance) -> list[dict]:
        """
        IFRS_004: IAS 36 - Impairment reversal is ALLOWED under IFRS (except for goodwill).
        GAAP prohibits all impairment reversals.
        """
        findings = []
        
        impairment_keywords = ["impairment", "impaired", "write-down", "recoverable amount"]
        reversal_keywords = ["reversal", "recovery", "write-up", "restore"]
        goodwill_keywords = ["goodwill", "acquisition", "business combination"]
        
        for entry in gl.entries:
            desc = entry.description.lower()
            
            # Check for impairment reversals
            if any(kw in desc for kw in impairment_keywords):
                if any(kw in desc for kw in reversal_keywords):
                    # Check if this is goodwill (reversal prohibited)
                    is_goodwill = any(kw in desc for kw in goodwill_keywords) or entry.account_code.startswith("18")
                    
                    if is_goodwill:
                        findings.append({
                            "finding_id": f"IFRS-IMP-{uuid.uuid4().hex[:8]}",
                            "category": FindingCategory.STRUCTURAL.value,
                            "severity": Severity.CRITICAL.value,
                            "issue": "Goodwill Impairment Reversal - PROHIBITED",
                            "details": f"Goodwill impairment reversal detected. This is PROHIBITED under IAS 36 Paragraph 124.",
                            "affected_transactions": [entry.entry_id],
                            "transaction_details": [{
                                "entry_id": entry.entry_id,
                                "date": str(entry.date),
                                "account_code": entry.account_code,
                                "account_name": entry.account_name,
                                "description": entry.description,
                                "debit": entry.debit,
                                "credit": entry.credit,
                                "vendor": entry.vendor_or_customer
                            }],
                            "recommendation": "Reverse this entry. Goodwill impairment cannot be reversed under IFRS.",
                            "confidence": 0.95,
                            "ifrs_standard": "IAS 36 Impairment of Assets",
                            "audit_rule": "IFRS_004_GOODWILL_IMPAIRMENT_REVERSAL",
                            "rule_code": """
# IFRS_004: Goodwill Impairment Reversal PROHIBITION
# Source: IAS 36 Impairment of Assets, Paragraph 124
# Goodwill impairment CANNOT be reversed
# Other asset impairments CAN be reversed

def check_goodwill_impairment_reversal(entry):
    if 'goodwill' in entry.description.lower() and 'reversal' in entry.description.lower():
        return {
            'flagged': True,
            'severity': 'CRITICAL',
            'reason': 'Goodwill impairment reversal PROHIBITED under IAS 36'
        }
    return {'flagged': False}
"""
                        })
                    else:
                        # Non-goodwill impairment reversal (allowed)
                        findings.append({
                            "finding_id": f"IFRS-IMPR-{uuid.uuid4().hex[:8]}",
                            "category": FindingCategory.BALANCE.value,
                            "severity": Severity.LOW.value,
                            "issue": "Impairment Reversal Detected (Permitted Under IFRS)",
                            "details": f"Asset impairment reversal of ${entry.debit:,.2f}. This is ALLOWED under IAS 36 for non-goodwill assets.",
                            "affected_transactions": [entry.entry_id],
                            "transaction_details": [{
                                "entry_id": entry.entry_id,
                                "date": str(entry.date),
                                "account_code": entry.account_code,
                                "account_name": entry.account_name,
                                "description": entry.description,
                                "debit": entry.debit,
                                "credit": entry.credit,
                                "vendor": entry.vendor_or_customer
                            }],
                            "recommendation": "Verify: 1) Indicators of reversal exist, 2) Recoverable amount recalculated, 3) Reversal limited to original impairment",
                            "confidence": 0.80,
                            "ifrs_standard": "IAS 36 Impairment of Assets",
                            "audit_rule": "IFRS_004_IMPAIRMENT_REVERSAL",
                            "rule_code": """
# IFRS_004: Impairment Reversal (Non-Goodwill)
# Source: IAS 36 Impairment of Assets, Paragraphs 109-123
# Reversal ALLOWED for assets other than goodwill
# Must have indicators that impairment has decreased
# Reversal limited to carrying amount without impairment

def check_impairment_reversal(entry):
    if 'reversal' in entry.description.lower():
        return {
            'flagged': True,
            'note': 'Impairment reversal PERMITTED for non-goodwill assets',
            'gaap_difference': 'ALL impairment reversals PROHIBITED under US GAAP'
        }
    return {'flagged': False}
"""
                        })
        
        return findings
    
    # =========================================================================
    # IAS 38 - INTANGIBLE ASSETS (Development Costs)
    # =========================================================================
    
    def _check_development_capitalization(self, gl: GeneralLedger, tb: TrialBalance) -> list[dict]:
        """
        IFRS_006: IAS 38 - Development costs can be capitalized if 6 criteria met.
        Research costs must always be expensed.
        Under US GAAP, generally all R&D is expensed.
        """
        findings = []
        
        research_keywords = ["research", "r&d", "basic research", "exploratory"]
        development_keywords = ["development", "capitalize", "intangible", "software development"]
        
        for entry in gl.entries:
            desc = entry.description.lower()
            
            # Check for capitalized development costs (intangible assets typically 1800-1899)
            if entry.account_code.startswith("18") and entry.debit > 0:
                if any(kw in desc for kw in development_keywords):
                    findings.append({
                        "finding_id": f"IFRS-DEV-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.CLASSIFICATION.value,
                        "severity": Severity.MEDIUM.value,
                        "issue": "Development Cost Capitalization Detected",
                        "details": f"Development costs of ${entry.debit:,.2f} capitalized. Verify all 6 IAS 38 criteria are met.",
                        "affected_transactions": [entry.entry_id],
                        "transaction_details": [{
                            "entry_id": entry.entry_id,
                            "date": str(entry.date),
                            "account_code": entry.account_code,
                            "account_name": entry.account_name,
                            "description": entry.description,
                            "debit": entry.debit,
                            "credit": entry.credit,
                            "vendor": entry.vendor_or_customer
                        }],
                        "recommendation": "Verify 6 criteria: 1) Technical feasibility, 2) Intention to complete, 3) Ability to use/sell, 4) Future economic benefits, 5) Adequate resources, 6) Reliable measurement",
                        "confidence": 0.85,
                        "ifrs_standard": "IAS 38 Intangible Assets",
                        "audit_rule": "IFRS_006_DEVELOPMENT_CAPITALIZATION",
                        "rule_code": """
# IFRS_006: Development Cost Capitalization
# Source: IAS 38 Intangible Assets, Paragraphs 57-64
# Development costs CAN be capitalized if ALL 6 criteria met:
# 1. Technical feasibility to complete
# 2. Intention to complete and use/sell
# 3. Ability to use or sell
# 4. Asset will generate future economic benefits
# 5. Adequate resources available
# 6. Reliable measurement of costs
#
# Research costs must ALWAYS be expensed
# US GAAP: Generally expenses all R&D (except software dev)

def check_development_capitalization(entry):
    if entry.account_code.startswith('18') and entry.debit > 0:
        return {
            'flagged': True,
            'verify': 'All 6 IAS 38 criteria must be met',
            'gaap_difference': 'US GAAP generally expenses all R&D'
        }
    return {'flagged': False}
"""
                    })
            
            # Check for research costs that might be incorrectly capitalized
            if entry.account_code.startswith("18") and entry.debit > 0:
                if any(kw in desc for kw in research_keywords) and "development" not in desc:
                    findings.append({
                        "finding_id": f"IFRS-RES-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.CLASSIFICATION.value,
                        "severity": Severity.HIGH.value,
                        "issue": "Research Costs Incorrectly Capitalized",
                        "details": f"Research costs of ${entry.debit:,.2f} appear to be capitalized. Research costs must be EXPENSED under IAS 38.",
                        "affected_transactions": [entry.entry_id],
                        "transaction_details": [{
                            "entry_id": entry.entry_id,
                            "date": str(entry.date),
                            "account_code": entry.account_code,
                            "account_name": entry.account_name,
                            "description": entry.description,
                            "debit": entry.debit,
                            "credit": entry.credit,
                            "vendor": entry.vendor_or_customer
                        }],
                        "recommendation": "Reclassify to R&D expense. Research costs cannot be capitalized under IAS 38.",
                        "confidence": 0.90,
                        "ifrs_standard": "IAS 38 Intangible Assets",
                        "audit_rule": "IFRS_006_RESEARCH_EXPENSE",
                        "rule_code": """
# IFRS_006: Research Costs Must Be Expensed
# Source: IAS 38 Intangible Assets, Paragraph 54
# Research costs must ALWAYS be expensed as incurred
# Cannot be capitalized even if future benefits expected

def check_research_expense(entry):
    if 'research' in entry.description.lower() and entry.account_code.startswith('18'):
        return {
            'flagged': True,
            'severity': 'HIGH',
            'reason': 'Research costs must be expensed under IAS 38'
        }
    return {'flagged': False}
"""
                    })
        
        return findings
    
    # =========================================================================
    # IAS 37 - PROVISIONS, CONTINGENT LIABILITIES
    # =========================================================================
    
    def _check_provisions(self, gl: GeneralLedger, tb: TrialBalance) -> list[dict]:
        """
        IFRS_005: IAS 37 - Provisions require 3 criteria.
        """
        findings = []
        
        provision_keywords = ["provision", "contingent", "warranty", "legal", "restructuring", "onerous"]
        
        for entry in gl.entries:
            desc = entry.description.lower()
            
            # Provision accounts typically 2400-2499
            if entry.account_code.startswith("24") or any(kw in desc for kw in provision_keywords):
                if entry.credit > 10000:  # Significant provisions
                    findings.append({
                        "finding_id": f"IFRS-PRV-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.BALANCE.value,
                        "severity": Severity.MEDIUM.value,
                        "issue": "Provision Recorded - Verify IAS 37 Criteria",
                        "details": f"Provision of ${entry.credit:,.2f} recorded for '{entry.description}'. Verify all 3 IAS 37 recognition criteria.",
                        "affected_transactions": [entry.entry_id],
                        "transaction_details": [{
                            "entry_id": entry.entry_id,
                            "date": str(entry.date),
                            "account_code": entry.account_code,
                            "account_name": entry.account_name,
                            "description": entry.description,
                            "debit": entry.debit,
                            "credit": entry.credit,
                            "vendor": entry.vendor_or_customer
                        }],
                        "recommendation": "Verify: 1) Present obligation from past event, 2) Probable outflow (>50%), 3) Reliable estimate possible",
                        "confidence": 0.75,
                        "ifrs_standard": "IAS 37 Provisions, Contingent Liabilities and Contingent Assets",
                        "audit_rule": "IFRS_005_PROVISIONS",
                        "rule_code": """
# IFRS_005: Provision Recognition Criteria
# Source: IAS 37, Paragraphs 14-26
# Recognition requires ALL 3 criteria:
# 1. Present obligation (legal or constructive) from past event
# 2. Probable outflow of resources (>50% likelihood)
# 3. Reliable estimate can be made
#
# If criteria not met, may be contingent liability (disclosure only)

def check_provision_criteria(entry):
    if entry.account_code.startswith('24') and entry.credit > 10000:
        return {
            'flagged': True,
            'verify': ['Present obligation', 'Probable outflow >50%', 'Reliable estimate']
        }
    return {'flagged': False}
"""
                    })
        
        return findings
    
    # =========================================================================
    # IFRS 16 - LEASES
    # =========================================================================
    
    def _check_lease_recognition(self, gl: GeneralLedger, tb: TrialBalance) -> list[dict]:
        """
        IFRS_007: IFRS 16 - Single lessee model. ALL leases on balance sheet.
        """
        findings = []
        
        lease_keywords = ["lease", "rent", "rental", "operating lease", "right-of-use", "rou"]
        
        # Check for operating lease expense that should be on balance sheet
        for entry in gl.entries:
            desc = entry.description.lower()
            
            if any(kw in desc for kw in lease_keywords):
                # Check if it's going to expense (possible off-balance-sheet treatment)
                if entry.account_code.startswith("65"):  # Rent expense
                    if entry.debit > 5000:  # Significant lease
                        findings.append({
                            "finding_id": f"IFRS-LSE-{uuid.uuid4().hex[:8]}",
                            "category": FindingCategory.CLASSIFICATION.value,
                            "severity": Severity.HIGH.value,
                            "issue": "Potential Off-Balance-Sheet Lease",
                            "details": f"Rent/lease expense of ${entry.debit:,.2f} recorded. Under IFRS 16, most leases must be on balance sheet with ROU asset and lease liability.",
                            "affected_transactions": [entry.entry_id],
                            "transaction_details": [{
                                "entry_id": entry.entry_id,
                                "date": str(entry.date),
                                "account_code": entry.account_code,
                                "account_name": entry.account_name,
                                "description": entry.description,
                                "debit": entry.debit,
                                "credit": entry.credit,
                                "vendor": entry.vendor_or_customer
                            }],
                            "recommendation": "Verify if lease qualifies for short-term (<12 months) or low-value exemption. Otherwise, recognize ROU asset and lease liability.",
                            "confidence": 0.80,
                            "ifrs_standard": "IFRS 16 Leases",
                            "audit_rule": "IFRS_007_LEASE_RECOGNITION",
                            "rule_code": """
# IFRS_007: Lease Recognition
# Source: IFRS 16 Leases
# Single lessee model - ALL leases on balance sheet (with exemptions)
# Recognize: Right-of-use asset + Lease liability
# Exemptions: Short-term (<12 months) and Low-value assets only
#
# US GAAP ASC 842: Still has operating/finance distinction for lessees

def check_lease_recognition(entry):
    if 'rent' in entry.description.lower() and entry.debit > 5000:
        return {
            'flagged': True,
            'reason': 'Potential off-balance-sheet lease',
            'verify': 'Check for ROU asset and lease liability',
            'exemptions': ['Short-term <12 months', 'Low-value assets']
        }
    return {'flagged': False}
"""
                        })
        
        return findings
    
    # =========================================================================
    # IAS 12 - INCOME TAXES
    # =========================================================================
    
    def _check_deferred_tax(self, gl: GeneralLedger, tb: TrialBalance) -> list[dict]:
        """
        IFRS_008: IAS 12 - Deferred tax recognition and measurement.
        """
        findings = []
        
        # Check deferred tax accounts in trial balance
        for row in tb.rows:
            if "deferred tax" in row.account_name.lower():
                if row.ending_balance > 50000:  # Significant balance
                    findings.append({
                        "finding_id": f"IFRS-TAX-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.BALANCE.value,
                        "severity": Severity.MEDIUM.value,
                        "issue": "Significant Deferred Tax Balance",
                        "details": f"Deferred tax balance of ${row.ending_balance:,.2f} in {row.account_name}. Review temporary differences and recoverability.",
                        "affected_accounts": [row.account_code],
                        "account_details": {
                            "account_code": row.account_code,
                            "account_name": row.account_name,
                            "beginning_balance": row.beginning_balance,
                            "ending_balance": row.ending_balance
                        },
                        "recommendation": "Verify: 1) All temporary differences identified, 2) DTA recoverability assessed, 3) Correct tax rates used",
                        "confidence": 0.75,
                        "ifrs_standard": "IAS 12 Income Taxes",
                        "audit_rule": "IFRS_008_DEFERRED_TAX",
                        "rule_code": """
# IFRS_008: Deferred Tax Recognition
# Source: IAS 12 Income Taxes
# Recognize deferred tax for all temporary differences
# DTA only if probable future taxable profit
# Use enacted or substantively enacted tax rates

def check_deferred_tax(tb_row):
    if 'deferred tax' in tb_row.account_name.lower():
        return {
            'flagged': True,
            'verify': ['Temporary differences', 'DTA recoverability', 'Tax rates']
        }
    return {'flagged': False}
"""
                    })
        
        return findings
    
    # =========================================================================
    # IAS 24 - RELATED PARTY DISCLOSURES
    # =========================================================================
    
    def _check_related_party(self, gl: GeneralLedger) -> list[dict]:
        """
        IFRS_010: IAS 24 - Related party transaction detection.
        """
        findings = []
        
        related_party_keywords = ["related party", "affiliate", "subsidiary", "parent company", 
                                   "director", "officer", "shareholder", "key management"]
        
        for entry in gl.entries:
            desc = entry.description.lower()
            vendor = (entry.vendor_or_customer or "").lower()
            
            if any(kw in desc or kw in vendor for kw in related_party_keywords):
                amount = max(entry.debit, entry.credit)
                if amount > 1000:
                    findings.append({
                        "finding_id": f"IFRS-RPT-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.FRAUD.value,
                        "severity": Severity.HIGH.value,
                        "issue": "Related Party Transaction Detected",
                        "details": f"Potential related party transaction of ${amount:,.2f} with {entry.vendor_or_customer or 'Unknown'}. Requires disclosure per IAS 24.",
                        "affected_transactions": [entry.entry_id],
                        "transaction_details": [{
                            "entry_id": entry.entry_id,
                            "date": str(entry.date),
                            "account_code": entry.account_code,
                            "account_name": entry.account_name,
                            "description": entry.description,
                            "debit": entry.debit,
                            "credit": entry.credit,
                            "vendor": entry.vendor_or_customer
                        }],
                        "recommendation": "Verify: 1) Arm's length pricing, 2) Proper disclosure in notes, 3) Board approval if required",
                        "confidence": 0.85,
                        "ifrs_standard": "IAS 24 Related Party Disclosures",
                        "audit_rule": "IFRS_010_RELATED_PARTY",
                        "rule_code": """
# IFRS_010: Related Party Transactions
# Source: IAS 24 Related Party Disclosures
# Must disclose: Nature of relationship, transaction amounts, outstanding balances
# Key management compensation also requires disclosure

def check_related_party(entry):
    RELATED_KEYWORDS = ['related party', 'affiliate', 'subsidiary', 'director']
    if any(kw in entry.description.lower() for kw in RELATED_KEYWORDS):
        return {
            'flagged': True,
            'verify': ['Arm\'s length pricing', 'Disclosure', 'Approval']
        }
    return {'flagged': False}
"""
                    })
        
        return findings
    
    # =========================================================================
    # IAS 21 - FOREIGN CURRENCY
    # =========================================================================
    
    def _check_foreign_currency(self, gl: GeneralLedger) -> list[dict]:
        """
        IFRS_012: IAS 21 - Foreign currency transactions.
        """
        findings = []
        
        fx_keywords = ["fx", "foreign exchange", "currency", "translation", "forex", 
                       "eur", "gbp", "jpy", "cad", "aud", "unrealized"]
        
        for entry in gl.entries:
            desc = entry.description.lower()
            
            if any(kw in desc for kw in fx_keywords):
                amount = max(entry.debit, entry.credit)
                if amount > 1000:
                    findings.append({
                        "finding_id": f"IFRS-FX-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.BALANCE.value,
                        "severity": Severity.LOW.value,
                        "issue": "Foreign Currency Transaction",
                        "details": f"Foreign currency transaction of ${amount:,.2f}. Verify exchange rate and translation per IAS 21.",
                        "affected_transactions": [entry.entry_id],
                        "transaction_details": [{
                            "entry_id": entry.entry_id,
                            "date": str(entry.date),
                            "account_code": entry.account_code,
                            "account_name": entry.account_name,
                            "description": entry.description,
                            "debit": entry.debit,
                            "credit": entry.credit,
                            "vendor": entry.vendor_or_customer
                        }],
                        "recommendation": "Verify: 1) Correct exchange rate used, 2) Monetary items at closing rate, 3) FX gains/losses in P&L",
                        "confidence": 0.70,
                        "ifrs_standard": "IAS 21 The Effects of Changes in Foreign Exchange Rates",
                        "audit_rule": "IFRS_012_FOREIGN_CURRENCY",
                        "rule_code": """
# IFRS_012: Foreign Currency Transactions
# Source: IAS 21 Effects of Changes in Foreign Exchange Rates
# Initial recognition: Spot rate at transaction date
# Subsequent: Monetary items at closing rate, non-monetary at historical
# Exchange differences in P&L (except specific OCI items)

def check_foreign_currency(entry):
    FX_KEYWORDS = ['fx', 'foreign exchange', 'currency', 'translation']
    if any(kw in entry.description.lower() for kw in FX_KEYWORDS):
        return {
            'flagged': True,
            'verify': ['Exchange rate', 'Classification', 'P&L/OCI treatment']
        }
    return {'flagged': False}
"""
                    })
        
        return findings
    
    # =========================================================================
    # IAS 10 - EVENTS AFTER REPORTING PERIOD
    # =========================================================================
    
    def _check_subsequent_events(self, gl: GeneralLedger) -> list[dict]:
        """
        IFRS_013: IAS 10 - Subsequent events (adjusting vs non-adjusting).
        """
        findings = []
        
        period_end = gl.period_end
        subsequent_keywords = ["subsequent", "post-period", "post-closing", "adjustment", "after year-end"]
        
        for entry in gl.entries:
            desc = entry.description.lower()
            
            if any(kw in desc for kw in subsequent_keywords):
                amount = max(entry.debit, entry.credit)
                findings.append({
                    "finding_id": f"IFRS-SUB-{uuid.uuid4().hex[:8]}",
                    "category": FindingCategory.TIMING.value,
                    "severity": Severity.MEDIUM.value,
                    "issue": "Potential Subsequent Event Adjustment",
                    "details": f"Entry of ${amount:,.2f} references post-period events. Classify as adjusting or non-adjusting per IAS 10.",
                    "affected_transactions": [entry.entry_id],
                    "transaction_details": [{
                        "entry_id": entry.entry_id,
                        "date": str(entry.date),
                        "account_code": entry.account_code,
                        "account_name": entry.account_name,
                        "description": entry.description,
                        "debit": entry.debit,
                        "credit": entry.credit,
                        "vendor": entry.vendor_or_customer
                    }],
                    "recommendation": "Determine if adjusting (conditions existed at period end) or non-adjusting (conditions arose after - disclose only)",
                    "confidence": 0.75,
                    "ifrs_standard": "IAS 10 Events After the Reporting Period",
                    "audit_rule": "IFRS_013_SUBSEQUENT_EVENTS",
                    "rule_code": """
# IFRS_013: Events After Reporting Period
# Source: IAS 10
# Adjusting events: Conditions existed at period end - ADJUST statements
# Non-adjusting events: Conditions arose after - DISCLOSE only
# Going concern issues always require adjustment

def check_subsequent_events(entry, period_end):
    if 'subsequent' in entry.description.lower():
        return {
            'flagged': True,
            'classify': ['Adjusting - conditions existed at period end',
                        'Non-adjusting - disclose only']
        }
    return {'flagged': False}
"""
                })
        
        return findings
    
    # =========================================================================
    # IAS 8 - ACCOUNTING POLICIES, CHANGES, ERRORS
    # =========================================================================
    
    def _check_policy_changes(self, gl: GeneralLedger) -> list[dict]:
        """
        IFRS_014: IAS 8 - Accounting policy changes and error corrections.
        """
        findings = []
        
        policy_keywords = ["policy change", "restatement", "prior period", "correction", 
                           "retrospective", "error", "reclassification"]
        
        for entry in gl.entries:
            desc = entry.description.lower()
            
            if any(kw in desc for kw in policy_keywords):
                amount = max(entry.debit, entry.credit)
                findings.append({
                    "finding_id": f"IFRS-POL-{uuid.uuid4().hex[:8]}",
                    "category": FindingCategory.STRUCTURAL.value,
                    "severity": Severity.HIGH.value,
                    "issue": "Accounting Policy Change or Error Correction",
                    "details": f"Entry of ${amount:,.2f} suggests policy change or error correction. Apply retrospectively per IAS 8.",
                    "affected_transactions": [entry.entry_id],
                    "transaction_details": [{
                        "entry_id": entry.entry_id,
                        "date": str(entry.date),
                        "account_code": entry.account_code,
                        "account_name": entry.account_name,
                        "description": entry.description,
                        "debit": entry.debit,
                        "credit": entry.credit,
                        "vendor": entry.vendor_or_customer
                    }],
                    "recommendation": "Verify: 1) Retrospective application, 2) Comparative periods restated, 3) Required disclosures made",
                    "confidence": 0.80,
                    "ifrs_standard": "IAS 8 Accounting Policies, Changes in Accounting Estimates and Errors",
                    "audit_rule": "IFRS_014_POLICY_CHANGES",
                    "rule_code": """
# IFRS_014: Accounting Policy Changes and Errors
# Source: IAS 8
# Policy changes: Apply retrospectively, restate comparatives
# Errors: Correct retrospectively
# Estimates: Apply prospectively (no restatement)

def check_policy_changes(entry):
    POLICY_KEYWORDS = ['policy change', 'restatement', 'prior period', 'error']
    if any(kw in entry.description.lower() for kw in POLICY_KEYWORDS):
        return {
            'flagged': True,
            'verify': ['Retrospective application', 'Comparatives restated', 'Disclosures']
        }
    return {'flagged': False}
"""
                })
        
        return findings
    
    # =========================================================================
    # IFRS 15 - REVENUE FROM CONTRACTS WITH CUSTOMERS
    # =========================================================================
    
    def _check_revenue_recognition_ifrs15(self, gl: GeneralLedger) -> list[dict]:
        """
        IFRS_001: IFRS 15 - Revenue recognition 5-step model.
        """
        findings = []
        
        period_end = gl.period_end
        
        for entry in gl.entries:
            # Revenue accounts typically 4000-4999
            if entry.account_code.startswith("4") and entry.credit > 0:
                # Check for large period-end revenue (timing risk)
                if entry.date == period_end and entry.credit > 10000:
                    findings.append({
                        "finding_id": f"IFRS-REV-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.TIMING.value,
                        "severity": Severity.MEDIUM.value,
                        "issue": "Large Period-End Revenue - IFRS 15 Review",
                        "details": f"Revenue of ${entry.credit:,.2f} recorded on period end. Verify performance obligation satisfied per IFRS 15.",
                        "affected_transactions": [entry.entry_id],
                        "transaction_details": [{
                            "entry_id": entry.entry_id,
                            "date": str(entry.date),
                            "account_code": entry.account_code,
                            "account_name": entry.account_name,
                            "description": entry.description,
                            "debit": entry.debit,
                            "credit": entry.credit,
                            "vendor": entry.vendor_or_customer
                        }],
                        "recommendation": "Apply IFRS 15 5-step model: 1) Identify contract, 2) Identify obligations, 3) Determine price, 4) Allocate price, 5) Recognize when satisfied",
                        "confidence": 0.75,
                        "ifrs_standard": "IFRS 15 Revenue from Contracts with Customers",
                        "audit_rule": "IFRS_001_REVENUE_RECOGNITION",
                        "rule_code": """
# IFRS_001: Revenue Recognition (IFRS 15 5-Step Model)
# Source: IFRS 15 Revenue from Contracts with Customers
# 5-Step Model:
# 1. Identify contract with customer
# 2. Identify performance obligations
# 3. Determine transaction price
# 4. Allocate price to obligations
# 5. Recognize revenue when obligation satisfied

def check_revenue_ifrs15(entry, period_end):
    if entry.account_code.startswith('4') and entry.credit > 10000:
        if entry.date == period_end:
            return {
                'flagged': True,
                'reason': 'Large period-end revenue',
                'apply': 'IFRS 15 5-step model'
            }
    return {'flagged': False}
"""
                    })
        
        return findings
    
    # =========================================================================
    # IAS 1 - PRESENTATION OF FINANCIAL STATEMENTS
    # =========================================================================
    
    def _check_accrual_basis_presentation(self, gl: GeneralLedger, tb: TrialBalance) -> list[dict]:
        """
        IFRS_011: IAS 1 - Accrual basis and presentation requirements.
        """
        findings = []
        
        # Check for proper accrual entries
        accrual_accounts = [row for row in tb.rows 
                           if any(x in row.account_name.lower() for x in ["accrued", "prepaid", "receivable", "payable"])]
        
        if not accrual_accounts:
            findings.append({
                "finding_id": f"IFRS-IAS1-{uuid.uuid4().hex[:8]}",
                "category": FindingCategory.STRUCTURAL.value,
                "severity": Severity.MEDIUM.value,
                "issue": "Limited Accrual Accounts Detected",
                "details": "Few or no accrual-type accounts found. Verify accrual basis is properly applied per IAS 1.",
                "affected_accounts": [],
                "recommendation": "Ensure accrued expenses, prepaid assets, and receivables/payables are properly recorded",
                "confidence": 0.65,
                "ifrs_standard": "IAS 1 Presentation of Financial Statements",
                "audit_rule": "IFRS_011_ACCRUAL_BASIS",
                "rule_code": """
# IFRS_011: Accrual Basis Requirement
# Source: IAS 1 Presentation of Financial Statements
# All entities must use accrual basis (except cash flow statement)
# Recognize items when definition and criteria met, not when cash moves

def check_accrual_basis(tb_rows):
    ACCRUAL_KEYWORDS = ['accrued', 'prepaid', 'receivable', 'payable']
    accrual_accounts = [r for r in tb_rows 
                        if any(kw in r.account_name.lower() for kw in ACCRUAL_KEYWORDS)]
    if len(accrual_accounts) < 2:
        return {
            'flagged': True,
            'reason': 'Limited accrual accounts may indicate cash basis'
        }
    return {'flagged': False}
"""
            })
        
        return findings
    
    # =========================================================================
    # COMMON RULES (Similar to GAAP but with IFRS references)
    # =========================================================================
    
    def _check_approval_controls(self, gl: GeneralLedger) -> list[dict]:
        """Check for transactions over threshold without approval (internal controls)."""
        findings = []
        threshold = 5000.0
        
        for entry in gl.entries:
            if entry.debit > threshold:
                findings.append({
                    "finding_id": f"IFRS-APR-{uuid.uuid4().hex[:8]}",
                    "category": FindingCategory.DOCUMENTATION.value,
                    "severity": Severity.HIGH.value,
                    "issue": "High-Value Transaction Requires Review",
                    "details": f"Transaction of ${entry.debit:,.2f} to {entry.vendor_or_customer or 'Unknown'} exceeds review threshold",
                    "affected_transactions": [entry.entry_id],
                    "transaction_details": [{
                        "entry_id": entry.entry_id,
                        "date": str(entry.date),
                        "account_code": entry.account_code,
                        "account_name": entry.account_name,
                        "description": entry.description,
                        "debit": entry.debit,
                        "credit": entry.credit,
                        "vendor": entry.vendor_or_customer
                    }],
                    "recommendation": "Verify proper approval documentation exists",
                    "confidence": 0.85,
                    "ifrs_standard": "Internal Controls (ISA 315)",
                    "audit_rule": "IFRS_COMMON_APPROVAL_THRESHOLD",
                    "rule_code": """
# IFRS_COMMON: Approval Threshold Check
# Source: ISA 315 Internal Controls
# Transactions over threshold require documented approval

def check_approval_threshold(entry):
    THRESHOLD = 5000.0
    if entry.debit > THRESHOLD:
        return {'flagged': True, 'amount': entry.debit}
    return {'flagged': False}
"""
                })
        
        return findings
    
    def _check_expense_classification(self, gl: GeneralLedger) -> list[dict]:
        """Check for potential expense misclassifications."""
        findings = []
        
        travel_keywords = ["flight", "hotel", "airline", "uber", "lyft", "rental car", "airbnb"]
        
        for entry in gl.entries:
            desc = entry.description.lower()
            
            if any(kw in desc for kw in travel_keywords):
                if not entry.account_code.startswith("66"):
                    findings.append({
                        "finding_id": f"IFRS-CLS-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.CLASSIFICATION.value,
                        "severity": Severity.MEDIUM.value,
                        "issue": "Potential Expense Misclassification",
                        "details": f"Transaction appears to be travel-related but coded to {entry.account_name}",
                        "affected_transactions": [entry.entry_id],
                        "transaction_details": [{
                            "entry_id": entry.entry_id,
                            "date": str(entry.date),
                            "account_code": entry.account_code,
                            "account_name": entry.account_name,
                            "description": entry.description,
                            "debit": entry.debit,
                            "credit": entry.credit,
                            "vendor": entry.vendor_or_customer
                        }],
                        "recommendation": "Verify classification; may need to reclassify to Travel Expense",
                        "confidence": 0.75,
                        "ifrs_standard": "IAS 1 Presentation (Expense Classification)",
                        "audit_rule": "IFRS_COMMON_EXPENSE_CLASSIFICATION",
                        "rule_code": """
# IFRS_COMMON: Expense Classification Check
# Source: IAS 1 Presentation of Financial Statements
# Expenses should be classified by nature or function consistently

def check_expense_classification(entry):
    TRAVEL_KEYWORDS = ['flight', 'hotel', 'airline', 'uber', 'lyft']
    if any(kw in entry.description.lower() for kw in TRAVEL_KEYWORDS):
        if not entry.account_code.startswith('66'):
            return {'flagged': True, 'current_account': entry.account_code}
    return {'flagged': False}
"""
                    })
        
        return findings
    
    def _check_cash_basis_compliance(self, gl: GeneralLedger) -> list[dict]:
        """Check cash basis compliance (if used)."""
        findings = []
        
        for entry in gl.entries:
            if entry.account_code in ["1100", "2000"]:
                findings.append({
                    "finding_id": f"IFRS-CSH-{uuid.uuid4().hex[:8]}",
                    "category": FindingCategory.STRUCTURAL.value,
                    "severity": Severity.HIGH.value,
                    "issue": "Accrual Entry Under Cash Basis",
                    "details": f"Entry to {entry.account_name} recorded under cash basis. Note: IFRS requires accrual basis per IAS 1.",
                    "affected_transactions": [entry.entry_id],
                    "transaction_details": [{
                        "entry_id": entry.entry_id,
                        "date": str(entry.date),
                        "account_code": entry.account_code,
                        "account_name": entry.account_name,
                        "description": entry.description,
                        "debit": entry.debit,
                        "credit": entry.credit,
                        "vendor": entry.vendor_or_customer
                    }],
                    "recommendation": "IFRS requires accrual basis accounting per IAS 1. Consider transitioning to accrual basis.",
                    "confidence": 0.90,
                    "ifrs_standard": "IAS 1 Presentation of Financial Statements",
                    "audit_rule": "IFRS_COMMON_CASH_BASIS",
                    "rule_code": """
# IFRS_COMMON: Cash Basis Warning
# Source: IAS 1 Presentation of Financial Statements
# IFRS REQUIRES accrual basis accounting
# Cash basis only permitted for cash flow statement

def check_cash_basis(entry, accounting_basis):
    if accounting_basis == 'cash':
        return {
            'flagged': True,
            'warning': 'IFRS requires accrual basis per IAS 1'
        }
    return {'flagged': False}
"""
                })
        
        return findings
