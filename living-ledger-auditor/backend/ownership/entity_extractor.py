"""
Entity Extractor for Ownership Discovery

Extracts all relevant entities from financial data:
- Vendors (from expense entries)
- Customers (from revenue entries)
- Related parties (from descriptions)
- Any company names mentioned in the financial records

This feeds into the ownership discovery to build a comprehensive graph.
"""
import re
from typing import Optional
from collections import defaultdict
from loguru import logger

from core.schemas import GeneralLedger, ChartOfAccounts, TrialBalance


# Known entity patterns to extract from descriptions
COMPANY_SUFFIXES = [
    r'\b(Inc\.?|LLC|Ltd\.?|Corp\.?|Corporation|Company|Co\.?|PLC|LLP|LP|GmbH|AG|SA|SAS|BV|NV)\b',
]

# Patterns that indicate a company name in descriptions
PAYMENT_PATTERNS = [
    r'payment\s+(?:to|from)\s+([A-Z][A-Za-z0-9\s&\.\,\-\']+(?:Inc|LLC|Ltd|Corp|Co)\.?)',
    r'(?:paid|received)\s+(?:to|from)\s+([A-Z][A-Za-z0-9\s&\.\,\-\']+)',
    r'invoice\s+(?:from|to)\s+([A-Z][A-Za-z0-9\s&\.\,\-\']+)',
    r'(?:services?|goods?|supplies?)\s+(?:from|by)\s+([A-Z][A-Za-z0-9\s&\.\,\-\']+)',
]

# Words that indicate relationship types
VENDOR_KEYWORDS = ['payment', 'paid', 'expense', 'purchase', 'supplies', 'services from', 'invoice from']
CUSTOMER_KEYWORDS = ['received', 'revenue', 'sales', 'invoice to', 'payment from customer']
RELATED_PARTY_KEYWORDS = ['related party', 'subsidiary', 'parent company', 'affiliate', 'intercompany', 'transfer']


class ExtractedEntity:
    """Represents an entity extracted from financial data."""
    
    def __init__(self, name: str, entity_type: str = "unknown"):
        self.name = name
        self.entity_type = entity_type  # vendor, customer, related_party, unknown
        self.total_debits = 0.0
        self.total_credits = 0.0
        self.transaction_count = 0
        self.account_codes = set()
        self.descriptions = []
        self.source_entries = []  # entry_ids
        
    @property
    def total_value(self) -> float:
        """Total transaction value with this entity."""
        return self.total_debits + self.total_credits
        
    @property
    def net_flow(self) -> float:
        """Net cash flow (positive = paying them, negative = receiving from them)."""
        return self.total_debits - self.total_credits
        
    def add_transaction(self, entry_id: str, debit: float, credit: float, 
                       account_code: str, description: str):
        """Add a transaction to this entity's record."""
        self.total_debits += debit
        self.total_credits += credit
        self.transaction_count += 1
        self.account_codes.add(account_code)
        if description and description not in self.descriptions:
            self.descriptions.append(description[:100])  # Truncate long descriptions
        self.source_entries.append(entry_id)
        
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "total_debits": self.total_debits,
            "total_credits": self.total_credits,
            "total_value": self.total_value,
            "net_flow": self.net_flow,
            "transaction_count": self.transaction_count,
            "account_codes": list(self.account_codes),
            "sample_descriptions": self.descriptions[:3]  # First 3 descriptions
        }


def classify_entity_type(account_code: str, account_name: str, 
                        description: str, coa: Optional[ChartOfAccounts] = None) -> str:
    """
    Classify an entity as vendor, customer, or related party based on context.
    
    Args:
        account_code: The account code used in the transaction
        account_name: The account name
        description: Transaction description
        coa: Optional Chart of Accounts for account type lookup
        
    Returns:
        Entity type: 'vendor', 'customer', 'related_party', or 'unknown'
    """
    desc_lower = description.lower() if description else ""
    account_lower = account_name.lower() if account_name else ""
    
    # Check for related party keywords first (highest priority)
    for keyword in RELATED_PARTY_KEYWORDS:
        if keyword in desc_lower or keyword in account_lower:
            return "related_party"
    
    # Check account type if COA available
    if coa:
        for account in coa.accounts:
            if account.code == account_code:
                if account.type == "expense":
                    return "vendor"
                elif account.type == "revenue":
                    return "customer"
                elif account.type == "liability" and "payable" in account.name.lower():
                    return "vendor"
                elif account.type == "asset" and "receivable" in account.name.lower():
                    return "customer"
                break
    
    # Check keywords in description
    for keyword in VENDOR_KEYWORDS:
        if keyword in desc_lower:
            return "vendor"
            
    for keyword in CUSTOMER_KEYWORDS:
        if keyword in desc_lower:
            return "customer"
    
    # Check account name patterns
    if any(x in account_lower for x in ['expense', 'payable', 'purchase', 'supplies']):
        return "vendor"
    if any(x in account_lower for x in ['revenue', 'receivable', 'sales', 'income']):
        return "customer"
    
    return "unknown"


def extract_company_names_from_description(description: str) -> list[str]:
    """
    Extract potential company names from a transaction description.
    
    Uses regex patterns to find:
    - Names followed by company suffixes (Inc, LLC, etc.)
    - Names in common payment patterns
    
    Args:
        description: Transaction description text
        
    Returns:
        List of potential company names found
    """
    if not description:
        return []
        
    companies = []
    
    # Look for company suffix patterns
    for pattern in COMPANY_SUFFIXES:
        # Find words before the suffix
        full_pattern = r'([A-Z][A-Za-z0-9\s&\.\,\-\']+?)' + pattern
        matches = re.findall(full_pattern, description, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                name = match[0].strip()
            else:
                name = match.strip()
            if name and len(name) > 2:
                companies.append(name)
    
    # Look for payment patterns
    for pattern in PAYMENT_PATTERNS:
        matches = re.findall(pattern, description, re.IGNORECASE)
        for match in matches:
            name = match.strip() if isinstance(match, str) else match[0].strip()
            if name and len(name) > 2 and name not in companies:
                companies.append(name)
    
    return companies


def extract_entities_from_gl(
    gl: GeneralLedger,
    coa: Optional[ChartOfAccounts] = None
) -> dict[str, ExtractedEntity]:
    """
    Extract all entities from a General Ledger.
    
    This is the main extraction function that pulls:
    1. Named vendors/customers from the vendor_or_customer field
    2. Company names mentioned in descriptions
    
    Args:
        gl: The General Ledger to analyze
        coa: Optional Chart of Accounts for better classification
        
    Returns:
        Dictionary mapping entity names to ExtractedEntity objects
    """
    entities: dict[str, ExtractedEntity] = {}
    
    logger.info(f"[extract_entities_from_gl] Extracting entities from {len(gl.entries)} GL entries")
    
    for entry in gl.entries:
        # 1. Extract from vendor_or_customer field (primary source)
        if entry.vendor_or_customer:
            name = entry.vendor_or_customer.strip()
            if name:
                entity_type = classify_entity_type(
                    entry.account_code, 
                    entry.account_name,
                    entry.description,
                    coa
                )
                
                if name not in entities:
                    entities[name] = ExtractedEntity(name, entity_type)
                
                entities[name].add_transaction(
                    entry.entry_id,
                    entry.debit,
                    entry.credit,
                    entry.account_code,
                    entry.description
                )
        
        # 2. Extract company names from descriptions
        description_companies = extract_company_names_from_description(entry.description)
        for company_name in description_companies:
            # Skip if it's already captured from vendor_or_customer
            if company_name in entities:
                continue
                
            # Skip very short names or obvious non-companies
            if len(company_name) < 3:
                continue
                
            entity_type = classify_entity_type(
                entry.account_code,
                entry.account_name,
                entry.description,
                coa
            )
            
            if company_name not in entities:
                entities[company_name] = ExtractedEntity(company_name, entity_type)
            
            entities[company_name].add_transaction(
                entry.entry_id,
                entry.debit,
                entry.credit,
                entry.account_code,
                entry.description
            )
    
    # Log summary
    by_type = defaultdict(int)
    for entity in entities.values():
        by_type[entity.entity_type] += 1
    
    logger.info(f"[extract_entities_from_gl] Extracted {len(entities)} entities: {dict(by_type)}")
    
    return entities


def prioritize_entities(
    entities: dict[str, ExtractedEntity],
    max_entities: int = 30,
    min_transaction_value: float = 1000.0
) -> list[dict]:
    """
    Prioritize entities for ownership discovery based on risk and value.
    
    Prioritization criteria:
    1. Related parties (highest priority - potential fraud)
    2. High-value transactions
    3. Frequent transactions
    4. Unknown entity types (need investigation)
    
    Args:
        entities: Dictionary of extracted entities
        max_entities: Maximum number of entities to return
        min_transaction_value: Minimum total transaction value to include
        
    Returns:
        List of entity dictionaries sorted by priority
    """
    # Filter by minimum value
    significant_entities = [
        e for e in entities.values()
        if e.total_value >= min_transaction_value
    ]
    
    # Sort by priority
    def priority_score(entity: ExtractedEntity) -> float:
        score = 0.0
        
        # Related parties get highest priority
        if entity.entity_type == "related_party":
            score += 100000
            
        # Unknown types need investigation
        if entity.entity_type == "unknown":
            score += 10000
            
        # Higher transaction value = higher priority
        score += entity.total_value
        
        # More transactions = higher priority (potential ongoing relationship)
        score += entity.transaction_count * 100
        
        return score
    
    sorted_entities = sorted(significant_entities, key=priority_score, reverse=True)
    
    # Take top N
    top_entities = sorted_entities[:max_entities]
    
    logger.info(f"[prioritize_entities] Selected {len(top_entities)} entities from {len(entities)} total")
    
    return [e.to_dict() for e in top_entities]


def extract_all_entities(
    gl: Optional[GeneralLedger] = None,
    coa: Optional[ChartOfAccounts] = None,
    tb: Optional[TrialBalance] = None,
    max_entities: int = 30
) -> dict:
    """
    Main function to extract all entities from financial data.
    
    Args:
        gl: General Ledger
        coa: Chart of Accounts
        tb: Trial Balance
        max_entities: Maximum entities to return for discovery
        
    Returns:
        Dictionary with:
        - entities: List of prioritized entities for discovery
        - summary: Extraction summary statistics
    """
    all_entities: dict[str, ExtractedEntity] = {}
    
    # Extract from GL (primary source)
    if gl:
        gl_entities = extract_entities_from_gl(gl, coa)
        all_entities.update(gl_entities)
    
    # Could add extraction from TB account names in the future
    # For now, GL is the primary source of entity data
    
    # Prioritize and return
    prioritized = prioritize_entities(all_entities, max_entities)
    
    # Build summary
    by_type = defaultdict(int)
    total_value_by_type = defaultdict(float)
    for entity in all_entities.values():
        by_type[entity.entity_type] += 1
        total_value_by_type[entity.entity_type] += entity.total_value
    
    summary = {
        "total_entities_found": len(all_entities),
        "entities_for_discovery": len(prioritized),
        "by_type": dict(by_type),
        "total_value_by_type": {k: round(v, 2) for k, v in total_value_by_type.items()},
        "vendors_count": by_type.get("vendor", 0),
        "customers_count": by_type.get("customer", 0),
        "related_parties_count": by_type.get("related_party", 0),
        "unknown_count": by_type.get("unknown", 0),
    }
    
    logger.info(f"[extract_all_entities] Summary: {summary}")
    
    return {
        "entities": prioritized,
        "summary": summary
    }
