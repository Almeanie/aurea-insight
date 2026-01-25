"""
PDF Report Generator
Generates audit reports in PDF format.
"""
from datetime import datetime


async def generate_pdf_report(
    company_data: dict,
    audit_data: dict,
    include_findings: bool = True,
    include_ajes: bool = True,
    include_audit_trail: bool = False
) -> bytes:
    """
    Generate a PDF audit report.
    
    Note: This is a simplified HTML-based implementation.
    In production, use WeasyPrint or ReportLab for proper PDF generation.
    """
    
    metadata = company_data["metadata"]
    findings = audit_data.get("findings", [])
    ajes = audit_data.get("ajes", [])
    risk_score = audit_data.get("risk_score", {})
    
    # Build HTML report
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Audit Report - {metadata.name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
        h1 {{ color: #0a0a0a; border-bottom: 2px solid #00d4ff; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 30px; }}
        .header {{ background: #0a0a0a; color: white; padding: 20px; margin-bottom: 30px; }}
        .header h1 {{ color: white; border: none; margin: 0; }}
        .summary-box {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .risk-critical {{ color: #ff3366; font-weight: bold; }}
        .risk-high {{ color: #ff6b35; font-weight: bold; }}
        .risk-medium {{ color: #fbbf24; }}
        .risk-low {{ color: #22c55e; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background: #0a0a0a; color: white; }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        .severity-badge {{ padding: 4px 8px; border-radius: 4px; color: white; font-size: 12px; }}
        .badge-critical {{ background: #ff3366; }}
        .badge-high {{ background: #ff6b35; }}
        .badge-medium {{ background: #fbbf24; color: black; }}
        .badge-low {{ background: #22c55e; }}
        .disclaimer {{ margin-top: 40px; padding: 20px; background: #fff3cd; border: 1px solid #ffc107; }}
        .footer {{ margin-top: 40px; text-align: center; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AUDIT REPORT</h1>
        <p>{metadata.name} | {metadata.reporting_period} | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
    </div>
    
    <h2>Executive Summary</h2>
    <div class="summary-box">
        <p><strong>Company:</strong> {metadata.name}</p>
        <p><strong>Industry:</strong> {metadata.industry.value}</p>
        <p><strong>Accounting Basis:</strong> {metadata.accounting_basis.value}</p>
        <p><strong>Reporting Period:</strong> {metadata.reporting_period}</p>
        <p><strong>Risk Score:</strong> <span class="risk-{risk_score.get('risk_level', 'low')}">{risk_score.get('overall_score', 0)}/100 ({risk_score.get('risk_level', 'N/A').upper()})</span></p>
        <p><strong>Total Findings:</strong> {len(findings)}</p>
    </div>
    
    <p>{risk_score.get('interpretation', '')}</p>
"""
    
    if include_findings and findings:
        html += """
    <h2>Audit Findings</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Severity</th>
            <th>Category</th>
            <th>Issue</th>
            <th>Recommendation</th>
        </tr>
"""
        for finding in findings:
            severity = finding.get('severity', 'low')
            html += f"""
        <tr>
            <td>{finding.get('finding_id', 'N/A')}</td>
            <td><span class="severity-badge badge-{severity}">{severity.upper()}</span></td>
            <td>{finding.get('category', 'N/A')}</td>
            <td>{finding.get('issue', 'N/A')}</td>
            <td>{finding.get('recommendation', 'N/A')}</td>
        </tr>
"""
        html += "</table>"
    
    if include_ajes and ajes:
        html += """
    <h2>Adjusting Journal Entries</h2>
    <table>
        <tr>
            <th>AJE ID</th>
            <th>Description</th>
            <th>Total Amount</th>
            <th>Related Finding</th>
        </tr>
"""
        for aje in ajes:
            html += f"""
        <tr>
            <td>{aje.get('aje_id', 'N/A')}</td>
            <td>{aje.get('description', 'N/A')}</td>
            <td>${aje.get('total_debits', 0):,.2f}</td>
            <td>{aje.get('finding_reference', 'N/A')}</td>
        </tr>
"""
        html += "</table>"
    
    html += """
    <div class="disclaimer">
        <h3>Important Disclaimers</h3>
        <ul>
            <li>This audit was performed by an AI system and requires human review.</li>
            <li>This report does not constitute legal or accounting advice.</li>
            <li>Findings are based on the data provided and may not be exhaustive.</li>
            <li>Professional judgment is required for all material decisions.</li>
            <li>This system uses synthetic or simulated data for demonstration purposes.</li>
        </ul>
    </div>
    
    <div class="footer">
        <p>Generated by Living Ledger Auditor | Powered by Gemini 3</p>
        <p>This is a hackathon demonstration project.</p>
    </div>
</body>
</html>
"""
    
    # For hackathon, return HTML as bytes (would use WeasyPrint in production)
    return html.encode("utf-8")
