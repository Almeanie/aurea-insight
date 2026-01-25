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
from loguru import logger

from core.gemini_client import GeminiClient
from core.schemas import OwnershipGraph, EntityNode, OwnershipEdge
from ownership.registries import (
    OpenCorporatesAPI,
    SECEdgarAPI,
    UKCompaniesHouseAPI,
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
        self.opencorporates = OpenCorporatesAPI()
        self.sec_edgar = SECEdgarAPI()
        self.uk_companies_house = UKCompaniesHouseAPI()
        self.gleif = GLEIFAPI()
        
        # Gemini for parsing only
        self.gemini = GeminiClient()
        
        # NetworkX graph for analysis
        self.graph = nx.DiGraph()
        
        # Track data sources for transparency
        self.data_sources = {}
        
        # Track API statuses for reporting
        self.api_status = {
            "opencorporates": {"available": False, "reason": "Requires paid API key"},
            "sec_edgar": {"available": True, "reason": "Free, no key required"},
            "uk_companies_house": {"available": bool(self.uk_companies_house.api_key), "reason": "Key configured" if self.uk_companies_house.api_key else "No API key"},
            "gleif": {"available": self.gleif.enabled, "reason": "Free, no key required" if self.gleif.enabled else "Disabled in config"}
        }
        
        # Track API call stats
        self.api_stats = {
            "opencorporates": {"calls": 0, "success": 0, "errors": 0},
            "sec_edgar": {"calls": 0, "success": 0, "errors": 0},
            "uk_companies_house": {"calls": 0, "success": 0, "errors": 0},
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
        status["opencorporates"] = {
            "configured": bool(self.opencorporates.api_key),
            "note": "Requires paid API subscription" if not self.opencorporates.api_key else "Key configured"
        }
        
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
        
        # Check UK Companies House
        status["uk_companies_house"] = {
            "configured": bool(self.uk_companies_house.api_key),
            "note": "API key configured" if self.uk_companies_house.api_key else "No API key - get one at developer.company-information.service.gov.uk"
        }
        
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
        progress_callback: callable = None
    ) -> dict:
        """
        Discover ownership network starting from seed entities.
        
        Uses REAL APIs in this order:
        1. OpenCorporates (global coverage)
        2. SEC EDGAR (US public companies)
        3. UK Companies House (UK companies with PSC data)
        4. GLEIF (LEI relationships)
        
        Falls back to deterministic mock data only if ALL APIs return nothing.
        
        Args:
            seed_entities: List of company/entity names to search
            depth: How deep to traverse ownership chains (1-3)
            progress_callback: Optional callback for progress updates (msg, pct, data)
            
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
        
        report_progress(f"Starting discovery for {len(seed_entities)} entities", 5.0)
        
        # Check API availability and report
        api_status = await self.check_api_availability()
        available_apis = [name for name, status in api_status.items() if status.get("configured")]
        report_progress(f"APIs available: {', '.join(available_apis) if available_apis else 'None - using mock data'}", 7.0, {"api_status": api_status})
        
        discovered_entities = {}
        entities_to_process = list(seed_entities)
        processed_entities = set()
        current_depth = 0
        total_to_process = len(seed_entities)
        processed_count = 0
        
        while entities_to_process and current_depth < depth:
            current_depth += 1
            next_batch = []
            
            logger.info(f"[discover_ownership_network] Processing depth {current_depth}, {len(entities_to_process)} entities")
            report_progress(f"Depth {current_depth}: Processing {len(entities_to_process)} entities", 10.0 + (current_depth * 30.0))
            
            for idx, entity_name in enumerate(entities_to_process):
                if entity_name in processed_entities:
                    continue
                
                processed_entities.add(entity_name)
                processed_count += 1
                
                # Calculate progress percentage
                depth_progress = 10.0 + ((current_depth - 1) * 30.0)
                entity_progress = (idx + 1) / max(len(entities_to_process), 1) * 25.0
                pct = min(depth_progress + entity_progress, 85.0)
                
                report_progress(
                    f"Searching: {entity_name[:40]}...",
                    pct,
                    {"entity": entity_name, "depth": current_depth, "processed": processed_count}
                )
                
                # Fetch from real APIs
                entity_data = await self._lookup_entity_from_apis(entity_name)
                
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
                    
                    # Queue owners for next depth level
                    for owner in entity_data.get("beneficial_owners", []):
                        owner_name = owner.get("name", "")
                        if owner_name and owner_name not in processed_entities:
                            next_batch.append(owner_name)
                    
                    # Queue parent companies from corporate relationships
                    for parent in entity_data.get("parent_companies", []):
                        parent_name = parent.get("name", "")
                        if parent_name and parent_name not in processed_entities:
                            next_batch.append(parent_name)
            
            entities_to_process = next_batch
        
        # Analyze for fraud patterns
        logger.info("[discover_ownership_network] Analyzing graph for fraud patterns")
        report_progress("Analyzing ownership graph for fraud patterns...", 88.0)
        findings = await self._analyze_fraud_patterns()
        
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
        
        # 1. Try OpenCorporates (best global coverage - requires paid API key)
        if self.opencorporates._has_api_key():
            try:
                self.api_stats["opencorporates"]["calls"] += 1
                oc_results = await self.opencorporates.search_companies(entity_name)
                if oc_results:
                    found = True
                    self.api_stats["opencorporates"]["success"] += 1
                    best_match = oc_results[0]  # Take top result
                    normalized = self.opencorporates.normalize_company_data(best_match)
                    
                    results.update({
                        "company_name": normalized.get("company_name") or entity_name,
                        "jurisdiction": normalized.get("jurisdiction"),
                        "registration_number": normalized.get("registration_number"),
                        "registration_date": normalized.get("registration_date"),
                        "status": normalized.get("status"),
                        "registered_address": normalized.get("registered_address"),
                        "opencorporates_url": normalized.get("opencorporates_url"),
                    })
                    results["red_flags"].extend(normalized.get("red_flags", []))
                    results["api_sources"].append("opencorporates")
                    
                    # Get officers if we have jurisdiction and company number
                    jcode = normalized.get("jurisdiction_code")
                    company_num = normalized.get("registration_number")
                    if jcode and company_num:
                        officers = await self.opencorporates.get_officers(jcode, company_num)
                        owners, directors = self.opencorporates.normalize_officer_data(officers)
                        results["beneficial_owners"].extend(owners)
                        results["directors"].extend(directors)
                    
                    self.data_sources[entity_name] = "opencorporates"
                    logger.info(f"[_lookup_entity_from_apis] Found in OpenCorporates: {entity_name}")
            except Exception as e:
                self.api_stats["opencorporates"]["errors"] += 1
                logger.warning(f"[_lookup_entity_from_apis] OpenCorporates error for {entity_name}: {e}")
        
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
                    
                    # Get more details
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
                        })
                        results["api_sources"].append("sec_edgar")
                        self.data_sources[entity_name] = "sec_edgar"
                        logger.info(f"[_lookup_entity_from_apis] Found in SEC EDGAR: {entity_name}")
                else:
                    logger.debug(f"[_lookup_entity_from_apis] SEC EDGAR: No match for '{entity_name}'")
            except Exception as e:
                self.api_stats["sec_edgar"]["errors"] += 1
                logger.warning(f"[_lookup_entity_from_apis] SEC EDGAR error for {entity_name}: {e}")
        
        # 3. Try UK Companies House (UK companies with PSC - requires free API key)
        if self.uk_companies_house.api_key:
            try:
                self.api_stats["uk_companies_house"]["calls"] += 1
                uk_results = await self.uk_companies_house.search_companies(entity_name)
                if uk_results:
                    self.api_stats["uk_companies_house"]["success"] += 1
                    best_match = uk_results[0]
                    company_number = best_match.get("company_number", "")
                    
                    if company_number:
                        # Get detailed company info
                        company_detail = await self.uk_companies_house.get_company(company_number)
                        if company_detail:
                            found = True
                            normalized = self.uk_companies_house.normalize_company_data(company_detail)
                            
                            # Update only if we don't have this data yet
                            if not results.get("jurisdiction"):
                                results.update({
                                    "jurisdiction": normalized.get("jurisdiction"),
                                    "registration_number": normalized.get("registration_number"),
                                    "registration_date": normalized.get("registration_date"),
                                    "status": normalized.get("status"),
                                    "registered_address": normalized.get("registered_address"),
                                })
                            
                            results["api_sources"].append("uk_companies_house")
                            
                            # Get PSC (Persons with Significant Control) - the gold standard for beneficial ownership
                            pscs = await self.uk_companies_house.get_persons_with_significant_control(company_number)
                            if pscs:
                                normalized_pscs = self.uk_companies_house.normalize_psc_data(pscs)
                                results["beneficial_owners"].extend(normalized_pscs)
                                logger.info(f"[_lookup_entity_from_apis] Found {len(pscs)} PSC records in UK Companies House")
                            
                            # Get officers
                            officers = await self.uk_companies_house.get_officers(company_number)
                            for officer in officers:
                                results["directors"].append({
                                    "name": officer.get("name", "Unknown"),
                                    "role": officer.get("officer_role", "Director"),
                                    "appointed_on": officer.get("appointed_on", ""),
                                    "api_source": "uk_companies_house"
                                })
                            
                            self.data_sources[entity_name] = "uk_companies_house"
                            logger.info(f"[_lookup_entity_from_apis] Found in UK Companies House: {entity_name}")
                else:
                    logger.debug(f"[_lookup_entity_from_apis] UK Companies House: No match for '{entity_name}'")
            except Exception as e:
                self.api_stats["uk_companies_house"]["errors"] += 1
                logger.warning(f"[_lookup_entity_from_apis] UK Companies House error for {entity_name}: {e}")
        
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
                    
                    # Add LEI data
                    if normalized.get("lei"):
                        found = True
                        results["lei"] = normalized.get("lei")
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
                        
                        logger.info(f"[_lookup_entity_from_apis] Found in GLEIF: {entity_name} (LEI: {lei})")
                else:
                    logger.debug(f"[_lookup_entity_from_apis] GLEIF: No match for '{entity_name}'")
            except Exception as e:
                self.api_stats["gleif"]["errors"] += 1
                logger.warning(f"[_lookup_entity_from_apis] GLEIF error for {entity_name}: {e}")
        
        # If nothing found from real APIs, use deterministic mock data for demo
        if not found:
            logger.info(f"[_lookup_entity_from_apis] No API results, using mock data for: {entity_name}")
            mock_data = self._generate_deterministic_mock(entity_name)
            mock_data["api_sources"] = ["mock_demo"]
            self.data_sources[entity_name] = "mock_demo"
            return mock_data
        
        # Use Gemini to classify and enrich the data (NOT generate)
        if results["api_sources"]:
            results = await self._gemini_classify_entity(results)
        
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
            # Build a classification prompt
            prompt = f"""
You are analyzing REAL company registry data (NOT generating fake data).
Your task is to CLASSIFY and ENRICH this data, not invent new information.

REAL API DATA:
{self._format_for_gemini(entity_data)}

Based on this REAL data, provide:
1. Entity classification (public_company, private_company, shell_company_risk, holding_company, etc.)
2. Risk assessment based on ACTUAL data (jurisdiction, missing info, patterns)
3. Normalized beneficial ownership structure
4. Any red flags visible in the ACTUAL data

IMPORTANT: Only analyze what's in the data. Do NOT invent owners, directors, or other information.

Return JSON:
{{
    "entity_classification": "private_company|public_company|holding_company|shell_risk|unknown",
    "risk_level": "low|medium|high|critical",
    "risk_factors": ["List of ACTUAL risk factors from the data"],
    "ownership_structure_type": "simple|complex|layered|circular_risk",
    "data_quality_score": 0.0 to 1.0,
    "notes": "Any observations about the REAL data"
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
    
    def _generate_deterministic_mock(self, entity_name: str) -> dict:
        """
        Generate deterministic synthetic entity data for DEMO purposes.
        Used ONLY when all real APIs return nothing.
        
        Args:
            entity_name: Entity name
            
        Returns:
            Mock entity data (clearly labeled as mock)
        """
        import hashlib
        
        # Use hash of name to generate consistent but varied data
        name_hash = int(hashlib.md5(entity_name.encode()).hexdigest()[:8], 16)
        
        jurisdictions = [
            ("Delaware, USA", "us_de"),
            ("Nevada, USA", "us_nv"),
            ("California, USA", "us_ca"),
            ("New York, USA", "us_ny"),
            ("United Kingdom", "gb"),
            ("Cayman Islands", "ky"),
            ("British Virgin Islands", "vg"),
            ("Ireland", "ie"),
            ("Luxembourg", "lu"),
        ]
        
        first_names = ["John", "Jane", "Michael", "Sarah", "Robert", "Emily", "David", "Lisa"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Wilson"]
        
        jurisdiction, jcode = jurisdictions[name_hash % len(jurisdictions)]
        
        # Generate owners
        num_owners = (name_hash % 3) + 1
        owners = []
        for i in range(num_owners):
            owner_first = first_names[(name_hash + i) % len(first_names)]
            owner_last = last_names[(name_hash + i + 3) % len(last_names)]
            owners.append({
                "name": f"{owner_first} {owner_last}",
                "ownership_percentage": round(100.0 / num_owners, 1),
                "type": "individual",
                "api_source": "mock_demo"
            })
        
        # Generate director
        director_first = first_names[(name_hash + 5) % len(first_names)]
        director_last = last_names[(name_hash + 7) % len(last_names)]
        
        # Add red flags for certain jurisdictions
        red_flags = ["DEMO DATA - Not from real registry"]
        if jcode in ["ky", "vg", "lu"]:
            red_flags.append("Secrecy jurisdiction")
        if (name_hash % 5) == 0:
            red_flags.append("Recently incorporated")
        
        return {
            "company_name": entity_name,
            "jurisdiction": jurisdiction,
            "jurisdiction_code": jcode,
            "registration_number": f"MOCK-{name_hash % 1000000:06d}",
            "registration_date": f"20{(name_hash % 10) + 15}-{(name_hash % 12) + 1:02d}-{(name_hash % 28) + 1:02d}",
            "status": "active",
            "registered_address": f"{name_hash % 999 + 1} Demo Street, {jurisdiction}",
            "beneficial_owners": owners,
            "directors": [
                {
                    "name": f"{director_first} {director_last}",
                    "role": "Director",
                    "api_source": "mock_demo"
                }
            ],
            "parent_companies": [],
            "red_flags": red_flags,
            "is_mock_data": True
        }
    
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
            is_mock=entity_data.get("is_mock_data", False),
            is_boilerplate=is_boilerplate
        )
        
        # Add beneficial owners
        for owner in entity_data.get("beneficial_owners", []):
            owner_name = owner.get("name", "Unknown")
            owner_type = owner.get("type", "unknown")
            
            self.graph.add_node(
                owner_name,
                type=owner_type,
                api_source=owner.get("api_source", "unknown")
            )
            self.graph.add_edge(
                owner_name,
                company_name,
                relationship="owns",
                percentage=owner.get("ownership_percentage")
            )
        
        # Add directors
        for director in entity_data.get("directors", []):
            director_name = director.get("name", "Unknown")
            
            # Don't duplicate if already added as owner
            if not self.graph.has_node(director_name):
                self.graph.add_node(
                    director_name,
                    type="individual",
                    api_source=director.get("api_source", "unknown")
                )
            
            self.graph.add_edge(
                director_name,
                company_name,
                relationship="directs",
                role=director.get("role", "Director")
            )
        
        # Add parent companies
        for parent in entity_data.get("parent_companies", []):
            parent_name = parent.get("name", "Unknown Parent")
            
            self.graph.add_node(
                parent_name,
                type="company",
                api_source=parent.get("api_source", "unknown")
            )
            self.graph.add_edge(
                parent_name,
                company_name,
                relationship="owns",
                relationship_type=parent.get("relationship_type", "parent")
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
                        "is_mock": data.get("is_mock", False)
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
                if k not in ["mock_demo", "boilerplate_detection"]
            ),
            "total_mock": len(sources.get("mock_demo", [])),
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
