"""
Audit API Routes
Handles running audits and retrieving results.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Optional
import uuid
import asyncio
import json
from loguru import logger

from core.schemas import AuditFindingsResponse, AJEResponse, RiskScore, AccountingStandard
from core.audit_trail import audit_trail
from core.progress import progress_tracker

router = APIRouter()

# In-memory storage for audit results
audit_results: dict[str, dict] = {}


async def _run_audit_task(
    company_id: str, 
    company_data: dict, 
    audit_id: str, 
    resume: bool = False,
    accounting_standard: AccountingStandard = AccountingStandard.GAAP
):
    """Background task to run the actual audit."""
    try:
        from audit.engine import get_audit_engine
        # Get checkpoint data if resuming
        checkpoint = None
        if resume:
            checkpoint = progress_tracker.get_checkpoint(audit_id)
            logger.info(f"[_run_audit_task] Resuming from checkpoint: {checkpoint}")
        
        # Create audit trail record (or reuse existing)
        if not resume:
            logger.info(f"[_run_audit_task] Creating audit trail record for {audit_id}")
            progress_tracker.add_step(audit_id, "info", "Creating audit trail record...", current_step=1, step_name="Initialization")
            record = audit_trail.create_record(
                audit_id=audit_id,
                company_id=company_id,
                created_by="api"
            )
        else:
            # Try to get existing record or create new
            record = audit_trail.get_record(audit_id)
            if not record:
                record = audit_trail.create_record(
                    audit_id=audit_id,
                    company_id=company_id,
                    created_by="api"
                )
        
        # Get cached audit engine (singleton - fast!)
        progress_tracker.add_step(audit_id, "info", "Starting audit...", progress_percent=5.0, current_step=1, step_name="Initialization")
        progress_tracker.set_total_steps(audit_id, 7)  # 7 main phases
        engine = get_audit_engine()
        
        # Data callback to stream findings/ajes/risk to frontend
        def data_callback(data_type: str, data: dict):
            """Stream data updates to frontend in real-time."""
            progress_tracker.add_step(
                audit_id, 
                "data", 
                f"Streaming {data_type}", 
                data={"data_type": data_type, "payload": data}
            )
        
        # Cancellation check callback
        def is_cancelled():
            return progress_tracker.is_cancelled(audit_id)
        
        # Checkpoint callback
        def save_checkpoint(phase: str, data: dict):
            progress_tracker.save_checkpoint(audit_id, {"phase": phase, "data": data})
        
        # Quota exceeded callback
        def on_quota_exceeded():
            progress_tracker.set_quota_exceeded(audit_id)
            save_checkpoint("quota_exceeded", {"partial_results": True})
        
        # Gemini call logging callback
        def gemini_callback(purpose: str, prompt: str, response: str, error: str = None):
            """Stream Gemini API call details to frontend."""
            progress_tracker.add_step(
                audit_id,
                "gemini_call",
                f"Gemini API: {purpose}",
                data={
                    "purpose": purpose,
                    "prompt": prompt[:500] + "..." if len(prompt) > 500 else prompt,
                    "response": response[:800] + "..." if response and len(response) > 800 else response,
                    "error": error
                }
            )
        
        # Run the audit
        standard_name = "IFRS" if accounting_standard == AccountingStandard.IFRS else "US GAAP"
        logger.info(f"[_run_audit_task] Running full audit with {standard_name} rules...")
        progress_tracker.add_step(audit_id, "info", f"Starting {standard_name} compliance checks...", progress_percent=10.0, current_step=2, step_name=f"{standard_name} Compliance")
        
        results = await engine.run_full_audit(
            company_data=company_data,
            audit_record=record,
            progress_callback=lambda msg, pct, step=None, total=7, sname=None: progress_tracker.add_step(
                audit_id, "info", msg, 
                progress_percent=pct, 
                current_step=step, 
                total_steps=total,
                step_name=sname,
            ),
            data_callback=data_callback,
            is_cancelled=is_cancelled,
            save_checkpoint=save_checkpoint,
            on_quota_exceeded=on_quota_exceeded,
            gemini_callback=gemini_callback,
            resume_from=checkpoint,
            accounting_standard=accounting_standard
        )
        
        logger.info(f"[_run_audit_task] Audit completed")
        logger.info(f"[_run_audit_task] Findings count: {len(results['findings'])}")
        logger.info(f"[_run_audit_task] AJEs count: {len(results['ajes'])}")
        logger.info(f"[_run_audit_task] Risk level: {results['risk_score'].get('risk_level', 'unknown')}")
        
        # Store results
        audit_results[audit_id] = {
            "company_id": company_id,
            "findings": results["findings"],
            "ajes": results["ajes"],
            "risk_score": results["risk_score"],
            "audit_trail": record,
            "accounting_standard": results.get("accounting_standard", accounting_standard.value)
        }
        
        # Finalize audit trail
        logger.info(f"[_run_audit_task] Finalizing audit trail")
        audit_trail.finalize_record(audit_id)
        
        response = {
            "audit_id": audit_id,
            "company_id": company_id,
            "status": "completed",
            "findings_count": len(results["findings"]),
            "ajes_count": len(results["ajes"]),
            "risk_level": results["risk_score"]["risk_level"]
        }
        
        # Complete progress tracking
        progress_tracker.complete_operation(audit_id, response)
        
        logger.info(f"[_run_audit_task] Audit task finished: {response}")
        
    except Exception as e:
        logger.error(f"[_run_audit_task] Error during audit: {str(e)}")
        logger.exception(e)
        progress_tracker.fail_operation(audit_id, str(e))


@router.post("/{company_id}/run")
async def run_audit(
    company_id: str, 
    background_tasks: BackgroundTasks,
    accounting_standard: AccountingStandard = AccountingStandard.GAAP
):
    """
    Run a full audit on a company.
    
    Args:
        company_id: The company to audit
        accounting_standard: Which accounting standard to use (gaap or ifrs). Default is GAAP.
    
    Returns immediately with audit_id so frontend can connect to SSE stream.
    The actual audit runs in the background.
    """
    standard_name = "IFRS" if accounting_standard == AccountingStandard.IFRS else "US GAAP"
    logger.info(f"[run_audit] Starting audit for company: {company_id} with {standard_name} rules")
    
    from api.routes.company import companies
    
    if company_id not in companies:
        logger.error(f"[run_audit] Company not found: {company_id}")
        raise HTTPException(status_code=404, detail="Company not found")
    
    company_data = companies[company_id]
    audit_id = str(uuid.uuid4())
    
    # Start progress tracking immediately
    progress_tracker.start_operation(audit_id, "audit")
    
    logger.info(f"[run_audit] Created audit ID: {audit_id}")
    logger.info(f"[run_audit] Company: {company_data['metadata'].name}")
    logger.info(f"[run_audit] Accounting Standard: {standard_name}")
    
    progress_tracker.add_step(audit_id, "info", f"Auditing: {company_data['metadata'].name} using {standard_name}")
    
    # Schedule the audit to run in background
    # Use asyncio.create_task so it runs concurrently
    asyncio.create_task(_run_audit_task(company_id, company_data, audit_id, accounting_standard=accounting_standard))
    
    # Return immediately so frontend can connect to SSE
    return {
        "audit_id": audit_id,
        "company_id": company_id,
        "status": "running",
        "accounting_standard": accounting_standard.value,
        "message": f"Audit started with {standard_name} rules. Connect to SSE stream for live updates."
    }


@router.get("/{company_id}/stream/{audit_id}")
async def stream_audit_progress(company_id: str, audit_id: str):
    """
    Stream audit progress updates via Server-Sent Events.
    Connect to this endpoint before starting an audit to receive real-time updates.
    """
    async def event_generator():
        queue = progress_tracker.subscribe(audit_id)
        try:
            while True:
                try:
                    # Wait for progress update with timeout
                    step = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    if step.get("type") == "end":
                        yield f"data: {json.dumps({'type': 'end', 'message': 'Audit complete'})}\n\n"
                        break
                    
                    yield f"data: {json.dumps(step)}\n\n"
                    
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    
                    # Check if operation completed
                    if progress_tracker.is_completed(audit_id):
                        yield f"data: {json.dumps({'type': 'end', 'message': 'Audit complete'})}\n\n"
                        break
                        
        finally:
            progress_tracker.unsubscribe(audit_id, queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/{company_id}/findings", response_model=AuditFindingsResponse)
async def get_findings(company_id: str, audit_id: Optional[str] = None):
    """Get audit findings for a company."""
    logger.info(f"[get_findings] Fetching findings for company: {company_id}, audit_id: {audit_id}")
    
    # Find the most recent audit for this company if no audit_id provided
    if audit_id:
        if audit_id not in audit_results:
            logger.warning(f"[get_findings] Audit not found: {audit_id}")
            raise HTTPException(status_code=404, detail="Audit not found")
        result = audit_results[audit_id]
    else:
        # Find most recent audit for company
        result = None
        for aid, data in audit_results.items():
            if data["company_id"] == company_id:
                result = data
                audit_id = aid
                break
        
        if not result:
            logger.warning(f"[get_findings] No audit found for company: {company_id}")
            raise HTTPException(status_code=404, detail="No audit found for this company")
    
    findings = result["findings"]
    logger.info(f"[get_findings] Found {len(findings)} findings")
    
    # Calculate counts by severity and category
    by_severity = {}
    by_category = {}
    for f in findings:
        sev = f.get("severity", "unknown")
        cat = f.get("category", "unknown")
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_category[cat] = by_category.get(cat, 0) + 1
    
    logger.info(f"[get_findings] By severity: {by_severity}")
    logger.info(f"[get_findings] By category: {by_category}")
    
    return AuditFindingsResponse(
        audit_id=audit_id,
        company_id=company_id,
        findings=findings,
        total_count=len(findings),
        by_severity=by_severity,
        by_category=by_category
    )


@router.get("/{company_id}/ajes", response_model=AJEResponse)
async def get_ajes(company_id: str, audit_id: Optional[str] = None):
    """Get Adjusting Journal Entries for a company audit."""
    logger.info(f"[get_ajes] Fetching AJEs for company: {company_id}, audit_id: {audit_id}")
    
    if audit_id:
        if audit_id not in audit_results:
            logger.warning(f"[get_ajes] Audit not found: {audit_id}")
            raise HTTPException(status_code=404, detail="Audit not found")
        result = audit_results[audit_id]
    else:
        result = None
        for aid, data in audit_results.items():
            if data["company_id"] == company_id:
                result = data
                audit_id = aid
                break
        
        if not result:
            logger.warning(f"[get_ajes] No audit found for company: {company_id}")
            raise HTTPException(status_code=404, detail="No audit found for this company")
    
    logger.info(f"[get_ajes] Found {len(result['ajes'])} AJEs")
    
    return AJEResponse(
        audit_id=audit_id,
        company_id=company_id,
        ajes=result["ajes"],
        total_count=len(result["ajes"])
    )


@router.get("/{company_id}/risk-score", response_model=RiskScore)
async def get_risk_score(company_id: str, audit_id: Optional[str] = None):
    """Get risk assessment for a company audit."""
    logger.info(f"[get_risk_score] Fetching risk score for company: {company_id}, audit_id: {audit_id}")
    
    if audit_id:
        if audit_id not in audit_results:
            logger.warning(f"[get_risk_score] Audit not found: {audit_id}")
            raise HTTPException(status_code=404, detail="Audit not found")
        result = audit_results[audit_id]
    else:
        result = None
        for aid, data in audit_results.items():
            if data["company_id"] == company_id:
                result = data
                audit_id = aid
                break
        
        if not result:
            logger.warning(f"[get_risk_score] No audit found for company: {company_id}")
            raise HTTPException(status_code=404, detail="No audit found for this company")
    
    logger.info(f"[get_risk_score] Risk score: {result['risk_score']}")
    
    return RiskScore(
        audit_id=audit_id,
        company_id=company_id,
        **result["risk_score"]
    )


@router.get("/{company_id}/trail")
async def get_audit_trail(company_id: str, audit_id: Optional[str] = None):
    """Get the full audit trail for regulatory compliance."""
    logger.info(f"[get_audit_trail] Fetching audit trail for company: {company_id}, audit_id: {audit_id}")
    
    if audit_id:
        if audit_id not in audit_results:
            logger.warning(f"[get_audit_trail] Audit not found: {audit_id}")
            raise HTTPException(status_code=404, detail="Audit not found")
        result = audit_results[audit_id]
    else:
        result = None
        for aid, data in audit_results.items():
            if data["company_id"] == company_id:
                result = data
                audit_id = aid
                break
        
        if not result:
            logger.warning(f"[get_audit_trail] No audit found for company: {company_id}")
            raise HTTPException(status_code=404, detail="No audit found for this company")
    
    record = result["audit_trail"]
    
    logger.info(f"[get_audit_trail] Returning audit trail with {len(record.reasoning_chain)} reasoning steps")
    
    return {
        "audit_id": audit_id,
        "company_id": company_id,
        "audit_trail": record.to_dict(),
        "regulatory_report": record.to_regulatory_report()
    }


@router.get("/{company_id}/findings/{finding_id}/reasoning")
async def get_finding_reasoning(company_id: str, finding_id: str, audit_id: Optional[str] = None):
    """
    Get detailed AI reasoning for a specific finding.
    Returns the full AI explanation, related transactions, and detection methodology.
    """
    logger.info(f"[get_finding_reasoning] Fetching reasoning for finding: {finding_id}")
    
    if audit_id:
        if audit_id not in audit_results:
            raise HTTPException(status_code=404, detail="Audit not found")
        result = audit_results[audit_id]
    else:
        result = None
        for aid, data in audit_results.items():
            if data["company_id"] == company_id:
                result = data
                audit_id = aid
                break
        
        if not result:
            raise HTTPException(status_code=404, detail="No audit found for this company")
    
    # Find the specific finding
    finding = None
    for f in result["findings"]:
        if f.get("finding_id") == finding_id:
            finding = f
            break
    
    if not finding:
        raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found")
    
    # Get related AI interactions from audit trail
    record = result["audit_trail"]
    related_ai_interactions = []
    for interaction in record.gemini_interactions:
        if interaction.get("purpose") == "finding_explanation":
            # Check if this interaction relates to this finding
            prompt_preview = interaction.get("prompt_preview", "")
            if finding.get("issue", "") in prompt_preview or finding_id in prompt_preview:
                related_ai_interactions.append({
                    "timestamp": interaction.get("timestamp"),
                    "purpose": interaction.get("purpose"),
                    "prompt_preview": interaction.get("prompt_preview"),
                    "response_preview": interaction.get("response_preview"),
                    "model": interaction.get("model")
                })
    
    # Get related reasoning steps
    related_steps = []
    for step in record.reasoning_chain:
        if isinstance(step, dict):
            step_text = step.get("step", "")
            details = step.get("details", {})
            # Check if step mentions this finding
            findings_summary = details.get("findings_summary", [])
            for fs in findings_summary:
                if isinstance(fs, dict) and fs.get("id") == finding_id:
                    related_steps.append(step)
                    break
                elif isinstance(fs, str) and finding_id in fs:
                    related_steps.append(step)
                    break
    
    return {
        "finding_id": finding_id,
        "finding": finding,
        "ai_explanation": finding.get("ai_explanation"),
        "detection_method": finding.get("detection_method", "rule-based"),
        "gaap_principle": finding.get("gaap_principle"),
        "ifrs_standard": finding.get("ifrs_standard"),
        "accounting_standard_used": finding.get("accounting_standard_used"),
        "confidence": finding.get("confidence"),
        "related_ai_interactions": related_ai_interactions,
        "related_reasoning_steps": related_steps,
        "recommendation": finding.get("recommendation"),
        "affected_transactions": finding.get("affected_transactions", []),
        "affected_accounts": finding.get("affected_accounts", [])
    }


@router.get("/{company_id}/reasoning-chain")
async def get_reasoning_chain(company_id: str, audit_id: Optional[str] = None):
    """
    Get the complete AI reasoning chain for an audit.
    Shows step-by-step how the AI analyzed the data and reached conclusions.
    """
    logger.info(f"[get_reasoning_chain] Fetching reasoning chain for company: {company_id}")
    
    if audit_id:
        if audit_id not in audit_results:
            raise HTTPException(status_code=404, detail="Audit not found")
        result = audit_results[audit_id]
    else:
        result = None
        for aid, data in audit_results.items():
            if data["company_id"] == company_id:
                result = data
                audit_id = aid
                break
        
        if not result:
            raise HTTPException(status_code=404, detail="No audit found for this company")
    
    record = result["audit_trail"]
    
    # Format reasoning chain with full details
    formatted_chain = []
    for i, step in enumerate(record.reasoning_chain):
        if isinstance(step, dict):
            formatted_chain.append({
                "step_number": i + 1,
                "timestamp": step.get("timestamp"),
                "action": step.get("step"),
                "details": step.get("details", {}),
                "description": step.get("details", {}).get("description", "")
            })
        else:
            formatted_chain.append({
                "step_number": i + 1,
                "action": str(step),
                "details": {}
            })
    
    # Get AI interaction summary
    ai_summary = {
        "total_ai_calls": len(record.gemini_interactions),
        "purposes": list(set(i.get("purpose", "unknown") for i in record.gemini_interactions)),
        "model_used": record.gemini_interactions[0].get("model") if record.gemini_interactions else None
    }
    
    return {
        "audit_id": audit_id,
        "company_id": company_id,
        "reasoning_chain": formatted_chain,
        "total_steps": len(formatted_chain),
        "ai_summary": ai_summary,
        "findings_count": len(result["findings"]),
        "ajes_count": len(result["ajes"])
    }


@router.post("/{company_id}/cancel/{audit_id}")
async def cancel_audit(company_id: str, audit_id: str):
    """
    Cancel a running audit.
    The audit will pause at the next checkpoint and can be resumed later.
    """
    logger.info(f"[cancel_audit] Cancelling audit: {audit_id}")
    
    if not progress_tracker.get_status(audit_id):
        raise HTTPException(status_code=404, detail="Audit not found or not running")
    
    if progress_tracker.is_completed(audit_id):
        raise HTTPException(status_code=400, detail="Audit already completed")
    
    # Cancel the operation
    progress_tracker.cancel_operation(audit_id)
    
    return {
        "audit_id": audit_id,
        "company_id": company_id,
        "status": "paused",
        "message": "Audit paused. You can resume it later."
    }


@router.post("/{company_id}/resume/{audit_id}")
async def resume_audit(company_id: str, audit_id: str):
    """
    Resume a paused or quota-exceeded audit from its last checkpoint.
    """
    logger.info(f"[resume_audit] Resuming audit: {audit_id}")
    
    from api.routes.company import companies
    
    if company_id not in companies:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if not progress_tracker.has_checkpoint(audit_id):
        raise HTTPException(status_code=400, detail="No checkpoint available for resume")
    
    company_data = companies[company_id]
    
    # Reset cancellation and set status to running
    progress_tracker.reset_cancellation(audit_id)
    progress_tracker.add_step(audit_id, "info", "Resuming audit from checkpoint...")
    
    # Schedule the resumed audit to run in background
    asyncio.create_task(_run_audit_task(company_id, company_data, audit_id, resume=True))
    
    return {
        "audit_id": audit_id,
        "company_id": company_id,
        "status": "running",
        "message": "Audit resumed from checkpoint."
    }


@router.get("/{company_id}/status/{audit_id}")
async def get_audit_status(company_id: str, audit_id: str):
    """
    Get the current status of an audit.
    """
    status = progress_tracker.get_status(audit_id)
    step_info = progress_tracker.get_step_info(audit_id)
    has_checkpoint = progress_tracker.has_checkpoint(audit_id)
    
    return {
        "audit_id": audit_id,
        "company_id": company_id,
        "status": status or "not_found",
        "current_step": step_info.get("current_step"),
        "total_steps": step_info.get("total_steps"),
        "step_name": step_info.get("step_name"),
        "has_checkpoint": has_checkpoint,
        "is_completed": progress_tracker.is_completed(audit_id)
    }
