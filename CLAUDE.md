# CLAUDE.md

## Project Overview

관리팀 내부용 유지보수 계약·청구·외주·이익 관리 시스템

**Primary Goals:** 매월 청구 누락 0건 / 계약·금액·외주 변경에도 정확한 수익 계산

Excel 기반 업무를 대체하는 관리팀 내부 시스템.

## Tech Stack

- Python 3.11 / Streamlit (UI) / SQLite (DB) / SQLModel (ORM) / openpyxl (Excel)
- Docker (Streamlit 컨테이너 단독 실행, SQLite volume 마운트)
- No external APIs, SaaS, or cloud services (offline capable)

## Build and Run Commands

```bash
# Local
pip install -r requirements.txt
python -c "from database.init_db import initialize_all; initialize_all()"
streamlit run app.py

# Docker
docker build -t maintenance-billing .
docker run -p 8501:8501 -v ./data:/app/data maintenance-billing

# Tests
pytest                                          # 전체
pytest tests/test_billing_engine.py -v          # 특정 파일
pytest tests/test_billing_engine.py::TestAutoRenewal::test_auto_renewal_generates_billing -v
pytest --cov=. --cov-report=html                # 커버리지
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Streamlit UI (ui/)                      │
├─────────────────────────────────────────────────────────────┤
│ contract_page │ billing_page │ validation_page │ report_page │
└───────────────────────────┬─────────────────────────────────┘
┌───────────────────────────┴─────────────────────────────────┐
│                 Business Logic (services/)                   │
│  BillingEngine │ ValidationEngine │ CalculationEngine │ Excel │
└───────────────────────────┬─────────────────────────────────┘
┌───────────────────────────┴─────────────────────────────────┐
│            Data Layer (database/ - SQLModel + SQLite)         │
└─────────────────────────────────────────────────────────────┘
```

## Key Domain Rules (사내 표준)

- **자동갱신**: 기본값 True, 갱신 주기 12개월, 만료 후에도 자동갱신 시 청구 대상
- **계약기간 미확정**: 청구 허용하되 경고 표시
- **청구 주기**: Monthly(1개월), Quarterly(3개월, 3/6/9/12월), Semiannual(6개월, 6/12월), Biannual(6개월, 6/12월), Irregular(수동)
- **외주**: 건별 엔트리 합산 → 없으면 기본값 사용 → 0원은 `outsourcing_amount_zero` 플래그 필요
- **역발행**: 발행일 제안 없음, 이메일 없음, 메모만

**월 청구 생성 Flow**: 대상월 선택 → 계약 자동탐지(자동갱신 포함) → 청구주기 검증 → 변경이력 적용 → 금액 계산(월금액×커버개월) → 외주/이익 계산 → 발행일 제안(휴일→직전영업일) → 검증 → 경고 표시

## Validation Rules (검증 규칙)

`PERIOD_UNDEFINED`, `TIMING_MANUAL_REQUIRED`, `AMOUNT_SUDDEN_CHANGE`(30%+), `OUTSOURCING_MISSING`, `DUPLICATE_BILLING`, `REVERSE_BILLING`, `PO_REQUIRED`/`ATTACHMENT_REQUIRED`, `CONTRACT_EXPIRING`, `PREVIOUS_UNCONFIRMED`, `AUTO_RENEWED`

## Data Models

**Contract**(Company, period, amount, billing_cycle, auto_renewal) → **ContractHistory**(변경 추적) → **MonthlyBilling**(월 청구, override 가능) → **OutsourcingEntry**(월별 다건) / **CodeMapping**(창고/팀 코드) / **Holiday**(발행일 보정)

## Testing

테스트 파일: `test_date_utils`(25) / `test_calculation_engine`(10) / `test_billing_engine`(10) / `test_validation_engine`(8) / `test_excel_engine`(6) — 총 59개

**Rules**: services/ TDD 필수 | `Decimal` 사용, `float` 금지 | 새 청구 주기 추가 시 생성+미생성 테스트 필수 | conftest.py의 `sqlite:///:memory:` 사용 | 엣지 케이스(월/년 전환, 윤년, 잠금, 만료) 포함 | 커밋 전 `pytest` 통과 필수

## Development Principles

1. **청구 누락 방지 최우선** 2. **사용자 오버라이드 항상 가능** 3. **변경 이력 추적** (덮어쓰기 금지) 4. **원문 보존** + 파싱 데이터 병행 5. **모든 계산 테스트 가능**

## 핵심 문서

`CLAUDE.md`(본 파일) / `PROGRESS.md`(진행 상황, 작업 후 업데이트) / `NOTE.md`(빈번한 실수 기록) / `design_spec.xml`(UI 사양) / `utils/constants.py`(Enum, 설정) / `tests/conftest.py`(테스트 픽스처)

## 공통 작업 가이드

1. **분석**: 관련 소스·테스트 읽기, PROGRESS.md·NOTE.md 확인, 영향 엔진 식별
2. **계획**: 영향받는 테스트 클래스 식별, UI는 design_spec.xml 참조, 레이어별 변경점 정리(ui→services→database)
3. **구현**: services/는 TDD (테스트 먼저), 금융 계산은 Decimal 필수, conftest.py 픽스처 활용
4. **검증**: 변경마다 `pytest`, 대상 엔진: `pytest tests/test_<엔진명>.py -v`
5. **코드 리뷰**: 전체 테스트 통과, 청구 누락 시나리오 검토, 엣지 케이스(자동갱신/기간미확정/역발행/외주제로) 확인
6. **문서 업데이트**: PROGRESS.md(완료 작업), NOTE.md(실수 기록), CLAUDE.md(아키텍처 변경 시)
