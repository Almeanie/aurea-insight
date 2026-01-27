"""
GLEIF API Wrapper
For accessing Legal Entity Identifier (LEI) data and corporate relationships.
API Documentation: https://www.gleif.org/en/lei-data/gleif-api
"""
import httpx
from typing import Optional
from loguru import logger

from config import settings


class GLEIFAPI:
    """
    Wrapper for GLEIF (Global Legal Entity Identifier Foundation) API.
    Free API - no authentication required.
    Provides LEI data and parent-child relationships between legal entities.
    """
    
    BASE_URL = "https://api.gleif.org/api/v1"
    
    def __init__(self):
        self.enabled = settings.GLEIF_API_ENABLED
    
    async def search_entities(self, query: str, page_size: int = 10) -> list[dict]:
        """
        Search for legal entities by name using multiple search strategies.
        
        Strategy:
        1. First try fulltext search (more permissive, handles partial matches)
        2. If no results, try exact legal name filter
        
        Args:
            query: Entity name to search
            page_size: Number of results
            
        Returns:
            List of matching LEI records
        """
        if not self.enabled:
            return []
        
        # Clean the query - remove common suffixes that might interfere
        clean_query = query.strip()
        
        try:
            async with httpx.AsyncClient() as client:
                # Strategy 1: Fulltext search (more permissive, handles partial matches)
                params = {
                    "filter[fulltext]": clean_query,
                    "page[size]": min(page_size, 100)
                }
                
                response = await client.get(
                    f"{self.BASE_URL}/lei-records",
                    params=params,
                    headers={"Accept": "application/vnd.api+json"},
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    records = data.get("data", [])
                    if records:
                        logger.info(f"[GLEIF] Fulltext search found {len(records)} entities for: {query}")
                        return records
                
                # Strategy 2: Try exact legal name filter if fulltext returned nothing
                params = {
                    "filter[entity.legalName]": clean_query,
                    "page[size]": min(page_size, 100)
                }
                
                response = await client.get(
                    f"{self.BASE_URL}/lei-records",
                    params=params,
                    headers={"Accept": "application/vnd.api+json"},
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    records = data.get("data", [])
                    if records:
                        logger.info(f"[GLEIF] Exact name search found {len(records)} entities for: {query}")
                        return records
                
                logger.debug(f"[GLEIF] No entities found for: {query}")
                return []
                    
        except Exception as e:
            logger.warning(f"[GLEIF] API exception: {e}")
            return []
    
    async def get_entity_by_lei(self, lei: str) -> dict | None:
        """
        Get entity details by LEI code.
        
        Args:
            lei: Legal Entity Identifier (20-character code)
            
        Returns:
            Entity details or None
        """
        if not self.enabled:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/lei-records/{lei}",
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", {})
                elif response.status_code == 404:
                    logger.info(f"[GLEIF] LEI not found: {lei}")
                    return None
                else:
                    logger.warning(f"[GLEIF] API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"[GLEIF] API exception: {e}")
            return None
    
    async def get_parent_relationships(self, lei: str) -> list[dict]:
        """
        Get parent relationships (who owns this entity).
        
        Args:
            lei: Legal Entity Identifier
            
        Returns:
            List of parent relationship records
        """
        if not self.enabled:
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                # Get direct parent
                response = await client.get(
                    f"{self.BASE_URL}/lei-records/{lei}/direct-parent",
                    timeout=15.0
                )
                
                parents = []
                
                if response.status_code == 200:
                    data = response.json()
                    parent = data.get("data")
                    if parent:
                        parents.append({
                            "type": "direct_parent",
                            "parent": parent
                        })
                
                # Get ultimate parent
                response = await client.get(
                    f"{self.BASE_URL}/lei-records/{lei}/ultimate-parent",
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    ultimate = data.get("data")
                    if ultimate:
                        parents.append({
                            "type": "ultimate_parent",
                            "parent": ultimate
                        })
                
                logger.info(f"[GLEIF] Found {len(parents)} parent relationships for LEI: {lei}")
                return parents
                    
        except Exception as e:
            logger.error(f"[GLEIF] API exception: {e}")
            return []
    
    async def get_child_relationships(self, lei: str) -> list[dict]:
        """
        Get child relationships (entities owned by this one).
        
        Args:
            lei: Legal Entity Identifier
            
        Returns:
            List of child entity records
        """
        if not self.enabled:
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/lei-records/{lei}/direct-children",
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    children = data.get("data", [])
                    logger.info(f"[GLEIF] Found {len(children)} child entities for LEI: {lei}")
                    return children
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"[GLEIF] API exception: {e}")
            return []
    
    async def fuzzy_search(self, query: str, page_size: int = 10) -> list[dict]:
        """
        Fuzzy search for entities - more permissive matching.
        
        Args:
            query: Search query
            page_size: Number of results
            
        Returns:
            List of matching entities
        """
        if not self.enabled:
            return []
        
        params = {
            "filter[fulltext]": query,
            "page[size]": min(page_size, 100)
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/lei-records",
                    params=params,
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", [])
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"[GLEIF] API exception: {e}")
            return []
    
    def normalize_entity_data(self, raw_data: dict) -> dict:
        """
        Normalize GLEIF data to standard format.
        
        Args:
            raw_data: Raw API response
            
        Returns:
            Normalized entity data
        """
        if not raw_data:
            return {}
        
        attributes = raw_data.get("attributes", {})
        entity = attributes.get("entity", {})
        legal_address = entity.get("legalAddress", {})
        headquarters = entity.get("headquartersAddress", {})
        
        # Build address from legal address
        address_parts = [
            legal_address.get("addressLines", [""])[0] if legal_address.get("addressLines") else "",
            legal_address.get("city", ""),
            legal_address.get("region", ""),
            legal_address.get("postalCode", ""),
            legal_address.get("country", "")
        ]
        full_address = ", ".join(part for part in address_parts if part)
        
        # Determine jurisdiction
        jurisdiction = legal_address.get("country", "Unknown")
        
        # Determine status
        registration = attributes.get("registration", {})
        status = registration.get("status", "UNKNOWN")
        
        return {
            "company_name": entity.get("legalName", {}).get("name", "Unknown"),
            "lei": raw_data.get("id", ""),
            "jurisdiction": jurisdiction,
            "registration_date": registration.get("initialRegistrationDate", ""),
            "status": status.lower() if status else "unknown",
            "registered_address": full_address,
            "headquarters_country": headquarters.get("country", ""),
            "legal_form": entity.get("legalForm", {}).get("id", ""),
            "entity_category": entity.get("category", ""),
            "api_source": "gleif"
        }
    
    def normalize_parent_data(self, parent_data: dict, relationship_type: str) -> dict:
        """
        Normalize parent relationship data.
        
        Args:
            parent_data: Parent entity data
            relationship_type: Type of relationship (direct_parent, ultimate_parent)
            
        Returns:
            Normalized beneficial owner record
        """
        if not parent_data:
            return {}
        
        normalized = self.normalize_entity_data(parent_data)
        normalized["relationship_type"] = relationship_type
        normalized["type"] = "company"  # GLEIF only tracks legal entities
        
        return {
            "name": normalized.get("company_name", "Unknown Parent"),
            "type": "company",
            "ownership_percentage": None,  # GLEIF doesn't provide exact percentages
            "lei": normalized.get("lei", ""),
            "jurisdiction": normalized.get("jurisdiction", ""),
            "relationship_type": relationship_type,
            "api_source": "gleif"
        }
