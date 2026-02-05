"""날짜 유틸리티 테스트"""

import pytest
from datetime import date
from utils.date_utils import (
    get_last_day_of_month,
    add_months,
    is_leap_year,
    is_billing_target_month,
    calculate_contract_period_status,
    get_previous_business_day,
    parse_billing_timing,
    calculate_billing_date
)
from utils.constants import BillingCycle


class TestGetLastDayOfMonth:
    """월 말일 계산 테스트"""

    def test_regular_month(self):
        """일반 월 말일"""
        assert get_last_day_of_month(2024, 1) == date(2024, 1, 31)
        assert get_last_day_of_month(2024, 4) == date(2024, 4, 30)

    def test_february_leap_year(self):
        """윤년 2월"""
        assert get_last_day_of_month(2024, 2) == date(2024, 2, 29)

    def test_february_non_leap_year(self):
        """평년 2월"""
        assert get_last_day_of_month(2023, 2) == date(2023, 2, 28)


class TestAddMonths:
    """월 더하기 테스트"""

    def test_add_months_normal(self):
        """일반 월 더하기"""
        result = add_months(date(2024, 1, 15), 3)
        assert result == date(2024, 4, 15)

    def test_add_months_year_change(self):
        """연도 변경"""
        result = add_months(date(2024, 11, 15), 3)
        assert result == date(2025, 2, 15)

    def test_add_months_end_of_month_adjustment(self):
        """말일 보정 (31일 → 30일 달)"""
        result = add_months(date(2024, 1, 31), 1)
        assert result == date(2024, 2, 29)  # 윤년 2월 말일

    def test_add_months_leap_year_february(self):
        """윤년 2월 말일에서 더하기"""
        result = add_months(date(2024, 2, 29), 12)
        assert result == date(2025, 2, 28)  # 평년이므로 28일


class TestIsBillingTargetMonth:
    """청구 대상 월 확인 테스트"""

    def test_monthly_billing(self):
        """매월 청구"""
        for month in range(1, 13):
            assert is_billing_target_month(BillingCycle.MONTHLY, 2024, month) is True

    def test_quarterly_billing(self):
        """분기 청구"""
        assert is_billing_target_month(BillingCycle.QUARTERLY, 2024, 3) is True
        assert is_billing_target_month(BillingCycle.QUARTERLY, 2024, 6) is True
        assert is_billing_target_month(BillingCycle.QUARTERLY, 2024, 9) is True
        assert is_billing_target_month(BillingCycle.QUARTERLY, 2024, 12) is True
        assert is_billing_target_month(BillingCycle.QUARTERLY, 2024, 1) is False
        assert is_billing_target_month(BillingCycle.QUARTERLY, 2024, 5) is False

    def test_semiannual_billing(self):
        """반기 청구"""
        assert is_billing_target_month(BillingCycle.SEMIANNUAL, 2024, 6) is True
        assert is_billing_target_month(BillingCycle.SEMIANNUAL, 2024, 12) is True
        assert is_billing_target_month(BillingCycle.SEMIANNUAL, 2024, 3) is False

    def test_irregular_billing_with_custom_months(self):
        """비정기 청구 (커스텀 월)"""
        custom = [2, 8]
        assert is_billing_target_month(BillingCycle.IRREGULAR, 2024, 2, custom) is True
        assert is_billing_target_month(BillingCycle.IRREGULAR, 2024, 8, custom) is True
        assert is_billing_target_month(BillingCycle.IRREGULAR, 2024, 6, custom) is False


class TestCalculateContractPeriodStatus:
    """계약기간 상태 계산 테스트 (자동갱신 포함)"""

    def test_active_contract(self):
        """활성 계약"""
        is_active, _, _, msg = calculate_contract_period_status(
            date(2024, 1, 1),
            date(2024, 12, 31),
            auto_renewal=False,
            renewal_period_months=12,
            check_date=date(2024, 6, 15)
        )
        assert is_active is True
        assert "계약기간 내" in msg

    def test_expired_contract_no_renewal(self):
        """만료 계약 (자동갱신 없음)"""
        is_active, _, _, msg = calculate_contract_period_status(
            date(2023, 1, 1),
            date(2023, 12, 31),
            auto_renewal=False,
            renewal_period_months=12,
            check_date=date(2024, 6, 15)
        )
        assert is_active is False
        assert "만료" in msg

    def test_auto_renewal(self):
        """자동갱신 롤링"""
        is_active, eff_start, eff_end, msg = calculate_contract_period_status(
            date(2023, 1, 1),
            date(2023, 12, 31),
            auto_renewal=True,
            renewal_period_months=12,
            check_date=date(2024, 6, 15)
        )
        assert is_active is True
        assert "자동갱신됨" in msg
        assert eff_start == date(2024, 1, 1)
        assert eff_end == date(2024, 12, 31)

    def test_period_undefined(self):
        """계약기간 미확정"""
        is_active, _, _, msg = calculate_contract_period_status(
            None, None,
            auto_renewal=True,
            renewal_period_months=12,
            check_date=date(2024, 6, 15)
        )
        assert is_active is True
        assert "미확정" in msg


class TestGetPreviousBusinessDay:
    """직전 영업일 계산 테스트"""

    def test_weekday(self):
        """평일"""
        holidays = []
        result = get_previous_business_day(date(2024, 1, 15), holidays)  # 월요일
        assert result == date(2024, 1, 15)

    def test_saturday(self):
        """토요일 → 금요일"""
        holidays = []
        result = get_previous_business_day(date(2024, 1, 13), holidays)  # 토요일
        assert result == date(2024, 1, 12)  # 금요일

    def test_sunday(self):
        """일요일 → 금요일"""
        holidays = []
        result = get_previous_business_day(date(2024, 1, 14), holidays)  # 일요일
        assert result == date(2024, 1, 12)  # 금요일

    def test_holiday(self):
        """휴일 → 직전 영업일"""
        holidays = [date(2024, 1, 1)]
        result = get_previous_business_day(date(2024, 1, 1), holidays)  # 월요일 휴일
        assert result == date(2023, 12, 29)  # 금요일


class TestParseBillingTiming:
    """발행시기 파싱 테스트"""

    def test_parse_last_day(self):
        """말일 파싱"""
        result = parse_billing_timing("말일")
        assert result['parsed'] is True
        assert result['day'] == 'last'

    def test_parse_specific_day(self):
        """특정일 파싱"""
        result = parse_billing_timing("매월 10일")
        assert result['parsed'] is True
        assert result['day'] == 10

    def test_parse_reverse_billing(self):
        """역발행 파싱"""
        result = parse_billing_timing("역발행")
        assert result['parsed'] is True
        assert result['is_reverse_billing'] is True

    def test_parse_quarterly_months(self):
        """분기월 파싱"""
        result = parse_billing_timing("3,6,9,12월 말일")
        assert result['parsed'] is True
        assert result['months'] == [3, 6, 9, 12]

    def test_parse_requires_manual(self):
        """수동 지정 필요"""
        result = parse_billing_timing("상무님 요청시")
        assert result['requires_manual'] is True

    def test_parse_biannual(self):
        """연 2회 파싱"""
        result = parse_billing_timing("연 2회(6월,12월)")
        assert result['parsed'] is True
        assert result['months'] == [6, 12]
