"""
Auditor Assistant
AI chatbot for explaining audit findings and answering questions.
"""
from loguru import logger

from core.gemini_client import GeminiClient


class AuditorAssistant:
    """AI-powered auditor assistant chatbot."""
    
    def __init__(self):
        logger.info("[AuditorAssistant.__init__] Initializing auditor assistant")
        self.gemini = GeminiClient()
    
    async def respond(
        self,
        message: str,
        context: dict,
        history: list[dict]
    ) -> dict:
        """Generate response to user message."""
        logger.info(f"[respond] Received message: {message[:50]}...")
        
        # Build context summary
        context_summary = self._build_context_summary(context)
        logger.debug(f"[respond] Context summary length: {len(context_summary)} chars")
        
        # Check if Gemini is available
        if not self.gemini.model:
            logger.warning("[respond] Gemini not available, using fallback response")
            return self._fallback_response(message, context)
        
        # Build conversation history
        history_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in history[-10:]  # Last 10 messages
        ])
        
        prompt = f"""
You are an AI auditor assistant helping explain audit findings and financial analysis.

CONTEXT:
{context_summary}

CONVERSATION HISTORY:
{history_text}

USER QUESTION: {message}

INSTRUCTIONS:
1. Answer the question based on the audit context provided
2. Be specific and cite finding IDs or transaction IDs when relevant
3. Explain in clear, professional language
4. If you don't have enough information, say so
5. Never make up data - only reference what's in the context
6. Keep response concise (2-4 sentences unless more detail is needed)

Respond:
"""
        
        try:
            result = await self.gemini.generate(
                prompt=prompt,
                purpose="chatbot_response"
            )
            
            # Check for quota exceeded
            if result.get("quota_exceeded") or result.get("error"):
                logger.warning(f"[respond] Gemini error/quota exceeded: {result.get('error')}")
                return self._fallback_response(message, context)
            
            response_text = result.get("text", "I apologize, but I'm unable to respond at the moment.")
        except Exception as e:
            logger.error(f"[respond] Exception during Gemini call: {e}")
            return self._fallback_response(message, context)
        
        # Extract citations (simple pattern matching)
        citations = []
        if context.get("audit"):
            findings = context["audit"].get("findings", [])
            for finding in findings:
                finding_id = finding.get("finding_id", "")
                if finding_id and finding_id in response_text:
                    citations.append(finding_id)
        
        logger.info(f"[respond] Generated response with {len(citations)} citations")
        return {
            "message": response_text,
            "citations": citations,
            "confidence": 0.85
        }
    
    def _fallback_response(self, message: str, context: dict) -> dict:
        """Generate a fallback response when Gemini is unavailable."""
        logger.info("[_fallback_response] Generating fallback response")
        
        message_lower = message.lower()
        
        # Check for specific questions about findings
        if context.get("audit"):
            audit = context["audit"]
            findings = audit.get("findings", [])
            risk_score = audit.get("risk_score", {})
            
            if "risk" in message_lower or "score" in message_lower:
                return {
                    "message": f"The current risk score is {risk_score.get('overall_score', 'N/A')}/100, classified as {risk_score.get('risk_level', 'N/A').upper()}. There are {risk_score.get('critical_count', 0)} critical, {risk_score.get('high_count', 0)} high, {risk_score.get('medium_count', 0)} medium, and {risk_score.get('low_count', 0)} low severity findings.",
                    "citations": [],
                    "confidence": 1.0
                }
            
            if "transaction" in message_lower or "flagged" in message_lower or "finding" in message_lower:
                # List the flagged transactions
                transaction_info = []
                for f in findings[:5]:  # Top 5
                    transaction_info.append(f"- [{f.get('severity', 'N/A').upper()}] {f.get('finding_id')}: {f.get('issue')} - Transaction: {f.get('transaction_id', 'N/A')}")
                
                return {
                    "message": f"Here are the top flagged items:\\n" + "\\n".join(transaction_info) + f"\\n\\nTotal findings: {len(findings)}. Check the Findings tab for complete details with transaction IDs and amounts.",
                    "citations": [f.get('finding_id') for f in findings[:5]],
                    "confidence": 1.0
                }
            
            if "critical" in message_lower or "highest" in message_lower or "worst" in message_lower:
                critical = [f for f in findings if f.get('severity') == 'critical']
                if critical:
                    f = critical[0]
                    return {
                        "message": f"The highest severity finding is {f.get('finding_id')}: {f.get('issue')}. Details: {f.get('details', 'N/A')}. This is a CRITICAL severity issue requiring immediate attention.",
                        "citations": [f.get('finding_id')],
                        "confidence": 1.0
                    }
            
            if "aje" in message_lower or "adjust" in message_lower or "journal" in message_lower:
                ajes = audit.get("ajes", [])
                if ajes:
                    return {
                        "message": f"There are {len(ajes)} Adjusting Journal Entries generated. Check the Data > AJEs tab for details.",
                        "citations": [],
                        "confidence": 1.0
                    }
                else:
                    return {
                        "message": "No Adjusting Journal Entries were generated. This may be due to API quota limitations or no correctable issues found.",
                        "citations": [],
                        "confidence": 1.0
                    }
        
        # Generic fallback
        return {
            "message": "I'm currently operating in limited mode (AI quota exceeded). I can answer questions about risk scores, findings counts, and specific transactions. Please check the Findings and Audit Trail tabs for detailed information.",
            "citations": [],
            "confidence": 0.5
        }
    
    def _build_context_summary(self, context: dict) -> str:
        """Build a summary of available context."""
        
        parts = []
        
        if context.get("company"):
            company = context["company"]
            parts.append(f"""
COMPANY: {company.name}
Industry: {company.industry}
Accounting Basis: {company.accounting_basis}
Reporting Period: {company.reporting_period}
""")
        
        if context.get("audit"):
            audit = context["audit"]
            findings = audit.get("findings", [])
            risk_score = audit.get("risk_score", {})
            
            parts.append(f"""
AUDIT SUMMARY:
- Total Findings: {len(findings)}
- Risk Level: {risk_score.get('risk_level', 'N/A')}
- Risk Score: {risk_score.get('overall_score', 'N/A')}/100
- Critical Issues: {risk_score.get('critical_count', 0)}
- High Issues: {risk_score.get('high_count', 0)}
""")
            
            # Add finding summaries
            if findings:
                parts.append("KEY FINDINGS:")
                for f in findings[:5]:  # Top 5 findings
                    parts.append(f"- [{f.get('severity', 'N/A').upper()}] {f.get('finding_id')}: {f.get('issue')}")
        
        return "\n".join(parts) if parts else "No audit context available."
