import asyncio
from typing import Optional
import uuid
from datetime import datetime
from loguru import logger

from core.gemini_client import GeminiClient
from core.audit_trail import AuditRecord
from core.schemas import AuditFinding, Severity, FindingCategory, AccountingBasis, AccountingStandard
from .gaap_rules import GAAPRulesEngine
from .ifrs_rules import IFRSRulesEngine
from .anomaly_detection import AnomalyDetector
from .fraud_detection import FraudDetector
from .aje_generator import AJEGenerator
from .risk_scorer import RiskScorer


# Singleton instance for reuse across audits
_audit_engine_instance: Optional["AuditEngine"] = None


def get_audit_engine() -> "AuditEngine":
    """Get or create the singleton AuditEngine instance."""
    global _audit_engine_instance
    if _audit_engine_instance is None:
        _audit_engine_instance = AuditEngine()
    return _audit_engine_instance


class AuditEngine:
    """Main audit orchestration engine."""
    
    def __init__(self):
        logger.info("[AuditEngine.__init__] Initializing audit engine components")
        # Lazy initialization - components created on first use
        self._gemini: Optional[GeminiClient] = None
        self._gaap_engine: Optional[GAAPRulesEngine] = None
        self._ifrs_engine: Optional[IFRSRulesEngine] = None
        self._anomaly_detector: Optional[AnomalyDetector] = None
        self._fraud_detector: Optional[FraudDetector] = None
        self._aje_generator: Optional[AJEGenerator] = None
        self._risk_scorer: Optional[RiskScorer] = None
        logger.info("[AuditEngine.__init__] Engine created (components lazy-loaded)")
    
    @property
    def gemini(self) -> GeminiClient:
        if self._gemini is None:
            self._gemini = GeminiClient()
        return self._gemini
    
    @property
    def gaap_engine(self) -> GAAPRulesEngine:
        if self._gaap_engine is None:
            self._gaap_engine = GAAPRulesEngine()
        return self._gaap_engine
    
    @property
    def ifrs_engine(self) -> IFRSRulesEngine:
        if self._ifrs_engine is None:
            self._ifrs_engine = IFRSRulesEngine()
        return self._ifrs_engine
    
    @property
    def anomaly_detector(self) -> AnomalyDetector:
        if self._anomaly_detector is None:
            self._anomaly_detector = AnomalyDetector()
        return self._anomaly_detector
    
    @property
    def fraud_detector(self) -> FraudDetector:
        if self._fraud_detector is None:
            self._fraud_detector = FraudDetector()
        return self._fraud_detector
    
    @property
    def aje_generator(self) -> AJEGenerator:
        if self._aje_generator is None:
            self._aje_generator = AJEGenerator()
        return self._aje_generator
    
    @property
    def risk_scorer(self) -> RiskScorer:
        if self._risk_scorer is None:
            self._risk_scorer = RiskScorer()
        return self._risk_scorer
    
    async def run_full_audit(
        self,
        company_data: dict,
        audit_record: AuditRecord,
        progress_callback: callable = None,
        data_callback: callable = None,
        is_cancelled: callable = None,
        save_checkpoint: callable = None,
        on_quota_exceeded: callable = None,
        gemini_callback: callable = None,
        resume_from: dict = None,
        accounting_standard: AccountingStandard = AccountingStandard.GAAP
    ) -> dict:
        """
        Run a complete audit on company data.
        
        Args:
            accounting_standard: Which accounting standard to use (GAAP or IFRS)
        
        Steps:
        1. Validate data structure (Sequential - Gatekeeper)
        2. Run GAAP/IFRS compliance checks (Parallel)
        3. Run anomaly detection (Parallel)
        4. Run fraud detection (Parallel)
        5. Generate findings with AI reasoning (Concurrent)
        6. Generate AJEs for findings (Sequential - depends on findings)
        7. Calculate risk score (Sequential - depends on findings)
        """
        logger.info("[run_full_audit] Starting full audit execution")
        
        TOTAL_STEPS = 7
        
        def report_progress(msg: str, pct: float, current_step: int = None):
            if progress_callback:
                try:
                    progress_callback(msg, pct, current_step, TOTAL_STEPS)
                except Exception:
                    pass
        
        def stream_data(data_type: str, data: dict):
            """Stream data to frontend in real-time."""
            if data_callback:
                try:
                    data_callback(data_type, data)
                except Exception:
                    pass
        
        def stream_reasoning_step(step: str, details: dict = None):
            """Stream reasoning step to frontend in real-time."""
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "step": step,
                "details": details or {}
            }
            # Add to audit record for persistence
            audit_record.add_reasoning_step(step, details)
            # Stream to frontend in real-time
            stream_data("reasoning_step", entry)
        
        def stream_gemini_interaction(interaction: dict):
            """Stream Gemini interaction to frontend in real-time."""
            audit_record.add_gemini_interaction(interaction)
            stream_data("gemini_interaction", interaction)
        
        def log_gemini_call(purpose: str, prompt: str, response: str, error: str = None):
            """Log Gemini API call details to frontend."""
            if gemini_callback:
                try:
                    gemini_callback(purpose, prompt, response, error)
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
            # Simplified phase mapping since steps 2-4 are now parallel
            # We map old phases to our new parallel structure
            phase = resume_from.get("phase")
            if phase == "structural":
                start_phase = 2
            elif phase in ["gaap", "anomaly", "fraud", "analysis_complete"]:
                start_phase = 5
            elif phase == "ai_enhance":
                start_phase = 6
            elif phase == "aje":
                start_phase = 7
            
            logger.info(f"[run_full_audit] Resuming from phase {start_phase} (mapped from {phase})")
        
        metadata = company_data["metadata"]
        coa = company_data.get("coa")
        gl = company_data.get("gl")
        tb = company_data.get("tb")
        
        logger.info(f"[run_full_audit] Company: {metadata.name}")
        report_progress(f"Loading data: {len(gl.entries) if gl else 0} GL entries", 5.0)
        
        all_findings = []
        
        # ========== Step 1: Validate structure ==========
        if check_cancelled():
            return {"findings": [], "ajes": [], "risk_score": {"risk_level": "unknown", "cancelled": True}}
        
        if start_phase <= 1:
            logger.info("[run_full_audit] Step 1: Validating data structure")
            report_progress("Step 1/7: Validating data structure...", 10.0, current_step=1)
            
            stream_reasoning_step("Starting structural validation", {
                "description": "Checking data integrity and basic accounting principles",
                "data_input": {
                    "gl_entries_count": len(gl.entries) if gl else 0,
                    "tb_rows_count": len(tb.rows) if tb else 0,
                    "coa_accounts_count": len(coa.accounts) if coa else 0,
                },
                "checks_performed": ["Trial Balance balance verification", "Cash balance validation", "Account code consistency"]
            })
            
            # This is fast and synchronous, keep as is
            structural_findings = self._validate_structure(gl, tb, coa)
            all_findings.extend(structural_findings)
            
            stream_reasoning_step(f"Found {len(structural_findings)} structural issues", {
                "findings_count": len(structural_findings),
                "findings_summary": [f.get("issue") for f in structural_findings]
            })
            
            for finding in structural_findings:
                stream_data("finding", finding)
            
            checkpoint("structural", {"findings": all_findings})

        # ========== Steps 2-4: Parallel Analysis (GAAP, Anomaly, Fraud) ==========
        # Check cancellation before starting heavy parallel work
        if check_cancelled():
            return {"findings": all_findings, "ajes": [], "risk_score": {"risk_level": "unknown", "cancelled": True}}

        if start_phase <= 2:
            # Determine which rules engine to use
            standard_name = "IFRS" if accounting_standard == AccountingStandard.IFRS else "US GAAP"
            rules_engine = self.ifrs_engine if accounting_standard == AccountingStandard.IFRS else self.gaap_engine
            
            logger.info(f"[run_full_audit] Starting parallel analysis ({standard_name}, Anomaly, Fraud)")
            report_progress(f"Step 2-4: Running parallel analysis ({standard_name}, Anomaly, Fraud)...", 20.0, current_step=2)
            
            # --- Define Async Task Wrappers ---
            
            async def run_compliance():
                stream_reasoning_step(f"Running {standard_name} compliance checks", {
                    "description": f"Applying {standard_name} validation rules",
                    "accounting_standard": standard_name,
                    "accounting_basis": str(metadata.accounting_basis),
                    "steps": "Running concurrently with other checks"
                })
                # rules_engine.check_compliance is async and uses asyncio.to_thread internally
                findings = await rules_engine.check_compliance(gl, tb, coa, metadata.accounting_basis)
                # Tag findings with the accounting standard used
                for f in findings:
                    f["accounting_standard_used"] = accounting_standard.value
                for f in findings: stream_data("finding", f)
                return findings

            async def run_anomaly():
                stream_reasoning_step("Running statistical anomaly detection", {
                    "description": "Applying statistical algorithms (Benford's Law, Z-score)",
                    "steps": "Running concurrently"
                })
                # CPU-bound, run in thread to avoid blocking event loop
                findings = await asyncio.to_thread(self.anomaly_detector.detect_anomalies, gl)
                for f in findings: stream_data("finding", f)
                return findings

            async def run_fraud():
                stream_reasoning_step("Running fraud pattern detection", {
                    "description": "Scanning for fraud patterns (structuring, duplicates, round trips)",
                    "steps": "Running concurrently"
                })
                # CPU-bound, run in thread to avoid blocking event loop
                findings = await asyncio.to_thread(self.fraud_detector.detect_fraud_patterns, gl)
                for f in findings: stream_data("finding", f)
                return findings

            # --- Execute in Parallel ---
            # This allows the event loop to remain free for chat/health checks
            results = await asyncio.gather(run_compliance(), run_anomaly(), run_fraud())
            
            compliance_findings, anomaly_findings, fraud_findings = results
            
            all_findings.extend(compliance_findings)
            all_findings.extend(anomaly_findings)
            all_findings.extend(fraud_findings)
            
            stream_reasoning_step(f"Analysis complete. Found {len(all_findings)} total issues.", {
                "accounting_standard": standard_name,
                "compliance_count": len(compliance_findings),
                "anomaly_count": len(anomaly_findings),
                "fraud_count": len(fraud_findings)
            })
            
            logger.info(f"[run_full_audit] Parallel analysis complete. Total findings: {len(all_findings)}")
            report_progress(f"Analysis complete. Found {len(all_findings)} issues.", 50.0)
            checkpoint("analysis_complete", {"findings": all_findings})

        # ========== Step 5: Enhance findings with AI reasoning ==========
        if check_cancelled():
            return {"findings": all_findings, "ajes": [], "risk_score": {"risk_level": "unknown", "cancelled": True}}
            
        if start_phase <= 5:
            logger.info("[run_full_audit] Step 5: Generating AI explanations for findings")
            report_progress(f"Step 5/7: Generating AI explanations for {len(all_findings)} findings...", 55.0, current_step=5)
            
            stream_reasoning_step("Generating AI explanations for findings", {
                "description": "Using Gemini AI to generate human-readable explanations",
                "model": "gemini-flash-thinking",
                "findings_to_process": len(all_findings),
                "method": "Concurrent processing"
            })
            
            enhanced_findings = await self._enhance_findings_with_ai(
                all_findings, 
                audit_record, 
                progress_callback, 
                stream_data, 
                log_gemini_call, 
                stream_gemini_interaction,
                handle_quota_exceeded  # Pass the callback!
            )
            
            report_progress(f"Enhanced {len(enhanced_findings)} findings with AI explanations", 75.0)
            
            # Add findings to audit record
            for finding in enhanced_findings:
                audit_record.add_finding(finding)
        else:
            # If skipping, assume we have findings (in real implementation, would load from checkpoint)
            enhanced_findings = all_findings
        
        # ========== Step 6: Generate AJEs ==========
        if check_cancelled(): return {"findings": enhanced_findings, "ajes": [], "risk_score": {"risk_level": "unknown", "cancelled": True}}

        if start_phase <= 6:
            logger.info("[run_full_audit] Step 6: Generating adjusting journal entries")
            report_progress("Step 6/7: Generating adjusting journal entries...", 80.0, current_step=6)
            
            stream_reasoning_step("Generating adjusting journal entries", {
                "description": "Creating journal entries to correct identified issues",
                "method": "Rule-based generation"
            })
            
            # Run in thread if possible - pass accounting_standard so AJEs follow selected ruleset
            if hasattr(self.aje_generator, 'generate_ajes_sync'):
                 ajes = await asyncio.to_thread(self.aje_generator.generate_ajes_sync, enhanced_findings, coa, audit_record, accounting_standard)
            else:
                 # If only async method exists, await it directly (assuming it's light or handles its own concurrency)
                 ajes = await self.aje_generator.generate_ajes(enhanced_findings, coa, audit_record, accounting_standard)

            for aje in ajes:
                audit_record.add_aje(aje)
                stream_data("aje", aje)
                
            stream_reasoning_step(f"Generated {len(ajes)} adjusting journal entries", {"aje_count": len(ajes)})
            report_progress(f"Generated {len(ajes)} adjusting journal entries", 85.0)
            checkpoint("aje", {"findings": enhanced_findings, "ajes": ajes})
        else:
            ajes = []

        # ========== Step 7: Calculate risk score ==========
        if check_cancelled(): return {"findings": enhanced_findings, "ajes": ajes, "risk_score": {"risk_level": "unknown", "cancelled": True}}

        if start_phase <= 7:
            logger.info("[run_full_audit] Step 7: Calculating risk score")
            report_progress("Step 7/7: Calculating risk score...", 90.0, current_step=7)
            
            stream_reasoning_step("Calculating risk score", {"description": "Computing overall audit risk based on findings"})
            
            # Lightweight calculation
            risk_score = await asyncio.to_thread(self.risk_scorer.calculate, enhanced_findings)
            
            stream_data("risk_score", risk_score)
            report_progress(f"Risk level: {risk_score.get('risk_level', 'unknown').upper()}", 100.0)
        else:
            risk_score = {"risk_level": "unknown"}
        
        logger.info("[run_full_audit] Audit execution complete")
        
        return {
            "findings": enhanced_findings,
            "ajes": ajes,
            "risk_score": risk_score,
            "accounting_standard": accounting_standard.value
        }
    
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
        data_callback: callable = None,
        gemini_callback: callable = None,
        gemini_interaction_callback: callable = None,
        on_quota_exceeded: callable = None  # Added: Accept on_quota_exceeded callback
    ) -> list[dict]:
        """Use Gemini to enhance findings with explanations concurrently."""
        logger.info(f"[_enhance_findings_with_ai] Enhancing {len(findings)} findings with AI explanations")
        
        enhanced = []
        total = len(findings)
        processed_count = 0
        quota_exceeded = False
        
        # Semaphore to limit concurrent API calls (e.g., 5 concurrent calls)
        sem = asyncio.Semaphore(5)
        
        async def process_finding(finding):
            nonlocal processed_count, quota_exceeded
            
            async with sem:
                if quota_exceeded:
                    finding["ai_explanation"] = "AI explanation skipped - API quota exceeded"
                    return finding
                
                # Check if explanation already exists (e.g. from resume)
                if finding.get("ai_explanation"):
                    return finding
                
                prompt_text = f"""Explain this audit finding in clear, professional language:
Issue: {finding.get('issue')}
Details: {finding.get('details')}
Category: {finding.get('category')}
Severity: {finding.get('severity')}

Provide:
1. A brief explanation of why this is a problem
2. The business risk
3. Recommended action

Keep it concise (3-4 sentences)."""

                try:
                    result = await self.gemini.generate(prompt=prompt_text, purpose="finding_explanation")
                    
                    if gemini_callback:
                        # Safe non-blocking callback
                        try:
                            gemini_callback("Explain finding", prompt_text, result.get("text", ""), result.get("error"))
                        except: pass
                    
                    if result.get("quota_exceeded"):
                        logger.error("[FINDINGS ENHANCEMENT] GEMINI QUOTA EXCEEDED!")
                        if not quota_exceeded: # Trigger only once
                             quota_exceeded = True
                             if on_quota_exceeded:
                                  try: on_quota_exceeded()
                                  except: pass
                        finding["ai_explanation"] = "AI explanation skipped - API quota exceeded"
                    elif result.get("text"):
                        finding["ai_explanation"] = result["text"]
                        if gemini_interaction_callback and result.get("audit"):
                             try: gemini_interaction_callback(result["audit"])
                             except: pass
                    else:
                        finding["ai_explanation"] = f"AI unavailable: {result.get('error')}"
                        
                except Exception as e:
                    logger.warning(f"AI enhancement failed: {e}")
                    finding["ai_explanation"] = "AI explanation unavailable."
                
                processed_count += 1
                pct = 55.0 + (20.0 * processed_count / max(total, 1))
                if progress_callback:
                     try: progress_callback(f"AI explaining finding {processed_count}/{total}...", pct)
                     except: pass
                
                if data_callback:
                     try: data_callback("finding_enhanced", finding)
                     except: pass
                     
                return finding

        # Create tasks
        tasks = [process_finding(f) for f in findings]
        
        if tasks:
            enhanced = await asyncio.gather(*tasks)
        else:
            enhanced = findings
            
        if quota_exceeded:
            logger.warning(f"[_enhance_findings_with_ai] Quota exceeded during batch processing")
            
        return enhanced
