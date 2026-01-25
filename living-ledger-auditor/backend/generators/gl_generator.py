"""
General Ledger Generator
Creates realistic journal entries for a company.
"""
import random
from datetime import datetime, timedelta
from typing import Optional
import uuid

from core.schemas import (
    GeneralLedger, JournalEntry, ChartOfAccounts, 
    Industry, AccountingBasis
)
from core.gemini_client import GeminiClient


# Vendor names by category
VENDORS = {
    "rent": ["Metro Commercial Properties", "Downtown Realty LLC", "Workspace Solutions"],
    "utilities": ["City Power & Light", "Metro Water Authority", "National Gas Co"],
    "software": ["Microsoft 365", "Salesforce", "AWS Services", "Google Cloud", "Slack Technologies"],
    "professional": ["Baker & Associates CPAs", "Smith Legal Group", "HR Consulting Partners"],
    "marketing": ["Digital Marketing Co", "Social Buzz Agency", "Print Solutions Inc"],
    "travel": ["Delta Airlines", "Marriott Hotels", "Hertz Car Rental", "United Airlines"],
    "meals": ["Blue Apron Catering", "Local Restaurant", "DoorDash Business"],
    "office": ["Staples Business", "Office Depot", "Amazon Business"],
    "insurance": ["Liberty Mutual", "Nationwide Insurance", "State Farm Business"],
}

# Customer names
CUSTOMERS = [
    "Acme Corporation", "GlobalTech Inc", "Smith Enterprises", "Johnson & Co",
    "Pacific Industries", "Mountain View LLC", "Sunrise Holdings", "Eastside Partners",
    "Northstar Group", "Lakeside Ventures", "Capital Resources", "Pioneer Solutions",
]


class GLGenerator:
    """Generates General Ledger entries."""
    
    def __init__(self):
        self.gemini = GeminiClient()
    
    async def generate(
        self,
        company_id: str,
        coa: ChartOfAccounts,
        industry: Industry,
        accounting_basis: AccountingBasis,
        num_transactions: int,
        reporting_period: str
    ) -> GeneralLedger:
        """Generate a complete General Ledger."""
        
        # Parse reporting period
        quarter, year = reporting_period.split()
        year = int(year)
        
        quarter_dates = {
            "Q1": (datetime(year, 1, 1), datetime(year, 3, 31)),
            "Q2": (datetime(year, 4, 1), datetime(year, 6, 30)),
            "Q3": (datetime(year, 7, 1), datetime(year, 9, 30)),
            "Q4": (datetime(year, 10, 1), datetime(year, 12, 31)),
        }
        
        period_start, period_end = quarter_dates.get(quarter, quarter_dates["Q2"])
        
        # Build account lookup
        account_map = {a.code: a for a in coa.accounts}
        
        entries = []
        
        # Generate different types of transactions
        entries.extend(self._generate_revenue_entries(
            account_map, period_start, period_end, 
            num=int(num_transactions * 0.25), industry=industry, basis=accounting_basis
        ))
        
        entries.extend(self._generate_expense_entries(
            account_map, period_start, period_end,
            num=int(num_transactions * 0.5)
        ))
        
        entries.extend(self._generate_payroll_entries(
            account_map, period_start, period_end
        ))
        
        entries.extend(self._generate_asset_entries(
            account_map, period_start, period_end,
            num=int(num_transactions * 0.1)
        ))
        
        if accounting_basis == AccountingBasis.ACCRUAL:
            entries.extend(self._generate_accrual_entries(
                account_map, period_end
            ))
        
        # Sort by date
        entries.sort(key=lambda e: e.date)
        
        return GeneralLedger(
            company_id=company_id,
            entries=entries,
            period_start=period_start.strftime("%Y-%m-%d"),
            period_end=period_end.strftime("%Y-%m-%d")
        )
    
    def _random_date(self, start: datetime, end: datetime) -> str:
        """Generate a random date in range."""
        delta = end - start
        random_days = random.randint(0, delta.days)
        return (start + timedelta(days=random_days)).strftime("%Y-%m-%d")
    
    def _generate_revenue_entries(
        self, account_map: dict, start: datetime, end: datetime, 
        num: int, industry: Industry, basis: AccountingBasis
    ) -> list[JournalEntry]:
        """Generate revenue transactions."""
        entries = []
        
        revenue_account = "4000"  # Service Revenue default
        if "4050" in account_map:  # SaaS
            revenue_account = "4050"
        elif "4030" in account_map:  # E-commerce
            revenue_account = "4030"
        
        for _ in range(num):
            entry_id = str(uuid.uuid4())[:8]
            date = self._random_date(start, end)
            customer = random.choice(CUSTOMERS)
            amount = round(random.uniform(1000, 50000), 2)
            
            # Debit Cash or AR, Credit Revenue
            if basis == AccountingBasis.CASH or random.random() > 0.3:
                debit_account = "1000"  # Cash
            else:
                debit_account = "1100"  # AR
            
            entries.append(JournalEntry(
                entry_id=f"REV-{entry_id}",
                date=date,
                account_code=debit_account,
                account_name=account_map.get(debit_account, {}).name if debit_account in account_map else "Cash",
                debit=amount,
                credit=0,
                description=f"Payment received from {customer}",
                vendor_or_customer=customer,
                reference=f"INV-{random.randint(1000, 9999)}"
            ))
            
            entries.append(JournalEntry(
                entry_id=f"REV-{entry_id}",
                date=date,
                account_code=revenue_account,
                account_name=account_map.get(revenue_account, {}).name if revenue_account in account_map else "Revenue",
                debit=0,
                credit=amount,
                description=f"Revenue from {customer}",
                vendor_or_customer=customer,
                reference=f"INV-{random.randint(1000, 9999)}"
            ))
        
        return entries
    
    def _generate_expense_entries(
        self, account_map: dict, start: datetime, end: datetime, num: int
    ) -> list[JournalEntry]:
        """Generate expense transactions."""
        entries = []
        
        expense_types = [
            ("6000", "rent", 2000, 8000),
            ("6100", "utilities", 200, 800),
            ("6200", "marketing", 500, 5000),
            ("6400", "professional", 1000, 10000),
            ("6500", "software", 100, 2000),
            ("6600", "travel", 300, 3000),
            ("6610", "meals", 50, 500),
            ("6800", "insurance", 500, 2000),
        ]
        
        for _ in range(num):
            account_code, vendor_type, min_amt, max_amt = random.choice(expense_types)
            
            if account_code not in account_map:
                continue
            
            entry_id = str(uuid.uuid4())[:8]
            date = self._random_date(start, end)
            vendor = random.choice(VENDORS.get(vendor_type, ["General Vendor"]))
            amount = round(random.uniform(min_amt, max_amt), 2)
            
            # Debit Expense, Credit Cash
            entries.append(JournalEntry(
                entry_id=f"EXP-{entry_id}",
                date=date,
                account_code=account_code,
                account_name=account_map[account_code].name,
                debit=amount,
                credit=0,
                description=f"Payment to {vendor}",
                vendor_or_customer=vendor,
                reference=f"CHK-{random.randint(1000, 9999)}"
            ))
            
            entries.append(JournalEntry(
                entry_id=f"EXP-{entry_id}",
                date=date,
                account_code="1000",
                account_name="Cash",
                debit=0,
                credit=amount,
                description=f"Payment to {vendor}",
                vendor_or_customer=vendor,
                reference=f"CHK-{random.randint(1000, 9999)}"
            ))
        
        return entries
    
    def _generate_payroll_entries(
        self, account_map: dict, start: datetime, end: datetime
    ) -> list[JournalEntry]:
        """Generate payroll transactions (monthly)."""
        entries = []
        
        # Calculate months in period
        current = start
        while current <= end:
            entry_id = str(uuid.uuid4())[:8]
            payroll_date = current.replace(day=15) if current.day < 15 else current.replace(day=28)
            
            if payroll_date > end:
                break
            
            gross_payroll = round(random.uniform(30000, 80000), 2)
            payroll_taxes = round(gross_payroll * 0.0765, 2)  # FICA
            
            # Debit Salaries Expense
            entries.append(JournalEntry(
                entry_id=f"PAY-{entry_id}",
                date=payroll_date.strftime("%Y-%m-%d"),
                account_code="6300",
                account_name="Salaries and Wages",
                debit=gross_payroll,
                credit=0,
                description=f"Payroll for {payroll_date.strftime('%B %Y')}",
                vendor_or_customer="Employees"
            ))
            
            # Debit Payroll Tax Expense
            entries.append(JournalEntry(
                entry_id=f"PAY-{entry_id}",
                date=payroll_date.strftime("%Y-%m-%d"),
                account_code="6310",
                account_name="Payroll Taxes",
                debit=payroll_taxes,
                credit=0,
                description=f"Employer payroll taxes",
                vendor_or_customer="IRS/State"
            ))
            
            # Credit Cash
            entries.append(JournalEntry(
                entry_id=f"PAY-{entry_id}",
                date=payroll_date.strftime("%Y-%m-%d"),
                account_code="1000",
                account_name="Cash",
                debit=0,
                credit=gross_payroll + payroll_taxes,
                description=f"Payroll disbursement",
                vendor_or_customer="Employees"
            ))
            
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        return entries
    
    def _generate_asset_entries(
        self, account_map: dict, start: datetime, end: datetime, num: int
    ) -> list[JournalEntry]:
        """Generate asset purchase transactions."""
        entries = []
        
        assets = [
            ("1510", "Computer Equipment", "Dell Technologies", 1000, 5000),
            ("1500", "Furniture and Equipment", "Office Furniture Plus", 500, 3000),
        ]
        
        for _ in range(min(num, 3)):  # Limit asset purchases
            account_code, account_name, vendor, min_amt, max_amt = random.choice(assets)
            
            if account_code not in account_map:
                continue
            
            entry_id = str(uuid.uuid4())[:8]
            date = self._random_date(start, end)
            amount = round(random.uniform(min_amt, max_amt), 2)
            
            entries.append(JournalEntry(
                entry_id=f"AST-{entry_id}",
                date=date,
                account_code=account_code,
                account_name=account_name,
                debit=amount,
                credit=0,
                description=f"Purchase of equipment from {vendor}",
                vendor_or_customer=vendor
            ))
            
            entries.append(JournalEntry(
                entry_id=f"AST-{entry_id}",
                date=date,
                account_code="1000",
                account_name="Cash",
                debit=0,
                credit=amount,
                description=f"Payment to {vendor}",
                vendor_or_customer=vendor
            ))
        
        return entries
    
    def _generate_accrual_entries(
        self, account_map: dict, period_end: datetime
    ) -> list[JournalEntry]:
        """Generate accrual adjusting entries at period end."""
        entries = []
        entry_id = str(uuid.uuid4())[:8]
        date = period_end.strftime("%Y-%m-%d")
        
        # Accrue wages
        accrued_wages = round(random.uniform(5000, 15000), 2)
        entries.append(JournalEntry(
            entry_id=f"ADJ-{entry_id}-1",
            date=date,
            account_code="6300",
            account_name="Salaries and Wages",
            debit=accrued_wages,
            credit=0,
            description="Accrued wages at period end"
        ))
        entries.append(JournalEntry(
            entry_id=f"ADJ-{entry_id}-1",
            date=date,
            account_code="2110",
            account_name="Accrued Wages",
            debit=0,
            credit=accrued_wages,
            description="Accrued wages at period end"
        ))
        
        # Record depreciation
        depreciation = round(random.uniform(1000, 3000), 2)
        entries.append(JournalEntry(
            entry_id=f"ADJ-{entry_id}-2",
            date=date,
            account_code="6700",
            account_name="Depreciation Expense",
            debit=depreciation,
            credit=0,
            description="Monthly depreciation"
        ))
        entries.append(JournalEntry(
            entry_id=f"ADJ-{entry_id}-2",
            date=date,
            account_code="1600",
            account_name="Accumulated Depreciation - Equipment",
            debit=0,
            credit=depreciation,
            description="Monthly depreciation"
        ))
        
        return entries
