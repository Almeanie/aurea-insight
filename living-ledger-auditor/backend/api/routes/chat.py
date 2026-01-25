"""
Chat API Routes
Handles the Auditor Assistant chatbot.
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from loguru import logger

from core.schemas import ChatRequest, ChatResponse

router = APIRouter()

# Chat history storage
chat_sessions: dict[str, list[dict]] = {}


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the Auditor Assistant.
    The assistant has context about the audit findings, company data, and can explain reasoning.
    """
    logger.info(f"[chat] Received message: {request.message[:50]}...")
    logger.info(f"[chat] Company ID: {request.company_id}, Audit ID: {request.audit_id}")
    
    from chatbot.assistant import AuditorAssistant
    
    assistant = AuditorAssistant()
    
    # Build context from audit data if available
    context = {}
    if request.company_id:
        from api.routes.company import companies
        if request.company_id in companies:
            context["company"] = companies[request.company_id]["metadata"]
    
    if request.audit_id:
        from api.routes.audit import audit_results
        if request.audit_id in audit_results:
            context["audit"] = audit_results[request.audit_id]
    
    # Get session history
    session_id = f"{request.company_id or 'general'}_{request.audit_id or 'none'}"
    history = chat_sessions.get(session_id, [])
    
    # Generate response
    response = await assistant.respond(
        message=request.message,
        context=context,
        history=history
    )
    
    # Update session history
    history.append({"role": "user", "content": request.message})
    history.append({"role": "assistant", "content": response["message"]})
    chat_sessions[session_id] = history[-20:]  # Keep last 20 messages
    
    return ChatResponse(
        message=response["message"],
        citations=response.get("citations", []),
        confidence=response.get("confidence", 0.8)
    )


@router.delete("/session/{company_id}")
async def clear_session(company_id: str, audit_id: Optional[str] = None):
    """Clear chat history for a session."""
    session_id = f"{company_id}_{audit_id or 'none'}"
    if session_id in chat_sessions:
        del chat_sessions[session_id]
    return {"status": "cleared"}
