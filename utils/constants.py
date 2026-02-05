"""사내 표준 상수 정의"""

from enum import Enum


class BillingCycle(str, Enum):
    """청구 주기"""
    MONTHLY = "monthly"           # 매월
    QUARTERLY = "quarterly"       # 분기 (3개월)
    SEMIANNUAL = "semiannual"     # 반기 (6개월)
    BIANNUAL = "biannual"         # 연 2회
    IRREGULAR = "irregular"       # 비정기


class ContractStatus(str, Enum):
    """계약 상태"""
    ACTIVE = "active"             # 활성
    EXPIRED = "expired"           # 만료
    TERMINATED = "terminated"     # 해지
    PERIOD_UNDEFINED = "period_undefined"  # 계약기간 미확정


class BillingStatus(str, Enum):
    """청구 상태"""
    DRAFT = "draft"               # 초안
    CONFIRMED = "confirmed"       # 확정
    LOCKED = "locked"             # 잠금(수정불가)
    CANCELLED = "cancelled"       # 취소


class CompanyType(str, Enum):
    """업체 유형"""
    SALES = "sales"               # 매출업체 (유지보수 계약업체)
    PURCHASE = "purchase"         # 매입업체 (외주)


# 청구 주기별 커버 개월 수
BILLING_CYCLE_MONTHS = {
    BillingCycle.MONTHLY: 1,
    BillingCycle.QUARTERLY: 3,
    BillingCycle.SEMIANNUAL: 6,
    BillingCycle.BIANNUAL: 6,  # 연 2회 = 6개월분
    BillingCycle.IRREGULAR: 1,  # 비정기는 기본 1개월
}

# 청구 주기별 청구 대상 월 (1월 기준)
BILLING_CYCLE_TARGET_MONTHS = {
    BillingCycle.MONTHLY: list(range(1, 13)),  # 모든 월
    BillingCycle.QUARTERLY: [3, 6, 9, 12],     # 분기말
    BillingCycle.SEMIANNUAL: [6, 12],          # 반기말
    BillingCycle.BIANNUAL: [6, 12],            # 연 2회
    BillingCycle.IRREGULAR: [],                 # 비정기는 수동
}

# 기본 갱신 주기 (개월)
DEFAULT_RENEWAL_PERIOD_MONTHS = 12

# 급변 탐지 임계값 (%)
SUDDEN_CHANGE_THRESHOLD_PERCENT = 30

# 엑셀 템플릿 컬럼 매핑 (A~S)
EXCEL_COLUMN_MAPPING = {
    'A': 'warehouse_code',        # 창고
    'B': 'company_code',          # 코드
    'C': 'company_name',          # 업체명
    'D': 'item_name',             # 품목명
    'E': 'contract_start_date',   # 계약시작일
    'F': 'contract_end_date',     # 계약종료일
    'G': 'monthly_amount',        # 월계약금액
    'H': 'billing_amount',        # 청구금액
    'I': 'vat_amount',            # 부가세
    'J': 'total_amount',          # 합계
    'K': 'outsourcing_company',   # 외주업체
    'L': 'outsourcing_amount',    # 외주금액
    'M': 'profit',                # 이익
    'N': 'billing_timing',        # 발행시기
    'O': 'sales_date',            # 매출일자
    'P': 'request_date',          # 요청일자
    'Q': 'purchase_date',         # 매입일자
    'R': 'notes',                 # 특이사항
    'S': 'auto_renewal',          # 자동갱신
}

# 역발행 키워드
REVERSE_BILLING_KEYWORDS = ['역발행', '역발급', '상대발행']

# 발행시기 파싱 패턴
BILLING_TIMING_PATTERNS = {
    '말일': {'day': 'last'},
    '월초': {'day': 1},
    '월말': {'day': 'last'},
    '10일': {'day': 10},
    '15일': {'day': 15},
    '20일': {'day': 20},
    '25일': {'day': 25},
}
