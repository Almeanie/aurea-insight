"""
Audit Trail - Complete logging for regulatory compliance.
Every AI decision, code generation, and finding is logged.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Any
import hashlib
import json
from loguru import logger


@dataclass
class AuditRecord:
    """Complete audit record for a single audit execution."""
    
    # Identity
    audit_id: str
    company_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    
    # Input Provenance
    input_type: str = "synthetic"  # "synthetic" or "uploaded"
    input_data_hash: Optional[str] = None
    input_snapshot_url: Optional[str] = None
    
    # AI Decision Chain (FULL TRANSPARENCY)
    gemini_interactions: list[dict] = field(default_factory=list)
    reasoning_chain: list[str] = field(default_factory=list)
    generated_code: Optional[str] = None
    code_hash: Optional[str] = None
    validation_results: Optional[dict] = None
    
    # Execution
    execution_environment: dict = field(default_factory=dict)
    execution_steps: list[dict] = field(default_factory=list)
    
    # Results
    findings: list[dict] = field(default_factory=list)
    ajes: list[dict] = field(default_factory=list)
    risk_score: Optional[dict] = None
    
    # Verification
    reproducibility_hash: Optional[str] = None
    record_integrity_hash: Optional[str] = None
    
    def add_reasoning_step(self, step: str, details: Optional[dict] = None):
        """Add a step to the reasoning chain with optional details."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "step": step,
            "details": details or {}
        }
        self.reasoning_chain.append(entry)
    
    def add_gemini_interaction(self, interaction: dict):
        """Add a Gemini interaction to the log."""
        self.gemini_interactions.append(interaction)
    
    def add_execution_step(self, step_name: str, details: dict):
        """Add an execution step."""
        self.execution_steps.append({
            "timestamp": datetime.utcnow().isoformat(),
            "step": step_name,
            "details": details
        })
    
    def add_finding(self, finding: dict):
        """Add an audit finding."""
        self.findings.append(finding)
    
    def add_aje(self, aje: dict):
        """Add an adjusting journal entry."""
        self.ajes.append(aje)
    
    def compute_integrity_hash(self) -> str:
        """Compute hash of entire record for integrity verification."""
        # Create a deterministic JSON representation
        record_dict = asdict(self)
        record_dict["record_integrity_hash"] = None  # Exclude self
        record_json = json.dumps(record_dict, sort_keys=True, default=str)
        
        self.record_integrity_hash = hashlib.sha256(record_json.encode()).hexdigest()
        return self.record_integrity_hash
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage/export."""
        return asdict(self)
    
    def to_regulatory_report(self) -> str:
        """Generate a regulator-friendly report."""
        lines = [
            f"AUDIT TRAIL REPORT",
            f"=" * 50,
            f"Audit ID: {self.audit_id}",
            f"Company ID: {self.company_id}",
            f"Created: {self.created_at.isoformat()}",
            f"Created By: {self.created_by}",
            f"",
            f"INPUT PROVENANCE",
            f"-" * 30,
            f"Type: {self.input_type}",
            f"Data Hash: {self.input_data_hash}",
            f"",
            f"AI INTERACTIONS: {len(self.gemini_interactions)} total",
            f"-" * 30,
        ]
        
        for i, interaction in enumerate(self.gemini_interactions[:5]):  # Limit for readability
            lines.append(f"  {i+1}. {interaction.get('purpose', 'Unknown')} - {interaction.get('timestamp', 'N/A')}")
        
        if len(self.gemini_interactions) > 5:
            lines.append(f"  ... and {len(self.gemini_interactions) - 5} more interactions")
        
        lines.extend([
            f"",
            f"REASONING CHAIN: {len(self.reasoning_chain)} steps",
            f"-" * 30,
        ])
        
        for step in self.reasoning_chain[:10]:
            if isinstance(step, dict):
                lines.append(f"  - {step.get('step', str(step))}")
            else:
                lines.append(f"  - {step}")
        
        lines.extend([
            f"",
            f"FINDINGS: {len(self.findings)} total",
            f"-" * 30,
        ])
        
        for finding in self.findings:
            lines.append(f"  [{finding.get('severity', 'N/A')}] {finding.get('issue', 'Unknown')}")
        
        lines.extend([
            f"",
            f"ADJUSTING ENTRIES: {len(self.ajes)} total",
            f"-" * 30,
        ])
        
        for aje in self.ajes:
            lines.append(f"  {aje.get('aje_id', 'N/A')}: {aje.get('description', 'No description')[:50]}")
        
        lines.extend([
            f"",
            f"INTEGRITY VERIFICATION",
            f"-" * 30,
            f"Record Hash: {self.record_integrity_hash or 'Not computed'}",
            f"",
            f"DISCLAIMER: This audit was performed by an AI system.",
            f"Human review is required for all findings.",
            f"This does not constitute legal or accounting advice.",
        ])
        
        return "\n".join(lines)


class AuditTrail:
    """Manager for audit trail records."""
    
    def __init__(self):
        self.records: dict[str, AuditRecord] = {}
    
    def create_record(self, audit_id: str, company_id: str, created_by: str = "system") -> AuditRecord:
        """Create a new audit record."""
        record = AuditRecord(
            audit_id=audit_id,
            company_id=company_id,
            created_by=created_by
        )
        self.records[audit_id] = record
        logger.info(f"Created audit record: {audit_id}")
        return record
    
    def get_record(self, audit_id: str) -> Optional[AuditRecord]:
        """Get an audit record by ID."""
        return self.records.get(audit_id)
    
    def finalize_record(self, audit_id: str) -> Optional[str]:
        """Finalize a record and compute integrity hash."""
        record = self.records.get(audit_id)
        if record:
            record.compute_integrity_hash()
            logger.info(f"Finalized audit record: {audit_id}, hash: {record.record_integrity_hash[:16]}...")
            return record.record_integrity_hash
        return None
    
    def export_record(self, audit_id: str) -> Optional[dict]:
        """Export a record as a dictionary."""
        record = self.records.get(audit_id)
        if record:
            return record.to_dict()
        return None


# Global audit trail instance
audit_trail = AuditTrail()
