"""
CSV Export
Exports audit data as CSV.
"""
import csv
import io


def generate_findings_csv(findings: list[dict]) -> str:
    """Generate CSV of audit findings."""
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Finding ID",
        "Severity",
        "Category",
        "Issue",
        "Details",
        "GAAP Principle",
        "Recommendation",
        "Confidence"
    ])
    
    # Data rows
    for finding in findings:
        writer.writerow([
            finding.get("finding_id", ""),
            finding.get("severity", ""),
            finding.get("category", ""),
            finding.get("issue", ""),
            finding.get("details", ""),
            finding.get("gaap_principle", ""),
            finding.get("recommendation", ""),
            finding.get("confidence", "")
        ])
    
    return output.getvalue()


def generate_ajes_csv(ajes: list[dict]) -> str:
    """Generate CSV of Adjusting Journal Entries."""
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "AJE ID",
        "Date",
        "Account Code",
        "Account Name",
        "Debit",
        "Credit",
        "Description",
        "Finding Reference"
    ])
    
    # Data rows
    for aje in ajes:
        for entry in aje.get("entries", []):
            writer.writerow([
                aje.get("aje_id", ""),
                aje.get("date", ""),
                entry.get("account_code", ""),
                entry.get("account_name", ""),
                entry.get("debit", 0),
                entry.get("credit", 0),
                aje.get("description", ""),
                aje.get("finding_reference", "")
            ])
    
    return output.getvalue()
