"""
UK Companies House API Wrapper
For accessing UK company registry data including Persons with Significant Control (PSC).
API Documentation: https://developer.company-information.service.gov.uk/
"""
import httpx
import base64
from typing import Optional
from loguru import logger

from config import settings


class UKCompaniesHouseAPI:
    """
    Wrapper for UK Companies House API.
    Free API - requires registration for API key.
    """
    
    BASE_URL = "https://api.company-information.service.gov.uk"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.UK_COMPANIES_HOUSE_API_KEY
        # UK Companies House uses HTTP Basic Auth with API key as username
        if self.api_key:
            credentials = base64.b64encode(f"{self.api_key}:".encode()).decode()
            self.auth_header = f"Basic {credentials}"
        else:
            self.auth_header = None
    
    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        headers = {
            "Accept": "application/json"
        }
        if self.auth_header:
            headers["Authorization"] = self.auth_header
        return headers
    
    async def search_companies(self, query: str, items_per_page: int = 10) -> list[dict]:
        """
        Search for companies by name.
        
        API Endpoint: GET /search/companies
        Docs: https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/reference/search/search-companies
        
        Args:
            query: Company name to search
            items_per_page: Number of results (max 100)
            
        Returns:
            List of matching company records
        """
        if not self.api_key:
            logger.warning("[UKCompaniesHouse] No API key configured - get one at https://developer.company-information.service.gov.uk/")
            return []
        
        # Clean the query - UK Companies House search works best with simpler queries
        clean_query = query.strip()
        
        params = {
            "q": clean_query,
            "items_per_page": min(items_per_page, 100)
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/search/companies",
                    params=params,
                    headers=self._get_headers(),
                    timeout=20.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    companies = data.get("items", [])
                    total_results = data.get("total_results", 0)
                    logger.info(f"[UKCompaniesHouse] Found {len(companies)} of {total_results} companies for: {query}")
                    return companies
                elif response.status_code == 401:
                    # Test API keys may have restrictions or take time to activate
                    # Keys need to be activated and may take up to 24 hours
                    logger.warning("[UKCompaniesHouse] Auth failed (401) - key may be invalid, expired, or not yet activated (can take 24h)")
                    return []
                elif response.status_code == 403:
                    logger.warning("[UKCompaniesHouse] Access forbidden (403) - check API key permissions")
                    return []
                elif response.status_code == 429:
                    logger.warning("[UKCompaniesHouse] Rate limit exceeded (429) - slow down requests")
                    return []
                elif response.status_code == 416:
                    # Requested range not satisfiable - no results
                    logger.debug(f"[UKCompaniesHouse] No results for: {query}")
                    return []
                else:
                    logger.debug(f"[UKCompaniesHouse] API response: {response.status_code} for {query}")
                    return []
                    
        except httpx.TimeoutException:
            logger.warning(f"[UKCompaniesHouse] Timeout searching for: {query}")
            return []
        except Exception as e:
            logger.warning(f"[UKCompaniesHouse] API exception: {e}")
            return []
    
    async def get_company(self, company_number: str) -> dict | None:
        """
        Get detailed company information.
        
        Args:
            company_number: UK company registration number (8 chars)
            
        Returns:
            Company details or None
        """
        if not self.api_key:
            logger.warning("[UKCompaniesHouse] No API key configured")
            return None
        
        # Pad company number to 8 characters
        company_number = company_number.zfill(8)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/company/{company_number}",
                    headers=self._get_headers(),
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"[UKCompaniesHouse] Retrieved company: {data.get('company_name')}")
                    return data
                elif response.status_code == 404:
                    logger.info(f"[UKCompaniesHouse] Company not found: {company_number}")
                    return None
                else:
                    logger.warning(f"[UKCompaniesHouse] API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"[UKCompaniesHouse] API exception: {e}")
            return None
    
    async def get_officers(self, company_number: str) -> list[dict]:
        """
        Get company officers (directors, secretaries).
        
        Args:
            company_number: UK company registration number
            
        Returns:
            List of officers
        """
        if not self.api_key:
            return []
        
        company_number = company_number.zfill(8)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/company/{company_number}/officers",
                    headers=self._get_headers(),
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    officers = data.get("items", [])
                    logger.info(f"[UKCompaniesHouse] Found {len(officers)} officers")
                    return officers
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"[UKCompaniesHouse] API exception: {e}")
            return []
    
    async def get_persons_with_significant_control(self, company_number: str) -> list[dict]:
        """
        Get Persons with Significant Control (PSC) - beneficial owners.
        This is the key endpoint for beneficial ownership data.
        
        Args:
            company_number: UK company registration number
            
        Returns:
            List of PSC records (beneficial owners with >25% ownership or control)
        """
        if not self.api_key:
            return []
        
        company_number = company_number.zfill(8)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/company/{company_number}/persons-with-significant-control",
                    headers=self._get_headers(),
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    pscs = data.get("items", [])
                    logger.info(f"[UKCompaniesHouse] Found {len(pscs)} PSC records")
                    return pscs
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"[UKCompaniesHouse] API exception: {e}")
            return []
    
    async def get_filing_history(self, company_number: str, items_per_page: int = 10) -> list[dict]:
        """
        Get company filing history.
        
        Args:
            company_number: UK company registration number
            items_per_page: Number of filings to retrieve
            
        Returns:
            List of filing records
        """
        if not self.api_key:
            return []
        
        company_number = company_number.zfill(8)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/company/{company_number}/filing-history",
                    params={"items_per_page": items_per_page},
                    headers=self._get_headers(),
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("items", [])
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"[UKCompaniesHouse] API exception: {e}")
            return []
    
    def normalize_company_data(self, raw_data: dict) -> dict:
        """
        Normalize UK Companies House data to standard format.
        
        Args:
            raw_data: Raw API response
            
        Returns:
            Normalized company data
        """
        if not raw_data:
            return {}
        
        # Extract registered office address
        address = raw_data.get("registered_office_address", {})
        address_parts = [
            address.get("address_line_1", ""),
            address.get("address_line_2", ""),
            address.get("locality", ""),
            address.get("region", ""),
            address.get("postal_code", ""),
            address.get("country", "United Kingdom")
        ]
        full_address = ", ".join(part for part in address_parts if part)
        
        return {
            "company_name": raw_data.get("company_name", ""),
            "jurisdiction": "United Kingdom",
            "registration_number": raw_data.get("company_number", ""),
            "registration_date": raw_data.get("date_of_creation", ""),
            "status": raw_data.get("company_status", "unknown"),
            "company_type": raw_data.get("type", ""),
            "registered_address": full_address,
            "sic_codes": raw_data.get("sic_codes", []),
            "api_source": "uk_companies_house"
        }
    
    def normalize_psc_data(self, psc_list: list[dict]) -> list[dict]:
        """
        Normalize PSC data to beneficial owners format.
        
        Args:
            psc_list: List of PSC records from API
            
        Returns:
            List of normalized beneficial owner records
        """
        owners = []
        
        for psc in psc_list:
            # Determine ownership percentage from natures_of_control
            natures = psc.get("natures_of_control", [])
            ownership_percentage = None
            
            for nature in natures:
                if "ownership-of-shares-25-to-50-percent" in nature:
                    ownership_percentage = 37.5  # Midpoint
                elif "ownership-of-shares-50-to-75-percent" in nature:
                    ownership_percentage = 62.5
                elif "ownership-of-shares-75-to-100-percent" in nature:
                    ownership_percentage = 87.5
                elif "ownership-of-shares-more-than-25-percent" in nature:
                    ownership_percentage = 50.0  # Unknown exact, use midpoint
            
            # Determine entity type
            kind = psc.get("kind", "")
            if "individual" in kind:
                entity_type = "individual"
                name = psc.get("name", "Unknown")
            elif "corporate" in kind:
                entity_type = "company"
                name = psc.get("name", "Unknown Corporate Entity")
            else:
                entity_type = "unknown"
                name = psc.get("name", "Unknown")
            
            owners.append({
                "name": name,
                "type": entity_type,
                "ownership_percentage": ownership_percentage,
                "nationality": psc.get("nationality", ""),
                "country_of_residence": psc.get("country_of_residence", ""),
                "natures_of_control": natures,
                "notified_on": psc.get("notified_on", ""),
                "api_source": "uk_companies_house"
            })
        
        return owners
