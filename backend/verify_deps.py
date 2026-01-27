import io
import sys

def verify_xhtml2pdf():
    try:
        from xhtml2pdf import pisa
        buffer = io.BytesIO()
        pisa.CreatePDF(src="<html><body>Test</body></html>", dest=buffer)
        pdf_content = buffer.getvalue()
        if pdf_content.startswith(b"%PDF"):
            print("SUCCESS: xhtml2pdf is working and generating PDF.")
        else:
            print(f"FAILURE: xhtml2pdf generated invalid data: {pdf_content[:20]}")
    except ImportError:
        print("FAILURE: xhtml2pdf not installed.")
    except Exception as e:
        print(f"FAILURE: xhtml2pdf error: {e}")

def verify_pandas_excel():
    try:
        import pandas as pd
        buffer = io.BytesIO()
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        buffer.seek(0)
        content = buffer.getvalue()
        # Excel .xlsx is a zip file, should start with PK
        if content.startswith(b"PK"):
            print("SUCCESS: pandas/openpyxl is working and generating Excel.")
        else:
            print(f"FAILURE: pandas generate invalid data: {content[:20]}")
    except ImportError:
        print("FAILURE: pandas or openpyxl not installed.")
    except Exception as e:
        print(f"FAILURE: pandas error: {e}")

if __name__ == "__main__":
    verify_xhtml2pdf()
    verify_pandas_excel()
