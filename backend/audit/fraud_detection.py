"""
Fraud Detection
Algorithms for detecting fraud patterns.
"""
from collections import defaultdict
from datetime import datetime, timedelta
import uuid
from loguru import logger

from core.schemas import GeneralLedger, Severity, FindingCategory


# US Federal Holidays (approximate - some dates vary by year)
US_HOLIDAYS = [
    (1, 1),   # New Year's Day
    (7, 4),   # Independence Day
    (12, 25), # Christmas Day
    (12, 24), # Christmas Eve (often observed)
    (11, 11), # Veterans Day
    (1, 15),  # MLK Day (approximate - 3rd Monday)
    (2, 15),  # Presidents Day (approximate - 3rd Monday)
    (5, 25),  # Memorial Day (approximate - last Monday)
    (9, 1),   # Labor Day (approximate - 1st Monday)
    (10, 10), # Columbus Day (approximate - 2nd Monday)
    (11, 25), # Thanksgiving (approximate - 4th Thursday)
]


class FraudDetector:
    """Detects potential fraud patterns."""
    
    def _entry_to_transaction_detail(self, entry) -> dict:
        """Convert a GL entry to transaction detail format for frontend display."""
        return {
            "entry_id": entry.entry_id,
            "date": str(entry.date),
            "account_code": entry.account_code,
            "account_name": entry.account_name or entry.account_code,
            "description": entry.description or "",
            "debit": entry.debit,
            "credit": entry.credit,
            "vendor": entry.vendor_or_customer
        }
    
    def detect_fraud_patterns(self, gl: GeneralLedger) -> list[dict]:
        """Run all fraud detection algorithms."""
        logger.info("[detect_fraud_patterns] Starting fraud pattern detection")
        logger.info(f"[detect_fraud_patterns] Analyzing {len(gl.entries) if gl else 0} GL entries")
        
        findings = []
        
        logger.info("[detect_fraud_patterns] Checking for duplicate payments")
        dup_findings = self._detect_duplicate_payments(gl)
        findings.extend(dup_findings)
        logger.info(f"[detect_fraud_patterns] Duplicate payments: {len(dup_findings)} findings")
        
        logger.info("[detect_fraud_patterns] Checking for structuring/smurfing")
        struct_findings = self._detect_structuring(gl)
        findings.extend(struct_findings)
        logger.info(f"[detect_fraud_patterns] Structuring: {len(struct_findings)} findings")
        
        logger.info("[detect_fraud_patterns] Checking for round number patterns")
        round_findings = self._detect_round_numbers(gl)
        findings.extend(round_findings)
        logger.info(f"[detect_fraud_patterns] Round numbers: {len(round_findings)} findings")
        
        logger.info("[detect_fraud_patterns] Checking for vendor anomalies")
        vendor_findings = self._detect_vendor_anomalies(gl)
        findings.extend(vendor_findings)
        logger.info(f"[detect_fraud_patterns] Vendor anomalies: {len(vendor_findings)} findings")
        
        logger.info("[detect_fraud_patterns] Checking for round-tripping patterns")
        round_trip_findings = self._detect_round_tripping(gl)
        findings.extend(round_trip_findings)
        logger.info(f"[detect_fraud_patterns] Round-tripping: {len(round_trip_findings)} findings")
        
        logger.info("[detect_fraud_patterns] Checking for weekend/holiday transactions")
        weekend_findings = self._detect_weekend_holiday_transactions(gl)
        findings.extend(weekend_findings)
        logger.info(f"[detect_fraud_patterns] Weekend/holiday: {len(weekend_findings)} findings")
        
        logger.info("[detect_fraud_patterns] Checking for shared addresses")
        address_findings = self._detect_shared_addresses(gl)
        findings.extend(address_findings)
        logger.info(f"[detect_fraud_patterns] Shared addresses: {len(address_findings)} findings")
        
        logger.info(f"[detect_fraud_patterns] Total fraud findings: {len(findings)}")
        return findings
    
    def _detect_duplicate_payments(self, gl: GeneralLedger) -> list[dict]:
        """Detect potential duplicate payments."""
        findings = []
        
        # Group by vendor + amount + date proximity
        vendor_payments = defaultdict(list)
        
        for entry in gl.entries:
            if entry.debit > 0 and entry.vendor_or_customer:
                key = (entry.vendor_or_customer.lower(), entry.debit)
                vendor_payments[key].append(entry)
        
        for (vendor, amount), entries in vendor_payments.items():
            if len(entries) >= 2:
                # Check if dates are close
                dates = [datetime.strptime(e.date, "%Y-%m-%d") for e in entries]
                dates.sort()
                
                for i in range(1, len(dates)):
                    if (dates[i] - dates[i-1]).days <= 7:
                        findings.append({
                            "finding_id": f"DUP-{uuid.uuid4().hex[:8]}",
                            "category": FindingCategory.FRAUD.value,
                            "severity": Severity.HIGH.value,
                            "issue": "Potential Duplicate Payment",
                            "details": f"Multiple payments of ${amount:,.2f} to {vendor} within 7 days",
                            "affected_transactions": [e.entry_id for e in entries],
                            "transaction_details": [self._entry_to_transaction_detail(e) for e in entries],
                            "recommendation": "Verify these are not duplicate payments for the same invoice",
                            "confidence": 0.80,
                            "gaap_principle": "Payment Controls",
                            "detection_method": "Rule-based pattern matching: Same vendor + same amount + date proximity analysis"
                        })
                        break
        
        return findings
    
    def _detect_structuring(self, gl: GeneralLedger) -> list[dict]:
        """
        Detect structuring (smurfing) - breaking transactions to avoid thresholds.
        Bank Secrecy Act requires reporting transactions over $10,000.
        """
        findings = []
        threshold = 10000
        
        # Look for multiple transactions just under threshold
        suspicious_range = (threshold * 0.8, threshold)
        
        vendor_groups = defaultdict(list)
        for entry in gl.entries:
            if entry.debit > 0:
                if suspicious_range[0] <= entry.debit < suspicious_range[1]:
                    vendor = entry.vendor_or_customer or "Unknown"
                    vendor_groups[vendor].append(entry)
        
        for vendor, entries in vendor_groups.items():
            if len(entries) >= 3:
                total = sum(e.debit for e in entries)
                findings.append({
                    "finding_id": f"STR-{uuid.uuid4().hex[:8]}",
                    "category": FindingCategory.FRAUD.value,
                    "severity": Severity.CRITICAL.value,
                    "issue": "Potential Structuring/Smurfing",
                    "details": f"{len(entries)} transactions between ${suspicious_range[0]:,.0f}-${suspicious_range[1]:,.0f} to {vendor}, totaling ${total:,.2f}. This pattern may indicate structuring to avoid reporting thresholds.",
                    "affected_transactions": [e.entry_id for e in entries],
                    "transaction_details": [self._entry_to_transaction_detail(e) for e in entries],
                    "recommendation": "Investigate for potential Bank Secrecy Act violations. Consider filing SAR if warranted.",
                    "confidence": 0.75,
                    "gaap_principle": "Bank Secrecy Act Compliance",
                    "detection_method": "Rule-based threshold analysis: Detecting transactions clustered just below $10,000 reporting threshold"
                })
        
        return findings
    
    def _detect_round_numbers(self, gl: GeneralLedger) -> list[dict]:
        """Detect suspiciously round transaction amounts."""
        findings = []
        
        round_amounts = [1000, 2000, 2500, 5000, 10000, 25000, 50000]
        round_entries = []
        
        for entry in gl.entries:
            if entry.debit in round_amounts and entry.debit >= 1000:
                round_entries.append(entry)
        
        if len(round_entries) >= 3:
            total = sum(e.debit for e in round_entries)
            findings.append({
                "finding_id": f"RND-{uuid.uuid4().hex[:8]}",
                "category": FindingCategory.FRAUD.value,
                "severity": Severity.MEDIUM.value,
                "issue": "Multiple Round-Number Transactions",
                "details": f"{len(round_entries)} transactions with suspiciously round amounts totaling ${total:,.2f}. Natural transactions rarely result in perfectly round numbers.",
                "affected_transactions": [e.entry_id for e in round_entries],
                "transaction_details": [self._entry_to_transaction_detail(e) for e in round_entries],
                "recommendation": "Review supporting documentation for these transactions",
                "confidence": 0.60,
                "gaap_principle": "Fraud Detection - Red Flags",
                "detection_method": "Statistical analysis: Round number frequency detection ($1000, $2500, $5000, etc.)"
            })
        
        return findings
    
    def _detect_vendor_anomalies(self, gl: GeneralLedger) -> list[dict]:
        """Detect unusual vendor patterns."""
        findings = []
        
        # Check for generic vendor names (potential shell company indicators)
        generic_indicators = [
            "consulting", "services", "solutions", "management",
            "enterprises", "holdings", "global", "international"
        ]
        
        vendor_totals = defaultdict(float)
        for entry in gl.entries:
            if entry.debit > 0 and entry.vendor_or_customer:
                vendor_totals[entry.vendor_or_customer] += entry.debit
        
        # Also collect entries by vendor for transaction details
        vendor_entries = defaultdict(list)
        for entry in gl.entries:
            if entry.debit > 0 and entry.vendor_or_customer:
                vendor_entries[entry.vendor_or_customer].append(entry)
        
        for vendor, total in vendor_totals.items():
            vendor_lower = vendor.lower()
            generic_count = sum(1 for ind in generic_indicators if ind in vendor_lower)
            
            if generic_count >= 2 and total > 10000:
                entries = vendor_entries.get(vendor, [])
                findings.append({
                    "finding_id": f"VND-{uuid.uuid4().hex[:8]}",
                    "category": FindingCategory.FRAUD.value,
                    "severity": Severity.MEDIUM.value,
                    "issue": "Generic Vendor Name Pattern",
                    "details": f"Vendor '{vendor}' has generic naming patterns common to shell companies. Total payments: ${total:,.2f}",
                    "affected_transactions": [e.entry_id for e in entries],
                    "transaction_details": [self._entry_to_transaction_detail(e) for e in entries[:20]],
                    "recommendation": "Verify vendor legitimacy - check for physical address, tax ID, business registration",
                    "confidence": 0.55,
                    "gaap_principle": "Vendor Due Diligence",
                    "detection_method": "Text analysis: Detecting generic naming patterns (consulting, services, holdings, etc.)"
                })
        
        return findings
    
    def _detect_round_tripping(self, gl: GeneralLedger) -> list[dict]:
        """
        Detect round-tripping: circular money flows where funds return to origin.
        Pattern: Company pays A -> A pays B -> B pays back to Company
        This is detected by finding:
        1. Payments out to vendors
        2. Receipts from customers within a time window
        3. Similar amounts suggesting money cycling
        """
        findings = []
        
        # Build payment/receipt maps - store entry objects for transaction_details
        payments = []  # (date, vendor, amount, entry_id, entry_object)
        receipts = []  # (date, customer, amount, entry_id, entry_object)
        
        for entry in gl.entries:
            try:
                entry_date = datetime.strptime(entry.date, "%Y-%m-%d")
            except (ValueError, TypeError):
                continue
                
            if entry.debit > 0 and entry.vendor_or_customer:
                payments.append((entry_date, entry.vendor_or_customer, entry.debit, entry.entry_id, entry))
            elif entry.credit > 0 and entry.vendor_or_customer:
                receipts.append((entry_date, entry.vendor_or_customer, entry.credit, entry.entry_id, entry))
        
        # Look for round-trip patterns: similar amounts within 30 days
        tolerance = 0.05  # 5% tolerance for similar amounts
        time_window = timedelta(days=30)
        
        suspicious_patterns = []
        
        for pay_date, vendor, pay_amount, pay_id, pay_entry in payments:
            if pay_amount < 5000:  # Skip small amounts
                continue
                
            for rec_date, customer, rec_amount, rec_id, rec_entry in receipts:
                if rec_amount < 5000:
                    continue
                    
                # Check time window (receipt should be after payment)
                if rec_date < pay_date or (rec_date - pay_date) > time_window:
                    continue
                
                # Check amount similarity
                amount_diff = abs(pay_amount - rec_amount) / pay_amount
                if amount_diff <= tolerance:
                    # Check if different entities (not self-payment)
                    if vendor.lower() != customer.lower():
                        suspicious_patterns.append({
                            "payment": (pay_date, vendor, pay_amount, pay_id),
                            "receipt": (rec_date, customer, rec_amount, rec_id),
                            "payment_entry": pay_entry,
                            "receipt_entry": rec_entry,
                            "amount_match": 1 - amount_diff
                        })
        
        # Group suspicious patterns
        if len(suspicious_patterns) >= 2:
            total_amount = sum(p["payment"][2] for p in suspicious_patterns)
            # Build transaction details from payment and receipt entries
            all_entries = []
            for p in suspicious_patterns[:10]:  # Limit to first 10 patterns
                all_entries.append(p["payment_entry"])
                all_entries.append(p["receipt_entry"])
            
            findings.append({
                "finding_id": f"RTR-{uuid.uuid4().hex[:8]}",
                "category": FindingCategory.FRAUD.value,
                "severity": Severity.CRITICAL.value,
                "issue": "Potential Round-Tripping Pattern",
                "details": f"Found {len(suspicious_patterns)} instances where payments to vendors were matched by similar receipts from customers within 30 days. Total amount: ${total_amount:,.2f}. This pattern may indicate circular money flows.",
                "affected_transactions": [p["payment"][3] for p in suspicious_patterns] + [p["receipt"][3] for p in suspicious_patterns],
                "transaction_details": [self._entry_to_transaction_detail(e) for e in all_entries],
                "patterns": [
                    {
                        "paid_to": p["payment"][1],
                        "amount_paid": p["payment"][2],
                        "received_from": p["receipt"][1],
                        "amount_received": p["receipt"][2],
                        "days_between": (p["receipt"][0] - p["payment"][0]).days
                    }
                    for p in suspicious_patterns[:5]  # Limit to first 5 for readability
                ],
                "recommendation": "Investigate business purpose of these transactions. Verify vendor/customer relationships. Check for common ownership.",
                "confidence": 0.70,
                "gaap_principle": "Anti-Money Laundering / Fraud Detection",
                "detection_method": "Pattern analysis: Detecting circular money flows (payment -> receipt pattern with similar amounts within 30 days)"
            })
        
        return findings
    
    def _detect_weekend_holiday_transactions(self, gl: GeneralLedger) -> list[dict]:
        """
        Detect transactions posted on weekends or holidays.
        These may indicate backdating or unauthorized access.
        """
        findings = []
        weekend_entries = []  # List of original entry objects
        holiday_entries = []  # List of original entry objects
        
        for entry in gl.entries:
            try:
                entry_date = datetime.strptime(entry.date, "%Y-%m-%d")
            except (ValueError, TypeError):
                continue
            
            # Check for weekend (5 = Saturday, 6 = Sunday)
            if entry_date.weekday() >= 5:
                weekend_entries.append(entry)
            
            # Check for holiday
            if (entry_date.month, entry_date.day) in US_HOLIDAYS:
                holiday_entries.append(entry)
        
        # Flag if significant weekend activity
        if len(weekend_entries) >= 3:
            total_amount = sum(e.debit if e.debit > 0 else e.credit for e in weekend_entries)
            findings.append({
                "finding_id": f"WKD-{uuid.uuid4().hex[:8]}",
                "category": FindingCategory.FRAUD.value,
                "severity": Severity.LOW.value,
                "issue": "Weekend Transaction Activity",
                "details": f"{len(weekend_entries)} transactions posted on weekends totaling ${total_amount:,.2f}. Weekend entries may indicate backdating or system access outside normal business hours.",
                "affected_transactions": [e.entry_id for e in weekend_entries],
                "transaction_details": [self._entry_to_transaction_detail(e) for e in weekend_entries[:20]],  # Limit to 20
                "recommendation": "Verify these entries were legitimately posted and properly authorized. Check system access logs.",
                "confidence": 0.50,
                "gaap_principle": "Internal Controls - Access Management",
                "detection_method": "Temporal analysis: Detecting transactions posted on Saturday/Sunday"
            })
        
        # Flag holiday entries
        if len(holiday_entries) >= 2:
            total_amount = sum(e.debit if e.debit > 0 else e.credit for e in holiday_entries)
            findings.append({
                "finding_id": f"HOL-{uuid.uuid4().hex[:8]}",
                "category": FindingCategory.FRAUD.value,
                "severity": Severity.LOW.value,
                "issue": "Holiday Transaction Activity",
                "details": f"{len(holiday_entries)} transactions posted on US holidays totaling ${total_amount:,.2f}. Holiday entries are unusual and may indicate backdating.",
                "affected_transactions": [e.entry_id for e in holiday_entries],
                "transaction_details": [self._entry_to_transaction_detail(e) for e in holiday_entries[:20]],  # Limit to 20
                "recommendation": "Verify authorization and business purpose for transactions posted on holidays.",
                "confidence": 0.45,
                "gaap_principle": "Internal Controls - Temporal Validation",
                "detection_method": "Temporal analysis: Detecting transactions posted on US federal holidays"
            })
        
        return findings
    
    def _detect_shared_addresses(self, gl: GeneralLedger) -> list[dict]:
        """
        Detect vendors/customers that may share addresses.
        This indicates potential related party relationships.
        
        Note: This is a heuristic based on vendor name patterns when 
        actual address data is not available.
        """
        findings = []
        
        # Collect unique vendors and customers, and their entries
        vendors = set()
        customers = set()
        entity_entries = defaultdict(list)  # Store entries for each entity
        
        for entry in gl.entries:
            if entry.vendor_or_customer:
                entity = entry.vendor_or_customer.strip()
                entity_entries[entity].append(entry)
                if entry.debit > 0:
                    vendors.add(entity)
                elif entry.credit > 0:
                    customers.add(entity)
        
        # Check for entities appearing as both vendor and customer (self-dealing indicator)
        both_roles = vendors.intersection(customers)
        if both_roles:
            # Collect all entries for entities with both roles
            affected_entries = []
            for entity in both_roles:
                affected_entries.extend(entity_entries.get(entity, []))
            
            findings.append({
                "finding_id": f"SLF-{uuid.uuid4().hex[:8]}",
                "category": FindingCategory.FRAUD.value,
                "severity": Severity.HIGH.value,
                "issue": "Entity as Both Vendor and Customer",
                "details": f"{len(both_roles)} entities appear as both vendor and customer: {', '.join(list(both_roles)[:5])}{'...' if len(both_roles) > 5 else ''}. This pattern may indicate related party transactions or self-dealing.",
                "entities": list(both_roles),
                "affected_transactions": [e.entry_id for e in affected_entries],
                "transaction_details": [self._entry_to_transaction_detail(e) for e in affected_entries[:30]],  # Limit to 30
                "recommendation": "Verify business purpose for each transaction. Document any related party relationships. Ensure arm's length transactions.",
                "confidence": 0.75,
                "gaap_principle": "Related Party Disclosure (ASC 850)",
                "detection_method": "Entity analysis: Detecting entities in dual vendor/customer roles"
            })
        
        # Check for similar names (potential shell company networks)
        all_entities = list(vendors.union(customers))
        similar_groups = self._find_similar_entity_names(all_entities)
        
        for group in similar_groups:
            if len(group) >= 2:
                # Collect entries for all entities in the group
                group_entries = []
                for entity in group:
                    group_entries.extend(entity_entries.get(entity, []))
                
                findings.append({
                    "finding_id": f"SIM-{uuid.uuid4().hex[:8]}",
                    "category": FindingCategory.FRAUD.value,
                    "severity": Severity.MEDIUM.value,
                    "issue": "Potentially Related Entities (Similar Names)",
                    "details": f"Found {len(group)} entities with similar names: {', '.join(group)}. This may indicate related parties or shell company network.",
                    "entities": group,
                    "affected_transactions": [e.entry_id for e in group_entries],
                    "transaction_details": [self._entry_to_transaction_detail(e) for e in group_entries[:20]],  # Limit to 20
                    "recommendation": "Verify if these entities share ownership, addresses, or management. Document any related party relationships.",
                    "confidence": 0.60,
                    "gaap_principle": "Related Party Disclosure (ASC 850)",
                    "detection_method": "Text analysis: Detecting similar entity names that may indicate related parties"
                })
        
        return findings
    
    def _find_similar_entity_names(self, entities: list[str]) -> list[list[str]]:
        """Find groups of entities with similar names."""
        if len(entities) < 2:
            return []
        
        groups = []
        processed = set()
        
        for i, entity1 in enumerate(entities):
            if entity1 in processed:
                continue
            
            group = [entity1]
            e1_words = set(entity1.lower().split())
            
            for j, entity2 in enumerate(entities):
                if i == j or entity2 in processed:
                    continue
                
                e2_words = set(entity2.lower().split())
                
                # Check word overlap (at least 2 significant words in common)
                common_words = e1_words.intersection(e2_words)
                # Remove common generic words
                common_words = common_words - {"the", "and", "of", "inc", "llc", "corp", "ltd", "co"}
                
                if len(common_words) >= 2:
                    group.append(entity2)
                    processed.add(entity2)
            
            if len(group) >= 2:
                processed.add(entity1)
                groups.append(group)
        
        return groups
