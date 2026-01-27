"""
Ownership Discovery API Routes
Handles beneficial ownership discovery and graph analysis.

ARCHITECTURE: Uses REAL public registry APIs, Gemini only for parsing/classification.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncio
import json
from loguru import logger

from core.schemas import OwnershipGraph, OwnershipDiscoveryRequest, DataSourceSummary
from core.progress import progress_tracker

router = APIRouter()

# In-memory storage for ownership graphs
ownership_graphs: dict[str, dict] = {}


@router.post("/discover")
async def discover_ownership(request: OwnershipDiscoveryRequest):
    """
    Discover beneficial ownership network for given entities.
    
    Data Flow:
    1. Searches REAL public registries (SEC EDGAR, GLEIF)
    2. Uses Gemini to PARSE and CLASSIFY the fetched data (NOT generate fake data)
    3. Builds ownership graph from real data
    4. Falls back to deterministic mock data only if all APIs return nothing
    
    Returns:
        Discovery results including data source transparency info
    """
    logger.info(f"[discover_ownership] Request to discover ownership for {len(request.seed_entities)} entities")
    from ownership.discovery import BeneficialOwnershipDiscovery
    
    discovery = BeneficialOwnershipDiscovery()
    
    result = await discovery.discover_ownership_network(
        seed_entities=request.seed_entities,
        depth=request.depth
    )
    
    # Store the graph
    graph_id = f"graph_{len(ownership_graphs)}"
    ownership_graphs[graph_id] = {
        "seed_entities": request.seed_entities,
        "graph": result["graph"],
        "findings": result.get("findings", []),
        "data_sources": result.get("data_sources", {}),
        "entities": result.get("entities", {})
    }
    
    graph_obj = result["graph"]
    data_sources = result.get("data_sources", {})
    
    # Calculate real data percentage
    total_entities = result["entities_discovered"]
    real_count = data_sources.get("total_from_real_apis", 0)
    real_percentage = (real_count / total_entities * 100) if total_entities > 0 else 0
    
    logger.info(f"[discover_ownership] Complete. Graph ID: {graph_id}, Entities: {total_entities}, Real API: {real_count}, Findings: {len(result.get('findings', []))}")
    
    return {
        "graph_id": graph_id,
        "entities_discovered": total_entities,
        "node_count": graph_obj.statistics.get("total_entities", len(graph_obj.nodes)) if isinstance(graph_obj.statistics, dict) else len(graph_obj.nodes),
        "edge_count": graph_obj.statistics.get("total_relationships", len(graph_obj.edges)) if isinstance(graph_obj.statistics, dict) else len(graph_obj.edges),
        "findings_count": len(result.get("findings", [])),
        "data_sources": {
            "sources_used": data_sources.get("sources_used", []),
            "entities_by_source": data_sources.get("entities_by_source", {}),
            "total_from_real_apis": real_count,
            "total_mock": data_sources.get("total_mock", 0)
        },
        "real_data_percentage": round(real_percentage, 1)
    }


@router.get("/graph/{graph_id}", response_model=OwnershipGraph)
async def get_ownership_graph(graph_id: str):
    """Get an ownership graph by ID."""
    if graph_id not in ownership_graphs:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    return ownership_graphs[graph_id]["graph"]


@router.get("/graph/{graph_id}/findings")
async def get_ownership_findings(graph_id: str):
    """Get fraud-related findings from ownership analysis."""
    if graph_id not in ownership_graphs:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    return {
        "graph_id": graph_id,
        "findings": ownership_graphs[graph_id]["findings"]
    }


async def _run_ownership_discovery_task(company_id: str, company_name: str, vendors: list, graph_id: str):
    """Background task to run ownership discovery."""
    from ownership.discovery import BeneficialOwnershipDiscovery
    
    try:
        # Set total steps
        progress_tracker.set_total_steps(graph_id, len(vendors[:20]) + 3)  # vendors + init + analyze + complete
        
        discovery = BeneficialOwnershipDiscovery()
        
        def ownership_progress(msg: str, pct: float, data: dict = None):
            progress_tracker.add_step(graph_id, "info", msg, data=data, progress_percent=pct)
        
        def data_callback(data_type: str, data: dict):
            """Stream graph data (nodes, edges, findings) to frontend in real-time."""
            progress_tracker.add_step(
                graph_id, 
                "data", 
                f"Streaming {data_type}", 
                data={"data_type": data_type, "payload": data}
            )
        
        def is_cancelled():
            """Check if discovery was cancelled."""
            return progress_tracker.is_cancelled(graph_id)
        
        def save_checkpoint(processed: list, remaining: list):
            """Save checkpoint for resume."""
            progress_tracker.save_checkpoint(graph_id, {
                "company_id": company_id,
                "processed_vendors": processed,
                "remaining_vendors": remaining
            })
        
        def on_quota_exceeded():
            """Handle quota exceeded."""
            progress_tracker.set_quota_exceeded(graph_id)
        
        # Stream the audited company as the ROOT node first
        root_node = {
            "id": company_id,
            "name": company_name,
            "type": "company",
            "is_root": True,
            "jurisdiction": "US",  # Default, can be overridden
        }
        data_callback("node", root_node)
        
        # Stream vendor relationship edges from audited company to each vendor
        # This shows the payment/service relationships
        for vendor in vendors[:20]:
            vendor_edge = {
                "source": company_id,
                "target": vendor,
                "relationship": "vendor",
            }
            data_callback("edge", vendor_edge)
        
        result = await discovery.discover_ownership_network(
            seed_entities=vendors[:20],  # Limit to first 20 vendors
            depth=2,
            progress_callback=ownership_progress,
            data_callback=data_callback,
            is_cancelled=is_cancelled,
            save_checkpoint=save_checkpoint,
            on_quota_exceeded=on_quota_exceeded
        )
        
        # Store the graph
        ownership_graphs[graph_id] = {
            "company_id": company_id,
            "seed_entities": vendors[:20],
            "graph": result["graph"],
            "findings": result.get("findings", [])
        }
        
        response = {
            "company_id": company_id,
            "graph_id": graph_id,
            "vendors_analyzed": len(vendors[:20]),
            "entities_discovered": result["entities_discovered"],
            "findings_count": len(result.get("findings", []))
        }
        
        progress_tracker.complete_operation(graph_id, response)
        
        logger.info(f"[_run_ownership_discovery_task] Complete: {response}")
        
    except Exception as e:
        logger.exception(f"[_run_ownership_discovery_task] Error: {str(e)}")
        progress_tracker.fail_operation(graph_id, str(e))


@router.post("/analyze-vendors/{company_id}")
async def analyze_vendors(company_id: str):
    """
    Analyze all vendors from a company's GL for ownership patterns.
    Returns immediately with graph_id so frontend can connect to SSE stream.
    Actual discovery runs in background.
    """
    from api.routes.company import companies
    
    if company_id not in companies:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company_data = companies[company_id]
    gl = company_data.get("gl")
    
    if not gl:
        raise HTTPException(status_code=400, detail="No General Ledger available")
    
    # Extract unique vendors from GL
    vendors = list(set(
        entry.vendor_or_customer
        for entry in gl.entries
        if entry.vendor_or_customer
    ))
    
    if not vendors:
        return {
            "company_id": company_id,
            "vendors_found": 0,
            "message": "No vendors found in General Ledger"
        }
    
    # Store the graph ID
    graph_id = f"vendor_graph_{company_id}"
    
    # Get company name for the root node
    company_info = company_data.get("company")
    company_name = company_info.name if company_info else company_id
    
    # Start progress tracking immediately
    progress_tracker.start_operation(graph_id, "ownership_discovery")
    progress_tracker.add_step(graph_id, "info", f"Found {len(vendors)} unique vendors in GL")
    
    # Run discovery in background
    asyncio.create_task(_run_ownership_discovery_task(company_id, company_name, vendors, graph_id))
    
    # Return immediately so frontend can connect to SSE
    return {
        "company_id": company_id,
        "graph_id": graph_id,
        "vendors_analyzed": len(vendors[:20]),
        "status": "running",
        "message": "Ownership discovery started. Connect to SSE stream for live updates."
    }


@router.get("/stream/{graph_id}")
async def stream_ownership_progress(graph_id: str):
    """
    Stream ownership discovery progress updates via Server-Sent Events.
    Connect to this endpoint to receive real-time updates during discovery.
    """
    async def event_generator():
        queue = progress_tracker.subscribe(graph_id)
        try:
            while True:
                try:
                    step = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    if step.get("type") == "end":
                        yield f"data: {json.dumps({'type': 'end', 'message': 'Discovery complete'})}\n\n"
                        break
                    
                    yield f"data: {json.dumps(step)}\n\n"
                    
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    
                    if progress_tracker.is_completed(graph_id):
                        yield f"data: {json.dumps({'type': 'end', 'message': 'Discovery complete'})}\n\n"
                        break
                        
        finally:
            progress_tracker.unsubscribe(graph_id, queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/cancel/{graph_id}")
async def cancel_ownership_discovery(graph_id: str):
    """
    Cancel a running ownership discovery.
    The discovery will pause at the next checkpoint and can be resumed later.
    """
    logger.info(f"[cancel_ownership_discovery] Cancelling discovery: {graph_id}")
    
    if not progress_tracker.get_status(graph_id):
        raise HTTPException(status_code=404, detail="Discovery not found or not running")
    
    if progress_tracker.is_completed(graph_id):
        raise HTTPException(status_code=400, detail="Discovery already completed")
    
    # Cancel the operation
    progress_tracker.cancel_operation(graph_id)
    
    return {
        "graph_id": graph_id,
        "status": "paused",
        "message": "Ownership discovery paused. You can resume it later."
    }


@router.post("/resume/{graph_id}")
async def resume_ownership_discovery(graph_id: str):
    """
    Resume a paused or quota-exceeded ownership discovery from its last checkpoint.
    """
    logger.info(f"[resume_ownership_discovery] Resuming discovery: {graph_id}")
    
    if not progress_tracker.has_checkpoint(graph_id):
        raise HTTPException(status_code=400, detail="No checkpoint available for resume")
    
    checkpoint = progress_tracker.get_checkpoint(graph_id)
    company_id = checkpoint.get("company_id") if checkpoint else None
    vendors = checkpoint.get("remaining_vendors", []) if checkpoint else []
    
    if not company_id or not vendors:
        raise HTTPException(status_code=400, detail="Invalid checkpoint data")
    
    # Reset cancellation and set status to running
    progress_tracker.reset_cancellation(graph_id)
    progress_tracker.add_step(graph_id, "info", "Resuming discovery from checkpoint...")
    
    # Schedule the resumed discovery to run in background
    asyncio.create_task(_run_ownership_discovery_task(company_id, vendors, graph_id))
    
    return {
        "graph_id": graph_id,
        "status": "running",
        "message": "Ownership discovery resumed from checkpoint."
    }


@router.get("/status/{graph_id}")
async def get_ownership_status(graph_id: str):
    """
    Get the current status of an ownership discovery.
    """
    status = progress_tracker.get_status(graph_id)
    step_info = progress_tracker.get_step_info(graph_id)
    has_checkpoint = progress_tracker.has_checkpoint(graph_id)
    
    return {
        "graph_id": graph_id,
        "status": status or "not_found",
        "current_step": step_info.get("current_step"),
        "total_steps": step_info.get("total_steps"),
        "step_name": step_info.get("step_name"),
        "has_checkpoint": has_checkpoint,
        "is_completed": progress_tracker.is_completed(graph_id)
    }
