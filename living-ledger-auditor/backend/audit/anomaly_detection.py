"""
Anomaly Detection
Statistical methods for detecting unusual patterns.
"""
import statistics
from collections import Counter
import uuid
from loguru import logger

from core.schemas import GeneralLedger, Severity, FindingCategory


class AnomalyDetector:
    """Detects statistical anomalies in financial data."""
    
    def detect_anomalies(self, gl: GeneralLedger) -> list[dict]:
        """Run all anomaly detection algorithms."""
        logger.info("[detect_anomalies] Starting anomaly detection")
        logger.info(f"[detect_anomalies] Analyzing {len(gl.entries) if gl else 0} GL entries")
        
        findings = []
        
        logger.info("[detect_anomalies] Running Benford's Law analysis")
        benford_findings = self._benfords_law_analysis(gl)
        findings.extend(benford_findings)
        logger.info(f"[detect_anomalies] Benford's Law: {len(benford_findings)} findings")
        
        logger.info("[detect_anomalies] Running statistical outlier detection")
        outlier_findings = self._statistical_outliers(gl)
        findings.extend(outlier_findings)
        logger.info(f"[detect_anomalies] Statistical outliers: {len(outlier_findings)} findings")
        
        logger.info("[detect_anomalies] Running timing anomaly detection")
        timing_findings = self._timing_anomalies(gl)
        findings.extend(timing_findings)
        logger.info(f"[detect_anomalies] Timing anomalies: {len(timing_findings)} findings")
        
        logger.info(f"[detect_anomalies] Total anomaly findings: {len(findings)}")
        return findings
    
    def _benfords_law_analysis(self, gl: GeneralLedger) -> list[dict]:
        """
        Benford's Law: First digits in natural datasets follow specific distribution.
        Deviation may indicate fabricated numbers.
        """
        findings = []
        
        # Expected Benford distribution
        BENFORD_EXPECTED = {
            1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097,
            5: 0.079, 6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046
        }
        
        # Get first digits of all amounts
        first_digits = []
        for entry in gl.entries:
            amount = entry.debit if entry.debit > 0 else entry.credit
            if amount > 0:
                first_digit = int(str(abs(amount)).lstrip("0").replace(".", "")[0])
                if 1 <= first_digit <= 9:
                    first_digits.append(first_digit)
        
        if len(first_digits) < 50:
            return findings  # Not enough data
        
        # Calculate actual distribution
        total = len(first_digits)
        actual = Counter(first_digits)
        actual_dist = {d: actual.get(d, 0) / total for d in range(1, 10)}
        
        # Chi-square test
        chi_square = sum(
            ((actual_dist.get(d, 0) - BENFORD_EXPECTED[d]) ** 2) / BENFORD_EXPECTED[d]
            for d in range(1, 10)
        )
        
        # Critical value at 0.05 significance (df=8) is 15.507
        if chi_square > 15.507:
            findings.append({
                "finding_id": f"BEN-{uuid.uuid4().hex[:8]}",
                "category": FindingCategory.FRAUD.value,
                "severity": Severity.MEDIUM.value,
                "issue": "Benford's Law Deviation",
                "details": f"Transaction amounts deviate from expected first-digit distribution (chi-square: {chi_square:.2f}). This may indicate fabricated or manipulated numbers.",
                "recommendation": "Review transactions for potential data manipulation or fraud",
                "confidence": min(chi_square / 30, 0.95),
                "gaap_principle": "Data Integrity",
                "detection_method": f"Statistical analysis: Benford's Law chi-square test (value: {chi_square:.2f}, critical: 15.507)"
            })
        
        return findings
    
    def _statistical_outliers(self, gl: GeneralLedger) -> list[dict]:
        """Detect statistical outliers using Z-score."""
        findings = []
        
        amounts = [e.debit for e in gl.entries if e.debit > 0]
        
        if len(amounts) < 10:
            return findings
        
        mean = statistics.mean(amounts)
        stdev = statistics.stdev(amounts)
        
        if stdev == 0:
            return findings
        
        for entry in gl.entries:
            if entry.debit > 0:
                z_score = (entry.debit - mean) / stdev
                
                if abs(z_score) > 3:
                    findings.append({
                        "finding_id": f"OUT-{uuid.uuid4().hex[:8]}",
                        "category": FindingCategory.FRAUD.value,
                        "severity": Severity.MEDIUM.value,
                        "issue": "Statistical Outlier",
                        "details": f"Transaction of ${entry.debit:,.2f} is {abs(z_score):.1f} standard deviations from mean (${mean:,.2f})",
                        "affected_transactions": [entry.entry_id],
                        "recommendation": "Verify this unusual transaction amount",
                        "confidence": min(abs(z_score) / 5, 0.90),
                        "gaap_principle": "Transaction Validity",
                        "detection_method": f"Statistical analysis: Z-score outlier detection (z={z_score:.2f}, threshold=3.0)"
                    })
        
        return findings
    
    def _timing_anomalies(self, gl: GeneralLedger) -> list[dict]:
        """Detect unusual timing patterns."""
        findings = []
        
        # Group entries by date
        entries_by_date = {}
        for entry in gl.entries:
            date = entry.date
            if date not in entries_by_date:
                entries_by_date[date] = []
            entries_by_date[date].append(entry)
        
        # Check for unusual spikes in activity
        counts = [len(entries) for entries in entries_by_date.values()]
        
        if len(counts) > 5:
            mean_count = statistics.mean(counts)
            stdev_count = statistics.stdev(counts) if len(counts) > 1 else 0
            
            for date, entries in entries_by_date.items():
                if stdev_count > 0:
                    z_score = (len(entries) - mean_count) / stdev_count
                    
                    if z_score > 2.5:
                        findings.append({
                            "finding_id": f"TME-{uuid.uuid4().hex[:8]}",
                            "category": FindingCategory.TIMING.value,
                            "severity": Severity.LOW.value,
                            "issue": "Unusual Activity Spike",
                            "details": f"Date {date} has {len(entries)} entries, significantly higher than average ({mean_count:.1f})",
                            "recommendation": "Review transactions on this date for unusual patterns",
                            "confidence": 0.65,
                            "gaap_principle": "Transaction Timing",
                            "detection_method": f"Statistical analysis: Daily volume Z-score (z={z_score:.2f}, threshold=2.5)"
                        })
        
        return findings
