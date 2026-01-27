"""
Gemini API Client with Audit Trail Integration
Uses the new google-genai package (replaces deprecated google-generativeai)
Supports both Google AI Studio and Vertex AI
Includes rate limiting and retry logic
"""
import asyncio
import time
from typing import Optional, Any
from datetime import datetime
import hashlib
import json
from loguru import logger

from config import settings


class RateLimiter:
    """Simple rate limiter with exponential backoff."""
    
    def __init__(self, requests_per_minute: int = 15, max_retries: int = 3):
        self.requests_per_minute = requests_per_minute
        self.max_retries = max_retries
        self.request_times: list[float] = []
        self.backoff_until: float = 0
        self.consecutive_failures = 0
    
    async def wait_if_needed(self):
        """Wait if rate limit is exceeded or in backoff period."""
        now = time.time()
        
        # Check if in backoff period
        if now < self.backoff_until:
            wait_time = self.backoff_until - now
            logger.warning(f"[RateLimiter] In backoff period, waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
            now = time.time()
        
        # Clean old requests (older than 1 minute)
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # Check if at limit
        if len(self.request_times) >= self.requests_per_minute:
            oldest = min(self.request_times)
            wait_time = 60 - (now - oldest) + 1  # Add 1s buffer
            if wait_time > 0:
                logger.info(f"[RateLimiter] Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        
        self.request_times.append(time.time())
    
    def record_failure(self):
        """Record a failure and calculate backoff."""
        self.consecutive_failures += 1
        # Exponential backoff: 5s, 10s, 20s, 40s, etc.
        backoff_seconds = min(5 * (2 ** (self.consecutive_failures - 1)), 120)
        self.backoff_until = time.time() + backoff_seconds
        logger.warning(f"[RateLimiter] Failure #{self.consecutive_failures}, backing off for {backoff_seconds}s")
        return backoff_seconds
    
    def record_success(self):
        """Record a success and reset failure counter."""
        self.consecutive_failures = 0


class GeminiClient:
    """
    Wrapper for Gemini API with built-in audit trail logging.
    All prompts and responses are logged for regulatory compliance.
    Uses the new google-genai package.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        logger.info("[GeminiClient.__init__] Initializing Gemini client")
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self.model = None
        self.client = None
        self.client_type = None
        self.rate_limiter = RateLimiter(
            requests_per_minute=settings.GEMINI_REQUESTS_PER_MINUTE,
            max_retries=settings.GEMINI_MAX_RETRIES
        )
        
        if not self.api_key:
            logger.warning("[GeminiClient.__init__] Gemini API key not configured. AI features will be limited.")
        else:
            self._initialize_client()
        
        self.interaction_log: list[dict] = []
    
    def _initialize_client(self):
        """Initialize the Gemini client using the new google-genai package."""
        
        # Try using the new google-genai package first
        try:
            from google import genai
            from google.genai import types
            
            logger.info(f"[GeminiClient] Using google-genai package with model: {self.model_name}")
            
            # Create client with API key
            self.client = genai.Client(api_key=self.api_key)
            self.client_type = "google_genai"
            self.genai_types = types
            
            # Set the model name
            self.model = self.model_name
            
            logger.info("[GeminiClient] google-genai client initialized successfully")
            return
            
        except ImportError:
            logger.warning("[GeminiClient] google-genai not installed, trying legacy package")
        except Exception as e:
            logger.warning(f"[GeminiClient] google-genai init failed: {e}")
        
        # Fallback to legacy google-generativeai package
        try:
            import google.generativeai as genai
            
            logger.info(f"[GeminiClient] Using legacy google-generativeai with model: {self.model_name}")
            
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            self.genai = genai
            self.client_type = "legacy_genai"
            
            logger.info("[GeminiClient] Legacy genai initialized successfully")
            return
            
        except ImportError:
            logger.error("[GeminiClient] No Gemini package installed. Run: pip install google-genai")
        except Exception as e:
            logger.error(f"[GeminiClient] Legacy genai init failed: {e}")
        
        self.model = None
        logger.error("[GeminiClient] Failed to initialize any Gemini client")
    
    async def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        purpose: str = "general"
    ) -> dict:
        """
        Generate content with full audit trail and rate limiting.
        
        Args:
            prompt: The prompt to send to Gemini
            context: Additional context to prepend
            temperature: Creativity level (0-1)
            max_tokens: Maximum response tokens
            purpose: Description of why this call is being made
            
        Returns:
            Dict with response text, metadata, and audit info
        """
        logger.info(f"[generate] Starting generation for purpose: {purpose}")
        
        if not self.model and not self.client:
            logger.warning("[generate] Model not configured, returning error")
            return {
                "text": None,
                "error": "Gemini API not configured",
                "audit": self._create_audit_entry(prompt, None, purpose, error="API not configured")
            }
        
        # Build full prompt
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        logger.debug(f"[generate] Prompt length: {len(full_prompt)} chars")
        
        # Create audit entry before call
        timestamp = datetime.utcnow()
        prompt_hash = hashlib.sha256(full_prompt.encode()).hexdigest()
        
        # Retry loop with rate limiting
        last_error = None
        for attempt in range(self.rate_limiter.max_retries + 1):
            try:
                # Wait for rate limit
                await self.rate_limiter.wait_if_needed()
                
                # Make API call
                logger.info(f"[generate] Calling Gemini API (attempt {attempt + 1}/{self.rate_limiter.max_retries + 1})")
                
                # Log the prompt being sent (truncated for readability)
                logger.debug(f"[generate] PROMPT PREVIEW (first 500 chars):\n{full_prompt[:500]}...")
                
                if self.client_type == "google_genai":
                    # New google-genai package
                    response = await asyncio.to_thread(
                        self._generate_with_new_client,
                        full_prompt,
                        temperature,
                        max_tokens
                    )
                else:
                    # Legacy google-generativeai package
                    response = await self._generate_with_legacy_client(
                        full_prompt,
                        temperature,
                        max_tokens
                    )
                
                response_text = response
                
                # Handle None or empty response
                if response_text is None:
                    raise ValueError("Gemini returned None response (empty or blocked)")
                
                if not response_text.strip():
                    raise ValueError("Gemini returned empty response")
                
                response_hash = hashlib.sha256(response_text.encode()).hexdigest()
                
                logger.info(f"[generate] Received response: {len(response_text)} chars")
                
                # Log the response (truncated for readability)
                logger.debug(f"[generate] RESPONSE PREVIEW (first 800 chars):\n{response_text[:800]}...")
                
                # Record success
                self.rate_limiter.record_success()
                
                # Create audit entry
                audit_entry = self._create_audit_entry(
                    prompt=full_prompt,
                    response=response_text,
                    purpose=purpose,
                    prompt_hash=prompt_hash,
                    response_hash=response_hash,
                    timestamp=timestamp
                )
                
                self.interaction_log.append(audit_entry)
                
                return {
                    "text": response_text,
                    "error": None,
                    "audit": audit_entry
                }
                
            except Exception as e:
                error_str = str(e)
                last_error = error_str
                
                # Detect retryable errors (quota, rate limit, overload, etc.)
                is_retryable_error = any(phrase in error_str.lower() for phrase in [
                    "quota", "rate limit", "resource exhausted", "429", 
                    "too many requests", "exceeded", "limit", "quota_exceeded",
                    "503", "unavailable", "overloaded", "overload", "service unavailable",
                    "500", "internal server error", "temporarily"
                ])
                
                if is_retryable_error:
                    logger.warning("=" * 60)
                    logger.warning(f"[GEMINI RETRYABLE ERROR] Attempt {attempt + 1}")
                    logger.warning(f"Error: {error_str}")
                    logger.warning("=" * 60)
                    
                    # Record failure and get backoff time
                    backoff_time = self.rate_limiter.record_failure()
                    
                    if attempt < self.rate_limiter.max_retries:
                        logger.info(f"[generate] Waiting {backoff_time}s before retry...")
                        await asyncio.sleep(backoff_time)
                        continue
                    else:
                        logger.error("[generate] Max retries exceeded")
                else:
                    logger.error(f"[generate] Gemini API error (non-retryable): {e}")
                    logger.exception(e)
                    break  # Don't retry non-retryable errors
        
        # All retries failed
        error_message = f"API Error after retries: {last_error}"
        is_retryable = any(phrase in (last_error or "").lower() for phrase in [
            "quota", "rate", "overload", "unavailable", "503", "500"
        ])
        
        audit_entry = self._create_audit_entry(
            prompt=full_prompt,
            response=None,
            purpose=purpose,
            error=error_message,
            timestamp=timestamp
        )
        self.interaction_log.append(audit_entry)
        
        return {
            "text": None,
            "error": error_message,
            "quota_exceeded": is_retryable,
            "retryable": is_retryable,
            "audit": audit_entry
        }
    
    def _generate_with_new_client(self, prompt: str, temperature: float, max_tokens: int) -> str:
        """Generate using the new google-genai client."""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self.genai_types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
        )
        
        # Handle blocked or empty responses
        if response.text is None:
            # Check if response was blocked
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    logger.warning(f"[_generate_with_new_client] Response blocked, reason: {candidate.finish_reason}")
            raise ValueError("Response text is None - content may be blocked or model overloaded")
        
        return response.text
    
    async def _generate_with_legacy_client(self, prompt: str, temperature: float, max_tokens: int) -> str:
        """Generate using the legacy google-generativeai client."""
        generation_config = self.genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        response = await self.model.generate_content_async(
            prompt,
            generation_config=generation_config
        )
        return response.text
    
    async def generate_json(
        self,
        prompt: str,
        context: Optional[str] = None,
        purpose: str = "json_generation"
    ) -> dict:
        """
        Generate JSON response from Gemini.
        Automatically parses the response as JSON.
        """
        # Add JSON instruction to prompt
        json_prompt = f"""{prompt}

IMPORTANT: Return ONLY valid JSON. No markdown, no explanation, just the JSON object."""
        
        result = await self.generate(
            prompt=json_prompt,
            context=context,
            temperature=0.3,  # Lower temperature for structured output
            purpose=purpose
        )
        
        if result["error"]:
            return result
        
        try:
            # Try to parse JSON from response
            text = result["text"]
            
            # Handle markdown code blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            parsed = json.loads(text.strip())
            
            # CRITICAL FIX: Ensure parsed result is a dictionary (or list)
            # Gemini sometimes returns a string literal if it fails to generate an object
            if not isinstance(parsed, (dict, list)):
                logger.warning(f"[generate_json] Parsed JSON is not a dict/list (got {type(parsed)}): {parsed}")
                # If it's a string, it might be the content we want, but we promised a structured object
                # For safety, we treat this as a parse failure unless the caller can handle it
                # But since callers expect .get(), we must return None for "parsed" or ensure it's a dict
                result["error"] = f"Gemini returned unstructured data: {type(parsed).__name__}"
                result["parsed"] = None
            else:
                result["parsed"] = parsed
            
        except json.JSONDecodeError as e:
            result["error"] = f"JSON parse error: {e}"
            result["parsed"] = None
        
        return result
    
    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        context: Optional[str] = None,
        purpose: str = "code_generation"
    ) -> dict:
        """
        Generate code with validation focus.
        Returns code that should be deterministic and safe.
        """
        code_prompt = f"""You are generating {language} code for a financial audit system.

REQUIREMENTS:
1. Code must be deterministic (same input = same output)
2. Use only standard library functions
3. No file I/O, network calls, or system commands
4. Include docstring explaining the GAAP/regulatory basis
5. Handle edge cases gracefully

{prompt}

Return ONLY the code, no explanation."""
        
        result = await self.generate(
            prompt=code_prompt,
            context=context,
            temperature=0.2,  # Very low temperature for code
            purpose=purpose
        )
        
        if result["text"]:
            # Extract code from markdown if present
            text = result["text"]
            if f"```{language}" in text:
                text = text.split(f"```{language}")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            result["code"] = text.strip()
        
        return result
    
    def _create_audit_entry(
        self,
        prompt: str,
        response: Optional[str],
        purpose: str,
        prompt_hash: Optional[str] = None,
        response_hash: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        error: Optional[str] = None
    ) -> dict:
        """Create a complete audit entry for regulatory compliance."""
        return {
            "timestamp": (timestamp or datetime.utcnow()).isoformat(),
            "purpose": purpose,
            "prompt_length": len(prompt),
            "prompt_hash": prompt_hash or hashlib.sha256(prompt.encode()).hexdigest(),
            "prompt_preview": prompt[:500] + "..." if len(prompt) > 500 else prompt,
            "prompt_full": prompt,  # Full prompt for regulatory review
            "response_length": len(response) if response else 0,
            "response_hash": response_hash,
            "response_preview": (response[:500] + "..." if len(response) > 500 else response) if response else None,
            "response_full": response,  # Full response for regulatory review
            "error": error,
            "model": self.model_name
        }
    
    def get_interaction_log(self) -> list[dict]:
        """Get the full interaction log for audit trail."""
        return self.interaction_log
    
    def clear_interaction_log(self):
        """Clear the interaction log (use with caution)."""
        self.interaction_log = []

    async def search(
        self,
        query: str,
        purpose: str = "web_search"
    ) -> dict:
        """
        Perform a web search using Gemini's Google Search grounding.
        
        Args:
            query: The search query
            purpose: Audit trail purpose
            
        Returns:
            Dict with text (answer) and sources
        """
        logger.info(f"[search] Performing web search for: {query}")
        
        if not self.model and not self.client:
            return {"text": None, "error": "Gemini API not configured"}
            
        prompt = f"Please search the web for information about:\n{query}\n\nProvide a comprehensive summary of what you find, focusing on business details, ownership, key personnel, and any controversy or red flags."
        
        # Create audit entry
        timestamp = datetime.utcnow()
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        
        try:
            # Wait for rate limit
            await self.rate_limiter.wait_if_needed()
            
            response_text = ""
            grounding_metadata = None
            
            if self.client_type == "google_genai":
                # New client with search tool
                tool = self.genai_types.Tool(google_search=self.genai_types.GoogleSearch())
                
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=prompt,
                    config=self.genai_types.GenerateContentConfig(
                        temperature=0.3,
                        tools=[tool]
                    )
                )
                
                response_text = response.text
                if hasattr(response, 'candidates') and response.candidates:
                    c = response.candidates[0]
                    if hasattr(c, 'grounding_metadata'):
                        grounding_metadata = c.grounding_metadata
                        
            else:
                # Legacy client
                # Note: Tools support in legacy vs new package differs, 
                # for now simplified to normal generation if tools not easily available
                # but ideally we use the new client which is preferred.
                
                # Try simple generation first for legacy as full tool support is complex to inject dynamically
                # or requires re-instantiation of model with tools.
                # Assuming new client is primary.
                response_text = await self._generate_with_legacy_client(prompt, 0.3, 2048)
            
            self.rate_limiter.record_success()
            
            audit_entry = self._create_audit_entry(
                prompt=prompt,
                response=response_text,
                purpose=purpose,
                prompt_hash=prompt_hash,
                timestamp=timestamp
            )
            self.interaction_log.append(audit_entry)
            
            return {
                "text": response_text,
                "grounding_metadata": grounding_metadata,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"[search] Error: {e}")
            return {"text": None, "error": str(e)}
