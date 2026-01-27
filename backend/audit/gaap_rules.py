import asyncio
import uuid
from loguru import logger

from core.schemas import (
    GeneralLedger, TrialBalance, ChartOfAccounts, 
    AccountingBasis, Severity, FindingCategory
)


class GAAPRulesEngine:
    """Checks GAAP compliance."""
    
    async def check_compliance(
        self,
        gl: GeneralLedger,
        tb: TrialBalance,
        coa: ChartOfAccounts,
        basis: AccountingBasis
    ) -> list[dict]:
        """Run all GAAP compliance checks concurrently."""
        logger.info(f"[check_compliance] Starting GAAP compliance checks for {basis} basis")
        logger.info(f"[check_compliance] GL entries: {len(gl.entries) if gl else 0}, TB rows: {len(tb.rows) if tb else 0}")
        
        findings = []
        
        # Define tasks for common rules
        tasks = [
            asyncio.to_thread(self._check_approval_controls, gl),
            asyncio.to_thread(self._check_expense_classification, gl),
            asyncio.to_thread(self._check_documentation, gl)
        ]
        
        # Add tasks for basis-specific rules
        if basis == AccountingBasis.ACCRUAL:
            logger.info("[check_compliance] Adding accrual-specific checks")
            tasks.extend([
                asyncio.to_thread(self._check_revenue_recognition, gl),
                asyncio.to_thread(self._check_matching_principle, gl, tb),
                asyncio.to_thread(self._check_accruals, gl, tb)
            ])
        else:
            logger.info("[check_compliance] Adding cash basis-specific checks")
            tasks.append(asyncio.to_thread(self._check_cash_basis_compliance, gl))
            
        # Run all checks in parallel
        results = await asyncio.gather(*tasks)
        
        # Aggregate findings
        for result in results:
            findings.extend(result)
        
        logger.info(f"[check_compliance] Total GAAP findings: {len(findings)}")
        return findings
    
    def _check_approval_controls(self, gl: GeneralLedger) -> list[dict]:
        """Check for transactions over threshold without approval."""
        findings = []
        threshold = 500.0
        
        for entry in gl.entries:
            if entry.debit > threshold:
                # In a real system, we'd check approval metadata
                # For simulation, flag high-value transactions
                if entry.debit > 5000:
                    findings.append({
                        "finding_id": f"APR-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.DOCUMENTATION.value,
                        "severity": Severity.HIGH.value,
                        "issue": "High-Value Transaction Requires Review",
                        "details": f"Transaction of ${entry.debit:,.2f} to {entry.vendor_or_customer or 'Unknown'} exceeds review threshold",
                        "affected_transactions": [entry.entry_id],
                        "transaction_details": [{
                            "entry_id": entry.entry_id,
                            "date": entry.date,
                            "account_code": entry.account_code,
                            "account_name": entry.account_name,
                            "description": entry.description,
                            "debit": entry.debit,
                            "credit": entry.credit,
                            "vendor": entry.vendor_or_customer
                        }],
                        "recommendation": "Verify proper approval documentation exists",
                        "confidence": 0.85,
                        "gaap_principle": "Internal Controls (COSO Framework)",
                        "audit_rule": "RULE_001_APPROVAL_THRESHOLD",
                        "rule_code": """
# RULE_001: Approval Threshold Check
# Source: COSO Internal Control Framework
# Threshold: Transactions > $5,000 require documented approval

def check_approval_threshold(entry):
    THRESHOLD = 5000.0
    if entry.debit > THRESHOLD:
        return {
            'flagged': True,
            'reason': 'Transaction exceeds approval threshold',
            'amount': entry.debit,
            'threshold': THRESHOLD
        }
    return {'flagged': False}
"""
                    })
        
        return findings
    
    def _check_expense_classification(self, gl: GeneralLedger) -> list[dict]:
        """Check for potential expense misclassifications."""
        findings = []
        
        # Keywords that suggest misclassification
        travel_keywords = ["flight", "hotel", "airline", "uber", "lyft", "rental car", "airbnb"]
        office_keywords = ["staples", "office depot", "amazon", "paper", "supplies"]
        
        for entry in gl.entries:
            desc = entry.description.lower()
            
            # Check if travel expense is coded elsewhere
            if any(kw in desc for kw in travel_keywords):
                if not entry.account_code.startswith("66"):  # Not in Travel (6600)
                    findings.append({
                        "finding_id": f"CLS-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.CLASSIFICATION.value,
                        "severity": Severity.MEDIUM.value,
                        "issue": "Potential Expense Misclassification",
                        "details": f"Transaction appears to be travel-related but coded to {entry.account_name}",
                        "affected_transactions": [entry.entry_id],
                        "transaction_details": [{
                            "entry_id": entry.entry_id,
                            "date": entry.date,
                            "account_code": entry.account_code,
                            "account_name": entry.account_name,
                            "description": entry.description,
                            "debit": entry.debit,
                            "credit": entry.credit,
                            "vendor": entry.vendor_or_customer
                        }],
                        "recommendation": f"Verify classification; may need to reclassify to Travel Expense",
                        "confidence": 0.75,
                        "gaap_principle": "Proper Expense Classification",
                        "audit_rule": "RULE_002_EXPENSE_CLASSIFICATION",
                        "rule_code": """
# RULE_002: Expense Classification Check  
# Source: GAAP Expense Classification Standards
# Keywords: travel, hotel, flight, airline, uber, lyft

def check_expense_classification(entry):
    TRAVEL_KEYWORDS = ['flight', 'hotel', 'airline', 'uber', 'lyft', 'rental car']
    desc_lower = entry.description.lower()
    
    if any(kw in desc_lower for kw in TRAVEL_KEYWORDS):
        if not entry.account_code.startswith('66'):  # Travel account
            return {
                'flagged': True,
                'reason': 'Travel-related expense in wrong account',
                'current_account': entry.account_code,
                'suggested_account': '6600'
            }
    return {'flagged': False}
"""
                    })
        
        return findings
    
    def _check_documentation(self, gl: GeneralLedger) -> list[dict]:
        """Check for documentation issues."""
        findings = []
        
        # Check for transactions over $75 that might need receipts (IRS requirement)
        for entry in gl.entries:
            if entry.debit > 75 and entry.account_code.startswith("66"):  # Travel/Meals
                # In real system, check if receipt exists
                pass
        
        return findings
    
    def _check_revenue_recognition(self, gl: GeneralLedger) -> list[dict]:
        """Check revenue recognition timing (ASC 606)."""
        findings = []
        
        # Look for large revenue entries at period end (potential manipulation)
        period_end = gl.period_end
        
        for entry in gl.entries:
            if entry.account_code.startswith("4") and entry.credit > 0:
                if entry.date == period_end and entry.credit > 10000:
                    findings.append({
                        "finding_id": f"REV-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.TIMING.value,
                        "severity": Severity.MEDIUM.value,
                        "issue": "Large Period-End Revenue Entry",
                        "details": f"Revenue of ${entry.credit:,.2f} recorded on period end date. Verify timing is appropriate.",
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
                        "recommendation": "Confirm delivery occurred and revenue recognition criteria met per ASC 606",
                        "confidence": 0.70,
                        "gaap_principle": "ASC 606 Revenue Recognition",
                        "audit_rule": "RULE_003_REVENUE_TIMING",
                        "rule_code": """
# RULE_003: Revenue Timing Check (ASC 606)
# Source: ASC 606 Revenue Recognition
# Flags: Large revenue entries on period-end date

def check_revenue_timing(entry, period_end):
    if entry.account_code.startswith('4') and entry.credit > 0:
        if entry.date == period_end and entry.credit > 10000:
            return {
                'flagged': True,
                'reason': 'Large revenue on period end',
                'amount': entry.credit,
                'date': entry.date
            }
    return {'flagged': False}
"""
                    })
        
        return findings
    
    def _check_matching_principle(self, gl: GeneralLedger, tb: TrialBalance) -> list[dict]:
        """Check matching principle compliance."""
        findings = []
        
        # Check for prepaid expenses without amortization
        prepaid_accounts = [row for row in tb.rows if "prepaid" in row.account_name.lower()]
        
        for prepaid in prepaid_accounts:
            if prepaid.ending_balance > 0:
                # Check if there are any amortization entries
                amort_entries = [
                    e for e in gl.entries 
                    if e.account_code == prepaid.account_code and e.credit > 0
                ]
                
                if not amort_entries:
                    findings.append({
                        "finding_id": f"MAT-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.TIMING.value,
                        "severity": Severity.MEDIUM.value,
                        "issue": "Prepaid Expense Not Amortized",
                        "details": f"{prepaid.account_name} has balance of ${prepaid.ending_balance:,.2f} with no amortization entries",
                        "affected_accounts": [prepaid.account_code],
                        "account_details": {
                            "account_code": prepaid.account_code,
                            "account_name": prepaid.account_name,
                            "beginning_balance": prepaid.beginning_balance,
                            "ending_balance": prepaid.ending_balance
                        },
                        "recommendation": "Record appropriate amortization to recognize expense in proper period",
                        "confidence": 0.80,
                        "gaap_principle": "Matching Principle",
                        "audit_rule": "RULE_004_PREPAID_AMORTIZATION",
                        "rule_code": """
# RULE_004: Prepaid Expense Amortization Check
# Source: GAAP Matching Principle
# Flags: Prepaid accounts with no amortization entries

def check_prepaid_amortization(prepaid_account, gl_entries):
    if prepaid_account.ending_balance > 0:
        # Look for credit entries (amortization)
        amort_entries = [e for e in gl_entries 
                        if e.account_code == prepaid_account.account_code 
                        and e.credit > 0]
        if not amort_entries:
            return {
                'flagged': True,
                'reason': 'No amortization entries found',
                'balance': prepaid_account.ending_balance
            }
    return {'flagged': False}
"""
                    })
        
        return findings
    
    def _check_accruals(self, gl: GeneralLedger, tb: TrialBalance) -> list[dict]:
        """Check for missing accruals."""
        findings = []
        
        # This would check for missing accruals based on known recurring expenses
        # Simplified for demo
        
        return findings
    
    def _check_cash_basis_compliance(self, gl: GeneralLedger) -> list[dict]:
        """Check cash basis compliance."""
        findings = []
        
        # Under cash basis, should not have AR/AP entries
        for entry in gl.entries:
            if entry.account_code in ["1100", "2000"]:  # AR or AP
                findings.append({
                    "finding_id": f"CSH-{uuid.uuid4().hex[:8]}",
                    "category": FindingCategory.STRUCTURAL.value,
                    "severity": Severity.HIGH.value,
                    "issue": "Accrual Entry Under Cash Basis",
                    "details": f"Entry to {entry.account_name} recorded under cash basis accounting",
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
                    "recommendation": "Remove accrual entries or switch to accrual basis",
                    "confidence": 0.90,
                    "gaap_principle": "Cash Basis Accounting",
                    "audit_rule": "RULE_005_CASH_BASIS_COMPLIANCE",
                    "rule_code": """
# RULE_005: Cash Basis Compliance Check
# Source: Cash Basis Accounting Standards
# Flags: AR/AP entries when company uses cash basis

def check_cash_basis_compliance(entry, accounting_basis):
    ACCRUAL_ACCOUNTS = ['1100', '2000']  # AR, AP
    if accounting_basis == 'cash':
        if entry.account_code in ACCRUAL_ACCOUNTS:
            return {
                'flagged': True,
                'reason': 'Accrual account used under cash basis',
                'account': entry.account_code
            }
    return {'flagged': False}
"""
                })
        
        return findings
