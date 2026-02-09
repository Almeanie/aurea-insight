"""
PDF Report Generator
Generates audit reports in PDF format using WeasyPrint and Tailwind CSS.
"""
from datetime import datetime
from weasyprint import HTML
from io import BytesIO
import base64
import os

async def generate_pdf_report(
    company_data: dict,
    audit_data: dict,
    include_findings: bool = True,
    include_ajes: bool = True,
    include_audit_trail: bool = False
) -> bytes:
    """
    Generate a high-quality PDF audit report using WeasyPrint.
    """
    
    metadata = company_data.get("metadata", {})
    findings = audit_data.get("findings", [])
    ajes = audit_data.get("ajes", [])
    risk_score = audit_data.get("risk_score", {})
    
    # Load banner image and encode as base64
    banner_base64 = ""
    banner_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "public", "aurea_insight_banner.webp")
    try:
        if os.path.exists(banner_path):
            with open(banner_path, "rb") as image_file:
                banner_base64 = base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error loading banner: {e}")
    
    # Brand colors and styles based on globals.css
    brand_styles = """
    :root {
        --background: #fafafa; /* Use light background for better PDF printing */
        --foreground: #0a0a0a;
        --card: #ffffff;
        --border: #e5e7eb;
        --primary: #00d4ff;
        --primary-foreground: #ffffff;
        --severity-critical: #ff3366;
        --severity-high: #ff6b35;
        --severity-medium: #fbbf24;
        --severity-low: #22c55e;
        --muted: #6b7280;
    }
    @page {
        size: A4;
        margin: 2cm;
        @bottom-right {
            content: "Page " counter(page) " of " counter(pages);
            font-size: 9pt;
            color: #6b7280;
        }
    }
    body {
        font-family: 'Helvetica', 'Arial', sans-serif;
        color: var(--foreground);
        background: var(--background);
        line-height: 1.5;
    }
    .badge {
        padding: 2px 8px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        color: white;
        display: inline-block;
    }
    .badge-critical { background-color: var(--severity-critical); }
    .badge-high { background-color: var(--severity-high); }
    .badge-medium { background-color: var(--severity-medium); color: #0a0a0a; }
    .badge-low { background-color: var(--severity-low); }
    
    .financial-number {
        font-family: monospace;
        font-variant-numeric: tabular-nums;
    }
    """
    
    # Build findings rows
    findings_html = ""
    if include_findings and findings:
        for f in findings:
            sev = f.get('severity', 'low').lower()
            findings_html += f"""
            <tr class="border-b border-gray-100">
                <td class="py-3 pr-4 text-xs font-mono text-gray-500">{f.get('finding_id', 'N/A')}</td>
                <td class="py-3 pr-4"><span class="badge badge-{sev}">{sev.upper()}</span></td>
                <td class="py-3 pr-4 text-sm font-medium">{f.get('category', 'N/A')}</td>
                <td class="py-3 pr-4 text-sm">{f.get('issue', 'N/A')}</td>
                <td class="py-3 text-sm italic text-gray-700">{f.get('recommendation', 'N/A')}</td>
            </tr>
            """

    # Build AJEs rows
    ajes_html = ""
    if include_ajes and ajes:
        for aje in ajes:
            ajes_html += f"""
            <tr class="border-b border-gray-100">
                <td class="py-3 pr-4 text-xs font-mono text-gray-500">{aje.get('aje_id', 'N/A')}</td>
                <td class="py-3 pr-4 text-sm">{aje.get('description', 'N/A')}</td>
                <td class="py-3 pr-4 text-sm font-mono text-right">${aje.get('total_debits', 0):,.2f}</td>
                <td class="py-3 text-sm text-gray-500">{aje.get('finding_reference', 'N/A')}</td>
            </tr>
            """

    # Construct complete HTML
    banner_html = f'<img src="data:image/webp;base64,{banner_base64}" class="w-full h-auto mb-4">' if banner_base64 else '<h2 class="text-xs uppercase tracking-[0.2em] font-bold text-cyan-500 mb-1">Aurea Insight</h2>'
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        {brand_styles}
    </style>
</head>
<body class="p-0 m-0 text-gray-900 bg-white">
    <!-- Header -->
    <div class="mb-8 p-0">
        {banner_html}
        <div class="flex justify-between items-end border-b-2 border-gray-900 pb-2">
            <div>
                <h1 class="text-2xl font-light tracking-tight text-gray-900 uppercase">Audit Narrative Report</h1>
            </div>
            <div class="text-right">
                <p class="text-xs font-semibold text-gray-500 uppercase">Generated</p>
                <p class="text-sm font-medium">{datetime.now().strftime("%B %d, %Y | %H:%M")}</p>
            </div>
        </div>
    </div>

    <!-- Executive Summary Section -->
    <section class="mb-10">
        <h3 class="text-sm font-bold uppercase tracking-widest text-gray-400 mb-4">Executive Summary</h3>
        <div class="grid grid-cols-2 gap-8 mb-6">
            <div class="space-y-3">
                <div class="flex justify-between border-b border-gray-100 pb-1">
                    <span class="text-xs text-gray-500 uppercase font-semibold">Company</span>
                    <span class="text-sm font-bold">{metadata.get('name', 'N/A')}</span>
                </div>
                <div class="flex justify-between border-b border-gray-100 pb-1">
                    <span class="text-xs text-gray-500 uppercase font-semibold">Industry</span>
                    <span class="text-sm">{metadata.get('industry', 'N/A').value if hasattr(metadata.get('industry'), 'value') else metadata.get('industry', 'N/A')}</span>
                </div>
                <div class="flex justify-between border-b border-gray-100 pb-1">
                    <span class="text-xs text-gray-500 uppercase font-semibold">Methodology</span>
                    <span class="text-sm font-mono uppercase text-xs">{metadata.get('accounting_basis', 'N/A').value if hasattr(metadata.get('accounting_basis'), 'value') else metadata.get('accounting_basis', 'N/A')}</span>
                </div>
            </div>
            <div class="flex items-center justify-center bg-gray-50 rounded-lg p-4 border border-gray-100">
                <div class="text-center">
                    <p class="text-[10px] uppercase tracking-tighter text-gray-400 font-bold mb-1">Overall Risk Score</p>
                    <p class="text-4xl font-extrabold tracking-tighter" style="color: var(--severity-{risk_score.get('risk_level', 'low')})">
                        {risk_score.get('overall_score', 0)}<span class="text-lg text-gray-400">/100</span>
                    </p>
                    <p class="text-xs font-bold uppercase mt-1 tracking-widest" style="color: var(--severity-{risk_score.get('risk_level', 'low')})">
                        {risk_score.get('risk_level', 'N/A').upper()} RISK
                    </p>
                </div>
            </div>
        </div>
        <div class="bg-cyan-50 border-l-4 border-cyan-500 p-4 rounded-r-md">
            <p class="text-sm text-cyan-900 leading-relaxed italic">
                "{risk_score.get('interpretation', 'No interpretation provided.')}"
            </p>
        </div>
    </section>

    <!-- Audit Findings -->
    {f'''
    <section class="mb-10 px-0">
        <h3 class="text-sm font-bold uppercase tracking-widest text-gray-400 mb-4">Audit Findings ({len(findings)})</h3>
        <table class="w-full">
            <thead>
                <tr class="text-[10px] text-gray-400 uppercase tracking-widest border-b-2 border-gray-900">
                    <th class="py-2 text-left font-bold w-20">ID</th>
                    <th class="py-2 text-left font-bold w-24">Severity</th>
                    <th class="py-2 text-left font-bold w-32">Category</th>
                    <th class="py-2 text-left font-bold">Issue</th>
                    <th class="py-2 text-left font-bold">Recommendation</th>
                </tr>
            </thead>
            <tbody>
                {findings_html}
            </tbody>
        </table>
    </section>
    ''' if include_findings and findings else ''}

    <!-- AJEs -->
    {f'''
    <section class="mb-10 page-break-before">
        <h3 class="text-sm font-bold uppercase tracking-widest text-gray-400 mb-4">Adjusting Journal Entries ({len(ajes)})</h3>
        <table class="w-full">
            <thead>
                <tr class="text-[10px] text-gray-400 uppercase tracking-widest border-b-2 border-gray-900">
                    <th class="py-2 text-left font-bold w-20">AJE ID</th>
                    <th class="py-2 text-left font-bold">Description</th>
                    <th class="py-2 text-right font-bold w-32">Amount</th>
                    <th class="py-2 text-left font-bold w-32 pl-4">Ref finding</th>
                </tr>
            </thead>
            <tbody>
                {ajes_html}
            </tbody>
        </table>
    </section>
    ''' if include_ajes and ajes else ''}

    <!-- Disclaimer -->
    <div class="mt-12 p-6 bg-gray-50 border border-gray-200 rounded-lg">
        <h4 class="text-xs font-bold uppercase tracking-widest text-gray-400 mb-3">Important Disclaimers</h4>
        <ul class="text-[10px] text-gray-500 space-y-1.5 list-disc pl-4 italic">
            <li>This audit was performed by Aurea Insight AI and requires human professional review.</li>
            <li>This report provides narrative analysis and does not constitute formal legal or accounting advice.</li>
            <li>Observations are based solely on provided documentation and data streams.</li>
            <li>This is a demonstration project using synthetic data for hackathon purposes.</li>
        </ul>
    </div>

    <!-- Footer Footer -->
    <div class="mt-8 pt-6 border-t border-gray-100 text-center">
        <p class="text-[10px] font-bold text-gray-300 uppercase tracking-[0.5em]">Aurea Insight | Powered by Gemini 3</p>
    </div>
</body>
</html>
"""
    
    # Render PDF
    buffer = BytesIO()
    # WeasyPrint handles HTML objects or strings
    HTML(string=html_content).write_pdf(buffer)
    
    return buffer.getvalue()
