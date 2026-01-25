# Example Data for Living Ledger Auditor

This folder contains realistic financial data for testing the audit functionality.

## Files

### `general_ledger.csv`
40 journal entries for Q4 2024 representing typical SaaS company transactions.

### `chart_of_accounts.csv`
Standard chart of accounts with asset, liability, equity, revenue, and expense accounts.

### `trial_balance.csv`
Trial balance as of December 31, 2024 derived from the general ledger.

## Known Issues (Planted for Audit Testing)

The example data contains these intentional issues that the auditor should detect:

### 1. High-Value Transactions Without Approval
- **Entry EX-007**: $25,000 Google Ads expense exceeds typical approval threshold
- **Entry EX-025**: $15,000 equipment purchase exceeds typical approval threshold

### 2. Expense Misclassifications
- **Entry EX-009**: Flight expense ($2,500) incorrectly coded to "Office Supplies" instead of "Travel & Entertainment"
- **Entry EX-017**: Hotel expense ($1,800) incorrectly coded to "Office Supplies" instead of "Travel & Entertainment"
- **Entry EX-031**: Uber rides ($450) incorrectly coded to "Office Supplies" instead of "Travel & Entertainment"

### 3. Prepaid Expense Not Amortized
- **Entry EX-013**: $6,000 annual insurance premium recorded as prepaid but no monthly amortization entries exist

### 4. Large Period-End Revenue (Timing Concern)
- **Entry EX-021**: $45,000 revenue recognized on December 31st (period end) - potential revenue recognition timing issue

### 5. Negative Cash Balance
- The trial balance shows a negative cash balance of -$6,200, indicating potential overdraft or data error

## Company Profile

- **Name**: Acme Software Solutions Inc.
- **Industry**: SaaS
- **Accounting Basis**: Accrual
- **Reporting Period**: Q4 2024 (October - December)
- **Entity Type**: Synthetic (for testing)

## Usage

Load this example data using:
```python
from generators.example_data import get_example_company

company_data = get_example_company()
```

Or via API:
```bash
curl -X POST http://localhost:8000/api/companies/example
```

## Expected Audit Results

When running an audit on this data, expect to find:
- 5-8 classification findings (misclassified expenses)
- 2-3 approval/control findings (high-value transactions)
- 1-2 timing findings (period-end revenue, prepaid amortization)
- 1 structural finding (negative cash balance)
- Risk score: HIGH to CRITICAL
