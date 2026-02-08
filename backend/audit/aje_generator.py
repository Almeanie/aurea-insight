"""
AJE Generator
Generates Adjusting Journal Entries for audit findings.
"""
import uuid
from loguru import logger

from core.gemini_client import GeminiClient
from core.audit_trail import AuditRecord
from core.schemas import ChartOfAccounts, FindingCategory, AccountingStandard


class AJEGenerator:
    """Generates Adjusting Journal Entries."""
    
    def __init__(self):
        logger.info("[AJEGenerator.__init__] Initializing AJE generator")
        self.gemini = GeminiClient()
        self.quota_exceeded = False
        self.accounting_standard = AccountingStandard.GAAP
    
    async def generate_ajes(
        self,
        findings: list[dict],
        coa: ChartOfAccounts,
        audit_record: AuditRecord,
        accounting_standard: AccountingStandard = AccountingStandard.GAAP,
        on_aje_callback=None,
    ) -> list[dict]:
        """Generate AJEs for findings that can be corrected.
        
        Args:
            on_aje_callback: Optional callable invoked with each AJE dict as
                             soon as it is generated, so callers can stream it
                             to clients immediately.
        """
        logger.info(f"[generate_ajes] Processing {len(findings)} findings for AJE generation using {accounting_standard.value.upper()}")
        
        # Store accounting standard for use in generation methods
        self.accounting_standard = accounting_standard
        
        ajes = []
        
        # Only generate AJEs for certain categories
        correctable_categories = [
            FindingCategory.CLASSIFICATION.value,
            FindingCategory.TIMING.value,
            FindingCategory.STRUCTURAL.value,
            FindingCategory.FRAUD.value,
        ]
        
        correctable = [f for f in findings if f.get("category") in correctable_categories]
        logger.info(f"[generate_ajes] Found {len(correctable)} correctable findings")
        
        for i, finding in enumerate(correctable):
            if self.quota_exceeded:
                logger.warning("[generate_ajes] Skipping remaining AJEs due to quota exhaustion")
                audit_record.add_reasoning_step("Skipping remaining AJE generation - Gemini quota exceeded")
                break
                
            logger.debug(f"[generate_ajes] Generating AJE {i+1}/{len(correctable)} for finding: {finding.get('finding_id')}")
            aje = await self._generate_aje_for_finding(finding, coa, audit_record)
            if aje:
                ajes.append(aje)
                logger.info(f"[generate_ajes] Generated AJE {aje['aje_id']} for finding {finding.get('finding_id')}")
                # Stream this AJE to the client immediately
                if on_aje_callback:
                    on_aje_callback(aje)
        
        # If no AJEs generated due to quota, use deterministic fallback
        if len(ajes) == 0 and len(correctable) > 0:
            logger.info("[generate_ajes] Using deterministic AJE generation fallback")
            audit_record.add_reasoning_step(f"Using deterministic {accounting_standard.value.upper()} AJE rules (AI unavailable)")
            ajes = self._generate_deterministic_ajes(correctable, coa)
            # Stream deterministic AJEs too
            if on_aje_callback:
                for aje in ajes:
                    on_aje_callback(aje)
            logger.info(f"[generate_ajes] Generated {len(ajes)} deterministic AJEs")
        
        logger.info(f"[generate_ajes] Successfully generated {len(ajes)} total AJEs")
        return ajes
    
    def _generate_deterministic_ajes(
        self,
        findings: list[dict],
        coa: ChartOfAccounts
    ) -> list[dict]:
        """Generate AJEs using deterministic rules without AI."""
        logger.info(f"[_generate_deterministic_ajes] Processing {len(findings)} findings with {self.accounting_standard.value.upper()} rules")
        
        ajes = []
        
        # Build account lookup
        accounts = {a.code: a for a in coa.accounts}
        
        for finding in findings:
            aje = self._apply_aje_rule(finding, accounts)
            if aje:
                ajes.append(aje)
        
        return ajes
    
    def _apply_aje_rule(self, finding: dict, accounts: dict) -> dict | None:
        """Apply deterministic rules to generate an AJE based on GAAP or IFRS."""
        category = finding.get("category", "")
        issue = finding.get("issue", "").lower()
        details = finding.get("details", "")
        affected_transactions = finding.get("affected_transactions", [])
        transaction_details = finding.get("transaction_details", [])
        
        # Determine if IFRS or GAAP
        is_ifrs = self.accounting_standard == AccountingStandard.IFRS
        standard_prefix = "IFRS" if is_ifrs else "GAAP"
        
        # Extract amount from details if present (look for $ amounts)
        import re
        amount_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', details)
        amount = float(amount_match.group(1).replace(',', '')) if amount_match else 1000.00
        
        # Common AJE fields
        base_aje = {
            "aje_id": f"AJE-DET-{uuid.uuid4().hex[:6]}",
            "date": "Period End",
            "accounting_standard": self.accounting_standard.value,
            "affected_transactions": affected_transactions,
            "transaction_details": transaction_details,
        }
        
        # Rule 1: Expense Misclassification
        if "misclass" in issue or "classification" in category.lower():
            rationale = ("IAS 1 requires proper expense classification for fair presentation" if is_ifrs 
                        else "GAAP requires proper expense classification for accurate financial reporting")
            return {
                **base_aje,
                "entries": [
                    {"account_code": "6900", "account_name": "Miscellaneous Expense", "debit": 0, "credit": amount},
                    {"account_code": "6200", "account_name": "Marketing Expense", "debit": amount, "credit": 0}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Reclassify expense per {standard_prefix} audit finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": rationale,
                "rule_applied": f"RULE_EXPENSE_RECLASSIFICATION_{standard_prefix}",
                "standard_reference": "IAS 1 - Presentation of Financial Statements" if is_ifrs else "ASC 220 - Income Statement",
                "is_balanced": True
            }
        
        # Rule 2: Revenue Recognition Timing
        if "revenue" in issue and ("timing" in issue or "recognition" in issue):
            rationale = ("IFRS 15 requires revenue recognition when performance obligations are satisfied" if is_ifrs
                        else "ASC 606 requires revenue recognition only when performance obligations are satisfied")
            return {
                **base_aje,
                "entries": [
                    {"account_code": "4000", "account_name": "Service Revenue", "debit": amount, "credit": 0},
                    {"account_code": "2200", "account_name": "Deferred Revenue", "debit": 0, "credit": amount}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Defer unearned revenue per {standard_prefix} finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": rationale,
                "rule_applied": f"RULE_REVENUE_DEFERRAL_{standard_prefix}",
                "standard_reference": "IFRS 15 - Revenue from Contracts with Customers" if is_ifrs else "ASC 606 - Revenue Recognition",
                "is_balanced": True
            }
        
        # Rule 3: Accrual Missing
        if "accrual" in issue or "accrue" in issue:
            rationale = ("IAS 1 accrual basis requires expenses to be recorded when incurred" if is_ifrs
                        else "Matching principle requires expenses to be recorded in the period incurred")
            return {
                **base_aje,
                "entries": [
                    {"account_code": "6000", "account_name": "Operating Expense", "debit": amount, "credit": 0},
                    {"account_code": "2100", "account_name": "Accrued Expenses", "debit": 0, "credit": amount}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Accrue unrecorded expense per {standard_prefix} finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": rationale,
                "rule_applied": f"RULE_EXPENSE_ACCRUAL_{standard_prefix}",
                "standard_reference": "IAS 1.27-28 - Accrual Basis" if is_ifrs else "ASC 450 - Contingencies",
                "is_balanced": True
            }
        
        # Rule 4: Prepaid Expense Amortization
        if "prepaid" in issue or "amortiz" in issue:
            rationale = ("IFRS Framework requires systematic allocation of prepaid expenses" if is_ifrs
                        else "Prepaid expenses must be amortized over the benefit period per GAAP")
            return {
                **base_aje,
                "entries": [
                    {"account_code": "6000", "account_name": "Operating Expense", "debit": amount, "credit": 0},
                    {"account_code": "1200", "account_name": "Prepaid Expenses", "debit": 0, "credit": amount}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Amortize prepaid expense per {standard_prefix} finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": rationale,
                "rule_applied": f"RULE_PREPAID_AMORTIZATION_{standard_prefix}",
                "standard_reference": "IAS 1 - Presentation of Financial Statements" if is_ifrs else "ASC 340 - Other Assets and Deferred Costs",
                "is_balanced": True
            }
        
        # Rule 5: Depreciation
        if "deprec" in issue:
            rationale = ("IAS 16 requires systematic depreciation over the asset's useful life" if is_ifrs
                        else "Fixed assets must be depreciated over their useful life per GAAP")
            return {
                **base_aje,
                "entries": [
                    {"account_code": "6700", "account_name": "Depreciation Expense", "debit": amount, "credit": 0},
                    {"account_code": "1600", "account_name": "Accumulated Depreciation", "debit": 0, "credit": amount}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Record depreciation per {standard_prefix} finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": rationale,
                "rule_applied": f"RULE_DEPRECIATION_{standard_prefix}",
                "standard_reference": "IAS 16 - Property, Plant and Equipment" if is_ifrs else "ASC 360 - Property, Plant, and Equipment",
                "is_balanced": True
            }
        
        # Rule 6: Lease Accounting (IFRS 16 / ASC 842)
        if "lease" in issue:
            rationale = ("IFRS 16 requires recognition of right-of-use asset and lease liability" if is_ifrs
                        else "ASC 842 requires recognition of right-of-use asset and lease liability")
            return {
                **base_aje,
                "entries": [
                    {"account_code": "1700", "account_name": "Right-of-Use Asset", "debit": amount, "credit": 0},
                    {"account_code": "2300", "account_name": "Lease Liability", "debit": 0, "credit": amount}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Recognize lease per {standard_prefix} finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": rationale,
                "rule_applied": f"RULE_LEASE_RECOGNITION_{standard_prefix}",
                "standard_reference": "IFRS 16 - Leases" if is_ifrs else "ASC 842 - Leases",
                "is_balanced": True
            }
        
        # Rule 7: Impairment
        if "impair" in issue:
            rationale = ("IAS 36 requires impairment when carrying amount exceeds recoverable amount" if is_ifrs
                        else "ASC 360 requires impairment testing when triggering events occur")
            return {
                **base_aje,
                "entries": [
                    {"account_code": "6800", "account_name": "Impairment Loss", "debit": amount, "credit": 0},
                    {"account_code": "1600", "account_name": "Accumulated Impairment", "debit": 0, "credit": amount}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Record impairment per {standard_prefix} finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": rationale,
                "rule_applied": f"RULE_IMPAIRMENT_{standard_prefix}",
                "standard_reference": "IAS 36 - Impairment of Assets" if is_ifrs else "ASC 360-10 - Impairment",
                "is_balanced": True
            }
        
        # Rule 8: Fraud - Duplicate/Suspicious Payments (provision for loss)
        if category == "fraud" and ("duplicate" in issue or "structuring" in issue or "suspicious" in issue):
            rationale = ("Provision for probable loss from suspected fraudulent transactions per IAS 37" if is_ifrs
                        else "Provision for probable loss from suspected fraudulent transactions per ASC 450")
            return {
                **base_aje,
                "entries": [
                    {"account_code": "6850", "account_name": "Fraud Loss Expense", "debit": amount, "credit": 0},
                    {"account_code": "2150", "account_name": "Provision for Fraud Losses", "debit": 0, "credit": amount}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Provision for suspected fraud per {standard_prefix} finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": rationale,
                "rule_applied": f"RULE_FRAUD_PROVISION_{standard_prefix}",
                "standard_reference": "IAS 37 - Provisions, Contingent Liabilities" if is_ifrs else "ASC 450 - Contingencies",
                "is_balanced": True
            }
        
        # Rule 9: Fraud - Round-tripping / Vendor anomalies (reclassify revenue)
        if category == "fraud" and ("round-trip" in issue or "vendor" in issue or "round number" in issue):
            rationale = ("Reclassify potentially fictitious revenue per IAS 18 / IFRS 15" if is_ifrs
                        else "Reclassify potentially fictitious revenue per ASC 606")
            return {
                **base_aje,
                "entries": [
                    {"account_code": "4000", "account_name": "Revenue", "debit": amount, "credit": 0},
                    {"account_code": "2200", "account_name": "Deferred Revenue / Suspense", "debit": 0, "credit": amount}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Reclassify suspect revenue per {standard_prefix} finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": rationale,
                "rule_applied": f"RULE_FRAUD_REVENUE_RECLASSIFICATION_{standard_prefix}",
                "standard_reference": "IFRS 15 - Revenue from Contracts with Customers" if is_ifrs else "ASC 606 - Revenue Recognition",
                "is_balanced": True
            }
        
        # Rule 10: Fraud - Generic (Benford's, timing, weekend, shared address)
        if category == "fraud":
            rationale = (f"Segregate flagged transactions pending investigation per {standard_prefix} audit procedures" if is_ifrs
                        else f"Segregate flagged transactions pending investigation per {standard_prefix} audit procedures")
            return {
                **base_aje,
                "entries": [
                    {"account_code": "1950", "account_name": "Suspense - Under Investigation", "debit": amount, "credit": 0},
                    {"account_code": "6900", "account_name": "Miscellaneous Expense", "debit": 0, "credit": amount}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Reclassify to suspense pending fraud investigation per {standard_prefix} finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": rationale,
                "rule_applied": f"RULE_FRAUD_SUSPENSE_{standard_prefix}",
                "standard_reference": "ISA 240 - Auditor's Responsibilities Relating to Fraud" if is_ifrs else "AU-C 240 - Consideration of Fraud",
                "is_balanced": True
            }
        
        # Default: Generic reclassification
        if category in ["classification", "structural", "timing"]:
            rationale = (f"Correction required per {standard_prefix} audit finding" if is_ifrs
                        else "Correction required per audit finding")
            return {
                **base_aje,
                "entries": [
                    {"account_code": "6900", "account_name": "Miscellaneous Expense", "debit": 0, "credit": amount},
                    {"account_code": "6000", "account_name": "Operating Expense", "debit": amount, "credit": 0}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Correcting entry per {standard_prefix} finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": rationale,
                "rule_applied": f"RULE_GENERIC_CORRECTION_{standard_prefix}",
                "standard_reference": "IAS 8 - Accounting Policies, Changes in Accounting Estimates and Errors" if is_ifrs else "ASC 250 - Accounting Changes and Error Corrections",
                "is_balanced": True
            }
        
        return None
    
    async def _generate_aje_for_finding(
        self,
        finding: dict,
        coa: ChartOfAccounts,
        audit_record: AuditRecord
    ) -> dict | None:
        """Generate a single AJE for a finding."""
        logger.debug(f"[_generate_aje_for_finding] Generating AJE for: {finding.get('issue')} using {self.accounting_standard.value.upper()}")
        
        try:
            # Build COA summary for prompt
            coa_summary = "\n".join([
                f"{a.code}: {a.name} ({a.type}, {a.normal_balance})"
                for a in coa.accounts[:30]  # Limit for prompt size
            ])
            
            # Determine standard-specific context
            is_ifrs = self.accounting_standard == AccountingStandard.IFRS
            standard_name = "IFRS" if is_ifrs else "US GAAP"
            standard_principle = finding.get('ifrs_standard') if is_ifrs else finding.get('gaap_principle')
            
            prompt = f"""
Generate an Adjusting Journal Entry to correct this audit finding under {standard_name}:

ACCOUNTING STANDARD: {standard_name}

FINDING:
Issue: {finding.get('issue')}
Details: {finding.get('details')}
Category: {finding.get('category')}
{standard_name} Reference: {standard_principle or 'N/A'}

CHART OF ACCOUNTS:
{coa_summary}

Generate a balanced journal entry with proper debits and credits following {standard_name} principles.
For fraud findings, consider: provision for losses (ASC 450/IAS 37), reclassification to suspense accounts, or reversal of fictitious entries.
Return ONLY valid JSON in this format:
{{
    "description": "Brief description of the adjustment",
    "entries": [
        {{"account_code": "XXXX", "account_name": "Account Name", "debit": 0.00, "credit": 0.00}}
    ],
    "rationale": "Why this entry corrects the issue under {standard_name}",
    "standard_reference": "The specific {standard_name} standard (e.g., {'IFRS 15, IAS 16' if is_ifrs else 'ASC 606, ASC 842'})"
}}

CRITICAL: Debits must equal credits. Use realistic amounts based on the finding.
Ensure the rationale references the appropriate {standard_name} standard.
"""
            
            result = await self.gemini.generate_json(
                prompt=prompt,
                purpose="aje_generation"
            )
            
            # Check for quota exceeded
            if result.get("quota_exceeded"):
                logger.error("=" * 60)
                logger.error("[AJE GENERATION] GEMINI QUOTA EXCEEDED!")
                logger.error("Cannot generate AJEs - API limit reached")
                logger.error("=" * 60)
                self.quota_exceeded = True
                audit_record.add_reasoning_step("AJE generation skipped - Gemini API quota exceeded")
                return None
            
            if result.get("audit"):
                audit_record.add_gemini_interaction(result["audit"])
            
            if result.get("error"):
                logger.warning(f"[_generate_aje_for_finding] Gemini error: {result.get('error')}")
                return None
            
            if result.get("parsed"):
                parsed = result["parsed"]
                
                # Validate balance
                total_debits = sum(e.get("debit", 0) for e in parsed.get("entries", []))
                total_credits = sum(e.get("credit", 0) for e in parsed.get("entries", []))
                
                if abs(total_debits - total_credits) < 0.01:
                    logger.info(f"[_generate_aje_for_finding] Generated balanced {standard_name} AJE: ${total_debits:,.2f}")
                    return {
                        "aje_id": f"AJE-{uuid.uuid4().hex[:8]}",
                        "date": "Period End",
                        "entries": parsed.get("entries", []),
                        "total_debits": total_debits,
                        "total_credits": total_credits,
                        "description": parsed.get("description", "Adjusting entry"),
                        "finding_reference": finding.get("finding_id"),
                        "rationale": parsed.get("rationale", ""),
                        "standard_reference": parsed.get("standard_reference", f"{standard_name} Standard"),
                        "accounting_standard": self.accounting_standard.value,
                        "affected_transactions": finding.get("affected_transactions", []),
                        "transaction_details": finding.get("transaction_details", []),
                        "is_balanced": True
                    }
                else:
                    logger.warning(f"[_generate_aje_for_finding] AJE not balanced: debits={total_debits}, credits={total_credits}")
            
            return None
            
        except Exception as e:
            logger.error(f"[_generate_aje_for_finding] Exception during AJE generation: {e}")
            return None
