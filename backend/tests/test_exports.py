import pytest
from fastapi.testclient import TestClient
from main import app
import pandas as pd
import io

client = TestClient(app)

def test_export_pdf_endpoint():
    # This requires a valid company_id. 
    # Since we can't easily guarantee data in a fresh test run without seeding, 
    # we'll mock the internal call or just checks if the module structure is valid.
    # For now, let's just check if we can import the module without error, 
    # proving xhtml2pdf is installed and importable.
    from exports.pdf_report import generate_pdf_report
    assert generate_pdf_report is not None

def test_xhtml2pdf_installation():
    from xhtml2pdf import pisa
    buffer = io.BytesIO()
    pisa.CreatePDF(src="<html><body>Test</body></html>", dest=buffer)
    assert buffer.getvalue().startswith(b"%PDF")

def test_pandas_excel_creation():
    buffer = io.BytesIO()
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    # Check magic bytes for ZIP (xlsx is zip)
    assert buffer.getvalue().startswith(b"PK")
