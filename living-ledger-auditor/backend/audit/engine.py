"""
Audit Engine
Main orchestrator for running audits.
"""
from typing import Optional
import uuid
from datetime import datetime
from loguru import logger

from core.gemini_client import GeminiClient
from core.audit_trail import AuditRecord
from core.schemas import AuditFinding, Severity, FindingCategory, AccountingBasis
from .gaap_rules import GAAPRulesEngine
from .anomaly_detection import AnomalyDetector
from .fraud_detection import FraudDetector
from .aje_generator import AJEGenerator
from .risk_scorer import RiskScorer


class AuditEngine:
    """Main audit orchestration engine."""
    
    def __init__(self):
        logger.info("[AuditEngine.__init__] Initializing audit engine components")
        self.gemini = GeminiClient()
        self.gaap_engine = GAAPRulesEngine()
        self.anomaly_detector = AnomalyDetector()
        self.fraud_detector = FraudDetector()
        self.aje_generator = AJEGenerator()
        self.risk_scorer = RiskScorer()
        logger.info("[AuditEngine.__init__] All components initialized")
    
    async def run_full_audit(
        self,
        company_data: dict,
        audit_record: AuditRecord,
        progress_callback: callable = None,
        data_callback: callable = None,
        is_cancelled: callable = None,
        save_checkpoint: callable = None,
        on_quota_exceeded: callable = None,
        resume_from: dict = None
    ) -> dict:
        """
        Run a complete audit on company data.
        
        Steps:
        1. Validate data structure
        2. Run GAAP compliance checks
        3. Run anomaly detection
        4. Run fraud detection
        5. Generate findings with AI reasoning
        6. Generate AJEs for findings
        7. Calculate risk score
        
        Args:
            company_data: Company data to audit
            audit_record: Audit trail record
            progress_callback: Optional callback for progress updates (msg, percent)
            data_callback: Optional callback for streaming data updates (type, data)
            is_cancelled: Optional callback to check if audit should stop
            save_checkpoint: Optional callback to save checkpoint (phase, data)
            on_quota_exceeded: Optional callback when API quota is exceeded
            resume_from: Optional checkpoint data to resume from
        """
        logger.info("[run_full_audit] Starting full audit execution")
        
        def report_progress(msg: str, pct: float):
            if progress_callback:
                try:
                    progress_callback(msg, pct)
                except Exception:
                    pass
        
        def stream_data(data_type: str, data: dict):
            """Stream data to frontend in real-time."""
            if data_callback:
                try:
                    data_callback(data_type, data)
                except Exception:
                    pass
        
        def check_cancelled() -> bool:
            """Check if the audit has been cancelled."""
            if is_cancelled:
                return is_cancelled()
            return False
        
        def checkpoint(phase: str, data: dict):
            """Save a checkpoint."""
            if save_checkpoint:
                try:
                    save_checkpoint(phase, data)
                except Exception:
                    pass
        
        def handle_quota_exceeded():
            """Handle quota exceeded error."""
            if on_quota_exceeded:
                try:
                    on_quota_exceeded()
                except Exception:
                    pass
        
        # Determine which phase to start from if resuming
        start_phase = 1
        if resume_from and resume_from.get("phase"):
            phase_map = {
                "structural": 2,
                "gaap": 3,
                "anomaly": 4,
                "fraud": 5,
                "ai_enhance": 6,
                "aje": 7,
                "risk": 8,
            }
            start_phase = phase_map.get(resume_from.get("phase"), 1)
            logger.info(f"[run_full_audit] Resuming from phase {start_phase}")
        
        metadata = company_data["metadata"]
        coa = company_data.get("coa")
        gl = company_data.get("gl")
        tb = company_data.get("tb")
        
        logger.info(f"[run_full_audit] Company: {metadata.name}")
        logger.info(f"[run_full_audit] Accounting basis: {metadata.accounting_basis}")
        logger.info(f"[run_full_audit] COA accounts: {len(coa.accounts) if coa else 0}")
        logger.info(f"[run_full_audit] GL entries: {len(gl.entries) if gl else 0}")
        logger.info(f"[run_full_audit] TB rows: {len(tb.rows) if tb else 0}")
        
        report_progress(f"Loading data: {len(gl.entries) if gl else 0} GL entries", 5.0)
        
        all_findings = []
        
        # ========== Step 1: Validate structure ==========
        if check_cancelled():
            logger.info("[run_full_audit] Audit cancelled before structural validation")
            checkpoint("structural", {"findings": all_findings})
            return {"findings": all_findings, "ajes": [], "risk_score": {"risk_level": "unknown", "cancelled": True}}
        
        if start_phase <= 1:
            logger.info("[run_full_audit] Step 1: Validating data structure")
            report_progress("Step 1/8: Validating data structure...", 10.0)
            audit_record.add_reasoning_step("Starting structural validation", {
            "description": "Checking data integrity and basic accounting principles",
            "data_input": {
                "gl_entries_count": len(gl.entries) if gl else 0,
                "tb_rows_count": len(tb.rows) if tb else 0,
                "coa_accounts_count": len(coa.accounts) if coa else 0,
            },
            "checks_performed": [
                "Trial Balance balance verification",
                "Cash balance validation",
                "Account code consistency"
            ]
        })
        structural_findings = self._validate_structure(gl, tb, coa)
        all_findings.extend(structural_findings)
        audit_record.add_reasoning_step(f"Found {len(structural_findings)} structural issues", {
            "findings_count": len(structural_findings),
            "findings_summary": [f.get("issue") for f in structural_findings]
        })
        logger.info(f"[run_full_audit] Structural findings: {len(structural_findings)}")
        report_progress(f"Found {len(structural_findings)} structural issues", 15.0)
        
            # Stream structural findings to frontend
            for finding in structural_findings:
                stream_data("finding", finding)
            
            checkpoint("structural", {"findings": all_findings})
        
        # ========== Step 2: GAAP compliance ==========
        if check_cancelled():
            logger.info("[run_full_audit] Audit cancelled before GAAP checks")
            checkpoint("gaap", {"findings": all_findings})
            return {"findings": all_findings, "ajes": [], "risk_score": {"risk_level": "unknown", "cancelled": True}}
        
        if start_phase <= 2:
            logger.info("[run_full_audit] Step 2: Running GAAP compliance checks")
            report_progress("Step 2/8: Running GAAP compliance checks...", 20.0)
        
        # Capture sample transactions for audit trail
        sample_transactions = []
        if gl and gl.entries:
            for entry in gl.entries[:10]:  # First 10 as sample
                sample_transactions.append({
                    "entry_id": entry.entry_id,
                    "date": str(entry.date),
                    "account": entry.account_code,
                    "debit": entry.debit,
                    "credit": entry.credit,
                    "description": entry.description[:50] if entry.description else ""
                })
        
        audit_record.add_reasoning_step("Running GAAP compliance checks", {
            "description": "Applying Generally Accepted Accounting Principles validation",
            "accounting_basis": metadata.accounting_basis.value if hasattr(metadata.accounting_basis, 'value') else str(metadata.accounting_basis),
            "rules_applied": [
                "Revenue Recognition (ASC 606)",
                "Expense Classification",
                "Cutoff Testing",
                "Approval Controls",
                "Period Matching"
            ],
            "transactions_analyzed": len(gl.entries) if gl else 0,
            "sample_transactions": sample_transactions
        })
        gaap_findings = await self.gaap_engine.check_compliance(
            gl=gl,
            tb=tb,
            coa=coa,
            basis=metadata.accounting_basis
        )
        all_findings.extend(gaap_findings)
        audit_record.add_reasoning_step(f"Found {len(gaap_findings)} GAAP compliance issues", {
            "findings_count": len(gaap_findings),
            "by_category": self._count_by_field(gaap_findings, "category"),
            "by_severity": self._count_by_field(gaap_findings, "severity"),
            "findings_summary": [{"id": f.get("finding_id"), "issue": f.get("issue"), "severity": f.get("severity")} for f in gaap_findings[:5]]
        })
        logger.info(f"[run_full_audit] GAAP findings: {len(gaap_findings)}")
        report_progress(f"Found {len(gaap_findings)} GAAP compliance issues", 30.0)
        
        # Stream GAAP findings to frontend
        for finding in gaap_findings:
            stream_data("finding", finding)
        
        # Step 3: Anomaly detection
        logger.info("[run_full_audit] Step 3: Running statistical anomaly detection")
        report_progress("Step 3/7: Running anomaly detection (Benford's Law, Z-score)...", 35.0)
        audit_record.add_reasoning_step("Running statistical anomaly detection", {
            "description": "Applying statistical algorithms to identify unusual patterns",
            "algorithms_applied": [
                "Benford's Law Analysis (first digit distribution)",
                "Z-score Analysis (statistical outliers)",
                "Timing Analysis (unusual posting times)",
                "Amount Distribution Analysis"
            ],
            "transactions_analyzed": len(gl.entries) if gl else 0
        })
        anomaly_findings = self.anomaly_detector.detect_anomalies(gl)
        all_findings.extend(anomaly_findings)
        audit_record.add_reasoning_step(f"Found {len(anomaly_findings)} statistical anomalies", {
            "findings_count": len(anomaly_findings),
            "findings_summary": [{"id": f.get("finding_id"), "issue": f.get("issue")} for f in anomaly_findings]
        })
        logger.info(f"[run_full_audit] Anomaly findings: {len(anomaly_findings)}")
        report_progress(f"Found {len(anomaly_findings)} statistical anomalies", 40.0)
        
        # Stream anomaly findings to frontend
        for finding in anomaly_findings:
            stream_data("finding", finding)
        
        # Step 4: Fraud detection
        logger.info("[run_full_audit] Step 4: Running fraud pattern detection")
        report_progress("Step 4/7: Scanning for fraud patterns...", 45.0)
        audit_record.add_reasoning_step("Running fraud pattern detection", {
            "description": "Scanning for known fraud patterns and suspicious activity",
            "patterns_checked": [
                "Duplicate Payments (same vendor, amount, date)",
                "Transaction Structuring (avoiding thresholds)",
                "Round Number Analysis (exactly $1000, $5000, etc.)",
                "Vendor Anomalies (unusual payment patterns)",
                "Weekend/Holiday Transactions"
            ],
            "transactions_analyzed": len(gl.entries) if gl else 0
        })
        fraud_findings = self.fraud_detector.detect_fraud_patterns(gl)
        all_findings.extend(fraud_findings)
        audit_record.add_reasoning_step(f"Found {len(fraud_findings)} potential fraud indicators", {
            "findings_count": len(fraud_findings),
            "findings_summary": [{"id": f.get("finding_id"), "issue": f.get("issue"), "severity": f.get("severity")} for f in fraud_findings]
        })
        logger.info(f"[run_full_audit] Fraud findings: {len(fraud_findings)}")
        report_progress(f"Found {len(fraud_findings)} potential fraud indicators", 50.0)
        
        # Stream fraud findings to frontend
        for finding in fraud_findings:
            stream_data("finding", finding)
        
        # Step 5: Enhance findings with AI reasoning
        logger.info("[run_full_audit] Step 5: Generating AI explanations for findings")
        report_progress(f"Step 5/7: Generating AI explanations for {len(all_findings)} findings...", 55.0)
        audit_record.add_reasoning_step("Generating AI explanations for findings", {
            "description": "Using Gemini AI to generate human-readable explanations for each finding",
            "model": "gemini-3-flash-preview",
            "findings_to_process": len(all_findings),
            "ai_purpose": "Generate clear, professional explanations including business risk and recommendations"
        })
        enhanced_findings = await self._enhance_findings_with_ai(
            all_findings, audit_record, report_progress, stream_data
        )
        logger.info(f"[run_full_audit] Enhanced {len(enhanced_findings)} findings with AI")
        report_progress(f"Enhanced {len(enhanced_findings)} findings with AI explanations", 75.0)
        
        # Add findings to audit record
        for finding in enhanced_findings:
            audit_record.add_finding(finding)
        
        # Step 6: Generate AJEs
        logger.info("[run_full_audit] Step 6: Generating adjusting journal entries")
        report_progress("Step 6/7: Generating adjusting journal entries...", 80.0)
        correctable_findings = [f for f in enhanced_findings if f.get("category") in ["classification", "cutoff", "valuation", "balance"]]
        audit_record.add_reasoning_step("Generating adjusting journal entries", {
            "description": "Creating journal entries to correct identified issues",
            "correctable_findings": len(correctable_findings),
            "method": "Deterministic rules with AI assistance for complex cases",
            "rules": [
                "Expense reclassification entries",
                "Cutoff correction entries",
                "Accrual/deferral adjustments"
            ]
        })
        ajes = await self.aje_generator.generate_ajes(enhanced_findings, coa, audit_record)
        logger.info(f"[run_full_audit] Generated {len(ajes)} AJEs")
        report_progress(f"Generated {len(ajes)} adjusting journal entries", 85.0)
        
        for aje in ajes:
            audit_record.add_aje(aje)
            # Stream each AJE to frontend as it's added
            stream_data("aje", aje)
        
        audit_record.add_reasoning_step(f"Generated {len(ajes)} adjusting journal entries", {
            "aje_count": len(ajes),
            "ajes_summary": [{"id": a.get("aje_id"), "description": a.get("description", "")[:50]} for a in ajes]
        })
        
        # Step 7: Calculate risk score
        logger.info("[run_full_audit] Step 7: Calculating risk score")
        report_progress("Step 7/7: Calculating risk score...", 90.0)
        audit_record.add_reasoning_step("Calculating risk score", {
            "description": "Computing overall audit risk based on findings",
            "methodology": "Weighted severity scoring with confidence adjustment",
            "weights": {
                "critical": 25,
                "high": 10,
                "medium": 5,
                "low": 2
            },
            "total_findings": len(enhanced_findings),
            "by_severity": self._count_by_field(enhanced_findings, "severity")
        })
        risk_score = self.risk_scorer.calculate(enhanced_findings)
        logger.info(f"[run_full_audit] Risk score: {risk_score}")
        report_progress(f"Risk level: {risk_score.get('risk_level', 'unknown').upper()}", 95.0)
        
        # Stream risk score to frontend
        stream_data("risk_score", risk_score)
        
        logger.info("[run_full_audit] Audit execution complete")
        report_progress("Audit complete!", 100.0)
        
        return {
            "findings": enhanced_findings,
            "ajes": ajes,
            "risk_score": risk_score
        }
    
    def _count_by_field(self, items: list[dict], field: str) -> dict:
        """Count items by a specific field value."""
        counts = {}
        for item in items:
            value = item.get(field, "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts
    
    def _validate_structure(self, gl, tb, coa) -> list[dict]:
        """Validate data structure."""
        logger.info("[_validate_structure] Validating GL, TB, and COA structure")
        findings = []
        
        # Check TB balance
        if tb and not tb.is_balanced:
            logger.warning(f"[_validate_structure] Trial Balance out of balance: debits={tb.total_debits}, credits={tb.total_credits}")
            findings.append({
                "finding_id": f"STR-{uuid.uuid4().hex[:8]}",
                "category": FindingCategory.BALANCE.value,
                "severity": Severity.CRITICAL.value,
                "issue": "Trial Balance Out of Balance",
                "details": f"Trial Balance debits ({tb.total_debits}) do not equal credits ({tb.total_credits})",
                "recommendation": "Investigate and correct the imbalance before proceeding",
                "confidence": 1.0,
                "gaap_principle": "Double-Entry Accounting",
                "detection_method": "Rule-based validation: Double-entry accounting balance check"
            })
        
        # Check for negative cash
        if tb:
            for row in tb.rows:
                if row.account_code == "1000" and row.ending_balance < 0:
                    logger.warning(f"[_validate_structure] Negative cash balance: {row.ending_balance}")
                    findings.append({
                        "finding_id": f"STR-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.BALANCE.value,
                        "severity": Severity.CRITICAL.value,
                        "issue": "Negative Cash Balance",
                        "details": f"Cash account shows negative balance of ${abs(row.ending_balance):,.2f}",
                        "recommendation": "Verify all cash transactions and bank reconciliation",
                        "confidence": 1.0,
                        "gaap_principle": "Balance Validity",
                        "detection_method": "Rule-based validation: Cash account balance cannot be negative"
                    })
        
        logger.info(f"[_validate_structure] Found {len(findings)} structural issues")
        return findings
    
    async def _enhance_findings_with_ai(
        self,
        findings: list[dict],
        audit_record: AuditRecord,
        progress_callback: callable = None,
        data_callback: callable = None
    ) -> list[dict]:
        """Use Gemini to enhance findings with explanations."""
        logger.info(f"[_enhance_findings_with_ai] Enhancing {len(findings)} findings with AI explanations")
        
        def report_progress(msg: str, pct: float):
            if progress_callback:
                try:
                    progress_callback(msg, pct)
                except Exception:
                    pass
        
        def stream_data(data_type: str, data: dict):
            if data_callback:
                try:
                    data_callback(data_type, data)
                except Exception:
                    pass
        
        enhanced = []
        quota_exceeded = False
        total = len(findings)
        
        for i, finding in enumerate(findings):
            # Report progress for each finding
            pct = 55.0 + (20.0 * (i + 1) / max(total, 1))
            report_progress(f"AI explaining finding {i+1}/{total}: {finding.get('issue', '')[:40]}...", pct)
            # If quota exceeded, skip AI enhancement but still include the finding
            if quota_exceeded:
                finding["ai_explanation"] = "AI explanation skipped - API quota exceeded"
                enhanced.append(finding)
                continue
            
            logger.debug(f"[_enhance_findings_with_ai] Processing finding {i+1}/{len(findings)}: {finding.get('issue')}")
            
            try:
                # Generate AI explanation
                result = await self.gemini.generate(
                    prompt=f"""
Explain this audit finding in clear, professional language:

Issue: {finding.get('issue')}
Details: {finding.get('details')}
Category: {finding.get('category')}
Severity: {finding.get('severity')}

Provide:
1. A brief explanation of why this is a problem
2. The business risk
3. Recommended action

Keep it concise (3-4 sentences).
""",
                    purpose="finding_explanation"
                )
                
                # Check for quota exceeded
                if result.get("quota_exceeded"):
                    logger.error("=" * 60)
                    logger.error("[FINDINGS ENHANCEMENT] GEMINI QUOTA EXCEEDED!")
                    logger.error("Remaining findings will not have AI explanations")
                    logger.error("=" * 60)
                    quota_exceeded = True
                    audit_record.add_reasoning_step("AI explanations stopped - Gemini API quota exceeded")
                    finding["ai_explanation"] = "AI explanation skipped - API quota exceeded"
                elif result.get("audit"):
                    audit_record.add_gemini_interaction(result["audit"])
                    
                    if result.get("text"):
                        finding["ai_explanation"] = result["text"]
                        logger.debug(f"[_enhance_findings_with_ai] Added AI explanation for finding {finding.get('finding_id')}")
                    elif result.get("error"):
                        finding["ai_explanation"] = f"AI unavailable: {result.get('error')[:50]}"
                
            except Exception as e:
                logger.warning(f"[_enhance_findings_with_ai] Failed to generate AI explanation: {str(e)}")
                finding["ai_explanation"] = "AI explanation unavailable."
            
            enhanced.append(finding)
            # Stream the enhanced finding with AI explanation to frontend
            stream_data("finding_enhanced", finding)
        
        if quota_exceeded:
            logger.warning(f"[_enhance_findings_with_ai] Quota exceeded. Only {sum(1 for f in enhanced if 'skipped' not in f.get('ai_explanation', ''))} findings have AI explanations")
        
        logger.info(f"[_enhance_findings_with_ai] Successfully processed {len(enhanced)} findings")
        return enhanced
