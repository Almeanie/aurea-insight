"""
Export API Routes
Handles PDF and CSV exports.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import io
from loguru import logger

from core.schemas import ExportRequest

router = APIRouter()


@router.get("/{company_id}/pdf")
async def export_pdf(
    company_id: str,
    audit_id: Optional[str] = None,
    include_findings: bool = True,
    include_ajes: bool = True,
    include_audit_trail: bool = False
):
    """
    Export audit report as PDF.
    Includes executive summary, findings, AJEs, and optionally the audit trail.
    """
    from api.routes.company import companies
    from api.routes.audit import audit_results
    
    if company_id not in companies:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Find audit results
    if audit_id:
        if audit_id not in audit_results:
            raise HTTPException(status_code=404, detail="Audit not found")
        result = audit_results[audit_id]
    else:
        result = None
        for aid, data in reversed(list(audit_results.items())):
            if data["company_id"] == company_id:
                result = data
                audit_id = aid
                break
    
    if not result:
        raise HTTPException(status_code=404, detail="No audit found for this company")
    
    # Generate PDF
    try:
        from exports.pdf_report import generate_pdf_report
        pdf_bytes = await generate_pdf_report(
            company_data=companies[company_id],
            audit_data=result,
            include_findings=include_findings,
            include_ajes=include_ajes,
            include_audit_trail=include_audit_trail
        )
    except Exception as e:
        logger.exception(f"PDF export failed for company_id={company_id}, audit_id={audit_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to generate PDF report. "
                "If this is a deployed environment, ensure WeasyPrint system dependencies "
                "(libglib2.0-0, libpango-1.0-0, libgdk-pixbuf-2.0-0) are installed."
            )
        )
    
    # Return as streaming response
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=audit_report_{company_id}.pdf"
        }
    )


@router.get("/{company_id}/csv/findings")
async def export_findings_csv(company_id: str, audit_id: Optional[str] = None):
    """Export audit findings as CSV."""
    from api.routes.audit import audit_results
    from exports.csv_export import generate_findings_csv
    
    # Find audit results
    if audit_id:
        if audit_id not in audit_results:
            raise HTTPException(status_code=404, detail="Audit not found")
        result = audit_results[audit_id]
    else:
        result = None
        for aid, data in reversed(list(audit_results.items())):
            if data["company_id"] == company_id:
                result = data
                audit_id = aid
                break
    
    if not result:
        raise HTTPException(status_code=404, detail="No audit found for this company")
    
    # Generate CSV
    csv_content = generate_findings_csv(result["findings"])
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode()),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=findings_{company_id}.csv"
        }
    )


@router.get("/{company_id}/csv/ajes")
async def export_ajes_csv(company_id: str, audit_id: Optional[str] = None):
    """Export Adjusting Journal Entries as CSV."""
    from api.routes.audit import audit_results
    from exports.csv_export import generate_ajes_csv
    
    # Find audit results
    if audit_id:
        if audit_id not in audit_results:
            raise HTTPException(status_code=404, detail="Audit not found")
        result = audit_results[audit_id]
    else:
        result = None
        for aid, data in reversed(list(audit_results.items())):
            if data["company_id"] == company_id:
                result = data
                audit_id = aid
                break
    
    if not result:
        raise HTTPException(status_code=404, detail="No audit found for this company")
    
    # Generate CSV
    csv_content = generate_ajes_csv(result["ajes"])
    
    return StreamingResponse(
        io.BytesIO(csv_content.encode()),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=ajes_{company_id}.csv"
        }
    )


@router.get("/{company_id}/xlsx/ajes")
async def export_ajes_xlsx(company_id: str, audit_id: Optional[str] = None):
    """Export Adjusting Journal Entries as Excel."""
    from api.routes.audit import audit_results
    
    # Find audit results
    if audit_id:
        if audit_id not in audit_results:
            raise HTTPException(status_code=404, detail="Audit not found")
        result = audit_results[audit_id]
    else:
        result = None
        for aid, data in reversed(list(audit_results.items())):
            if data["company_id"] == company_id:
                result = data
                audit_id = aid
                break
    
    if not result:
        raise HTTPException(status_code=404, detail="No audit found for this company")
    
    # Generate Excel
    from exports.excel_export import generate_ajes_xlsx
    ajes = result.get("ajes", [])
    output = generate_ajes_xlsx(ajes)
        
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=ajes_{company_id}.xlsx"
        }
    )
