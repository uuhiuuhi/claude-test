# NOTE.md - 빈번한 실수와 해결 방법

## 금융 계산
- **Decimal 필수**: 금액 계산에 `float` 절대 사용 금지. 반드시 `Decimal("1000000")` 형태 사용
- **부가세 반올림**: `int(amount * Decimal("0.1"))` - 원 단위 절사

## 도메인 로직
- **BillingCycle.BIANNUAL vs SEMIANNUAL**: 둘 다 6개월분이지만 개념이 다름. BIANNUAL=연 2회, SEMIANNUAL=반기. `BILLING_CYCLE_MONTHS`에서 둘 다 6으로 매핑됨
- **outsourcing_amount_zero 플래그**: `default_outsourcing_amount=0`과 `outsourcing_amount_zero=True`는 다름. `True`는 "외주 0원을 명시적으로 설정"한 것, 플래그 없이 0이면 "미입력" 상태로 경고 대상
- **자동갱신**: `auto_renewal=True`가 사내 기본값. 만료된 계약도 자동갱신 플래그가 있으면 청구 대상

## SQLModel / Database
- **Relationship foreign_keys**: 같은 테이블에 FK가 여러 개일 때 `sa_relationship_kwargs={"foreign_keys": "[Model.field]"}` 형태로 명시 필요 (Company → Contract 참조)
- **In-memory SQLite**: 테스트에서 `sqlite:///:memory:` 사용. 세션 간 데이터 공유 안 됨

## Windows 환경
- **openpyxl 임시 파일 정리**: Windows에서 Excel 파일 핸들이 남아있을 수 있음. 테스트 정리 시 `gc.collect()` 호출 후 삭제 필요 (test_excel_engine.py 패턴 참조)

## 청구 주기
- **IRREGULAR(비정기)**: 대상 월이 빈 리스트 `[]`. 자동 청구 대상에서 제외되며 수동 처리 필요
- **분기 대상 월**: 3, 6, 9, 12월만 청구 대상 (QUARTERLY)
- **반기 대상 월**: 6, 12월만 청구 대상 (SEMIANNUAL, BIANNUAL)
