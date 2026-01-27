"""
AJE Generator
Generates Adjusting Journal Entries for audit findings.
"""
import uuid
from loguru import logger

from core.gemini_client import GeminiClient
from core.audit_trail import AuditRecord
from core.schemas import ChartOfAccounts, FindingCategory


class AJEGenerator:
    """Generates Adjusting Journal Entries."""
    
    def __init__(self):
        logger.info("[AJEGenerator.__init__] Initializing AJE generator")
        self.gemini = GeminiClient()
        self.quota_exceeded = False
    
    async def generate_ajes(
        self,
        findings: list[dict],
        coa: ChartOfAccounts,
        audit_record: AuditRecord
    ) -> list[dict]:
        """Generate AJEs for findings that can be corrected."""
        logger.info(f"[generate_ajes] Processing {len(findings)} findings for AJE generation")
        
        ajes = []
        
        # Only generate AJEs for certain categories
        correctable_categories = [
            FindingCategory.CLASSIFICATION.value,
            FindingCategory.TIMING.value,
            FindingCategory.STRUCTURAL.value
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
        
        # If no AJEs generated due to quota, use deterministic fallback
        if len(ajes) == 0 and len(correctable) > 0:
            logger.info("[generate_ajes] Using deterministic AJE generation fallback")
            audit_record.add_reasoning_step("Using deterministic AJE rules (AI unavailable)")
            ajes = self._generate_deterministic_ajes(correctable, coa)
            logger.info(f"[generate_ajes] Generated {len(ajes)} deterministic AJEs")
        
        logger.info(f"[generate_ajes] Successfully generated {len(ajes)} total AJEs")
        return ajes
    
    def _generate_deterministic_ajes(
        self,
        findings: list[dict],
        coa: ChartOfAccounts
    ) -> list[dict]:
        """Generate AJEs using deterministic rules without AI."""
        logger.info(f"[_generate_deterministic_ajes] Processing {len(findings)} findings with rules")
        
        ajes = []
        
        # Build account lookup
        accounts = {a.code: a for a in coa.accounts}
        
        for finding in findings:
            aje = self._apply_aje_rule(finding, accounts)
            if aje:
                ajes.append(aje)
        
        return ajes
    
    def _apply_aje_rule(self, finding: dict, accounts: dict) -> dict | None:
        """Apply deterministic rules to generate an AJE."""
        category = finding.get("category", "")
        issue = finding.get("issue", "").lower()
        details = finding.get("details", "")
        
        # Extract amount from details if present (look for $ amounts)
        import re
        amount_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', details)
        amount = float(amount_match.group(1).replace(',', '')) if amount_match else 1000.00
        
        # Rule 1: Expense Misclassification
        if "misclass" in issue or "classification" in category.lower():
            # Reclassify from miscellaneous to correct expense
            return {
                "aje_id": f"AJE-DET-{uuid.uuid4().hex[:6]}",
                "date": "Period End",
                "entries": [
                    {"account_code": "6900", "account_name": "Miscellaneous Expense", "debit": 0, "credit": amount},
                    {"account_code": "6200", "account_name": "Marketing Expense", "debit": amount, "credit": 0}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Reclassify expense per audit finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": "GAAP requires proper expense classification for accurate financial reporting",
                "rule_applied": "RULE_EXPENSE_RECLASSIFICATION",
                "is_balanced": True
            }
        
        # Rule 2: Revenue Recognition Timing
        if "revenue" in issue and ("timing" in issue or "recognition" in issue):
            return {
                "aje_id": f"AJE-DET-{uuid.uuid4().hex[:6]}",
                "date": "Period End",
                "entries": [
                    {"account_code": "4000", "account_name": "Service Revenue", "debit": amount, "credit": 0},
                    {"account_code": "2200", "account_name": "Deferred Revenue", "debit": 0, "credit": amount}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Defer unearned revenue per finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": "ASC 606 requires revenue recognition only when performance obligations are satisfied",
                "rule_applied": "RULE_REVENUE_DEFERRAL",
                "is_balanced": True
            }
        
        # Rule 3: Accrual Missing
        if "accrual" in issue or "accrue" in issue:
            return {
                "aje_id": f"AJE-DET-{uuid.uuid4().hex[:6]}",
                "date": "Period End",
                "entries": [
                    {"account_code": "6000", "account_name": "Operating Expense", "debit": amount, "credit": 0},
                    {"account_code": "2100", "account_name": "Accrued Expenses", "debit": 0, "credit": amount}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Accrue unrecorded expense per finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": "Matching principle requires expenses to be recorded in the period incurred",
                "rule_applied": "RULE_EXPENSE_ACCRUAL",
                "is_balanced": True
            }
        
        # Rule 4: Prepaid Expense Amortization
        if "prepaid" in issue or "amortiz" in issue:
            return {
                "aje_id": f"AJE-DET-{uuid.uuid4().hex[:6]}",
                "date": "Period End",
                "entries": [
                    {"account_code": "6000", "account_name": "Operating Expense", "debit": amount, "credit": 0},
                    {"account_code": "1200", "account_name": "Prepaid Expenses", "debit": 0, "credit": amount}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Amortize prepaid expense per finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": "Prepaid expenses must be amortized over the benefit period",
                "rule_applied": "RULE_PREPAID_AMORTIZATION",
                "is_balanced": True
            }
        
        # Rule 5: Depreciation
        if "deprec" in issue:
            return {
                "aje_id": f"AJE-DET-{uuid.uuid4().hex[:6]}",
                "date": "Period End",
                "entries": [
                    {"account_code": "6700", "account_name": "Depreciation Expense", "debit": amount, "credit": 0},
                    {"account_code": "1600", "account_name": "Accumulated Depreciation", "debit": 0, "credit": amount}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Record depreciation per finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": "Fixed assets must be depreciated over their useful life per GAAP",
                "rule_applied": "RULE_DEPRECIATION",
                "is_balanced": True
            }
        
        # Default: Generic reclassification
        if category in ["classification", "structural", "timing"]:
            return {
                "aje_id": f"AJE-DET-{uuid.uuid4().hex[:6]}",
                "date": "Period End",
                "entries": [
                    {"account_code": "6900", "account_name": "Miscellaneous Expense", "debit": 0, "credit": amount},
                    {"account_code": "6000", "account_name": "Operating Expense", "debit": amount, "credit": 0}
                ],
                "total_debits": amount,
                "total_credits": amount,
                "description": f"Correcting entry per finding {finding.get('finding_id')}",
                "finding_reference": finding.get("finding_id"),
                "rationale": "Correction required per audit finding",
                "rule_applied": "RULE_GENERIC_CORRECTION",
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
        logger.debug(f"[_generate_aje_for_finding] Generating AJE for: {finding.get('issue')}")
        
        try:
            # Build COA summary for prompt
            coa_summary = "\n".join([
                f"{a.code}: {a.name} ({a.type}, {a.normal_balance})"
                for a in coa.accounts[:30]  # Limit for prompt size
            ])
            
            prompt = f"""
Generate an Adjusting Journal Entry to correct this audit finding:

FINDING:
Issue: {finding.get('issue')}
Details: {finding.get('details')}
Category: {finding.get('category')}
GAAP Principle: {finding.get('gaap_principle', 'N/A')}

CHART OF ACCOUNTS:
{coa_summary}

Generate a balanced journal entry with proper debits and credits.
Return ONLY valid JSON in this format:
{{
    "description": "Brief description of the adjustment",
    "entries": [
        {{"account_code": "XXXX", "account_name": "Account Name", "debit": 0.00, "credit": 0.00}}
    ],
    "rationale": "Why this entry corrects the issue"
}}

CRITICAL: Debits must equal credits. Use realistic amounts based on the finding.
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
                    logger.info(f"[_generate_aje_for_finding] Generated balanced AJE: ${total_debits:,.2f}")
                    return {
                        "aje_id": f"AJE-{uuid.uuid4().hex[:8]}",
                        "date": "Period End",
                        "entries": parsed.get("entries", []),
                        "total_debits": total_debits,
                        "total_credits": total_credits,
                        "description": parsed.get("description", "Adjusting entry"),
                        "finding_reference": finding.get("finding_id"),
                        "rationale": parsed.get("rationale", ""),
                        "is_balanced": True
                    }
                else:
                    logger.warning(f"[_generate_aje_for_finding] AJE not balanced: debits={total_debits}, credits={total_credits}")
            
            return None
            
        except Exception as e:
            logger.error(f"[_generate_aje_for_finding] Exception during AJE generation: {e}")
            return None
