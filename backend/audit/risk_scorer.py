"""
Risk Scorer
Calculates overall risk assessment from findings.
"""
from collections import defaultdict

from core.schemas import Severity


class RiskScorer:
    """Calculates risk scores from audit findings."""
    
    SEVERITY_WEIGHTS = {
        Severity.CRITICAL.value: 10,
        Severity.HIGH.value: 5,
        Severity.MEDIUM.value: 2,
        Severity.LOW.value: 1,
        "critical": 10,
        "high": 5,
        "medium": 2,
        "low": 1
    }
    
    def calculate(self, findings: list[dict]) -> dict:
        """Calculate composite risk score."""
        
        if not findings:
            return {
                "overall_score": 0,
                "risk_level": "low",
                "total_findings": 0,
                "critical_count": 0,
                "high_count": 0,
                "medium_count": 0,
                "low_count": 0,
                "category_breakdown": {},
                "requires_immediate_action": False,
                "interpretation": "No findings identified. Financial statements appear materially correct."
            }
        
        # Count by severity
        critical_count = sum(1 for f in findings if f.get("severity") in ["critical", Severity.CRITICAL.value])
        high_count = sum(1 for f in findings if f.get("severity") in ["high", Severity.HIGH.value])
        medium_count = sum(1 for f in findings if f.get("severity") in ["medium", Severity.MEDIUM.value])
        low_count = sum(1 for f in findings if f.get("severity") in ["low", Severity.LOW.value])
        
        # Calculate raw score
        raw_score = (
            critical_count * self.SEVERITY_WEIGHTS["critical"] +
            high_count * self.SEVERITY_WEIGHTS["high"] +
            medium_count * self.SEVERITY_WEIGHTS["medium"] +
            low_count * self.SEVERITY_WEIGHTS["low"]
        )
        
        # Normalize to 0-100 scale
        max_possible = len(findings) * 10  # If all were critical
        normalized_score = min(100, (raw_score / max(max_possible, 1)) * 100)
        
        # Determine risk level
        if normalized_score >= 75 or critical_count >= 2:
            risk_level = "critical"
        elif normalized_score >= 50 or critical_count >= 1:
            risk_level = "high"
        elif normalized_score >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Category breakdown
        category_scores = defaultdict(float)
        for finding in findings:
            category = finding.get("category", "unknown")
            severity = finding.get("severity", "low")
            category_scores[category] += self.SEVERITY_WEIGHTS.get(severity, 1)
        
        # Interpretation
        interpretation = self._generate_interpretation(
            risk_level, critical_count, high_count, len(findings)
        )
        
        return {
            "overall_score": round(normalized_score, 1),
            "risk_level": risk_level,
            "total_findings": len(findings),
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "category_breakdown": dict(category_scores),
            "requires_immediate_action": risk_level in ["critical", "high"],
            "interpretation": interpretation
        }
    
    def _generate_interpretation(
        self,
        risk_level: str,
        critical_count: int,
        high_count: int,
        total: int
    ) -> str:
        """Generate human-readable interpretation."""
        
        if risk_level == "critical":
            return (
                f"CRITICAL RISK: {critical_count} critical findings require immediate attention. "
                f"Material misstatement or fraud indicators present. "
                f"Do not rely on these financial statements without remediation."
            )
        elif risk_level == "high":
            return (
                f"HIGH RISK: {critical_count + high_count} significant findings identified. "
                f"Material misstatement possible. "
                f"Recommend immediate review and corrective action before relying on statements."
            )
        elif risk_level == "medium":
            return (
                f"MEDIUM RISK: {total} findings identified, mostly non-critical. "
                f"Some control weaknesses present. "
                f"Recommend addressing findings to strengthen internal controls."
            )
        else:
            return (
                f"LOW RISK: {total} minor findings identified. "
                f"No material issues detected. "
                f"Financial statements appear reliable with minor improvements recommended."
            )
