# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

관리팀 내부용 유지보수 계약·청구·외주·이익 관리 시스템 (Internal Maintenance Contract/Billing/Outsourcing/Profit Management System)

**Primary Goals:**
1. Zero missed monthly billing (매월 유지보수 청구 누락 0건)
2. Accurate monthly revenue/outsourcing/profit calculation despite contract/amount/outsourcing changes

This system replaces Excel-based workflows used by the management team.

## Tech Stack

- Python 3.11
- Streamlit (UI)
- SQLite (DB)
- SQLModel (ORM)
- openpyxl (Excel import/export)
- No external APIs, SaaS, or cloud services (offline capable)

## Build and Run Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from database.init_db import initialize_all; initialize_all()"

# Run the application
streamlit run app.py

# Run all tests
pytest

# Run specific test file
pytest tests/test_billing_engine.py -v

# Run specific test function
pytest tests/test_billing_engine.py::TestAutoRenewal::test_auto_renewal_generates_billing -v

# Run tests with coverage
pytest --cov=. --cov-report=html
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Streamlit UI (ui/)                      │
├─────────────────────────────────────────────────────────────┤
│ contract_page │ billing_page │ validation_page │ report_page │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 Business Logic (services/)                   │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ BillingEngine│ Validation   │ Calculation  │ ExcelEngine    │
│              │ Engine       │ Engine       │                │
└──────────────┴──────────────┴──────────────┴────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer (database/)                    │
├─────────────────────────────────────────────────────────────┤
│ models.py (SQLModel) │ connection.py │ init_db.py          │
└─────────────────────────────────────────────────────────────┘
```

## Key Domain Rules (사내 표준)

### Contract Rules
- Auto-renewal default: True (자동갱신 기본값)
- Default renewal period: 12 months
- Undefined period contracts: Allow billing with warning

### Billing Generation Flow (월 청구 생성)
1. Select billing month
2. Auto-detect target contracts (including auto-renewed)
3. Validate billing cycle (monthly/quarterly/semiannual/biannual/irregular)
4. Apply contract history (금액 변경 이력)
5. Calculate billing amount (월금액 × 커버개월)
6. Calculate outsourcing amount
7. Calculate profit (청구금액 - 외주금액)
8. Suggest billing date (휴일 → 직전 영업일)
9. Run validation
10. Display warnings

### Billing Cycle Calculations
- Monthly: 1 month
- Quarterly: 3 months (target: 3,6,9,12월)
- Semiannual: 6 months (target: 6,12월)
- Biannual: 6 months (target: 6,12월)

### Outsourcing Rules
- If entries exist: Sum all entries
- If no entries: Use default outsourcing amount
- Zero outsourcing: Explicit flag required

### Reverse Billing (역발행)
- No billing date suggestion
- No email process
- Manual memo only

## Validation Rules (검증 규칙)

1. `PERIOD_UNDEFINED` - 계약기간 미확정
2. `TIMING_MANUAL_REQUIRED` - 발행시기 수동 지정 필요
3. `AMOUNT_SUDDEN_CHANGE` - 금액 급변 (30%+)
4. `OUTSOURCING_MISSING` - 외주금액 미입력
5. `DUPLICATE_BILLING` - 중복 청구
6. `REVERSE_BILLING` - 역발행 정보
7. `PO_REQUIRED` / `ATTACHMENT_REQUIRED` - 고객별 규칙
8. `CONTRACT_EXPIRING` - 계약 만료 임박
9. `PREVIOUS_UNCONFIRMED` - 이전월 미확정
10. `AUTO_RENEWED` - 자동갱신 상태

## Data Models

- **Contract**: Company, period, amount, billing cycle, auto-renewal
- **ContractHistory**: Track changes (amount, period, outsourcing)
- **MonthlyBilling**: Monthly billing records with override capability
- **OutsourcingEntry**: Multiple entries per month allowed
- **CodeMapping**: Warehouse/team codes (105=1팀, 106=2팀)
- **Holiday**: For billing date adjustment

## Testing Strategy

Tests are organized by engine:
- `test_date_utils.py` - Date calculations, auto-renewal rolling
- `test_calculation_engine.py` - Billing/VAT/outsourcing/profit calculations
- `test_billing_engine.py` - Billing generation, duplicates, overrides
- `test_validation_engine.py` - All 10 validation rules
- `test_excel_engine.py` - Import/Export, roundtrip

## Development Principles

1. **Billing miss prevention is top priority**
2. **User override always possible** - auto-calculated values must be editable
3. **History tracking for changes** - never overwrite; maintain history
4. **Preserve original text** with parsed structured data
5. **All calculations must be testable**
