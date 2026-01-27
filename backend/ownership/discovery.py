"""
Beneficial Ownership Discovery

ARCHITECTURE PRINCIPLE: Real APIs fetch data, Gemini only parses/classifies.

Flow:
1. Search public registries (OpenCorporates, SEC EDGAR, UK Companies House, GLEIF)
2. Use Gemini to parse complex API responses and classify entities
3. Build ownership graph from parsed data
4. Analyze graph for fraud patterns with Gemini assistance

Gemini is NEVER used to generate fake ownership data.
"""
import networkx as nx
from typing import Optional
import uuid
import asyncio
from datetime import datetime
from loguru import logger

from core.gemini_client import GeminiClient
from core.schemas import OwnershipGraph, EntityNode, OwnershipEdge
from ownership.registries import (

    SECEdgarAPI,
    GLEIFAPI

)


# Secrecy jurisdictions (tax havens) for risk flagging
SECRECY_JURISDICTIONS = [
    "British Virgin Islands", "Cayman Islands", "Panama",
    "Seychelles", "Belize", "Nevis", "Jersey", "Guernsey",
    "Isle of Man", "Liechtenstein", "Luxembourg", "Monaco",
    "Delaware", "Nevada", "Wyoming",  # US states with secrecy
    "ky", "vg", "pa", "sc", "bz", "je", "gg", "im", "li", "lu", "mc",  # Codes
    "us_de", "us_nv", "us_wy"  # US state codes
]

# Boilerplate/placeholder company names commonly used in templates and examples
# These should be flagged but not undergo full API discovery
BOILERPLATE_COMPANY_PATTERNS = [
    # Classic placeholder names
    "acme", "example", "test company", "demo company", "sample company",
    "your company", "mycompany", "abc company", "xyz company", "foo", "bar",
    "lorem ipsum", "placeholder", "template", "dummy", "mock", "fake",
    # Common tutorial/example names
    "widget", "widgets inc", "widgets corp", "contoso", "fabrikam", "northwind",
    "adventure works", "tailspin toys", "fourth coffee", "wingtip toys",
    # Generic placeholder patterns
    "company a", "company b", "company c", "company x", "company y", "company z",
    "vendor a", "vendor b", "vendor c", "client a", "client b", "client c",
    "test vendor", "test client", "test supplier", "sample vendor",
    # Obvious placeholders
    "xxx", "tbd", "n/a", "none", "null", "undefined", "unknown vendor",
    "misc", "miscellaneous", "other", "various", "sundry",
    # Tutorial/course examples
    "doe enterprises", "john doe inc", "jane doe llc", "smith corp",
]


def is_boilerplate_company(name: str) -> bool:
    """
    Check if a company name appears to be a boilerplate/placeholder example.
    
    Args:
        name: Company name to check
        
    Returns:
        True if the name matches boilerplate patterns
    """
    if not name:
        return False
    
    name_lower = name.lower().strip()
    
    # Check direct pattern matches
    for pattern in BOILERPLATE_COMPANY_PATTERNS:
        if pattern in name_lower:
            return True
    
    # Check for generic patterns like "Company 123" or "Vendor #1"
    import re
    generic_patterns = [
        r'^company\s*[0-9#]+$',
        r'^vendor\s*[0-9#]+$',
        r'^client\s*[0-9#]+$',
        r'^supplier\s*[0-9#]+$',
        r'^test\s*[0-9#]+$',
        r'^sample\s*[0-9#]+$',
        r'^example\s*[0-9#]+$',
    ]
    
    for pattern in generic_patterns:
        if re.match(pattern, name_lower):
            return True
    
    return False


class BeneficialOwnershipDiscovery:
    """
    Discovers beneficial ownership networks from PUBLIC REGISTRIES.
    Uses Gemini for parsing and classification, NOT data generation.
    """
    
    def __init__(self):
        logger.info("[BeneficialOwnershipDiscovery] Initializing with real API clients")
        
        # Initialize real API clients

        self.sec_edgar = SECEdgarAPI()

        self.gleif = GLEIFAPI()
        
        # Gemini for parsing only
        self.gemini = GeminiClient()
        
        # NetworkX graph for analysis
        self.graph = nx.DiGraph()
        
        # Track data sources for transparency
        self.data_sources = {}
        
        # Track API statuses for reporting
        self.api_status = {

            "sec_edgar": {"available": True, "reason": "Free, no key required"},
            "gleif": {"available": self.gleif.enabled, "reason": "Free, no key required" if self.gleif.enabled else "Disabled in config"}
        }
        
        # Track API call stats
        self.api_stats = {

            "sec_edgar": {"calls": 0, "success": 0, "errors": 0},
            "gleif": {"calls": 0, "success": 0, "errors": 0}
        }
    
    async def check_api_availability(self) -> dict:
        """
        Check which APIs are available and responding.
        Useful for debugging why discovery returns null.
        
        Returns:
            Dict with status of each API
        """
        status = {}
        
        # Check OpenCorporates

        
        # Check SEC EDGAR - try loading tickers
        try:
            await self.sec_edgar._load_tickers()
            has_tickers = SECEdgarAPI._tickers_cache is not None
            status["sec_edgar"] = {
                "configured": True,
                "working": has_tickers,
                "note": f"Loaded {len(SECEdgarAPI._tickers_cache) if has_tickers else 0} tickers" if has_tickers else "Could not load tickers"
            }
        except Exception as e:
            status["sec_edgar"] = {"configured": True, "working": False, "note": f"Error: {str(e)[:50]}"}
        

        
        # Check GLEIF
        status["gleif"] = {
            "configured": self.gleif.enabled,
            "note": "Free API, enabled" if self.gleif.enabled else "Disabled in config"
        }
        
        logger.info(f"[check_api_availability] API Status: {status}")
        return status
    
    async def discover_ownership_network(
        self,
        seed_entities: list[str],
        depth: int = 2,
        progress_callback: callable = None,
        data_callback: callable = None,
        is_cancelled: callable = None,
        save_checkpoint: callable = None,
        on_quota_exceeded: callable = None
    ) -> dict:
        """
        Discover ownership network starting from seed entities.
        
        Uses REAL APIs ONLY in this order:

        2. SEC EDGAR (US public companies)
        3. GLEIF (LEI relationships)
        4. Gemini Web Search (Fallback)
        
        If no API returns data, the entity is marked as "unknown" and filtered out.
        
        Args:
            seed_entities: List of company/entity names to search
            depth: How deep to traverse ownership chains (1-3)
            progress_callback: Optional callback for progress updates (msg, pct, data)
            data_callback: Optional callback for streaming graph data (type, data)
            is_cancelled: Optional callback to check if discovery should stop
            save_checkpoint: Optional callback to save checkpoint (processed, remaining)
            on_quota_exceeded: Optional callback when API quota is exceeded
            
        Returns:
            Discovery results with graph, findings, and data source info
        """
        logger.info(f"[discover_ownership_network] Starting discovery for {len(seed_entities)} entities, depth={depth}")
        
        def report_progress(msg: str, pct: float, data: dict = None):
            if progress_callback:
                try:
                    progress_callback(msg, pct, data)
                except Exception:
                    pass
        
        def stream_data(data_type: str, data: dict):
            """Stream graph data to frontend in real-time."""
            if data_callback:
                try:
                    data_callback(data_type, data)
                except Exception:
                    pass
        
        def check_cancelled() -> bool:
            """Check if discovery has been cancelled."""
            if is_cancelled:
                return is_cancelled()
            return False
        
        def checkpoint(processed: list, remaining: list):
            """Save a checkpoint."""
            if save_checkpoint:
                try:
                    save_checkpoint(processed, remaining)
                except Exception:
                    pass
        
        report_progress(f"Starting discovery for {len(seed_entities)} entities", 5.0)
        
        # Check API availability and report
        api_status = await self.check_api_availability()
        available_apis = [name for name, status in api_status.items() if status.get("configured")]
        report_progress(f"APIs available: {', '.join(available_apis) if available_apis else 'None configured'}", 7.0, {"api_status": api_status})
        
        discovered_entities = {}
        entities_to_process = list(seed_entities)
        processed_entities = set()
        current_depth = 0
        total_to_process = len(seed_entities)
        processed_count = 0
        
        semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
        
        async def process_entity(entity_name: str) -> list[str]:
            """Process a single entity and return found related entities."""
            async with semaphore:
                if entity_name in processed_entities:
                    return []
                
                processed_entities.add(entity_name)
                # processed_count is simple counter, might be slightly off in progress reporting due to concurrency
                # but acceptable for UI feedback.
                nonlocal processed_count
                processed_count += 1
                
                # Calculate progress (approximate)
                depth_progress = 10.0 + ((current_depth - 1) * 30.0)
                # Use processed_count for progress
                entity_progress = (processed_count / max(total_to_process, 1)) * 25.0
                pct = min(depth_progress + entity_progress, 85.0)
                
                report_progress(
                    f"Searching: {entity_name[:40]}...",
                    pct,
                    {"entity": entity_name, "depth": current_depth, "processed": processed_count}
                )
                
                # Fetch from real APIs
                entity_data = await self._lookup_entity_from_apis(entity_name)
                
                new_related_entities = []
                
                if entity_data:
                    discovered_entities[entity_name] = entity_data
                    self._add_to_graph(entity_data)
                    
                    # Report what was found
                    source = entity_data.get("api_sources", ["unknown"])[0] if entity_data.get("api_sources") else "unknown"
                    is_boilerplate = entity_data.get("is_boilerplate", False)
                    if is_boilerplate:
                        report_progress(f"Boilerplate detected: {entity_name}", pct, {"type": "boilerplate"})
                    else:
                        report_progress(f"Found: {entity_name} (via {source})", pct, {"source": source})
                    
                    # Stream the node to frontend with full entity data
                    node_data = {
                        "id": entity_data.get("entity_id", entity_name),
                        "name": entity_data.get("name", entity_name) or entity_data.get("company_name", entity_name),
                        "type": entity_data.get("entity_type", "company"),
                        "jurisdiction": entity_data.get("jurisdiction"),
                        "is_boilerplate": is_boilerplate,
                        "api_source": source,
                        "api_sources": entity_data.get("api_sources", []),
                        "red_flags": entity_data.get("red_flags", []),
                        # Registrar data
                        "registration_number": entity_data.get("registration_number"),
                        "registration_date": entity_data.get("registration_date"),
                        "status": entity_data.get("status"),
                        "registered_address": entity_data.get("registered_address"),
                        # Ownership data
                        "beneficial_owners": entity_data.get("beneficial_owners", []),
                        "directors": entity_data.get("directors", []),
                        "parent_companies": entity_data.get("parent_companies", []),
                        # Financial identifiers
                        "lei": entity_data.get("lei"),
                        "ticker": entity_data.get("ticker"),
                        # AI classification
                        "gemini_classification": entity_data.get("gemini_classification"),
                        "gemini_risk_level": entity_data.get("gemini_risk_level"),
                        "data_quality_score": entity_data.get("data_quality_score"),
                    }
                    stream_data("node", node_data)
                    
                    # Stream edges for beneficial owners
                    for owner in entity_data.get("beneficial_owners", []):
                        if isinstance(owner, str):
                            owner_name = owner
                            owner_pct = None
                        else:
                            owner_name = owner.get("name", "")
                            owner_pct = owner.get("percentage")

                        if owner_name and owner_name not in processed_entities:
                            # Stream stub node
                            stub_node = {
                                "id": owner_name,
                                "name": owner_name,
                                "type": "individual",
                                "is_stub": True,
                            }
                            stream_data("node", stub_node)
                            
                            edge_data = {
                                "source": owner_name,
                                "target": entity_name,
                                "relationship": "beneficial_owner",
                                "percentage": owner_pct,
                            }
                            stream_data("edge", edge_data)
                            new_related_entities.append(owner_name)
                        elif owner_name:
                            edge_data = {
                                "source": owner_name,
                                "target": entity_name,
                                "relationship": "beneficial_owner",
                                "percentage": owner_pct,
                            }
                            stream_data("edge", edge_data)
                    
                    # Stream edges for parent companies
                    for parent in entity_data.get("parent_companies", []):
                        if isinstance(parent, str):
                            parent_name = parent
                            parent_pct = None
                        else:
                            parent_name = parent.get("name", "")
                            parent_pct = parent.get("ownership_percentage")

                        if parent_name and parent_name not in processed_entities:
                            # Stream stub node
                            stub_node = {
                                "id": parent_name,
                                "name": parent_name,
                                "type": "company",
                                "is_stub": True,
                            }
                            stream_data("node", stub_node)
                            
                            edge_data = {
                                "source": parent_name,
                                "target": entity_name,
                                "relationship": "parent_company",
                                "percentage": parent_pct,
                            }
                            stream_data("edge", edge_data)
                            new_related_entities.append(parent_name)
                        elif parent_name:
                            edge_data = {
                                "source": parent_name,
                                "target": entity_name,
                                "relationship": "parent_company",
                                "percentage": parent_pct,
                            }
                            stream_data("edge", edge_data)
                
                return new_related_entities

        while entities_to_process and current_depth < depth:
            current_depth += 1
            
            logger.info(f"[discover_ownership_network] Processing depth {current_depth}, {len(entities_to_process)} entities")
            report_progress(f"Depth {current_depth}: Processing {len(entities_to_process)} entities", 10.0 + (current_depth * 30.0))
            
            # Prepare tasks
            tasks = []
            unique_batch = []
            
            # Filter duplicates in current batch before creating tasks
            for entity_name in entities_to_process:
                if entity_name not in processed_entities and entity_name not in unique_batch:
                    unique_batch.append(entity_name)
                    tasks.append(process_entity(entity_name))
            
            if not tasks:
                break
                
            # Run concurrently
            results = await asyncio.gather(*tasks)
            
            # Collect next batch
            next_batch = []
            for res in results:
                next_batch.extend(res)
            
            entities_to_process = next_batch

        
        # Analyze for fraud patterns
        logger.info("[discover_ownership_network] Analyzing graph for fraud patterns")
        report_progress("Analyzing ownership graph for fraud patterns...", 88.0)
        findings = await self._analyze_fraud_patterns()
        
        # Stream findings to frontend
        for finding in findings:
            stream_data("finding", finding)
            
            # If this is a circular ownership finding, stream the circular edges
            if finding.get("issue") == "Circular Ownership Structure":
                cycle = finding.get("entities", [])
                if len(cycle) >= 2:
                    # Stream each edge in the cycle as circular
                    for i in range(len(cycle)):
                        source = cycle[i]
                        target = cycle[(i + 1) % len(cycle)]
                        circular_edge = {
                            "source": source,
                            "target": target,
                            "relationship": "circular",
                            "is_circular": True,
                        }
                        stream_data("circular_edge", circular_edge)
        
        # Build response graph
        graph = self._build_graph_response()
        
        # Compile data source summary
        source_summary = self._compile_source_summary()
        
        logger.info(f"[discover_ownership_network] Complete. Found {len(discovered_entities)} entities, {len(findings)} findings")
        report_progress(f"Discovery complete: {len(discovered_entities)} entities, {len(findings)} findings", 100.0)
        
        return {
            "entities_discovered": len(discovered_entities),
            "graph": graph,
            "findings": findings,
            "data_sources": source_summary,
            "entities": discovered_entities
        }
    
    async def _lookup_entity_from_apis(self, entity_name: str) -> dict | None:
        """
        Look up entity from REAL public registries.
        Tries multiple APIs and merges results.
        
        Args:
            entity_name: Name of entity to look up
            
        Returns:
            Merged entity data or None if not found anywhere
        """
        logger.debug(f"[_lookup_entity_from_apis] Searching for: {entity_name}")
        
        # Check for boilerplate/placeholder company names - skip full discovery
        if is_boilerplate_company(entity_name):
            logger.info(f"[_lookup_entity_from_apis] BOILERPLATE detected: '{entity_name}' - skipping API discovery")
            return {
                "company_name": entity_name,
                "jurisdiction": None,
                "status": "boilerplate_example",
                "registration_number": None,
                "beneficial_owners": [],
                "directors": [],
                "parent_companies": [],
                "red_flags": ["BOILERPLATE/PLACEHOLDER - This appears to be a template or example company name"],
                "api_sources": ["boilerplate_detection"],
                "is_boilerplate": True,
                "gemini_classification": "boilerplate_example",
                "gemini_risk_level": "info",
                "data_quality_score": 0.0,
                "notes": "Detected as boilerplate/placeholder company name. No API lookup performed."
            }
        
        results = {
            "company_name": entity_name,
            "beneficial_owners": [],
            "directors": [],
            "parent_companies": [],
            "red_flags": [],
            "api_sources": []
        }
        
        found = False
        

        
        # 2. Try SEC EDGAR (US public companies - free, no key required)
        if not found:
            try:
                self.api_stats["sec_edgar"]["calls"] += 1
                sec_results = await self.sec_edgar.search_companies(entity_name)
                if sec_results:
                    found = True
                    self.api_stats["sec_edgar"]["success"] += 1
                    best_match = sec_results[0]
                    cik = best_match.get("cik", "")
                    
                    # Get more details from submissions
                    submissions = await self.sec_edgar.get_company_submissions(cik)
                    if submissions:
                        results.update({
                            "company_name": submissions.get("name") or entity_name,
                            "jurisdiction": f"US-{submissions.get('state', 'Unknown')}",
                            "registration_number": cik,
                            "status": "active",  # SEC listed = active
                            "ticker": best_match.get("ticker"),
                            "sic_code": submissions.get("sic"),
                            "sic_description": submissions.get("sic_description"),
                            "business_address": submissions.get("business_address"),
                        })
                        
                        # Fetch beneficial ownership filings for Gemini enrichment
                        ownership_filings = await self.sec_edgar.get_beneficial_ownership_filings(cik)
                        if ownership_filings:
                            results["sec_ownership_filings"] = ownership_filings
                            logger.info(f"[_lookup_entity_from_apis] Found {len(ownership_filings)} ownership filings for {entity_name}")
                        
                        # Get insider transaction count
                        insider_txns = await self.sec_edgar.get_insider_transactions(cik)
                        if insider_txns:
                            results["insider_transaction_count"] = len(insider_txns)
                        
                        results["api_sources"].append("sec_edgar")
                        self.data_sources[entity_name] = "sec_edgar"
                        logger.info(f"[_lookup_entity_from_apis] Found in SEC EDGAR: {entity_name}")
                else:
                    logger.debug(f"[_lookup_entity_from_apis] SEC EDGAR: No match for '{entity_name}'")
            except Exception as e:
                self.api_stats["sec_edgar"]["errors"] += 1
                logger.warning(f"[_lookup_entity_from_apis] SEC EDGAR error for {entity_name}: {e}")
        

        
        # 4. Try GLEIF (LEI relationships - free, no key required)
        if self.gleif.enabled:
            try:
                self.api_stats["gleif"]["calls"] += 1
                gleif_results = await self.gleif.search_entities(entity_name)
                if gleif_results:
                    self.api_stats["gleif"]["success"] += 1
                    best_match = gleif_results[0]
                    lei = best_match.get("id", "")
                    
                    normalized = self.gleif.normalize_entity_data(best_match)
                    
                    # Add all GLEIF data (not just LEI!)
                    if normalized.get("lei"):
                        found = True
                        # Merge all normalized GLEIF fields (only if not already set)
                        results["lei"] = normalized.get("lei")
                        if not results.get("jurisdiction") and normalized.get("jurisdiction"):
                            results["jurisdiction"] = normalized.get("jurisdiction")
                        if not results.get("status") and normalized.get("status"):
                            results["status"] = normalized.get("status")
                        if not results.get("registration_date") and normalized.get("registration_date"):
                            results["registration_date"] = normalized.get("registration_date")
                        if not results.get("registered_address") and normalized.get("registered_address"):
                            results["registered_address"] = normalized.get("registered_address")
                        if not results.get("legal_form") and normalized.get("legal_form"):
                            results["legal_form"] = normalized.get("legal_form")
                        if not results.get("entity_category") and normalized.get("entity_category"):
                            results["entity_category"] = normalized.get("entity_category")
                        if not results.get("headquarters_country") and normalized.get("headquarters_country"):
                            results["headquarters_country"] = normalized.get("headquarters_country")
                        
                        results["api_sources"].append("gleif")
                        
                        # Get parent relationships - key for beneficial ownership
                        parents = await self.gleif.get_parent_relationships(lei)
                        for parent_rel in parents:
                            parent_data = parent_rel.get("parent", {})
                            if parent_data:
                                normalized_parent = self.gleif.normalize_parent_data(
                                    parent_data, 
                                    parent_rel.get("type", "parent")
                                )
                                results["parent_companies"].append(normalized_parent)
                        
                        logger.info(f"[_lookup_entity_from_apis] Found in GLEIF: {entity_name} (LEI: {lei}, jurisdiction: {normalized.get('jurisdiction')}, status: {normalized.get('status')})")
                else:
                    logger.debug(f"[_lookup_entity_from_apis] GLEIF: No match for '{entity_name}'")
            except Exception as e:
                self.api_stats["gleif"]["errors"] += 1
                logger.warning(f"[_lookup_entity_from_apis] GLEIF error for {entity_name}: {e}")
        
        # If nothing found from real APIs, try Gemini Web Search as fallback
        if not found:
            logger.info(f"[_lookup_entity_from_apis] No API results for {entity_name} - attempting Gemini Web Search fallback")
            
            try:
                search_results = await self.gemini.search(
                    query=f"Beneficial ownership and company registration details for {entity_name}",
                    purpose="entity_discovery_fallback"
                )
                
                if search_results.get("text"):
                    # Use Gemini to parse the search text into our schema
                    prompt = f"""
                    Extract company details from this search result text:
                    {search_results['text']}
                    
                    Return JSON matching this schema:
                    {{
                        "company_name": "{entity_name}",
                        "jurisdiction": "Country or State",
                        "status": "Active/Inactive/Unknown",
                        "registration_number": "number or null",
                        "beneficial_owners": [
                            {{"name": "Owner Name", "percentage": 25.0, "type": "individual/company"}}
                        ],
                        "directors": [],
                        "parent_companies": [],
                        "red_flags": ["Any controversy or risk mentioned"],
                        "notes": "Source of info"
                    }}
                    """
                    
                    parsed = await self.gemini.generate_json(prompt, purpose="parse_search_results")
                    if parsed.get("parsed"):
                        extracted = parsed["parsed"]
                        # Defensive check: ensure extracted is a dict
                        if isinstance(extracted, dict):
                            results.update(extracted)
                            results["api_sources"].append("gemini_web_search")
                            results["is_boilerplate"] = False
                            
                            # Verify we actually got something useful
                            if extracted.get("jurisdiction") or extracted.get("beneficial_owners"):
                                found = True
                                logger.info(f"[_lookup_entity_from_apis] Found via Web Search: {entity_name}")
                        else:
                            logger.warning(f"[_lookup_entity_from_apis] Web search parse result is not a dict: {type(extracted)}")
                    else:
                        logger.warning(f"[_lookup_entity_from_apis] Web search parse failed: {parsed.get('error')}")
            except Exception as e:
                logger.warning(f"[_lookup_entity_from_apis] Web search fallback failed: {e}")

        if not found:
            logger.info(f"[_lookup_entity_from_apis] No API or Search results for: {entity_name} - marking as unknown")
            # Return minimal data with unknown source - frontend will filter this out
            return {
                "company_name": entity_name,
                "jurisdiction": None,
                "status": None,
                "registration_number": None,
                "beneficial_owners": [],
                "directors": [],
                "parent_companies": [],
                "red_flags": ["No data found in any official registry or web search"],
                "api_sources": ["unknown"],  # Frontend will filter this out
                "is_boilerplate": False
            }
        
        # Use Gemini to classify and enrich the data (NOT generate)
        if results["api_sources"]:
            results = await self._gemini_classify_entity(results)
            # Auto-enrich missing data using web search to resolve red flags
            results = await self._enrich_missing_data(results)
        
        return results
    
    async def _gemini_classify_entity(self, entity_data: dict) -> dict:
        """
        Use Gemini to CLASSIFY and ENRICH entity data (NOT generate).
        
        This analyzes real API data to:
        - Classify entity type more precisely
        - Identify risk indicators from the data
        - Parse complex ownership structures
        - Normalize inconsistent data formats
        
        Args:
            entity_data: Real data from APIs
            
        Returns:
            Enriched entity data (returns original data if classification fails)
        """
        if not self.gemini.model and not self.gemini.client:
            logger.debug("[_gemini_classify_entity] Gemini not configured, skipping classification")
            return entity_data
        
        try:
            # Build a classification and enrichment prompt
            api_data = self._format_for_gemini(entity_data)
            
            # Include SEC filings summary if available
            sec_filings_info = ""
            if entity_data.get("sec_ownership_filings"):
                filings = entity_data["sec_ownership_filings"]
                filings_summary = ", ".join([f"{f['form_type']} ({f.get('filing_date', 'N/A')})" for f in filings[:3]])
                sec_filings_info = f"""
SEC OWNERSHIP FILINGS AVAILABLE:
{filings_summary}
These filings contain beneficial ownership information that can be used to understand the ownership structure.
Insider transaction count: {entity_data.get('insider_transaction_count', 0)}
"""
            
            prompt = f"""
You are analyzing REAL company registry data from official sources.
Your task is to:
1. CLASSIFY this entity based on the available data
2. ENRICH missing fields using logical inference from the documentation
3. Flag any data quality issues

REAL API DATA:
{api_data}
{sec_filings_info}

Based on this REAL data, provide:
1. Entity classification (public_company, private_company, shell_company_risk, holding_company, etc.)
2. Risk assessment based on ACTUAL data (jurisdiction, missing info, patterns)
3. If data is missing, note what COULD be found by examining the SEC filings
4. Any red flags visible in the ACTUAL data

Today's Date: {datetime.now().strftime('%Y-%m-%d')}
(Use this date to determine if a date is in the past or future)

ENRICHMENT RULES:
- If SEC filings are listed, the company is a public company
- If there are insider transactions, ownership is likely institutional/public
- SIC codes indicate the industry sector
- Business addresses can reveal geographic operations
- Missing beneficial owner data in public companies suggests widely-held stock

Return JSON:
{{
    "entity_classification": "private_company|public_company|holding_company|shell_risk|unknown",
    "risk_level": "low|medium|high|critical",
    "risk_factors": ["List of ACTUAL risk factors from the data"],
    "ownership_structure_type": "simple|complex|layered|circular_risk|publicly_traded",
    "data_quality_score": 0.0 to 1.0,
    "inferred_company_type": "If public company with SEC filings, specify: 'Publicly traded, beneficial ownership via SEC Form 4/13D filings'",
    "industry_sector": "Infer from SIC code if available",
    "notes": "Any observations about the REAL data and what additional info could be obtained"
}}
"""
            
            result = await self.gemini.generate_json(
                prompt=prompt,
                purpose="entity_classification"
            )
            
            # Check for errors in the result
            if result.get("error"):
                logger.warning(f"[_gemini_classify_entity] Gemini returned error: {result.get('error')}")
                # Continue without classification - don't crash
                entity_data["gemini_classification"] = "unknown"
                entity_data["gemini_error"] = str(result.get("error"))[:100]
                return entity_data
            
            if result.get("parsed"):
                classification = result["parsed"]
                
                # Defensive check: ensure classification is a dict
                if not isinstance(classification, dict):
                    logger.warning(f"[_gemini_classify_entity] Classification result is not a dict: {type(classification)}")
                    entity_data["gemini_classification"] = "unknown"
                    if isinstance(classification, str):
                        entity_data["gemini_error"] = f"Invalid format: {classification[:50]}"
                    return entity_data
                
                # Merge classification into entity data
                entity_data["gemini_classification"] = classification.get("entity_classification", "unknown")
                entity_data["gemini_risk_level"] = classification.get("risk_level", "medium")
                
                # Add risk factors to red flags
                new_flags = classification.get("risk_factors", [])
                existing_flags = entity_data.get("red_flags", [])
                entity_data["red_flags"] = list(set(existing_flags + new_flags))
                
                entity_data["data_quality_score"] = classification.get("data_quality_score", 0.5)
                
                logger.debug(f"[_gemini_classify_entity] Classified as: {classification.get('entity_classification')}")
            else:
                logger.warning("[_gemini_classify_entity] No parsed result from Gemini")
                entity_data["gemini_classification"] = "unknown"
            
        except Exception as e:
            logger.warning(f"[_gemini_classify_entity] Classification failed with exception: {e}")
            # Don't crash - just skip classification
            entity_data["gemini_classification"] = "error"
            entity_data["gemini_error"] = str(e)[:100]
        
        return entity_data
    
    async def _enrich_missing_data(self, entity_data: dict) -> dict:
        """
        Use Gemini web search to fill missing data and resolve red flags.
        
        This method attempts to resolve resolvable red flags by:
        1. Identifying what data is missing from the red flag text
        2. Using Gemini web search to find the missing information
        3. Parsing the search results to extract structured data
        4. Updating entity data and removing resolved flags
        
        Args:
            entity_data: Entity data with potential red flags
            
        Returns:
            Enriched entity data with resolved flags removed
        """
        red_flags = entity_data.get("red_flags", [])
        if not red_flags:
            return entity_data
        
        company_name = entity_data.get("company_name", "Unknown")
        is_public = entity_data.get("gemini_classification") == "public_company"
        
        resolved_flags = []
        enrichment_notes = []
        
        for flag in red_flags:
            flag_lower = flag.lower()
            
            # Skip flags that are expected for public companies
            if is_public and "beneficial owner" in flag_lower:
                # Rephrase to be informational, not a warning
                if "expected for public" not in flag_lower:
                    # Update the flag text to be clearer
                    idx = red_flags.index(flag)
                    red_flags[idx] = "Missing explicit beneficial owner list in registry data (expected for public entities)"
                continue
            
            # Incomplete jurisdiction - try to find full jurisdiction
            if "incomplete jurisdiction" in flag_lower or "jurisdiction code" in flag_lower:
                try:
                    search_result = await self.gemini.search(
                        f"{company_name} company headquarters country location registered",
                        purpose="enrich_jurisdiction"
                    )
                    if search_result.get("text"):
                        # Parse jurisdiction from search result
                        parse_result = await self.gemini.generate_json(
                            prompt=f"""Extract the country/jurisdiction from this search result about {company_name}.
                            
Search result:
{search_result['text'][:2000]}

Return JSON: {{"jurisdiction": "Full country name or state/country", "confidence": 0.0-1.0}}
""",
                            purpose="parse_jurisdiction"
                        )
                        if parse_result.get("parsed") and parse_result["parsed"].get("jurisdiction"):
                            entity_data["jurisdiction"] = parse_result["parsed"]["jurisdiction"]
                            resolved_flags.append(flag)
                            enrichment_notes.append(f"Jurisdiction updated to: {parse_result['parsed']['jurisdiction']}")
                            logger.info(f"[_enrich_missing_data] Resolved jurisdiction for {company_name}")
                except Exception as e:
                    logger.warning(f"[_enrich_missing_data] Failed to enrich jurisdiction: {e}")
            
            # Missing director data - try to find directors
            elif "missing director" in flag_lower and not is_public:
                try:
                    search_result = await self.gemini.search(
                        f"{company_name} company directors officers executives leadership team",
                        purpose="enrich_directors"
                    )
                    if search_result.get("text"):
                        parse_result = await self.gemini.generate_json(
                            prompt=f"""Extract director/officer names from this search result about {company_name}.
                            
Search result:
{search_result['text'][:2000]}

Return JSON: {{"directors": [{{"name": "Full Name", "role": "Title/Role"}}], "confidence": 0.0-1.0}}
Only include people who are clearly identified as directors, executives, or officers.
""",
                            purpose="parse_directors"
                        )
                        if parse_result.get("parsed") and parse_result["parsed"].get("directors"):
                            directors = parse_result["parsed"]["directors"]
                            if directors:
                                existing = entity_data.get("directors", [])
                                # Add new directors with web_search source
                                for d in directors:
                                    if isinstance(d, dict):
                                        d["api_source"] = "gemini_web_search"
                                entity_data["directors"] = existing + directors
                                resolved_flags.append(flag)
                                enrichment_notes.append(f"Found {len(directors)} directors via web search")
                                logger.info(f"[_enrich_missing_data] Found {len(directors)} directors for {company_name}")
                except Exception as e:
                    logger.warning(f"[_enrich_missing_data] Failed to enrich directors: {e}")
            
            # Missing beneficial owner data (for private companies only)
            elif "beneficial owner" in flag_lower and not is_public:
                try:
                    search_result = await self.gemini.search(
                        f"{company_name} company owner ownership shareholders investors founders",
                        purpose="enrich_owners"
                    )
                    if search_result.get("text"):
                        parse_result = await self.gemini.generate_json(
                            prompt=f"""Extract owner/shareholder information from this search result about {company_name}.
                            
Search result:
{search_result['text'][:2000]}

Return JSON: {{"beneficial_owners": [{{"name": "Name", "type": "individual|company", "ownership_percentage": null or number}}], "confidence": 0.0-1.0}}
Only include clearly identified owners, shareholders, or major investors.
""",
                            purpose="parse_owners"
                        )
                        if parse_result.get("parsed") and parse_result["parsed"].get("beneficial_owners"):
                            owners = parse_result["parsed"]["beneficial_owners"]
                            if owners:
                                existing = entity_data.get("beneficial_owners", [])
                                for o in owners:
                                    if isinstance(o, dict):
                                        o["api_source"] = "gemini_web_search"
                                entity_data["beneficial_owners"] = existing + owners
                                resolved_flags.append(flag)
                                enrichment_notes.append(f"Found {len(owners)} owners via web search")
                                logger.info(f"[_enrich_missing_data] Found {len(owners)} owners for {company_name}")
                except Exception as e:
                    logger.warning(f"[_enrich_missing_data] Failed to enrich owners: {e}")
        
        # Remove resolved flags
        entity_data["red_flags"] = [f for f in red_flags if f not in resolved_flags]
        
        # Add enrichment notes
        if enrichment_notes:
            entity_data["enrichment_notes"] = enrichment_notes
            entity_data["enriched_via_web_search"] = True
        
        return entity_data
    
    def _format_for_gemini(self, data: dict) -> str:
        """Format entity data for Gemini prompt."""
        import json
        # Remove any circular references and limit size
        safe_data = {
            "company_name": data.get("company_name"),
            "jurisdiction": data.get("jurisdiction"),
            "status": data.get("status"),
            "registration_number": data.get("registration_number"),
            "beneficial_owners": data.get("beneficial_owners", [])[:5],  # Limit
            "directors": data.get("directors", [])[:5],
            "red_flags": data.get("red_flags", []),
            "api_sources": data.get("api_sources", [])
        }
        return json.dumps(safe_data, indent=2, default=str)
    
    def _add_to_graph(self, entity_data: dict):
        """Add entity and relationships to the network graph."""
        
        company_name = entity_data.get("company_name", "Unknown")
        is_boilerplate = entity_data.get("is_boilerplate", False)
        
        # Add company node
        self.graph.add_node(
            company_name,
            type="boilerplate" if is_boilerplate else "company",
            jurisdiction=entity_data.get("jurisdiction"),
            status=entity_data.get("status"),
            address=entity_data.get("registered_address"),
            red_flags=entity_data.get("red_flags", []),
            api_sources=entity_data.get("api_sources", []),
            is_unknown=entity_data.get("api_sources", ["unknown"])[0] == "unknown",
            is_boilerplate=is_boilerplate
        )
        
        # Add beneficial owners
        for owner in entity_data.get("beneficial_owners", []):
            if isinstance(owner, str):
                owner_name = owner
                owner_type = "unknown"
                owner_pct = None
                api_source = "unknown"
            else:
                owner_name = owner.get("name", "Unknown")
                owner_type = owner.get("type", "unknown")
                owner_pct = owner.get("ownership_percentage")
                api_source = owner.get("api_source", "unknown")
            
            self.graph.add_node(
                owner_name,
                type=owner_type,
                api_source=api_source
            )
            self.graph.add_edge(
                owner_name,
                company_name,
                relationship="owns",
                percentage=owner_pct
            )
        
        # Add directors
        for director in entity_data.get("directors", []):
            if isinstance(director, str):
                director_name = director
                director_role = "Director"
                api_source = "unknown"
            else:
                director_name = director.get("name", "Unknown")
                director_role = director.get("role", "Director")
                api_source = director.get("api_source", "unknown")
            
            # Don't duplicate if already added as owner
            if not self.graph.has_node(director_name):
                self.graph.add_node(
                    director_name,
                    type="individual",
                    api_source=api_source
                )
            
            self.graph.add_edge(
                director_name,
                company_name,
                relationship="directs",
                role=director_role
            )
        
        # Add parent companies
        for parent in entity_data.get("parent_companies", []):
            if isinstance(parent, str):
                parent_name = parent
                parent_type = "company"
                parent_rel_type = "parent"
                api_source = "unknown"
            else:
                parent_name = parent.get("name", "Unknown Parent")
                parent_type = "company"
                parent_rel_type = parent.get("relationship_type", "parent")
                api_source = parent.get("api_source", "unknown")
            
            self.graph.add_node(
                parent_name,
                type=parent_type,
                api_source=api_source
            )
            self.graph.add_edge(
                parent_name,
                company_name,
                relationship="owns",
                relationship_type=parent_rel_type
            )
    
    async def _analyze_fraud_patterns(self) -> list[dict]:
        """
        Analyze the graph for fraud indicators.
        Uses algorithmic analysis enhanced by Gemini interpretation.
        """
        findings = []
        
        # 1. Circular ownership detection (algorithmic)
        findings.extend(self._detect_circular_ownership())
        
        # 2. Common controllers (algorithmic)
        findings.extend(self._detect_common_controllers())
        
        # 3. Secrecy jurisdictions (algorithmic)
        findings.extend(self._detect_secrecy_jurisdictions())
        
        # 4. Use Gemini to analyze overall pattern (classification only)
        if self.gemini.model and len(self.graph.nodes()) > 2:
            gemini_findings = await self._gemini_pattern_analysis()
            findings.extend(gemini_findings)
        
        return findings
    
    async def _gemini_pattern_analysis(self) -> list[dict]:
        """
        Use Gemini to analyze the ownership graph for complex patterns.
        This CLASSIFIES patterns in real data, doesn't generate fake findings.
        """
        findings = []
        
        try:
            # Build graph summary for Gemini
            graph_summary = {
                "total_nodes": self.graph.number_of_nodes(),
                "total_edges": self.graph.number_of_edges(),
                "companies": [],
                "individuals": [],
                "relationships": []
            }
            
            for node, data in self.graph.nodes(data=True):
                if data.get("type") == "company":
                    graph_summary["companies"].append({
                        "name": node,
                        "jurisdiction": data.get("jurisdiction"),
                        "red_flags": data.get("red_flags", []),
                        "api_sources": data.get("api_sources", [])
                    })
                else:
                    graph_summary["individuals"].append(node)
            
            for source, target, data in self.graph.edges(data=True):
                graph_summary["relationships"].append({
                    "from": source,
                    "to": target,
                    "type": data.get("relationship"),
                    "percentage": data.get("percentage")
                })
            
            prompt = f"""
Analyze this REAL ownership network for fraud risk patterns.
Your job is to IDENTIFY patterns, not invent problems.

OWNERSHIP NETWORK DATA:
{self._format_for_gemini(graph_summary)}

Analyze for these REAL patterns:
1. Layered structures that obscure ownership
2. Cross-jurisdictional complexity (especially tax havens)
3. Nominee or shell company indicators
4. Related party transaction risks
5. Unusual ownership structures

IMPORTANT: Only report patterns you can SEE in the data. Do NOT invent findings.

If the network is simple and clean, say so.

Return JSON:
{{
    "patterns_detected": [
        {{
            "pattern_type": "layered_structure|cross_jurisdictional|shell_indicators|related_party_risk|unusual_structure",
            "severity": "low|medium|high|critical",
            "description": "What you observed in the ACTUAL data",
            "entities_involved": ["List of entity names"],
            "recommendation": "Audit recommendation"
        }}
    ],
    "overall_risk_assessment": "low|medium|high|critical",
    "network_complexity": "simple|moderate|complex|highly_complex"
}}
"""
            
            result = await self.gemini.generate_json(
                prompt=prompt,
                purpose="fraud_pattern_analysis"
            )
            
            if result.get("parsed"):
                analysis = result["parsed"]
                
                for pattern in analysis.get("patterns_detected", []):
                    findings.append({
                        "finding_id": f"PAT-{uuid.uuid4().hex[:8]}",
                        "issue": pattern.get("pattern_type", "Unknown Pattern").replace("_", " ").title(),
                        "severity": pattern.get("severity", "medium"),
                        "details": pattern.get("description", ""),
                        "entities": pattern.get("entities_involved", []),
                        "recommendation": pattern.get("recommendation", "Investigate further"),
                        "source": "gemini_analysis"
                    })
                
        except Exception as e:
            logger.warning(f"[_gemini_pattern_analysis] Analysis failed: {e}")
        
        return findings
    
    def _detect_circular_ownership(self) -> list[dict]:
        """Find circular ownership structures."""
        findings = []
        
        try:
            cycles = list(nx.simple_cycles(self.graph))
            
            for cycle in cycles:
                if len(cycle) >= 3:
                    findings.append({
                        "finding_id": f"CIR-{uuid.uuid4().hex[:8]}",
                        "issue": "Circular Ownership Structure",
                        "severity": "critical",
                        "entities": cycle,
                        "details": f"Circular ownership detected: {' -> '.join(cycle)} -> {cycle[0]}",
                        "recommendation": "Investigate business purpose of this structure",
                        "source": "algorithmic"
                    })
        except Exception:
            pass
        
        return findings
    
    def _detect_common_controllers(self) -> list[dict]:
        """Find individuals controlling multiple entities."""
        findings = []
        
        individuals = [
            n for n, d in self.graph.nodes(data=True)
            if d.get("type") == "individual"
        ]
        
        for person in individuals:
            controlled = list(self.graph.successors(person))
            if len(controlled) >= 2:
                findings.append({
                    "finding_id": f"CTL-{uuid.uuid4().hex[:8]}",
                    "issue": "Common Controller",
                    "severity": "high",
                    "controller": person,
                    "controlled_entities": controlled,
                    "details": f"'{person}' controls {len(controlled)} entities",
                    "recommendation": "Verify transactions between controlled entities",
                    "source": "algorithmic"
                })
        
        return findings
    
    def _detect_secrecy_jurisdictions(self) -> list[dict]:
        """Flag entities in secrecy jurisdictions."""
        findings = []
        secrecy_entities = []
        
        for node, data in self.graph.nodes(data=True):
            jurisdiction = str(data.get("jurisdiction", "")).lower()
            if any(sj.lower() in jurisdiction for sj in SECRECY_JURISDICTIONS):
                secrecy_entities.append({
                    "entity": node,
                    "jurisdiction": data.get("jurisdiction")
                })
        
        if secrecy_entities:
            findings.append({
                "finding_id": f"SEC-{uuid.uuid4().hex[:8]}",
                "issue": "Secrecy Jurisdiction Entities",
                "severity": "high",
                "entities": secrecy_entities,
                "details": f"{len(secrecy_entities)} entities in secrecy jurisdictions",
                "recommendation": "Request additional beneficial ownership documentation",
                "source": "algorithmic"
            })
        
        return findings
    
    def _build_graph_response(self) -> OwnershipGraph:
        """Build graph response for frontend."""
        
        nodes = []
        edges = []
        
        for node, data in self.graph.nodes(data=True):
            node_type = data.get("type", "unknown")
            # Normalize type for schema validation
            if node_type not in ["company", "individual", "unknown", "boilerplate"]:
                node_type = "unknown"
            
            nodes.append(EntityNode(
                id=node,
                name=node,
                type=node_type,
                jurisdiction=data.get("jurisdiction"),
                status=data.get("status"),
                address=data.get("address"),
                red_flags=data.get("red_flags", []),
                is_boilerplate=data.get("is_boilerplate", False)
            ))
        
        for source, target, data in self.graph.edges(data=True):
            edges.append(OwnershipEdge(
                source=source,
                target=target,
                relationship=data.get("relationship", "related"),
                percentage=data.get("percentage")
            ))
        
        return OwnershipGraph(
            nodes=nodes,
            edges=edges,
            statistics={
                "total_entities": len(nodes),
                "total_relationships": len(edges),
                "companies": sum(1 for n in nodes if n.type == "company"),
                "individuals": sum(1 for n in nodes if n.type == "individual"),
                "data_sources": list(set(self.data_sources.values()))
            }
        )
    
    def _compile_source_summary(self) -> dict:
        """Compile summary of data sources used and API performance."""
        sources = {}
        for entity, source in self.data_sources.items():
            if source not in sources:
                sources[source] = []
            sources[source].append(entity)
        
        return {
            "sources_used": list(sources.keys()),
            "entities_by_source": {k: len(v) for k, v in sources.items()},
            "total_from_real_apis": sum(
                len(v) for k, v in sources.items() 
                if k not in ["unknown", "boilerplate_detection"]
            ),
            "total_unknown": len(sources.get("unknown", [])),
            "total_boilerplate": len(sources.get("boilerplate_detection", [])),
            "api_stats": self.api_stats,
            "api_status": self.api_status,
            "notes": self._get_api_notes()
        }
    
    def _get_api_notes(self) -> list[str]:
        """Get helpful notes about API availability."""
        notes = []
        
        if not self.opencorporates._has_api_key():
            notes.append("OpenCorporates: Requires paid API subscription (global company data)")
        
        if not self.uk_companies_house.api_key:
            notes.append("UK Companies House: Free key required from developer.company-information.service.gov.uk")
        elif self.api_stats["uk_companies_house"]["calls"] > 0 and self.api_stats["uk_companies_house"]["success"] == 0:
            notes.append("UK Companies House: Key may not be activated yet (can take 24 hours)")
        
        if self.api_stats["sec_edgar"]["calls"] > 0 and self.api_stats["sec_edgar"]["success"] == 0:
            notes.append("SEC EDGAR: No US public companies matched the search queries")
        
        if self.api_stats["gleif"]["calls"] > 0 and self.api_stats["gleif"]["success"] == 0:
            notes.append("GLEIF: No LEI records found (LEIs are primarily for large financial entities)")
        
        return notes
