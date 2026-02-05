"""계산 엔진 - 청구금액, 외주금액, 실제이익 계산"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple
from sqlmodel import Session, select

from database.models import (
    Contract, ContractHistory, MonthlyBilling,
    Outsourcing, OutsourcingEntry
)
from utils.constants import BillingCycle, BILLING_CYCLE_MONTHS


class CalculationEngine:
    """계산 엔진 - 사내 표준 계산 규칙 적용"""

    VAT_RATE = Decimal("0.1")  # 부가세율 10%

    def __init__(self, session: Session):
        self.session = session

    def calculate_billing_amount(
        self,
        contract: Contract,
        billing_year: int,
        billing_month: int,
        cover_months: Optional[int] = None
    ) -> Tuple[Decimal, int, str]:
        """청구금액 계산

        Args:
            contract: 계약
            billing_year: 청구년도
            billing_month: 청구월
            cover_months: 커버 개월 수 (None이면 청구주기에서 자동 산정)

        Returns:
            (calculated_amount, cover_months, calculation_note)
        """
        # 커버 개월 수 결정
        if cover_months is None:
            billing_cycle = BillingCycle(contract.billing_cycle)
            cover_months = BILLING_CYCLE_MONTHS.get(billing_cycle, 1)

        # 적용 월 기준 계약금액 조회 (이력 반영)
        effective_amount = self._get_effective_amount(
            contract.id,
            billing_year,
            billing_month,
            contract.monthly_amount
        )

        # 청구금액 = 월 계약금액 × 커버 개월 수
        calculated_amount = effective_amount * cover_months

        note = f"월 {effective_amount:,}원 × {cover_months}개월"

        return (calculated_amount, cover_months, note)

    def _get_effective_amount(
        self,
        contract_id: int,
        year: int,
        month: int,
        default_amount: Decimal
    ) -> Decimal:
        """적용 월 기준 유효 계약금액 조회 (이력 반영)"""
        check_date = date(year, month, 1)

        # 금액 변경 이력 조회 (적용일 기준 내림차순)
        statement = select(ContractHistory).where(
            ContractHistory.contract_id == contract_id,
            ContractHistory.change_type == 'amount',
            ContractHistory.effective_date <= check_date
        ).order_by(ContractHistory.effective_date.desc())

        history = self.session.exec(statement).first()

        if history and history.new_value:
            import json
            new_value = json.loads(history.new_value)
            if 'monthly_amount' in new_value:
                return Decimal(str(new_value['monthly_amount']))

        return default_amount

    def calculate_vat_and_total(
        self,
        billing_amount: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """부가세 및 합계 계산

        Returns:
            (vat_amount, total_amount)
        """
        vat = (billing_amount * self.VAT_RATE).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP
        )
        total = billing_amount + vat
        return (vat, total)

    def calculate_outsourcing_amount(
        self,
        contract: Contract,
        billing_id: Optional[int],
        billing_year: int,
        billing_month: int,
        cover_months: int = 1
    ) -> Tuple[Decimal, str]:
        """외주금액 계산

        사내 표준 규칙:
        - 외주 매입건이 있으면 → 합산
        - 외주 매입건이 없으면 → 계약기준 월 외주금액 × 커버개월 자동 적용
        - 외주금액 0 명시 설정이면 → 0

        Returns:
            (outsourcing_amount, calculation_note)
        """
        # 외주금액 0 명시 설정 체크
        if contract.outsourcing_amount_zero:
            return (Decimal("0"), "외주금액 0 설정")

        # 매입건 조회 (billing_id가 있는 경우)
        if billing_id:
            statement = select(OutsourcingEntry).where(
                OutsourcingEntry.billing_id == billing_id
            )
            entries = self.session.exec(statement).all()

            if entries:
                total = sum(entry.amount for entry in entries)
                note = f"매입건 {len(entries)}건 합산"
                return (total, note)

        # 매입건 없음 → 기본값 적용
        if contract.default_outsourcing_amount > 0:
            # 적용 월 기준 외주금액 조회 (이력 반영)
            effective_amount = self._get_effective_outsourcing_amount(
                contract.id,
                billing_year,
                billing_month,
                contract.default_outsourcing_amount
            )
            total = effective_amount * cover_months
            note = f"기본 외주금액 월 {effective_amount:,}원 × {cover_months}개월"
            return (total, note)

        return (Decimal("0"), "외주 없음")

    def _get_effective_outsourcing_amount(
        self,
        contract_id: int,
        year: int,
        month: int,
        default_amount: Decimal
    ) -> Decimal:
        """적용 월 기준 유효 외주금액 조회 (이력 반영)"""
        check_date = date(year, month, 1)

        # 외주금액 변경 이력 조회
        statement = select(ContractHistory).where(
            ContractHistory.contract_id == contract_id,
            ContractHistory.change_type == 'outsourcing',
            ContractHistory.effective_date <= check_date
        ).order_by(ContractHistory.effective_date.desc())

        history = self.session.exec(statement).first()

        if history and history.new_value:
            import json
            new_value = json.loads(history.new_value)
            if 'outsourcing_amount' in new_value:
                return Decimal(str(new_value['outsourcing_amount']))

        return default_amount

    def calculate_profit(
        self,
        billing_amount: Decimal,
        outsourcing_amount: Decimal
    ) -> Decimal:
        """실제이익 계산

        사내 표준: 실제이익 = 청구금액(매출) - 외주금액(매입)
        """
        return billing_amount - outsourcing_amount

    def calculate_monthly_summary(
        self,
        year: int,
        month: int,
        warehouse_code: Optional[str] = None
    ) -> dict:
        """월별 집계 계산

        Returns:
            {
                'total_billing': Decimal,
                'total_outsourcing': Decimal,
                'total_profit': Decimal,
                'count': int,
                'by_warehouse': dict  # 창고별 집계
            }
        """
        statement = select(MonthlyBilling).where(
            MonthlyBilling.billing_year == year,
            MonthlyBilling.billing_month == month,
            MonthlyBilling.status != 'cancelled'
        )

        billings = self.session.exec(statement).all()

        result = {
            'total_billing': Decimal("0"),
            'total_outsourcing': Decimal("0"),
            'total_profit': Decimal("0"),
            'count': 0,
            'by_warehouse': {}
        }

        for billing in billings:
            contract = billing.contract
            if contract is None:
                continue

            # 창고 필터
            company_warehouse = contract.company.warehouse_code if contract.company else None
            if warehouse_code and company_warehouse != warehouse_code:
                continue

            result['total_billing'] += billing.final_amount
            result['total_outsourcing'] += billing.outsourcing_amount
            result['total_profit'] += billing.profit
            result['count'] += 1

            # 창고별 집계
            wh = company_warehouse or 'unknown'
            if wh not in result['by_warehouse']:
                result['by_warehouse'][wh] = {
                    'billing': Decimal("0"),
                    'outsourcing': Decimal("0"),
                    'profit': Decimal("0"),
                    'count': 0
                }

            result['by_warehouse'][wh]['billing'] += billing.final_amount
            result['by_warehouse'][wh]['outsourcing'] += billing.outsourcing_amount
            result['by_warehouse'][wh]['profit'] += billing.profit
            result['by_warehouse'][wh]['count'] += 1

        return result

    def calculate_yearly_summary(
        self,
        year: int,
        warehouse_code: Optional[str] = None
    ) -> dict:
        """연도별 집계 계산

        Returns:
            {
                'total_billing': Decimal,
                'total_outsourcing': Decimal,
                'total_profit': Decimal,
                'count': int,
                'by_month': dict  # 월별 집계
            }
        """
        result = {
            'total_billing': Decimal("0"),
            'total_outsourcing': Decimal("0"),
            'total_profit': Decimal("0"),
            'count': 0,
            'by_month': {}
        }

        for month in range(1, 13):
            monthly = self.calculate_monthly_summary(year, month, warehouse_code)
            result['total_billing'] += monthly['total_billing']
            result['total_outsourcing'] += monthly['total_outsourcing']
            result['total_profit'] += monthly['total_profit']
            result['count'] += monthly['count']
            result['by_month'][month] = monthly

        return result
