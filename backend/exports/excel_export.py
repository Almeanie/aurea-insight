"""
Excel Export Module
Generates audit data in XLSX format.
"""
import io
import pandas as pd
from typing import List, Dict

def generate_ajes_xlsx(ajes: List[Dict]) -> io.BytesIO:
    """
    Generate an Excel file (XLSX) for Adjusting Journal Entries.
    
    Args:
        ajes: List of Adjusted Journal Entry dictionaries.
        
    Returns:
        BytesIO: A byte stream containing the Excel file.
    """
    if not ajes:
        # Return empty excel with headers
        df = pd.DataFrame(columns=[
            "AJE ID", 
            "Description", 
            "Debit Account", 
            "Credit Account", 
            "Amount", 
            "Justification"
        ])
    else:
        rows = []
        for idx, aje in enumerate(ajes, 1):
            # Flatten entries for simpler excel view
            entries = aje.get("entries", [])
            debits = [e for e in entries if e.get("debit", 0) > 0]
            credits = [e for e in entries if e.get("credit", 0) > 0]
            
            # Form multi-account strings if needed
            debit_acc = ", ".join([d.get("account_code", "") for d in debits])
            credit_acc = ", ".join([c.get("account_code", "") for c in credits])
            
            # Use total_debits as the primary amount
            amount = aje.get("total_debits", 0)
            
            rows.append({
                "AJE ID": aje.get("aje_id", f"AJE #{idx}"),
                "Description": aje.get("description", "No description"),
                "Debit Account": debit_acc,
                "Credit Account": credit_acc,
                "Amount": amount,
                "Justification": aje.get("rationale", "") # Mapping rationale to Justification column
            })
        df = pd.DataFrame(rows)
        
    # Generate Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='AJEs')
        
    output.seek(0)
    return output
