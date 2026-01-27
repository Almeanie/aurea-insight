"""
Tests for Audit Trail module.
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.audit_trail import AuditRecord, AuditTrail


class TestAuditRecordBasics:
    """Test basic AuditRecord functionality."""
    
    def test_create_audit_record(self):
        """Test creating an audit record."""
        record = AuditRecord(
            audit_id="AUD-001",
            company_id="COMP-001"
        )
        
        assert record.audit_id == "AUD-001"
        assert record.company_id == "COMP-001"
        assert isinstance(record.created_at, datetime)
        assert record.created_by == "system"
    
    def test_record_defaults(self):
        """Test audit record default values."""
        record = AuditRecord(
            audit_id="AUD-001",
            company_id="COMP-001"
        )
        
        assert record.input_type == "synthetic"
        assert record.gemini_interactions == []
        assert record.reasoning_chain == []
        assert record.findings == []
        assert record.ajes == []


class TestReasoningChain:
    """Test reasoning chain management."""
    
    def test_add_reasoning_step(self):
        """Test adding a reasoning step."""
        record = AuditRecord(audit_id="AUD-001", company_id="COMP-001")
        
        record.add_reasoning_step("Starting audit")
        
        assert len(record.reasoning_chain) == 1
        assert record.reasoning_chain[0]["step"] == "Starting audit"
        assert "timestamp" in record.reasoning_chain[0]
    
    def test_multiple_reasoning_steps(self):
        """Test adding multiple reasoning steps."""
        record = AuditRecord(audit_id="AUD-001", company_id="COMP-001")
        
        record.add_reasoning_step("Step 1")
        record.add_reasoning_step("Step 2")
        record.add_reasoning_step("Step 3")
        
        assert len(record.reasoning_chain) == 3


class TestGeminiInteractions:
    """Test Gemini interaction logging."""
    
    def test_add_gemini_interaction(self):
        """Test adding a Gemini interaction."""
        record = AuditRecord(audit_id="AUD-001", company_id="COMP-001")
        
        interaction = {
            "timestamp": datetime.utcnow().isoformat(),
            "purpose": "finding_explanation",
            "prompt_hash": "abc123"
        }
        
        record.add_gemini_interaction(interaction)
        
        assert len(record.gemini_interactions) == 1
        assert record.gemini_interactions[0]["purpose"] == "finding_explanation"


class TestFindings:
    """Test finding management."""
    
    def test_add_finding(self, sample_finding):
        """Test adding a finding."""
        record = AuditRecord(audit_id="AUD-001", company_id="COMP-001")
        
        record.add_finding(sample_finding)
        
        assert len(record.findings) == 1
        assert record.findings[0]["finding_id"] == "FND-001"
    
    def test_add_multiple_findings(self, sample_findings_list):
        """Test adding multiple findings."""
        record = AuditRecord(audit_id="AUD-001", company_id="COMP-001")
        
        for finding in sample_findings_list:
            record.add_finding(finding)
        
        assert len(record.findings) == len(sample_findings_list)


class TestAJEs:
    """Test AJE management."""
    
    def test_add_aje(self):
        """Test adding an AJE."""
        record = AuditRecord(audit_id="AUD-001", company_id="COMP-001")
        
        aje = {
            "aje_id": "AJE-001",
            "description": "Adjust prepaid expense",
            "total_debits": 1000,
            "total_credits": 1000
        }
        
        record.add_aje(aje)
        
        assert len(record.ajes) == 1
        assert record.ajes[0]["aje_id"] == "AJE-001"


class TestExecutionSteps:
    """Test execution step logging."""
    
    def test_add_execution_step(self):
        """Test adding an execution step."""
        record = AuditRecord(audit_id="AUD-001", company_id="COMP-001")
        
        record.add_execution_step("gaap_check", {"rules_applied": 10, "findings": 3})
        
        assert len(record.execution_steps) == 1
        assert record.execution_steps[0]["step"] == "gaap_check"
        assert record.execution_steps[0]["details"]["rules_applied"] == 10


class TestIntegrityHash:
    """Test integrity hash computation."""
    
    def test_compute_integrity_hash(self):
        """Test computing integrity hash."""
        record = AuditRecord(audit_id="AUD-001", company_id="COMP-001")
        record.add_reasoning_step("Test step")
        
        hash_value = record.compute_integrity_hash()
        
        assert hash_value is not None
        assert len(hash_value) == 64  # SHA-256 hex digest length
        assert record.record_integrity_hash == hash_value
    
    def test_hash_changes_with_content(self):
        """Test that hash changes when content changes."""
        record1 = AuditRecord(audit_id="AUD-001", company_id="COMP-001")
        record1.add_reasoning_step("Step A")
        hash1 = record1.compute_integrity_hash()
        
        record2 = AuditRecord(audit_id="AUD-001", company_id="COMP-001")
        record2.add_reasoning_step("Step B")
        hash2 = record2.compute_integrity_hash()
        
        assert hash1 != hash2
    
    def test_hash_reproducible(self):
        """Test that hash is reproducible for same content."""
        record = AuditRecord(audit_id="AUD-001", company_id="COMP-001")
        record.add_reasoning_step("Test step")
        
        hash1 = record.compute_integrity_hash()
        hash2 = record.compute_integrity_hash()
        
        assert hash1 == hash2


class TestToDict:
    """Test dictionary conversion."""
    
    def test_to_dict(self):
        """Test converting record to dictionary."""
        record = AuditRecord(
            audit_id="AUD-001",
            company_id="COMP-001",
            created_by="test_user"
        )
        record.add_reasoning_step("Test")
        
        result = record.to_dict()
        
        assert isinstance(result, dict)
        assert result["audit_id"] == "AUD-001"
        assert result["company_id"] == "COMP-001"
        assert result["created_by"] == "test_user"


class TestRegulatoryReport:
    """Test regulatory report generation."""
    
    def test_to_regulatory_report(self):
        """Test generating regulatory report."""
        record = AuditRecord(audit_id="AUD-001", company_id="COMP-001")
        record.add_reasoning_step("Started audit")
        record.add_finding({
            "finding_id": "FND-001",
            "severity": "high",
            "issue": "Test finding"
        })
        
        report = record.to_regulatory_report()
        
        assert isinstance(report, str)
        assert "AUDIT TRAIL REPORT" in report
        assert "AUD-001" in report
        assert "COMP-001" in report
        assert "REASONING CHAIN" in report
        assert "FINDINGS" in report
        assert "DISCLAIMER" in report


class TestAuditTrailManager:
    """Test AuditTrail manager class."""
    
    def test_create_record(self):
        """Test creating a record through manager."""
        trail = AuditTrail()
        
        record = trail.create_record(
            audit_id="AUD-001",
            company_id="COMP-001",
            created_by="api"
        )
        
        assert record.audit_id == "AUD-001"
        assert "AUD-001" in trail.records
    
    def test_get_record(self):
        """Test retrieving a record."""
        trail = AuditTrail()
        trail.create_record(audit_id="AUD-001", company_id="COMP-001")
        
        record = trail.get_record("AUD-001")
        
        assert record is not None
        assert record.audit_id == "AUD-001"
    
    def test_get_nonexistent_record(self):
        """Test getting a record that doesn't exist."""
        trail = AuditTrail()
        
        record = trail.get_record("NONEXISTENT")
        
        assert record is None
    
    def test_finalize_record(self):
        """Test finalizing a record."""
        trail = AuditTrail()
        trail.create_record(audit_id="AUD-001", company_id="COMP-001")
        
        hash_value = trail.finalize_record("AUD-001")
        
        assert hash_value is not None
        assert len(hash_value) == 64
    
    def test_finalize_nonexistent_record(self):
        """Test finalizing a nonexistent record."""
        trail = AuditTrail()
        
        result = trail.finalize_record("NONEXISTENT")
        
        assert result is None
    
    def test_export_record(self):
        """Test exporting a record."""
        trail = AuditTrail()
        trail.create_record(audit_id="AUD-001", company_id="COMP-001")
        
        exported = trail.export_record("AUD-001")
        
        assert isinstance(exported, dict)
        assert exported["audit_id"] == "AUD-001"
    
    def test_export_nonexistent_record(self):
        """Test exporting a nonexistent record."""
        trail = AuditTrail()
        
        result = trail.export_record("NONEXISTENT")
        
        assert result is None


class TestMultipleRecords:
    """Test managing multiple records."""
    
    def test_multiple_records(self):
        """Test creating and managing multiple records."""
        trail = AuditTrail()
        
        trail.create_record("AUD-001", "COMP-001")
        trail.create_record("AUD-002", "COMP-002")
        trail.create_record("AUD-003", "COMP-001")
        
        assert len(trail.records) == 3
        assert trail.get_record("AUD-001") is not None
        assert trail.get_record("AUD-002") is not None
        assert trail.get_record("AUD-003") is not None
