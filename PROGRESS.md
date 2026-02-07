# PROGRESS.md - 개발 진행 상황

## Current Status
- 초기 개발 단계 (Initial Commit 완료)
- 핵심 엔진 및 데이터 모델 구현 완료
- UI 페이지 구현 진행 중

## Completed Features

### Data Layer
- [x] SQLModel 데이터 모델 정의 (models.py)
  - Company, Contract, ContractHistory, MonthlyBilling
  - Outsourcing, OutsourcingEntry, OutsourcingHistory
  - Holiday, BillingRule, CodeMapping
- [x] DB 초기화 (init_db.py)
- [x] DB 연결 관리 (connection.py)

### Business Logic (services/)
- [x] BillingEngine - 월 청구 생성, 자동갱신, 중복 방지
- [x] ValidationEngine - 10가지 검증 규칙
- [x] CalculationEngine - 금액/부가세/외주/이익 계산
- [x] ExcelEngine - Excel 임포트/익스포트

### Utils
- [x] constants.py - Enum, 청구주기 설정, Excel 컬럼 매핑
- [x] date_utils.py - 날짜 계산, 자동갱신 롤링
- [x] parsing_utils.py - 텍스트 파싱 유틸

### Tests (59개)
- [x] test_date_utils.py (25개) - 날짜 계산, 윤년, 영업일
- [x] test_calculation_engine.py (10개) - 금액/부가세/외주/이익
- [x] test_billing_engine.py (10개) - 청구 생성, 자동갱신, 중복
- [x] test_validation_engine.py (8개) - 검증 규칙
- [x] test_excel_engine.py (6개) - 임포트/익스포트/라운드트립

### UI Pages
- [x] app.py - 메인 앱 (사이드바 네비게이션)
- [x] contract_page.py - 계약 관리
- [x] billing_page.py - 월 청구 생성
- [x] validation_page.py - 검증/경고
- [x] report_page.py - 리포트
- [x] outsourcing_page.py - 외주 관리
- [x] settings_page.py - 설정
- [x] styles/ - Apple 테마, 재사용 컴포넌트

### DevOps
- [x] Dockerfile - Streamlit 컨테이너화
- [x] .dockerignore - 빌드 제외 파일 설정
- [x] CLAUDE.md compact 정리 (196줄 → 85줄, Docker 추가)

## In Progress
- UI 기능 세부 구현 및 테스트

## Known Issues
- (발견 시 기록)

## Next Steps
- 통합 테스트 추가
- UI 기능 검증
- 실 데이터 임포트 테스트
