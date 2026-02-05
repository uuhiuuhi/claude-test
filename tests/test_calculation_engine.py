"""계산 엔진 테스트"""

import pytest
from datetime import date
from decimal import Decimal

from services.calculation_engine import CalculationEngine
from database.models import Contract, MonthlyBilling, OutsourcingEntry
from utils.constants import BillingCycle


class TestBillingAmountCalculation:
    """청구금액 계산 테스트"""

    def test_monthly_billing_amount(self, session, sample_contract):
        """월 청구금액 계산"""
        engine = CalculationEngine(session)
        amount, cover_months, note = engine.calculate_billing_amount(
            sample_contract, 2024, 6
        )

        assert amount == Decimal("1000000")
        assert cover_months == 1

    def test_quarterly_billing_amount(self, session, sample_quarterly_contract):
        """분기 청구금액 계산 (월금액 × 3)"""
        engine = CalculationEngine(session)
        amount, cover_months, note = engine.calculate_billing_amount(
            sample_quarterly_contract, 2024, 6
        )

        assert amount == Decimal("1500000")  # 500,000 × 3
        assert cover_months == 3

    def test_semiannual_billing_amount(self, session, sample_semiannual_contract):
        """반기 청구금액 계산 (월금액 × 6)"""
        engine = CalculationEngine(session)
        amount, cover_months, note = engine.calculate_billing_amount(
            sample_semiannual_contract, 2024, 6
        )

        assert amount == Decimal("4800000")  # 800,000 × 6
        assert cover_months == 6


class TestVatCalculation:
    """부가세 계산 테스트"""

    def test_vat_calculation(self, session):
        """부가세 10% 계산"""
        engine = CalculationEngine(session)
        vat, total = engine.calculate_vat_and_total(Decimal("1000000"))

        assert vat == Decimal("100000")
        assert total == Decimal("1100000")

    def test_vat_rounding(self, session):
        """부가세 반올림"""
        engine = CalculationEngine(session)
        vat, total = engine.calculate_vat_and_total(Decimal("1234567"))

        assert vat == Decimal("123457")  # 반올림
        assert total == Decimal("1358024")


class TestOutsourcingAmountCalculation:
    """외주금액 계산 테스트"""

    def test_default_outsourcing_amount(self, session, sample_contract_with_outsourcing):
        """기본 외주금액 적용"""
        engine = CalculationEngine(session)
        amount, note = engine.calculate_outsourcing_amount(
            sample_contract_with_outsourcing, None, 2024, 6, 1
        )

        assert amount == Decimal("500000")
        assert "기본 외주금액" in note

    def test_outsourcing_zero_setting(self, session, sample_company):
        """외주금액 0 명시 설정"""
        from database.models import Contract
        from utils.constants import ContractStatus

        contract = Contract(
            company_id=sample_company.id,
            item_name="외주 0 테스트",
            contract_start=date(2024, 1, 1),
            contract_end=date(2024, 12, 31),
            monthly_amount=Decimal("1000000"),
            billing_cycle=BillingCycle.MONTHLY.value,
            outsourcing_amount_zero=True,  # 외주금액 0 명시
            status=ContractStatus.ACTIVE.value
        )
        session.add(contract)
        session.commit()

        engine = CalculationEngine(session)
        amount, note = engine.calculate_outsourcing_amount(contract, None, 2024, 6, 1)

        assert amount == Decimal("0")
        assert "0 설정" in note

    def test_outsourcing_multiple_entries(self, session, sample_contract, sample_outsourcing_company):
        """외주 다건 합산"""
        from utils.constants import BillingStatus

        # 청구 생성
        billing = MonthlyBilling(
            contract_id=sample_contract.id,
            billing_year=2024,
            billing_month=6,
            calculated_amount=Decimal("1000000"),
            final_amount=Decimal("1000000"),
            status=BillingStatus.DRAFT.value
        )
        session.add(billing)
        session.commit()
        session.refresh(billing)

        # 외주 매입건 추가 (다건)
        entries = [
            OutsourcingEntry(
                billing_id=billing.id,
                outsourcing_company_id=sample_outsourcing_company.id,
                amount=Decimal("200000"),
                purchase_date=date(2024, 6, 10)
            ),
            OutsourcingEntry(
                billing_id=billing.id,
                outsourcing_company_id=sample_outsourcing_company.id,
                amount=Decimal("150000"),
                purchase_date=date(2024, 6, 20)
            ),
        ]
        for entry in entries:
            session.add(entry)
        session.commit()

        engine = CalculationEngine(session)
        amount, note = engine.calculate_outsourcing_amount(
            sample_contract, billing.id, 2024, 6, 1
        )

        assert amount == Decimal("350000")  # 200,000 + 150,000
        assert "2건 합산" in note


class TestProfitCalculation:
    """이익 계산 테스트"""

    def test_profit_calculation(self, session):
        """실제이익 = 청구금액 - 외주금액"""
        engine = CalculationEngine(session)
        profit = engine.calculate_profit(
            Decimal("1000000"),
            Decimal("300000")
        )

        assert profit == Decimal("700000")

    def test_profit_with_zero_outsourcing(self, session):
        """외주금액 0인 경우"""
        engine = CalculationEngine(session)
        profit = engine.calculate_profit(
            Decimal("1000000"),
            Decimal("0")
        )

        assert profit == Decimal("1000000")
