"""검증 엔진 테스트"""

import pytest
from datetime import date
from decimal import Decimal
import json

from services.validation_engine import ValidationEngine
from services.billing_engine import BillingEngine
from database.models import Contract, MonthlyBilling, ContractHistory
from utils.constants import BillingCycle, BillingStatus, ContractStatus


class TestPeriodValidation:
    """계약기간 검증 테스트"""

    def test_undefined_period_warning(self, session, sample_company):
        """계약기간 미확정 경고"""
        contract = Contract(
            company_id=sample_company.id,
            item_name="기간 미확정",
            contract_start=None,
            contract_end=None,
            monthly_amount=Decimal("1000000"),
            billing_cycle=BillingCycle.MONTHLY.value,
            status=ContractStatus.PERIOD_UNDEFINED.value
        )
        session.add(contract)
        session.commit()

        billing = MonthlyBilling(
            contract_id=contract.id,
            billing_year=2024,
            billing_month=6,
            calculated_amount=Decimal("1000000"),
            final_amount=Decimal("1000000"),
            status=BillingStatus.DRAFT.value
        )

        engine = ValidationEngine(session)
        warnings = engine.validate_billing(billing, contract)

        period_warnings = [w for w in warnings if w['code'] in ['PERIOD_UNDEFINED', 'STATUS_PERIOD_UNDEFINED']]
        assert len(period_warnings) >= 1


class TestBillingTimingValidation:
    """발행시기 검증 테스트"""

    def test_manual_timing_warning(self, session, sample_company):
        """수동 발행일 지정 필요 경고"""
        contract = Contract(
            company_id=sample_company.id,
            item_name="수동 발행시기",
            contract_start=date(2024, 1, 1),
            contract_end=date(2024, 12, 31),
            monthly_amount=Decimal("1000000"),
            billing_cycle=BillingCycle.MONTHLY.value,
            billing_timing="상무님 요청시",  # 파싱 불가
            status=ContractStatus.ACTIVE.value
        )
        session.add(contract)
        session.commit()

        billing = MonthlyBilling(
            contract_id=contract.id,
            billing_year=2024,
            billing_month=6,
            calculated_amount=Decimal("1000000"),
            final_amount=Decimal("1000000"),
            status=BillingStatus.DRAFT.value
        )

        engine = ValidationEngine(session)
        warnings = engine.validate_billing(billing, contract)

        timing_warnings = [w for w in warnings if w['code'] == 'TIMING_MANUAL_REQUIRED']
        assert len(timing_warnings) == 1


class TestSuddenChangeDetection:
    """급변 탐지 테스트"""

    def test_sudden_amount_change_warning(self, session, sample_contract):
        """금액 급변 경고 (30% 이상)"""
        # 전월 청구 생성
        prev_billing = MonthlyBilling(
            contract_id=sample_contract.id,
            billing_year=2024,
            billing_month=5,
            calculated_amount=Decimal("1000000"),
            final_amount=Decimal("1000000"),
            status=BillingStatus.CONFIRMED.value
        )
        session.add(prev_billing)
        session.commit()

        # 이번 달 청구 (50% 증가)
        curr_billing = MonthlyBilling(
            contract_id=sample_contract.id,
            billing_year=2024,
            billing_month=6,
            calculated_amount=Decimal("1500000"),
            final_amount=Decimal("1500000"),
            status=BillingStatus.DRAFT.value
        )

        engine = ValidationEngine(session)
        warnings = engine.validate_billing(curr_billing, sample_contract)

        change_warnings = [w for w in warnings if w['code'] == 'AMOUNT_SUDDEN_CHANGE']
        assert len(change_warnings) == 1


class TestDuplicateValidation:
    """중복 청구 검증 테스트"""

    def test_duplicate_billing_warning(self, session, sample_contract):
        """중복 청구 경고"""
        # 기존 청구
        existing = MonthlyBilling(
            contract_id=sample_contract.id,
            billing_year=2024,
            billing_month=6,
            calculated_amount=Decimal("1000000"),
            final_amount=Decimal("1000000"),
            status=BillingStatus.CONFIRMED.value
        )
        session.add(existing)
        session.commit()

        # 새 청구 (중복)
        new_billing = MonthlyBilling(
            contract_id=sample_contract.id,
            billing_year=2024,
            billing_month=6,
            calculated_amount=Decimal("1000000"),
            final_amount=Decimal("1000000"),
            status=BillingStatus.DRAFT.value
        )

        engine = ValidationEngine(session)
        warnings = engine.validate_billing(new_billing, sample_contract)

        duplicate_warnings = [w for w in warnings if w['code'] == 'DUPLICATE_BILLING']
        assert len(duplicate_warnings) == 1


class TestReverseBillingValidation:
    """역발행 검증 테스트"""

    def test_reverse_billing_info(self, session, sample_reverse_billing_contract):
        """역발행 정보 표시"""
        billing = MonthlyBilling(
            contract_id=sample_reverse_billing_contract.id,
            billing_year=2024,
            billing_month=6,
            calculated_amount=Decimal("600000"),
            final_amount=Decimal("600000"),
            status=BillingStatus.DRAFT.value
        )

        engine = ValidationEngine(session)
        warnings = engine.validate_billing(billing, sample_reverse_billing_contract)

        reverse_warnings = [w for w in warnings if w['code'] == 'REVERSE_BILLING']
        assert len(reverse_warnings) == 1


class TestMissingBillings:
    """누락 청구 검증 테스트"""

    def test_get_missing_billings(self, session, sample_contract):
        """누락 가능 계약 조회"""
        engine = ValidationEngine(session)
        missing = engine.get_missing_billings(2024, 6)

        # 청구 미생성 상태이므로 누락 목록에 포함
        assert len(missing) == 1
        assert missing[0].id == sample_contract.id

    def test_no_missing_after_billing(self, session, sample_contract):
        """청구 생성 후 누락 없음"""
        # 청구 생성
        billing_engine = BillingEngine(session)
        billings, _ = billing_engine.generate_monthly_billings(2024, 6)
        billing_engine.save_billings(billings)

        # 누락 확인
        validation_engine = ValidationEngine(session)
        missing = validation_engine.get_missing_billings(2024, 6)

        assert len(missing) == 0


class TestOutsourcingValidation:
    """외주 검증 테스트"""

    def test_outsourcing_missing_warning(self, session, sample_contract_with_outsourcing):
        """외주금액 미입력 경고"""
        billing = MonthlyBilling(
            contract_id=sample_contract_with_outsourcing.id,
            billing_year=2024,
            billing_month=6,
            calculated_amount=Decimal("2000000"),
            final_amount=Decimal("2000000"),
            outsourcing_amount=Decimal("0"),  # 외주금액 0
            status=BillingStatus.DRAFT.value
        )

        engine = ValidationEngine(session)
        warnings = engine.validate_billing(billing, sample_contract_with_outsourcing)

        outsourcing_warnings = [w for w in warnings if w['code'] == 'OUTSOURCING_MISSING']
        assert len(outsourcing_warnings) == 1
