"""
Trial Balance Generator
Derives Trial Balance from General Ledger.
"""
from datetime import datetime
from collections import defaultdict

from core.schemas import (
    TrialBalance, TrialBalanceRow, GeneralLedger, ChartOfAccounts
)


class TBGenerator:
    """Derives Trial Balance from General Ledger."""
    
    def derive_from_gl(
        self,
        company_id: str,
        gl: GeneralLedger,
        coa: ChartOfAccounts,
        reporting_period: str
    ) -> TrialBalance:
        """
        Derive Trial Balance from General Ledger.
        The TB is a summary of all GL entries by account.
        """
        
        # Build account lookup
        account_map = {a.code: a for a in coa.accounts}
        
        # Aggregate debits and credits by account
        account_totals = defaultdict(lambda: {"debit": 0.0, "credit": 0.0})
        
        for entry in gl.entries:
            account_totals[entry.account_code]["debit"] += entry.debit
            account_totals[entry.account_code]["credit"] += entry.credit
        
        # Create TB rows
        rows = []
        total_debits = 0.0
        total_credits = 0.0
        
        for account_code in sorted(account_totals.keys()):
            totals = account_totals[account_code]
            account = account_map.get(account_code)
            account_name = account.name if account else f"Unknown ({account_code})"
            
            debit = totals["debit"]
            credit = totals["credit"]
            
            # Calculate ending balance based on normal balance
            if account and account.normal_balance == "debit":
                ending_balance = debit - credit
            else:
                ending_balance = credit - debit
            
            rows.append(TrialBalanceRow(
                account_code=account_code,
                account_name=account_name,
                debit=round(debit, 2),
                credit=round(credit, 2),
                ending_balance=round(ending_balance, 2)
            ))
            
            total_debits += debit
            total_credits += credit
        
        # Check if balanced (should be within rounding tolerance)
        is_balanced = abs(total_debits - total_credits) < 0.01
        
        return TrialBalance(
            company_id=company_id,
            period_end=gl.period_end,
            rows=rows,
            total_debits=round(total_debits, 2),
            total_credits=round(total_credits, 2),
            is_balanced=is_balanced
        )
