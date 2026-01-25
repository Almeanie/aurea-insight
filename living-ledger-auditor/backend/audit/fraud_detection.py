"""
Fraud Detection
Algorithms for detecting fraud patterns.
"""
from collections import defaultdict
from datetime import datetime, timedelta
import uuid
from loguru import logger

from core.schemas import GeneralLedger, Severity, FindingCategory


class FraudDetector:
    """Detects potential fraud patterns."""
    
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
        
        for vendor, total in vendor_totals.items():
            vendor_lower = vendor.lower()
            generic_count = sum(1 for ind in generic_indicators if ind in vendor_lower)
            
            if generic_count >= 2 and total > 10000:
                findings.append({
                    "finding_id": f"VND-{uuid.uuid4().hex[:8]}",
                    "category": FindingCategory.FRAUD.value,
                    "severity": Severity.MEDIUM.value,
                    "issue": "Generic Vendor Name Pattern",
                    "details": f"Vendor '{vendor}' has generic naming patterns common to shell companies. Total payments: ${total:,.2f}",
                    "recommendation": "Verify vendor legitimacy - check for physical address, tax ID, business registration",
                    "confidence": 0.55,
                    "gaap_principle": "Vendor Due Diligence",
                    "detection_method": "Text analysis: Detecting generic naming patterns (consulting, services, holdings, etc.)"
                })
        
        return findings
