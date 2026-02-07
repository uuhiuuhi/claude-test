"""날짜 관련 유틸리티 - 사내 표준 규칙 적용"""

import calendar
from datetime import date, timedelta
from typing import Optional, List, Tuple
import re

from utils.constants import (
    BillingCycle,
    BILLING_CYCLE_TARGET_MONTHS,
    BILLING_TIMING_PATTERNS,
    DEFAULT_RENEWAL_PERIOD_MONTHS
)


def get_last_day_of_month(year: int, month: int) -> date:
    """해당 월의 마지막 날짜 반환"""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def get_first_day_of_month(year: int, month: int) -> date:
    """해당 월의 첫째 날짜 반환"""
    return date(year, month, 1)


def is_leap_year(year: int) -> bool:
    """윤년 여부 확인"""
    return calendar.isleap(year)


def add_months(base_date: date, months: int) -> date:
    """월 단위 날짜 더하기 (말일 보정 포함)"""
    month = base_date.month - 1 + months
    year = base_date.year + month // 12
    month = month % 12 + 1

    # 말일 보정: 원래 말일이면 새 달도 말일로
    last_day = calendar.monthrange(year, month)[1]
    day = min(base_date.day, last_day)

    return date(year, month, day)


def is_billing_target_month(billing_cycle: BillingCycle, year: int, month: int,
                            custom_months: Optional[List[int]] = None) -> bool:
    """해당 월이 청구 대상 월인지 확인

    Args:
        billing_cycle: 청구 주기
        year: 연도
        month: 월
        custom_months: 비정기 청구의 경우 직접 지정된 월 목록
    """
    if billing_cycle == BillingCycle.IRREGULAR:
        return custom_months is not None and month in custom_months

    target_months = BILLING_CYCLE_TARGET_MONTHS.get(billing_cycle, [])
    return month in target_months


def calculate_contract_period_status(
    contract_start: Optional[date],
    contract_end: Optional[date],
    auto_renewal: bool,
    renewal_period_months: int,
    check_date: date
) -> Tuple[bool, Optional[date], Optional[date], str]:
    """계약기간 상태 계산 (자동갱신 포함)

    Returns:
        (is_active, effective_start, effective_end, status_message)
    """
    # 계약기간 미확정
    if contract_start is None and contract_end is None:
        return (True, None, None, "계약기간 미확정 - 청구 가능하나 확인 필요")

    if contract_start is None:
        return (True, None, contract_end, "계약시작일 미확정")

    if contract_end is None:
        if auto_renewal:
            return (True, contract_start, None, "계약종료일 미확정 - 자동갱신으로 처리")
        return (True, contract_start, None, "계약종료일 미확정")

    # 계약기간 내
    if contract_start <= check_date <= contract_end:
        return (True, contract_start, contract_end, "계약기간 내")

    # 계약 만료 후 - 자동갱신 확인
    if check_date > contract_end:
        if auto_renewal:
            # 자동갱신으로 롤링 계산
            current_start = contract_start
            current_end = contract_end

            while current_end < check_date:
                current_start = add_months(current_start, renewal_period_months)
                current_end = add_months(current_end, renewal_period_months)

            return (True, current_start, current_end, f"자동갱신됨 ({current_start} ~ {current_end})")
        else:
            return (False, contract_start, contract_end, "계약 만료")

    # 계약 시작 전
    return (False, contract_start, contract_end, "계약 시작 전")


def get_previous_business_day(target_date: date, holidays: List[date]) -> date:
    """직전 영업일 반환 (사내 표준: 휴일인 경우 직전 영업일로 보정)

    Args:
        target_date: 대상 날짜
        holidays: 휴일 목록
    """
    result = target_date

    while result.weekday() >= 5 or result in holidays:  # 토(5), 일(6) 또는 휴일
        result -= timedelta(days=1)

    return result


def parse_billing_timing(timing_text: str) -> dict:
    """발행시기 텍스트 파싱

    Returns:
        {
            'parsed': bool,
            'day': int or 'last',
            'months': List[int] or None (특정 월만 청구하는 경우),
            'is_reverse_billing': bool,
            'requires_manual': bool,
            'original_text': str
        }
    """
    result = {
        'parsed': False,
        'day': None,
        'months': None,
        'is_reverse_billing': False,
        'requires_manual': False,
        'original_text': timing_text
    }

    if not timing_text:
        result['requires_manual'] = True
        return result

    text = timing_text.strip()

    # 역발행 체크
    if any(kw in text for kw in ['역발행', '역발급', '상대발행']):
        result['is_reverse_billing'] = True
        result['parsed'] = True
        return result

    # 수동 지정 필요 키워드
    manual_keywords = ['요청시', '협의', '별도', '문의', '확인']
    if any(kw in text for kw in manual_keywords):
        result['requires_manual'] = True
        return result

    # 기본 패턴 매칭
    for pattern, value in BILLING_TIMING_PATTERNS.items():
        if pattern in text:
            result['day'] = value['day']
            result['parsed'] = True
            break

    # 특정 월 패턴 추출 (예: "3,6,9,12월", "6월, 12월")
    # 먼저 "숫자,숫자,...,숫자월" 패턴 시도 (콤마로 연결된 숫자 + 단일 월)
    multi_month_pattern = r'((?:\d+\s*,\s*)+\d+)\s*월'
    multi_match = re.search(multi_month_pattern, text)
    if multi_match:
        months_str = multi_match.group(1)
        result['months'] = [int(m.strip()) for m in months_str.split(',')]
    else:
        # 개별 "N월" 패턴 (예: "6월, 12월")
        month_pattern = r'(\d+)\s*월'
        month_matches = re.findall(month_pattern, text)
        if month_matches:
            result['months'] = [int(m) for m in month_matches]

    # 연 2회 패턴
    if '연 2회' in text or '연2회' in text:
        result['months'] = result['months'] or [6, 12]
        result['parsed'] = True

    # N일 패턴 (예: "매월 10일")
    day_pattern = r'(\d+)일'
    day_match = re.search(day_pattern, text)
    if day_match and result['day'] is None:
        result['day'] = int(day_match.group(1))
        result['parsed'] = True

    # 파싱 실패 시 수동 지정 필요
    if not result['parsed'] and result['day'] is None:
        result['requires_manual'] = True

    return result


def calculate_billing_date(year: int, month: int, day_spec: any,
                          holidays: List[date]) -> date:
    """청구일자 계산 (휴일 보정 포함)

    Args:
        year: 연도
        month: 월
        day_spec: 일자 지정 (int 또는 'last')
        holidays: 휴일 목록
    """
    if day_spec == 'last':
        target = get_last_day_of_month(year, month)
    else:
        last_day = calendar.monthrange(year, month)[1]
        day = min(int(day_spec), last_day)
        target = date(year, month, day)

    # 사내 표준: 휴일인 경우 직전 영업일로 보정
    return get_previous_business_day(target, holidays)


def get_month_range(year: int, month: int) -> Tuple[date, date]:
    """해당 월의 시작일과 종료일 반환"""
    start = get_first_day_of_month(year, month)
    end = get_last_day_of_month(year, month)
    return (start, end)
