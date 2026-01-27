"""
Chart of Accounts Generator
Creates a complete, industry-appropriate COA.
"""
from typing import Optional
from datetime import datetime

from core.schemas import ChartOfAccounts, Account, Industry, AccountingBasis


# Base account structure (common to all industries)
BASE_ACCOUNTS = [
    # Assets (1000-1999)
    Account(code="1000", name="Cash", type="asset", subtype="current_asset", normal_balance="debit"),
    Account(code="1010", name="Petty Cash", type="asset", subtype="current_asset", normal_balance="debit"),
    Account(code="1100", name="Accounts Receivable", type="asset", subtype="current_asset", normal_balance="debit"),
    Account(code="1150", name="Allowance for Doubtful Accounts", type="asset", subtype="contra_asset", normal_balance="credit"),
    Account(code="1200", name="Prepaid Expenses", type="asset", subtype="current_asset", normal_balance="debit"),
    Account(code="1210", name="Prepaid Insurance", type="asset", subtype="current_asset", normal_balance="debit"),
    Account(code="1220", name="Prepaid Rent", type="asset", subtype="current_asset", normal_balance="debit"),
    Account(code="1500", name="Furniture and Equipment", type="asset", subtype="fixed_asset", normal_balance="debit"),
    Account(code="1510", name="Computer Equipment", type="asset", subtype="fixed_asset", normal_balance="debit"),
    Account(code="1600", name="Accumulated Depreciation - Equipment", type="asset", subtype="contra_asset", normal_balance="credit"),
    
    # Liabilities (2000-2999)
    Account(code="2000", name="Accounts Payable", type="liability", subtype="current_liability", normal_balance="credit"),
    Account(code="2100", name="Accrued Expenses", type="liability", subtype="current_liability", normal_balance="credit"),
    Account(code="2110", name="Accrued Wages", type="liability", subtype="current_liability", normal_balance="credit"),
    Account(code="2200", name="Deferred Revenue", type="liability", subtype="current_liability", normal_balance="credit"),
    Account(code="2300", name="Payroll Taxes Payable", type="liability", subtype="current_liability", normal_balance="credit"),
    Account(code="2400", name="Sales Tax Payable", type="liability", subtype="current_liability", normal_balance="credit"),
    Account(code="2500", name="Notes Payable - Short Term", type="liability", subtype="current_liability", normal_balance="credit"),
    Account(code="2700", name="Notes Payable - Long Term", type="liability", subtype="long_term_liability", normal_balance="credit"),
    
    # Equity (3000-3999)
    Account(code="3000", name="Common Stock", type="equity", subtype="capital", normal_balance="credit"),
    Account(code="3100", name="Retained Earnings", type="equity", subtype="retained_earnings", normal_balance="credit"),
    Account(code="3200", name="Dividends", type="equity", subtype="dividends", normal_balance="debit"),
    
    # Revenue (4000-4999)
    Account(code="4000", name="Service Revenue", type="revenue", subtype="operating_revenue", normal_balance="credit"),
    Account(code="4100", name="Product Revenue", type="revenue", subtype="operating_revenue", normal_balance="credit"),
    Account(code="4900", name="Other Income", type="revenue", subtype="other_income", normal_balance="credit"),
    
    # Cost of Goods Sold (5000-5999)
    Account(code="5000", name="Cost of Goods Sold", type="expense", subtype="cogs", normal_balance="debit"),
    Account(code="5100", name="Direct Labor", type="expense", subtype="cogs", normal_balance="debit"),
    Account(code="5200", name="Materials and Supplies", type="expense", subtype="cogs", normal_balance="debit"),
    
    # Operating Expenses (6000-6999)
    Account(code="6000", name="Rent Expense", type="expense", subtype="operating_expense", normal_balance="debit"),
    Account(code="6100", name="Utilities Expense", type="expense", subtype="operating_expense", normal_balance="debit"),
    Account(code="6200", name="Marketing Expense", type="expense", subtype="operating_expense", normal_balance="debit"),
    Account(code="6300", name="Salaries and Wages", type="expense", subtype="operating_expense", normal_balance="debit"),
    Account(code="6310", name="Payroll Taxes", type="expense", subtype="operating_expense", normal_balance="debit"),
    Account(code="6320", name="Employee Benefits", type="expense", subtype="operating_expense", normal_balance="debit"),
    Account(code="6400", name="Professional Services", type="expense", subtype="operating_expense", normal_balance="debit"),
    Account(code="6410", name="Legal Fees", type="expense", subtype="operating_expense", normal_balance="debit"),
    Account(code="6420", name="Accounting Fees", type="expense", subtype="operating_expense", normal_balance="debit"),
    Account(code="6500", name="Software and Subscriptions", type="expense", subtype="operating_expense", normal_balance="debit"),
    Account(code="6600", name="Travel Expense", type="expense", subtype="operating_expense", normal_balance="debit"),
    Account(code="6610", name="Meals and Entertainment", type="expense", subtype="operating_expense", normal_balance="debit"),
    Account(code="6700", name="Depreciation Expense", type="expense", subtype="operating_expense", normal_balance="debit"),
    Account(code="6800", name="Insurance Expense", type="expense", subtype="operating_expense", normal_balance="debit"),
    Account(code="6900", name="Miscellaneous Expense", type="expense", subtype="operating_expense", normal_balance="debit"),
    Account(code="6950", name="Bank Fees", type="expense", subtype="operating_expense", normal_balance="debit"),
]

# Industry-specific accounts
INDUSTRY_ACCOUNTS = {
    Industry.SAAS: [
        Account(code="4050", name="Subscription Revenue", type="revenue", subtype="operating_revenue", normal_balance="credit"),
        Account(code="4060", name="Professional Services Revenue", type="revenue", subtype="operating_revenue", normal_balance="credit"),
        Account(code="5300", name="Hosting Costs", type="expense", subtype="cogs", normal_balance="debit"),
        Account(code="6250", name="Customer Acquisition Cost", type="expense", subtype="operating_expense", normal_balance="debit"),
    ],
    Industry.AGENCY: [
        Account(code="4070", name="Project Revenue", type="revenue", subtype="operating_revenue", normal_balance="credit"),
        Account(code="4080", name="Retainer Revenue", type="revenue", subtype="operating_revenue", normal_balance="credit"),
        Account(code="5400", name="Contractor Fees", type="expense", subtype="cogs", normal_balance="debit"),
        Account(code="6260", name="Client Entertainment", type="expense", subtype="operating_expense", normal_balance="debit"),
    ],
    Industry.RETAIL: [
        Account(code="1300", name="Inventory", type="asset", subtype="current_asset", normal_balance="debit"),
        Account(code="4020", name="Merchandise Sales", type="revenue", subtype="operating_revenue", normal_balance="credit"),
        Account(code="5010", name="Purchases", type="expense", subtype="cogs", normal_balance="debit"),
        Account(code="5020", name="Freight In", type="expense", subtype="cogs", normal_balance="debit"),
    ],
    Industry.MANUFACTURING: [
        Account(code="1300", name="Raw Materials Inventory", type="asset", subtype="current_asset", normal_balance="debit"),
        Account(code="1310", name="Work in Process", type="asset", subtype="current_asset", normal_balance="debit"),
        Account(code="1320", name="Finished Goods Inventory", type="asset", subtype="current_asset", normal_balance="debit"),
        Account(code="1520", name="Manufacturing Equipment", type="asset", subtype="fixed_asset", normal_balance="debit"),
        Account(code="5050", name="Manufacturing Overhead", type="expense", subtype="cogs", normal_balance="debit"),
    ],
    Industry.CONSULTING: [
        Account(code="4090", name="Consulting Fees", type="revenue", subtype="operating_revenue", normal_balance="credit"),
        Account(code="5500", name="Subcontractor Fees", type="expense", subtype="cogs", normal_balance="debit"),
        Account(code="6270", name="Research and Publications", type="expense", subtype="operating_expense", normal_balance="debit"),
    ],
    Industry.ECOMMERCE: [
        Account(code="1300", name="Inventory", type="asset", subtype="current_asset", normal_balance="debit"),
        Account(code="4030", name="Online Sales", type="revenue", subtype="operating_revenue", normal_balance="credit"),
        Account(code="5600", name="Payment Processing Fees", type="expense", subtype="cogs", normal_balance="debit"),
        Account(code="5700", name="Shipping and Fulfillment", type="expense", subtype="cogs", normal_balance="debit"),
        Account(code="6280", name="Platform Fees", type="expense", subtype="operating_expense", normal_balance="debit"),
    ],
}


class COAGenerator:
    """Generates Chart of Accounts."""
    
    async def generate(
        self,
        company_id: str,
        industry: Industry,
        accounting_basis: AccountingBasis
    ) -> ChartOfAccounts:
        """Generate a complete Chart of Accounts."""
        
        # Start with base accounts
        accounts = list(BASE_ACCOUNTS)
        
        # Add industry-specific accounts
        if industry in INDUSTRY_ACCOUNTS:
            accounts.extend(INDUSTRY_ACCOUNTS[industry])
        
        # If cash basis, remove some accrual-specific accounts
        if accounting_basis == AccountingBasis.CASH:
            accrual_codes = {"1100", "2100", "2110", "2200"}  # AR, Accrued, Deferred
            accounts = [a for a in accounts if a.code not in accrual_codes]
        
        # Sort by account code
        accounts.sort(key=lambda a: a.code)
        
        return ChartOfAccounts(
            company_id=company_id,
            accounts=accounts,
            created_at=datetime.utcnow()
        )
