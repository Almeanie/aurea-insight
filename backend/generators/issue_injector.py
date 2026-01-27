"""
Issue Injector
Plants realistic accounting issues into the General Ledger for audit testing.
"""
import random
from datetime import datetime, timedelta
from typing import Tuple
import uuid

from core.schemas import (
    GeneralLedger, JournalEntry, ChartOfAccounts, AccountingBasis,
    FindingCategory, Severity
)


class IssueType:
    """Definition of an issue type that can be injected."""
    
    def __init__(
        self,
        category: FindingCategory,
        name: str,
        description: str,
        severity: Severity,
        gaap_principle: str,
        probability: float = 0.1
    ):
        self.category = category
        self.name = name
        self.description = description
        self.severity = severity
        self.gaap_principle = gaap_principle
        self.probability = probability


# Pool of possible issues
ISSUE_POOL = [
    # Structural Issues
    IssueType(
        category=FindingCategory.STRUCTURAL,
        name="Wrong Account Usage",
        description="Expense posted to wrong account type",
        severity=Severity.HIGH,
        gaap_principle="Proper Classification",
        probability=0.15
    ),
    IssueType(
        category=FindingCategory.STRUCTURAL,
        name="Missing Contra Account",
        description="Asset without accumulated depreciation",
        severity=Severity.MEDIUM,
        gaap_principle="Matching Principle",
        probability=0.10
    ),
    
    # Timing Issues
    IssueType(
        category=FindingCategory.TIMING,
        name="Cutoff Error",
        description="Transaction recorded in wrong period",
        severity=Severity.HIGH,
        gaap_principle="Period Matching",
        probability=0.12
    ),
    IssueType(
        category=FindingCategory.TIMING,
        name="Early Revenue Recognition",
        description="Revenue recognized before delivery",
        severity=Severity.CRITICAL,
        gaap_principle="ASC 606 Revenue Recognition",
        probability=0.08
    ),
    
    # Classification Issues
    IssueType(
        category=FindingCategory.CLASSIFICATION,
        name="Personal Expense",
        description="Personal expense coded as business",
        severity=Severity.HIGH,
        gaap_principle="Business vs Personal",
        probability=0.12
    ),
    IssueType(
        category=FindingCategory.CLASSIFICATION,
        name="Travel as Supplies",
        description="Travel expense miscoded as office supplies",
        severity=Severity.MEDIUM,
        gaap_principle="Expense Classification",
        probability=0.10
    ),
    IssueType(
        category=FindingCategory.CLASSIFICATION,
        name="Expense as Asset",
        description="Low-value purchase incorrectly capitalized",
        severity=Severity.MEDIUM,
        gaap_principle="Capitalization Threshold",
        probability=0.08
    ),
    
    # Documentation Issues
    IssueType(
        category=FindingCategory.DOCUMENTATION,
        name="Missing Approval",
        description="Transaction over threshold without approval",
        severity=Severity.HIGH,
        gaap_principle="Internal Controls",
        probability=0.15
    ),
    IssueType(
        category=FindingCategory.DOCUMENTATION,
        name="Amount Mismatch",
        description="Receipt amount doesn't match entry",
        severity=Severity.MEDIUM,
        gaap_principle="Documentation Accuracy",
        probability=0.10
    ),
    
    # Balance Issues
    IssueType(
        category=FindingCategory.BALANCE,
        name="Negative Cash",
        description="Cash account has negative balance",
        severity=Severity.CRITICAL,
        gaap_principle="Balance Validity",
        probability=0.05
    ),
    IssueType(
        category=FindingCategory.BALANCE,
        name="Stale Prepaid",
        description="Prepaid expense not amortized",
        severity=Severity.MEDIUM,
        gaap_principle="Expense Recognition",
        probability=0.10
    ),
    
    # Fraud Indicators
    IssueType(
        category=FindingCategory.FRAUD,
        name="Duplicate Payment",
        description="Same invoice paid twice",
        severity=Severity.CRITICAL,
        gaap_principle="Payment Controls",
        probability=0.08
    ),
    IssueType(
        category=FindingCategory.FRAUD,
        name="Round Number Transaction",
        description="Suspicious round amount (potential fabrication)",
        severity=Severity.MEDIUM,
        gaap_principle="Fraud Detection",
        probability=0.12
    ),
    IssueType(
        category=FindingCategory.FRAUD,
        name="Structuring",
        description="Multiple transactions just under threshold",
        severity=Severity.HIGH,
        gaap_principle="Anti-Structuring Controls",
        probability=0.06
    ),
]


class IssueInjector:
    """Injects issues into the General Ledger."""
    
    def __init__(self):
        self.issue_pool = ISSUE_POOL
    
    async def inject(
        self,
        gl: GeneralLedger,
        coa: ChartOfAccounts,
        issue_count: int,
        accounting_basis: AccountingBasis
    ) -> Tuple[GeneralLedger, list[dict]]:
        """
        Inject issues into the GL.
        
        Returns:
            Tuple of (modified GL, list of injected issue metadata)
        """
        
        # Select issues to inject (ensuring category diversity)
        selected_issues = self._select_diverse_issues(issue_count)
        
        injected_metadata = []
        entries = list(gl.entries)
        
        for issue_type in selected_issues:
            # Apply the issue
            result = self._inject_issue(entries, coa, issue_type, accounting_basis)
            
            if result:
                entries = result["entries"]
                injected_metadata.append({
                    "issue_type": issue_type.name,
                    "category": issue_type.category.value,
                    "severity": issue_type.severity.value,
                    "affected_entries": result.get("affected_entries", []),
                    "description": issue_type.description
                })
        
        # Create modified GL
        modified_gl = GeneralLedger(
            company_id=gl.company_id,
            entries=entries,
            period_start=gl.period_start,
            period_end=gl.period_end
        )
        
        return modified_gl, injected_metadata
    
    def _select_diverse_issues(self, count: int) -> list[IssueType]:
        """Select issues ensuring category diversity."""
        
        # Get at least one from each category if possible
        categories = list(FindingCategory)
        selected = []
        
        for category in categories:
            category_issues = [i for i in self.issue_pool if i.category == category]
            if category_issues and len(selected) < count:
                selected.append(random.choice(category_issues))
        
        # Fill remaining with random weighted selection
        while len(selected) < count:
            remaining = [i for i in self.issue_pool if i not in selected]
            if not remaining:
                break
            
            weights = [i.probability for i in remaining]
            chosen = random.choices(remaining, weights=weights, k=1)[0]
            selected.append(chosen)
        
        return selected
    
    def _inject_issue(
        self,
        entries: list[JournalEntry],
        coa: ChartOfAccounts,
        issue_type: IssueType,
        basis: AccountingBasis
    ) -> dict:
        """Inject a specific issue into entries."""
        
        if issue_type.name == "Wrong Account Usage":
            return self._inject_wrong_account(entries)
        elif issue_type.name == "Cutoff Error":
            return self._inject_cutoff_error(entries)
        elif issue_type.name == "Personal Expense":
            return self._inject_personal_expense(entries)
        elif issue_type.name == "Travel as Supplies":
            return self._inject_misclassification(entries)
        elif issue_type.name == "Missing Approval":
            return self._inject_missing_approval(entries)
        elif issue_type.name == "Duplicate Payment":
            return self._inject_duplicate(entries)
        elif issue_type.name == "Round Number Transaction":
            return self._inject_round_number(entries)
        elif issue_type.name == "Structuring":
            return self._inject_structuring(entries)
        else:
            # Generic injection - just mark an entry
            return {"entries": entries, "affected_entries": []}
    
    def _inject_wrong_account(self, entries: list[JournalEntry]) -> dict:
        """Change an expense to wrong account type."""
        expense_entries = [e for e in entries if e.account_code.startswith("6") and e.debit > 0]
        if expense_entries:
            target = random.choice(expense_entries)
            idx = entries.index(target)
            
            # Change travel expense to office supplies or similar
            new_entry = JournalEntry(
                entry_id=target.entry_id,
                date=target.date,
                account_code="1510",  # Computer Equipment instead of expense
                account_name="Computer Equipment",
                debit=target.debit,
                credit=target.credit,
                description=target.description,
                vendor_or_customer=target.vendor_or_customer,
                reference=target.reference
            )
            entries[idx] = new_entry
            return {"entries": entries, "affected_entries": [target.entry_id]}
        return {"entries": entries, "affected_entries": []}
    
    def _inject_cutoff_error(self, entries: list[JournalEntry]) -> dict:
        """Move a transaction to wrong period."""
        if entries:
            target = random.choice(entries)
            idx = entries.index(target)
            
            # Move date by 1-2 months
            old_date = datetime.strptime(target.date, "%Y-%m-%d")
            new_date = old_date + timedelta(days=random.randint(30, 60))
            
            new_entry = JournalEntry(
                entry_id=target.entry_id,
                date=new_date.strftime("%Y-%m-%d"),
                account_code=target.account_code,
                account_name=target.account_name,
                debit=target.debit,
                credit=target.credit,
                description=target.description,
                vendor_or_customer=target.vendor_or_customer,
                reference=target.reference
            )
            entries[idx] = new_entry
            return {"entries": entries, "affected_entries": [target.entry_id]}
        return {"entries": entries, "affected_entries": []}
    
    def _inject_personal_expense(self, entries: list[JournalEntry]) -> dict:
        """Add a personal expense disguised as business."""
        entry_id = f"PRS-{str(uuid.uuid4())[:8]}"
        date = entries[0].date if entries else "2024-06-15"
        
        personal_expenses = [
            ("Amazon.com Personal", 299.99, "Electronics purchase"),
            ("Best Buy", 599.99, "Home entertainment"),
            ("Nordstrom", 450.00, "Clothing purchase"),
        ]
        
        vendor, amount, desc = random.choice(personal_expenses)
        
        entries.append(JournalEntry(
            entry_id=entry_id,
            date=date,
            account_code="6900",
            account_name="Miscellaneous Expense",
            debit=amount,
            credit=0,
            description=desc,
            vendor_or_customer=vendor
        ))
        
        entries.append(JournalEntry(
            entry_id=entry_id,
            date=date,
            account_code="1000",
            account_name="Cash",
            debit=0,
            credit=amount,
            description=desc,
            vendor_or_customer=vendor
        ))
        
        return {"entries": entries, "affected_entries": [entry_id]}
    
    def _inject_misclassification(self, entries: list[JournalEntry]) -> dict:
        """Misclassify travel as supplies."""
        travel_entries = [e for e in entries if "6600" in e.account_code and e.debit > 0]
        if travel_entries:
            target = random.choice(travel_entries)
            idx = entries.index(target)
            
            new_entry = JournalEntry(
                entry_id=target.entry_id,
                date=target.date,
                account_code="6900",  # Miscellaneous instead of Travel
                account_name="Miscellaneous Expense",
                debit=target.debit,
                credit=target.credit,
                description=target.description,
                vendor_or_customer=target.vendor_or_customer,
                reference=target.reference
            )
            entries[idx] = new_entry
            return {"entries": entries, "affected_entries": [target.entry_id]}
        return {"entries": entries, "affected_entries": []}
    
    def _inject_missing_approval(self, entries: list[JournalEntry]) -> dict:
        """Mark a high-value transaction as lacking approval."""
        # This is metadata-only - the entry exists but approval is missing
        high_value = [e for e in entries if e.debit > 500]
        if high_value:
            target = random.choice(high_value)
            return {"entries": entries, "affected_entries": [target.entry_id]}
        return {"entries": entries, "affected_entries": []}
    
    def _inject_duplicate(self, entries: list[JournalEntry]) -> dict:
        """Duplicate a payment."""
        expense_entries = [e for e in entries if e.debit > 0 and e.vendor_or_customer]
        if expense_entries:
            target = random.choice(expense_entries)
            
            # Create duplicate with slightly different ID
            duplicate = JournalEntry(
                entry_id=f"DUP-{target.entry_id}",
                date=target.date,
                account_code=target.account_code,
                account_name=target.account_name,
                debit=target.debit,
                credit=target.credit,
                description=target.description,
                vendor_or_customer=target.vendor_or_customer,
                reference=target.reference
            )
            entries.append(duplicate)
            
            # Add corresponding credit
            entries.append(JournalEntry(
                entry_id=f"DUP-{target.entry_id}",
                date=target.date,
                account_code="1000",
                account_name="Cash",
                debit=0,
                credit=target.debit,
                description=target.description,
                vendor_or_customer=target.vendor_or_customer
            ))
            
            return {"entries": entries, "affected_entries": [target.entry_id, f"DUP-{target.entry_id}"]}
        return {"entries": entries, "affected_entries": []}
    
    def _inject_round_number(self, entries: list[JournalEntry]) -> dict:
        """Add suspicious round-number transaction."""
        entry_id = f"RND-{str(uuid.uuid4())[:8]}"
        date = entries[0].date if entries else "2024-06-15"
        
        round_amounts = [1000, 2500, 5000, 10000]
        amount = random.choice(round_amounts)
        
        entries.append(JournalEntry(
            entry_id=entry_id,
            date=date,
            account_code="6400",
            account_name="Professional Services",
            debit=float(amount),
            credit=0,
            description="Consulting services",
            vendor_or_customer="Generic Consulting LLC"
        ))
        
        entries.append(JournalEntry(
            entry_id=entry_id,
            date=date,
            account_code="1000",
            account_name="Cash",
            debit=0,
            credit=float(amount),
            description="Payment for consulting",
            vendor_or_customer="Generic Consulting LLC"
        ))
        
        return {"entries": entries, "affected_entries": [entry_id]}
    
    def _inject_structuring(self, entries: list[JournalEntry]) -> dict:
        """Add multiple transactions just under threshold."""
        threshold = 10000
        base_date = entries[0].date if entries else "2024-06-15"
        affected = []
        
        # Create 3-4 transactions just under threshold
        for i in range(random.randint(3, 4)):
            entry_id = f"STR-{str(uuid.uuid4())[:8]}"
            amount = round(random.uniform(9000, 9900), 2)
            
            date = datetime.strptime(base_date, "%Y-%m-%d") + timedelta(days=i)
            
            entries.append(JournalEntry(
                entry_id=entry_id,
                date=date.strftime("%Y-%m-%d"),
                account_code="1000",
                account_name="Cash",
                debit=0,
                credit=amount,
                description="Cash withdrawal",
                vendor_or_customer="Bank Withdrawal"
            ))
            
            entries.append(JournalEntry(
                entry_id=entry_id,
                date=date.strftime("%Y-%m-%d"),
                account_code="6900",
                account_name="Miscellaneous Expense",
                debit=amount,
                credit=0,
                description="Cash expense",
                vendor_or_customer="Various"
            ))
            
            affected.append(entry_id)
        
        return {"entries": entries, "affected_entries": affected}
