"""
SEC EDGAR API Wrapper
For accessing US public company filings.

API Documentation: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
"""
import httpx
from typing import Optional
from loguru import logger


class SECEdgarAPI:
    """
    Wrapper for SEC EDGAR API.
    Free, no API key required.
    Rate limit: 10 requests per second.
    """
    
    # Main API for submissions and XBRL data
    DATA_URL = "https://data.sec.gov"
    
    # Static files location (company_tickers.json is here, NOT on data.sec.gov)
    STATIC_FILES_URL = "https://www.sec.gov/files"
    
    # SEC requires proper User-Agent format: Sample Company Name AdminContact@example.com
    # Without this, requests will be blocked
    USER_AGENT = "AureaInsight admin@hackathon-demo.com"
    
    # Cache for company tickers to avoid repeated requests
    _tickers_cache: dict | None = None
    _tickers_loaded: bool = False
    
    async def _load_tickers(self) -> bool:
        """
        Load company tickers from SEC static files.
        The file is at https://www.sec.gov/files/company_tickers.json (NOT data.sec.gov)
        
        Returns:
            True if successfully loaded, False otherwise
        """
        if SECEdgarAPI._tickers_loaded:
            return SECEdgarAPI._tickers_cache is not None
        
        SECEdgarAPI._tickers_loaded = True
        
        try:
            async with httpx.AsyncClient() as client:
                # CORRECT URL: www.sec.gov/files/ NOT data.sec.gov/files/
                response = await client.get(
                    f"{self.STATIC_FILES_URL}/company_tickers.json",
                    headers={
                        "User-Agent": self.USER_AGENT,
                        "Accept": "application/json"
                    },
                    timeout=30.0,
                    follow_redirects=True
                )
                
                if response.status_code == 200:
                    SECEdgarAPI._tickers_cache = response.json()
                    logger.info(f"[SEC EDGAR] Loaded {len(SECEdgarAPI._tickers_cache)} company tickers from SEC")
                    return True
                else:
                    logger.warning(f"[SEC EDGAR] Could not load tickers (status: {response.status_code})")
                    return False
                    
        except Exception as e:
            logger.warning(f"[SEC EDGAR] Failed to load tickers: {e}")
            return False
    
    async def search_companies(self, query: str) -> list[dict]:
        """
        Search for companies by name or ticker.
        
        Args:
            query: Company name or ticker symbol
            
        Returns:
            List of matching company records
        """
        try:
            # Load tickers if not already loaded
            if not await self._load_tickers():
                return []
            
            data = SECEdgarAPI._tickers_cache
            if not data:
                return []
                
            query_lower = query.lower().strip()
            
            # Remove common suffixes for better matching
            suffixes_to_remove = ["inc.", "inc", "corp.", "corp", "llc", "ltd.", "ltd", "company", "co.", "co"]
            query_base = query_lower
            for suffix in suffixes_to_remove:
                if query_base.endswith(suffix):
                    query_base = query_base[:-len(suffix)].strip()
            
            # Extract significant words from query (filter out common terms)
            common_words = {"the", "and", "of", "a", "an", "in", "for", "to", "on", "at", "by"}
            query_words = [w for w in query_lower.split() if w not in common_words and len(w) > 2]
            
            # Filter matching companies - check both name and ticker
            matches = []
            for key, company in data.items():
                title = company.get("title", "").lower()
                ticker = company.get("ticker", "").lower()
                
                # Match strategies (in order of quality):
                # 1. Exact query in title
                if query_lower in title:
                    matches.append({
                        "cik": str(company.get("cik_str", "")).zfill(10),
                        "ticker": company.get("ticker", ""),
                        "name": company.get("title", ""),
                        "match_quality": 1.0
                    })
                    continue
                
                # 2. Exact ticker match
                if query_lower == ticker:
                    matches.append({
                        "cik": str(company.get("cik_str", "")).zfill(10),
                        "ticker": company.get("ticker", ""),
                        "name": company.get("title", ""),
                        "match_quality": 1.0
                    })
                    continue
                
                # 3. Base query (without suffixes) in title
                if query_base and len(query_base) > 3 and query_base in title:
                    matches.append({
                        "cik": str(company.get("cik_str", "")).zfill(10),
                        "ticker": company.get("ticker", ""),
                        "name": company.get("title", ""),
                        "match_quality": 0.9
                    })
                    continue
                
                # 4. First significant word matches (e.g., "Marriott" from "Marriott Hotels")
                if query_words and len(query_words[0]) > 4:
                    if query_words[0] in title:
                        matches.append({
                            "cik": str(company.get("cik_str", "")).zfill(10),
                            "ticker": company.get("ticker", ""),
                            "name": company.get("title", ""),
                            "match_quality": 0.7
                        })
                        continue
            
            # Sort by match quality and limit
            matches.sort(key=lambda x: x.get("match_quality", 0), reverse=True)
            
            if matches:
                logger.info(f"[SEC EDGAR] Found {len(matches)} matches for: {query}")
            else:
                logger.debug(f"[SEC EDGAR] No matches found for: {query}")
            
            return matches[:10]  # Limit results
                    
        except Exception as e:
            logger.warning(f"[SEC EDGAR] Search failed: {e}")
            return []
    
    async def get_company_facts(self, cik: str) -> dict | None:
        """
        Get company facts and filings (XBRL data).
        
        Args:
            cik: Central Index Key (10-digit, zero-padded)
            
        Returns:
            Company facts or None
        """
        try:
            cik_padded = cik.zfill(10)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.DATA_URL}/api/xbrl/companyfacts/CIK{cik_padded}.json",
                    headers={
                        "User-Agent": self.USER_AGENT,
                        "Accept": "application/json"
                    },
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    logger.debug(f"[SEC EDGAR] Retrieved company facts for CIK: {cik_padded}")
                    return response.json()
                else:
                    logger.debug(f"[SEC EDGAR] Company facts not found for CIK: {cik_padded}")
                    return None
                    
        except Exception as e:
            logger.warning(f"[SEC EDGAR] Company facts exception: {e}")
            return None
    
    async def get_company_submissions(self, cik: str) -> dict | None:
        """
        Get company submission history and metadata.
        
        Endpoint: https://data.sec.gov/submissions/CIK{cik}.json
        Returns company name, SIC codes, state of incorporation, and filing history.
        
        Args:
            cik: Central Index Key
            
        Returns:
            Company submissions or None
        """
        try:
            cik_padded = cik.zfill(10)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.DATA_URL}/submissions/CIK{cik_padded}.json",
                    headers={
                        "User-Agent": self.USER_AGENT,
                        "Accept": "application/json"
                    },
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"[SEC EDGAR] Retrieved submissions for: {data.get('name', 'Unknown')}")
                    
                    # Extract business address
                    addresses = data.get("addresses", {})
                    business = addresses.get("business", {})
                    mailing = addresses.get("mailing", {})
                    
                    return {
                        "cik": data.get("cik"),
                        "name": data.get("name"),
                        "sic": data.get("sic"),
                        "sic_description": data.get("sicDescription"),
                        "state": data.get("stateOfIncorporation"),
                        "fiscal_year_end": data.get("fiscalYearEnd"),
                        "business_address": {
                            "street": business.get("street1", ""),
                            "city": business.get("city", ""),
                            "state": business.get("stateOrCountry", ""),
                            "zip": business.get("zipCode", "")
                        },
                        "filings_count": len(data.get("filings", {}).get("recent", {}).get("form", []))
                    }
                elif response.status_code == 404:
                    logger.debug(f"[SEC EDGAR] Company not found for CIK: {cik_padded}")
                    return None
                else:
                    logger.warning(f"[SEC EDGAR] Submissions request failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.warning(f"[SEC EDGAR] Company submissions exception: {e}")
            return None
    
    async def get_beneficial_ownership_filings(self, cik: str) -> list[dict]:
        """
        Get beneficial ownership data from SEC filings.
        
        Fetches data from:
        - DEF 14A (Proxy statements with ownership info)
        - SC 13D/G (Beneficial ownership reports)
        - 10-K (Annual reports with ownership section)
        
        Args:
            cik: Central Index Key
            
        Returns:
            List of ownership filings with extracted data
        """
        try:
            cik_padded = cik.zfill(10)
            filings = []
            
            async with httpx.AsyncClient() as client:
                # Get submission history to find ownership-related filings
                response = await client.get(
                    f"{self.DATA_URL}/submissions/CIK{cik_padded}.json",
                    headers={
                        "User-Agent": self.USER_AGENT,
                        "Accept": "application/json"
                    },
                    timeout=15.0
                )
                
                if response.status_code != 200:
                    return []
                
                data = response.json()
                recent = data.get("filings", {}).get("recent", {})
                forms = recent.get("form", [])
                accession_numbers = recent.get("accessionNumber", [])
                filing_dates = recent.get("filingDate", [])
                primary_documents = recent.get("primaryDocument", [])
                
                # Look for ownership-related filings (limit to recent ones)
                ownership_forms = ["DEF 14A", "SC 13D", "SC 13G", "SC 13D/A", "SC 13G/A", "3", "4", "5"]
                
                for i, form in enumerate(forms[:50]):  # Check last 50 filings
                    if form in ownership_forms:
                        filings.append({
                            "form_type": form,
                            "filing_date": filing_dates[i] if i < len(filing_dates) else None,
                            "accession_number": accession_numbers[i] if i < len(accession_numbers) else None,
                            "document": primary_documents[i] if i < len(primary_documents) else None,
                            "cik": cik_padded
                        })
                        
                        if len(filings) >= 5:  # Limit to 5 most recent
                            break
                
                if filings:
                    logger.info(f"[SEC EDGAR] Found {len(filings)} ownership filings for CIK: {cik_padded}")
                
                return filings
                    
        except Exception as e:
            logger.warning(f"[SEC EDGAR] Beneficial ownership filings exception: {e}")
            return []
    
    async def get_insider_transactions(self, cik: str) -> list[dict]:
        """
        Get insider transaction data (Forms 3, 4, 5).
        
        These forms show who owns significant portions of the company.
        
        Args:
            cik: Central Index Key
            
        Returns:
            List of insider transactions
        """
        try:
            cik_padded = cik.zfill(10)
            
            async with httpx.AsyncClient() as client:
                # Use the SEC full-text search for insider filings
                response = await client.get(
                    f"{self.DATA_URL}/submissions/CIK{cik_padded}.json",
                    headers={
                        "User-Agent": self.USER_AGENT,
                        "Accept": "application/json"
                    },
                    timeout=15.0
                )
                
                if response.status_code != 200:
                    return []
                
                data = response.json()
                recent = data.get("filings", {}).get("recent", {})
                forms = recent.get("form", [])
                filing_dates = recent.get("filingDate", [])
                
                # Count insider forms
                insider_forms = ["3", "4", "5"]
                transactions = []
                
                for i, form in enumerate(forms[:100]):
                    if form in insider_forms:
                        transactions.append({
                            "form_type": form,
                            "filing_date": filing_dates[i] if i < len(filing_dates) else None,
                        })
                
                if transactions:
                    logger.info(f"[SEC EDGAR] Found {len(transactions)} insider transactions for CIK: {cik_padded}")
                
                return transactions
                    
        except Exception as e:
            logger.warning(f"[SEC EDGAR] Insider transactions exception: {e}")
            return []
