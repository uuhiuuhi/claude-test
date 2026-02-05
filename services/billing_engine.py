"""청구 생성 엔진 - 사내 표준 월 청구 생성 로직"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Tuple
import json
from sqlmodel import Session, select

from database.models import (
    Contract, ContractHistory, MonthlyBilling, Company, Holiday
)
from utils.constants import (
    BillingCycle, BillingStatus, ContractStatus,
    BILLING_CYCLE_MONTHS, BILLING_CYCLE_TARGET_MONTHS,
    DEFAULT_RENEWAL_PERIOD_MONTHS
)
from utils.date_utils import (
    calculate_contract_period_status,
    is_billing_target_month,
    parse_billing_timing,
    calculate_billing_date,
    get_last_day_of_month
)
from services.calculation_engine import CalculationEngine
from services.validation_engine import ValidationEngine


class BillingEngine:
    """청구 생성 엔진 - 사내 표준 순서 적용"""

    def __init__(self, session: Session):
        self.session = session
        self.calc_engine = CalculationEngine(session)
        self.validation_engine = ValidationEngine(session)

    def generate_monthly_billings(
        self,
        billing_year: int,
        billing_month: int,
        exclude_contract_ids: Optional[List[int]] = None
    ) -> Tuple[List[MonthlyBilling], List[dict]]:
        """월 청구 생성 (사내 표준 순서)

        1) 청구월 선택
        2) 대상 계약 자동 산출(자동갱신 포함)
        3) 청구주기 검증
        4) 계약변경 이력 적용
        5) 청구금액 산정
        6) 외주금액 산정
        7) 실제이익 계산
        8) 발행일자 자동 제안
        9) 검증 로직 수행
        10) 확인필요 목록 표시

        Returns:
            (billings, warnings)
        """
        check_date = date(billing_year, billing_month, 1)
        billings = []
        all_warnings = []

        # 1) 이미 생성된 청구 제외
        existing_statement = select(MonthlyBilling).where(
            MonthlyBilling.billing_year == billing_year,
            MonthlyBilling.billing_month == billing_month
        )
        existing_billings = self.session.exec(existing_statement).all()
        existing_contract_ids = {b.contract_id for b in existing_billings}

        # 2) 대상 계약 산출
        target_contracts = self._get_target_contracts(
            check_date,
            exclude_contract_ids or []
        )

        # 휴일 조회
        holidays = self._get_holidays(billing_year)

        for contract in target_contracts:
            # 이미 생성된 계약 스킵
            if contract.id in existing_contract_ids:
                continue

            # 3) 청구주기 검증
            billing_cycle = BillingCycle(contract.billing_cycle)
            custom_months = self._get_custom_billing_months(contract)

            if not is_billing_target_month(billing_cycle, billing_year, billing_month, custom_months):
                continue

            # 청구 레코드 생성
            billing = self._create_billing_record(
                contract,
                billing_year,
                billing_month,
                holidays
            )

            # 9) 검증 로직 수행
            warnings = self.validation_engine.validate_billing(billing, contract)
            if warnings:
                billing.warnings = json.dumps(warnings, ensure_ascii=False)
                billing.has_warnings = True
                all_warnings.extend([{
                    'billing_id': None,  # 아직 저장 전
                    'contract_id': contract.id,
                    'company_name': contract.company.name if contract.company else '',
                    **w
                } for w in warnings])

            billings.append(billing)

        return (billings, all_warnings)

    def _get_target_contracts(
        self,
        check_date: date,
        exclude_ids: List[int]
    ) -> List[Contract]:
        """대상 계약 산출 (자동갱신 포함)"""
        statement = select(Contract).where(
            Contract.status.in_([
                ContractStatus.ACTIVE.value,
                ContractStatus.PERIOD_UNDEFINED.value
            ])
        )

        if exclude_ids:
            statement = statement.where(Contract.id.notin_(exclude_ids))

        all_contracts = self.session.exec(statement).all()
        target_contracts = []

        for contract in all_contracts:
            # 계약기간 상태 확인 (자동갱신 롤링 계산)
            is_active, _, _, _ = calculate_contract_period_status(
                contract.contract_start,
                contract.contract_end,
                contract.auto_renewal,
                contract.renewal_period_months or DEFAULT_RENEWAL_PERIOD_MONTHS,
                check_date
            )

            if is_active:
                target_contracts.append(contract)

        return target_contracts

    def _get_custom_billing_months(self, contract: Contract) -> Optional[List[int]]:
        """비정기 청구의 경우 커스텀 청구월 조회"""
        if contract.billing_timing_parsed:
            try:
                parsed = json.loads(contract.billing_timing_parsed)
                return parsed.get('months')
            except json.JSONDecodeError:
                pass
        return None

    def _create_billing_record(
        self,
        contract: Contract,
        billing_year: int,
        billing_month: int,
        holidays: List[date]
    ) -> MonthlyBilling:
        """청구 레코드 생성"""
        # 4) 계약변경 이력 적용 + 5) 청구금액 산정
        calculated_amount, cover_months, calc_note = self.calc_engine.calculate_billing_amount(
            contract, billing_year, billing_month
        )

        # 부가세/합계
        vat, total = self.calc_engine.calculate_vat_and_total(calculated_amount)

        # 6) 외주금액 산정 (아직 billing_id 없으므로 None)
        outsourcing_amount, _ = self.calc_engine.calculate_outsourcing_amount(
            contract, None, billing_year, billing_month, cover_months
        )

        # 7) 실제이익 계산
        profit = self.calc_engine.calculate_profit(calculated_amount, outsourcing_amount)

        # 8) 발행일자 자동 제안
        suggested_date = self._suggest_billing_date(
            contract, billing_year, billing_month, holidays
        )

        billing = MonthlyBilling(
            contract_id=contract.id,
            billing_year=billing_year,
            billing_month=billing_month,
            cover_months=cover_months,
            calculated_amount=calculated_amount,
            final_amount=calculated_amount,  # 초기값은 계산값
            vat_amount=vat,
            total_amount=total,
            outsourcing_amount=outsourcing_amount,
            profit=profit,
            suggested_date=suggested_date,
            sales_date=suggested_date,  # 초기값은 제안일
            status=BillingStatus.DRAFT.value
        )

        return billing

    def _suggest_billing_date(
        self,
        contract: Contract,
        billing_year: int,
        billing_month: int,
        holidays: List[date]
    ) -> Optional[date]:
        """발행일자 자동 제안"""
        # 역발행인 경우 제안 없음
        if contract.is_reverse_billing:
            return None

        # 발행시기 파싱
        if contract.billing_timing:
            parsed = parse_billing_timing(contract.billing_timing)

            if parsed['is_reverse_billing']:
                return None

            if parsed['requires_manual']:
                return None

            if parsed['day']:
                return calculate_billing_date(
                    billing_year, billing_month, parsed['day'], holidays
                )

        # 기본값: 말일
        return calculate_billing_date(
            billing_year, billing_month, 'last', holidays
        )

    def _get_holidays(self, year: int) -> List[date]:
        """해당 연도 휴일 조회"""
        statement = select(Holiday).where(
            Holiday.date >= date(year, 1, 1),
            Holiday.date <= date(year, 12, 31)
        )
        holidays = self.session.exec(statement).all()
        return [h.date for h in holidays]

    def save_billings(self, billings: List[MonthlyBilling]) -> List[MonthlyBilling]:
        """청구 저장"""
        for billing in billings:
            self.session.add(billing)
        self.session.commit()

        for billing in billings:
            self.session.refresh(billing)

        return billings

    def confirm_billing(self, billing_id: int) -> MonthlyBilling:
        """청구 확정"""
        billing = self.session.get(MonthlyBilling, billing_id)
        if billing:
            billing.status = BillingStatus.CONFIRMED.value
            billing.updated_at = datetime.now()
            self.session.commit()
            self.session.refresh(billing)
        return billing

    def lock_billing(self, billing_id: int, locked_by: Optional[str] = None) -> MonthlyBilling:
        """청구 잠금 (수정 불가)"""
        billing = self.session.get(MonthlyBilling, billing_id)
        if billing:
            billing.status = BillingStatus.LOCKED.value
            billing.locked_at = datetime.now()
            billing.locked_by = locked_by
            self.session.commit()
            self.session.refresh(billing)
        return billing

    def update_billing_override(
        self,
        billing_id: int,
        override_amount: Optional[Decimal] = None,
        sales_date: Optional[date] = None,
        request_date: Optional[date] = None,
        notes: Optional[str] = None
    ) -> MonthlyBilling:
        """청구 수동 오버라이드"""
        billing = self.session.get(MonthlyBilling, billing_id)
        if not billing:
            raise ValueError(f"Billing {billing_id} not found")

        if billing.status == BillingStatus.LOCKED.value:
            raise ValueError("Cannot modify locked billing")

        if override_amount is not None:
            billing.override_amount = override_amount
            billing.final_amount = override_amount
            # 부가세/합계/이익 재계산
            vat, total = self.calc_engine.calculate_vat_and_total(override_amount)
            billing.vat_amount = vat
            billing.total_amount = total
            billing.profit = self.calc_engine.calculate_profit(
                override_amount, billing.outsourcing_amount
            )

        if sales_date is not None:
            billing.sales_date = sales_date

        if request_date is not None:
            billing.request_date = request_date

        if notes is not None:
            billing.notes = notes

        billing.updated_at = datetime.now()
        self.session.commit()
        self.session.refresh(billing)

        return billing

    def get_billings_for_month(
        self,
        year: int,
        month: int,
        status: Optional[str] = None
    ) -> List[MonthlyBilling]:
        """월별 청구 조회"""
        statement = select(MonthlyBilling).where(
            MonthlyBilling.billing_year == year,
            MonthlyBilling.billing_month == month
        )

        if status:
            statement = statement.where(MonthlyBilling.status == status)

        return self.session.exec(statement).all()

    def check_duplicate_billing(
        self,
        contract_id: int,
        billing_year: int,
        billing_month: int
    ) -> Optional[MonthlyBilling]:
        """중복 청구 확인"""
        statement = select(MonthlyBilling).where(
            MonthlyBilling.contract_id == contract_id,
            MonthlyBilling.billing_year == billing_year,
            MonthlyBilling.billing_month == billing_month,
            MonthlyBilling.status != BillingStatus.CANCELLED.value
        )
        return self.session.exec(statement).first()
