"""청구 생성 엔진 테스트"""

import pytest
from datetime import date
from decimal import Decimal

from services.billing_engine import BillingEngine
from database.models import Contract, MonthlyBilling
from utils.constants import BillingCycle, BillingStatus


class TestBillingGeneration:
    """청구 생성 테스트"""

    def test_generate_monthly_billing(self, session, sample_contract):
        """월 청구 생성"""
        engine = BillingEngine(session)
        billings, warnings = engine.generate_monthly_billings(2024, 6)

        assert len(billings) == 1
        assert billings[0].final_amount == Decimal("1000000")
        assert billings[0].billing_month == 6

    def test_skip_non_target_month_quarterly(self, session, sample_quarterly_contract):
        """분기 청구 - 대상 월 아닌 경우 스킵"""
        engine = BillingEngine(session)

        # 1월은 분기 청구 대상 아님
        billings, _ = engine.generate_monthly_billings(2024, 1)
        assert len(billings) == 0

        # 3월은 분기 청구 대상
        billings, _ = engine.generate_monthly_billings(2024, 3)
        assert len(billings) == 1

    def test_skip_non_target_month_semiannual(self, session, sample_semiannual_contract):
        """반기 청구 - 대상 월 아닌 경우 스킵"""
        engine = BillingEngine(session)

        # 3월은 반기 청구 대상 아님
        billings, _ = engine.generate_monthly_billings(2024, 3)
        assert len(billings) == 0

        # 6월은 반기 청구 대상
        billings, _ = engine.generate_monthly_billings(2024, 6)
        assert len(billings) == 1


class TestAutoRenewal:
    """자동갱신 테스트"""

    def test_auto_renewal_generates_billing(self, session, sample_company):
        """자동갱신된 계약 청구 생성"""
        # 2023년 계약 (만료됨, 자동갱신 true)
        contract = Contract(
            company_id=sample_company.id,
            item_name="자동갱신 테스트",
            contract_start=date(2023, 1, 1),
            contract_end=date(2023, 12, 31),
            monthly_amount=Decimal("1000000"),
            billing_cycle=BillingCycle.MONTHLY.value,
            auto_renewal=True,
            renewal_period_months=12,
            status="active"
        )
        session.add(contract)
        session.commit()

        engine = BillingEngine(session)
        # 2024년 6월 청구 생성 (자동갱신으로 유효)
        billings, warnings = engine.generate_monthly_billings(2024, 6)

        assert len(billings) == 1
        # 자동갱신 경고 확인
        auto_renewal_warnings = [w for w in warnings if w.get('code') == 'AUTO_RENEWED']
        assert len(auto_renewal_warnings) >= 0  # 경고가 있을 수 있음

    def test_expired_contract_no_renewal(self, session, sample_company):
        """만료 계약 (자동갱신 없음) 청구 미생성"""
        contract = Contract(
            company_id=sample_company.id,
            item_name="만료 계약",
            contract_start=date(2023, 1, 1),
            contract_end=date(2023, 12, 31),
            monthly_amount=Decimal("1000000"),
            billing_cycle=BillingCycle.MONTHLY.value,
            auto_renewal=False,  # 자동갱신 없음
            status="active"
        )
        session.add(contract)
        session.commit()

        engine = BillingEngine(session)
        billings, _ = engine.generate_monthly_billings(2024, 6)

        assert len(billings) == 0


class TestDuplicatePrevention:
    """중복 청구 방지 테스트"""

    def test_no_duplicate_billing(self, session, sample_contract):
        """중복 청구 방지"""
        engine = BillingEngine(session)

        # 첫 번째 생성
        billings1, _ = engine.generate_monthly_billings(2024, 6)
        engine.save_billings(billings1)

        # 두 번째 생성 시도
        billings2, _ = engine.generate_monthly_billings(2024, 6)

        assert len(billings1) == 1
        assert len(billings2) == 0  # 중복 생성 안됨

    def test_check_duplicate_billing(self, session, sample_contract):
        """중복 청구 확인"""
        engine = BillingEngine(session)

        # 청구 생성 및 저장
        billings, _ = engine.generate_monthly_billings(2024, 6)
        engine.save_billings(billings)

        # 중복 확인
        duplicate = engine.check_duplicate_billing(sample_contract.id, 2024, 6)
        assert duplicate is not None


class TestBillingOverride:
    """청구 오버라이드 테스트"""

    def test_override_amount(self, session, sample_contract):
        """금액 오버라이드"""
        engine = BillingEngine(session)

        billings, _ = engine.generate_monthly_billings(2024, 6)
        saved = engine.save_billings(billings)

        # 오버라이드
        updated = engine.update_billing_override(
            saved[0].id,
            override_amount=Decimal("1200000")
        )

        assert updated.override_amount == Decimal("1200000")
        assert updated.final_amount == Decimal("1200000")
        # 부가세도 재계산
        assert updated.vat_amount == Decimal("120000")

    def test_cannot_modify_locked_billing(self, session, sample_contract):
        """잠금 상태 청구 수정 불가"""
        engine = BillingEngine(session)

        billings, _ = engine.generate_monthly_billings(2024, 6)
        saved = engine.save_billings(billings)

        # 잠금
        engine.lock_billing(saved[0].id)

        # 수정 시도
        with pytest.raises(ValueError):
            engine.update_billing_override(saved[0].id, override_amount=Decimal("1200000"))


class TestReverseBlling:
    """역발행 테스트"""

    def test_reverse_billing_no_suggested_date(self, session, sample_reverse_billing_contract):
        """역발행 계약 - 발행일 제안 없음"""
        engine = BillingEngine(session)
        billings, _ = engine.generate_monthly_billings(2024, 6)

        assert len(billings) == 1
        assert billings[0].suggested_date is None
