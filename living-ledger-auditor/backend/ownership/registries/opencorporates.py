"""
OpenCorporates API Wrapper
For accessing public company registry data worldwide.
API Documentation: https://api.opencorporates.com/documentation
"""
import httpx
from typing import Optional
from loguru import logger

from config import settings


# Jurisdiction codes mapping for common countries
JURISDICTION_CODES = {
    # USA
    "delaware": "us_de",
    "california": "us_ca",
    "new york": "us_ny",
    "texas": "us_tx",
    "nevada": "us_nv",
    "wyoming": "us_wy",
    "florida": "us_fl",
    # UK & Crown Dependencies
    "united kingdom": "gb",
    "uk": "gb",
    "england": "gb",
    "jersey": "je",
    "guernsey": "gg",
    "isle of man": "im",
    # Tax Havens
    "cayman islands": "ky",
    "british virgin islands": "vg",
    "bvi": "vg",
    "bermuda": "bm",
    "panama": "pa",
    "seychelles": "sc",
    "mauritius": "mu",
    "luxembourg": "lu",
    "liechtenstein": "li",
    "monaco": "mc",
    # Major Economies
    "ireland": "ie",
    "netherlands": "nl",
    "germany": "de",
    "france": "fr",
    "switzerland": "ch",
    "singapore": "sg",
    "hong kong": "hk",
    "australia": "au",
    "canada": "ca",
}


class OpenCorporatesAPI:
    """
    Wrapper for OpenCorporates API.
    API key is REQUIRED for all requests.
    Get a free API key at: https://opencorporates.com/api_accounts/new
    """
    
    BASE_URL = "https://api.opencorporates.com/v0.4"
    _warned_no_key = False  # Track if we've already warned about missing key
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENCORPORATES_API_KEY
        if not self.api_key and not OpenCorporatesAPI._warned_no_key:
            logger.warning("[OpenCorporates] No API key configured. Get one free at: https://opencorporates.com/api_accounts/new")
            OpenCorporatesAPI._warned_no_key = True
    
    def _get_params(self) -> dict:
        """Get base params with API token if available."""
        params = {}
        if self.api_key:
            params["api_token"] = self.api_key
        return params
    
    def _has_api_key(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)
    
    async def search_companies(
        self, 
        query: str, 
        jurisdiction: Optional[str] = None,
        per_page: int = 10,
        inactive: bool = False
    ) -> list[dict]:
        """
        Search for companies by name.
        
        Args:
            query: Company name to search
            jurisdiction: Optional jurisdiction code (e.g., 'us_de' for Delaware)
            per_page: Number of results (max 30 without API key)
            inactive: Include inactive companies
            
        Returns:
            List of matching company records
        """
        # Skip if no API key configured
        if not self._has_api_key():
            logger.debug("[OpenCorporates] Skipping search - no API key configured")
            return []
        
        params = self._get_params()
        params["q"] = query
        params["per_page"] = min(per_page, 100)
        
        if jurisdiction:
            # Convert friendly name to code if needed
            jcode = JURISDICTION_CODES.get(jurisdiction.lower(), jurisdiction.lower())
            params["jurisdiction_code"] = jcode
        
        if not inactive:
            params["inactive"] = "false"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/companies/search",
                    params=params,
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    companies = data.get("results", {}).get("companies", [])
                    result = [c.get("company", {}) for c in companies]
                    logger.info(f"[OpenCorporates] Found {len(result)} companies for query: {query}")
                    return result
                elif response.status_code == 401:
                    logger.warning("[OpenCorporates] Invalid API key - check your key at https://opencorporates.com/users/account")
                    return []
                elif response.status_code == 429:
                    logger.warning("[OpenCorporates] Rate limit exceeded - try again later")
                    return []
                else:
                    logger.debug(f"[OpenCorporates] API error: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.debug(f"[OpenCorporates] API exception: {e}")
            return []
    
    async def get_company(self, jurisdiction: str, company_number: str) -> dict | None:
        """
        Get detailed company information.
        
        Args:
            jurisdiction: Jurisdiction code (e.g., 'gb' for UK)
            company_number: Company registration number
            
        Returns:
            Company details or None
        """
        if not self._has_api_key():
            return None
            
        params = self._get_params()
        
        # Convert jurisdiction to code if needed
        jcode = JURISDICTION_CODES.get(jurisdiction.lower(), jurisdiction.lower())
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/companies/{jcode}/{company_number}",
                    params=params,
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    company = data.get("results", {}).get("company", {})
                    logger.info(f"[OpenCorporates] Retrieved company: {company.get('name')}")
                    return company
                elif response.status_code == 404:
                    logger.info(f"[OpenCorporates] Company not found: {jcode}/{company_number}")
                    return None
                else:
                    logger.warning(f"[OpenCorporates] API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"[OpenCorporates] API exception: {e}")
            return None
    
    async def get_officers(self, jurisdiction: str, company_number: str) -> list[dict]:
        """
        Get company officers (directors, secretaries).
        
        Args:
            jurisdiction: Jurisdiction code
            company_number: Company registration number
            
        Returns:
            List of officers
        """
        if not self._has_api_key():
            return []
            
        params = self._get_params()
        jcode = JURISDICTION_CODES.get(jurisdiction.lower(), jurisdiction.lower())
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/companies/{jcode}/{company_number}/officers",
                    params=params,
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    officers = data.get("results", {}).get("officers", [])
                    result = [o.get("officer", {}) for o in officers]
                    logger.info(f"[OpenCorporates] Found {len(result)} officers")
                    return result
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"[OpenCorporates] API exception: {e}")
            return []
    
    async def search_officers(self, query: str, jurisdiction: Optional[str] = None) -> list[dict]:
        """
        Search for officers (directors) by name across all companies.
        Useful for finding common controllers.
        
        Args:
            query: Officer name to search
            jurisdiction: Optional jurisdiction filter
            
        Returns:
            List of officer records
        """
        if not self._has_api_key():
            return []
            
        params = self._get_params()
        params["q"] = query
        params["per_page"] = 20
        
        if jurisdiction:
            jcode = JURISDICTION_CODES.get(jurisdiction.lower(), jurisdiction.lower())
            params["jurisdiction_code"] = jcode
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/officers/search",
                    params=params,
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    officers = data.get("results", {}).get("officers", [])
                    result = [o.get("officer", {}) for o in officers]
                    logger.info(f"[OpenCorporates] Found {len(result)} officers named: {query}")
                    return result
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"[OpenCorporates] API exception: {e}")
            return []
    
    def normalize_company_data(self, raw_data: dict) -> dict:
        """
        Normalize OpenCorporates data to standard format.
        
        Args:
            raw_data: Raw API response
            
        Returns:
            Normalized company data
        """
        if not raw_data:
            return {}
        
        # Extract address
        address = raw_data.get("registered_address_in_full", "")
        if not address:
            addr_obj = raw_data.get("registered_address", {})
            if addr_obj:
                address = addr_obj.get("street_address", "")
        
        # Parse jurisdiction
        jurisdiction_code = raw_data.get("jurisdiction_code", "")
        jurisdiction = raw_data.get("incorporation_jurisdiction", jurisdiction_code)
        
        # Detect secrecy jurisdictions
        secrecy_jurisdictions = ["ky", "vg", "bm", "pa", "sc", "je", "gg", "im", "li", "mc"]
        is_secrecy = jurisdiction_code.lower() in secrecy_jurisdictions
        
        red_flags = []
        if is_secrecy:
            red_flags.append("Secrecy jurisdiction")
        if raw_data.get("inactive"):
            red_flags.append("Inactive company")
        if raw_data.get("dissolution_date"):
            red_flags.append(f"Dissolved: {raw_data.get('dissolution_date')}")
        
        return {
            "company_name": raw_data.get("name", ""),
            "jurisdiction": jurisdiction,
            "jurisdiction_code": jurisdiction_code,
            "registration_number": raw_data.get("company_number", ""),
            "registration_date": raw_data.get("incorporation_date", ""),
            "status": "inactive" if raw_data.get("inactive") else "active",
            "company_type": raw_data.get("company_type", ""),
            "registered_address": address,
            "registry_url": raw_data.get("registry_url", ""),
            "opencorporates_url": raw_data.get("opencorporates_url", ""),
            "red_flags": red_flags,
            "api_source": "opencorporates"
        }
    
    def normalize_officer_data(self, officers: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        Normalize officer data into beneficial owners and directors.
        
        Args:
            officers: List of officer records from API
            
        Returns:
            Tuple of (beneficial_owners, directors)
        """
        owners = []
        directors = []
        
        for officer in officers:
            name = officer.get("name", "Unknown")
            position = officer.get("position", "").lower()
            
            # Determine if this is an ownership position or directorship
            is_owner = any(term in position for term in [
                "shareholder", "owner", "member", "partner", "beneficiary"
            ])
            is_director = any(term in position for term in [
                "director", "secretary", "officer", "manager", "president", "ceo", "cfo"
            ])
            
            record = {
                "name": name,
                "position": officer.get("position", ""),
                "start_date": officer.get("start_date", ""),
                "end_date": officer.get("end_date", ""),
                "current": officer.get("current", True),
                "nationality": officer.get("nationality", ""),
                "occupation": officer.get("occupation", ""),
                "api_source": "opencorporates"
            }
            
            if is_owner:
                record["type"] = "individual"
                record["ownership_percentage"] = None  # OpenCorporates doesn't provide percentages
                owners.append(record)
            
            if is_director or not is_owner:
                record["role"] = officer.get("position", "Director")
                directors.append(record)
        
        return owners, directors
