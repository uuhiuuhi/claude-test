"""검증 엔진 - 누락/오류 방지 검증 로직"""

from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict, Any
import json
from sqlmodel import Session, select

from database.models import (
    Contract, ContractHistory, MonthlyBilling, Company
)
from utils.constants import (
    ContractStatus, BillingStatus, SUDDEN_CHANGE_THRESHOLD_PERCENT
)
from utils.date_utils import (
    calculate_contract_period_status,
    parse_billing_timing,
    get_last_day_of_month
)


class ValidationEngine:
    """검증 엔진 - 사내 표준 10개 검증 규칙"""

    def __init__(self, session: Session):
        self.session = session

    def validate_billing(
        self,
        billing: MonthlyBilling,
        contract: Contract
    ) -> List[dict]:
        """청구 검증 (모든 규칙 적용)

        Returns:
            List of warning dicts: [{'code': str, 'level': str, 'message': str}]
        """
        warnings = []

        # 1. 계약기간 미확정 경고
        warnings.extend(self._check_undefined_period(contract))

        # 2. 발행시기 파싱 불가
        warnings.extend(self._check_billing_timing(contract))

        # 3. 금액 급변 탐지
        warnings.extend(self._check_sudden_amount_change(billing, contract))

        # 4. 외주금액 미입력
        warnings.extend(self._check_outsourcing_missing(billing, contract))

        # 5. 중복 청구 가능성
        warnings.extend(self._check_duplicate_risk(billing, contract))

        # 6. 역발행 규칙 체크
        warnings.extend(self._check_reverse_billing(billing, contract))

        # 7. PO/첨부 필수 체크
        warnings.extend(self._check_billing_rules(contract))

        # 8. 계약 만료 임박
        warnings.extend(self._check_expiring_contract(billing, contract))

        # 9. 이전 월 미확정 청구
        warnings.extend(self._check_previous_unconfirmed(billing))

        # 10. 자동갱신 롤링 상태
        warnings.extend(self._check_auto_renewal_status(billing, contract))

        return warnings

    def _check_undefined_period(self, contract: Contract) -> List[dict]:
        """1. 계약기간 미확정 경고"""
        warnings = []

        if contract.contract_start is None or contract.contract_end is None:
            warnings.append({
                'code': 'PERIOD_UNDEFINED',
                'level': 'warning',
                'message': '계약기간 미확정 - 청구 가능하나 확인 필요'
            })

        if contract.status == ContractStatus.PERIOD_UNDEFINED.value:
            warnings.append({
                'code': 'STATUS_PERIOD_UNDEFINED',
                'level': 'warning',
                'message': '계약 상태가 "계약기간 미확정"입니다'
            })

        return warnings

    def _check_billing_timing(self, contract: Contract) -> List[dict]:
        """2. 발행시기 파싱 불가"""
        warnings = []

        if contract.billing_timing:
            parsed = parse_billing_timing(contract.billing_timing)

            if parsed['requires_manual']:
                warnings.append({
                    'code': 'TIMING_MANUAL_REQUIRED',
                    'level': 'warning',
                    'message': f'수동 발행일 지정 필요: "{contract.billing_timing}"'
                })

            if not parsed['parsed'] and not parsed['requires_manual']:
                warnings.append({
                    'code': 'TIMING_PARSE_FAILED',
                    'level': 'warning',
                    'message': f'발행시기 파싱 실패: "{contract.billing_timing}"'
                })

        return warnings

    def _check_sudden_amount_change(
        self,
        billing: MonthlyBilling,
        contract: Contract
    ) -> List[dict]:
        """3. 금액 급변 탐지 (전월 대비 30% 이상)"""
        warnings = []

        # 전월 청구 조회
        prev_month = billing.billing_month - 1
        prev_year = billing.billing_year
        if prev_month == 0:
            prev_month = 12
            prev_year -= 1

        statement = select(MonthlyBilling).where(
            MonthlyBilling.contract_id == contract.id,
            MonthlyBilling.billing_year == prev_year,
            MonthlyBilling.billing_month == prev_month,
            MonthlyBilling.status != BillingStatus.CANCELLED.value
        )
        prev_billing = self.session.exec(statement).first()

        if prev_billing and prev_billing.final_amount > 0:
            change_rate = abs(
                (billing.final_amount - prev_billing.final_amount) /
                prev_billing.final_amount * 100
            )

            if change_rate >= SUDDEN_CHANGE_THRESHOLD_PERCENT:
                warnings.append({
                    'code': 'AMOUNT_SUDDEN_CHANGE',
                    'level': 'warning',
                    'message': f'금액 급변 감지: 전월 {prev_billing.final_amount:,.0f}원 → 이번달 {billing.final_amount:,.0f}원 ({change_rate:.1f}% 변동)'
                })

        return warnings

    def _check_outsourcing_missing(
        self,
        billing: MonthlyBilling,
        contract: Contract
    ) -> List[dict]:
        """4. 외주금액 미입력 경고"""
        warnings = []

        # 외주가 있어야 하는 계약인데 0인 경우
        has_default_outsourcing = (
            contract.default_outsourcing_company_id is not None or
            contract.default_outsourcing_amount > 0
        )

        if has_default_outsourcing and billing.outsourcing_amount == 0:
            if not contract.outsourcing_amount_zero:
                warnings.append({
                    'code': 'OUTSOURCING_MISSING',
                    'level': 'warning',
                    'message': '외주금액이 0원입니다. 확인이 필요합니다.'
                })

        return warnings

    def _check_duplicate_risk(
        self,
        billing: MonthlyBilling,
        contract: Contract
    ) -> List[dict]:
        """5. 중복 청구 가능성"""
        warnings = []

        # 동일 계약 동일 월 다른 청구 존재 여부
        statement = select(MonthlyBilling).where(
            MonthlyBilling.contract_id == contract.id,
            MonthlyBilling.billing_year == billing.billing_year,
            MonthlyBilling.billing_month == billing.billing_month,
            MonthlyBilling.status != BillingStatus.CANCELLED.value
        )

        if billing.id:
            statement = statement.where(MonthlyBilling.id != billing.id)

        existing = self.session.exec(statement).all()

        if existing:
            warnings.append({
                'code': 'DUPLICATE_BILLING',
                'level': 'error',
                'message': f'동일 계약에 대해 {len(existing)}건의 다른 청구가 존재합니다'
            })

        return warnings

    def _check_reverse_billing(
        self,
        billing: MonthlyBilling,
        contract: Contract
    ) -> List[dict]:
        """6. 역발행 규칙 체크"""
        warnings = []

        if contract.is_reverse_billing:
            # 역발행인데 발행일이 설정된 경우
            if billing.sales_date or billing.request_date:
                warnings.append({
                    'code': 'REVERSE_BILLING_DATE_SET',
                    'level': 'info',
                    'message': '역발행 계약입니다. 발행일자는 참고용입니다.'
                })

            warnings.append({
                'code': 'REVERSE_BILLING',
                'level': 'info',
                'message': '역발행 계약 - 상대방 발행 기준으로 관리'
            })

        return warnings

    def _check_billing_rules(self, contract: Contract) -> List[dict]:
        """7. PO/첨부 필수 체크"""
        warnings = []

        if contract.notes_parsed:
            try:
                rules = json.loads(contract.notes_parsed)

                if rules.get('requires_po'):
                    warnings.append({
                        'code': 'PO_REQUIRED',
                        'level': 'info',
                        'message': 'PO번호 필수 업체입니다'
                    })

                if rules.get('requires_attachment'):
                    attachment_note = rules.get('attachment_note', '')
                    warnings.append({
                        'code': 'ATTACHMENT_REQUIRED',
                        'level': 'info',
                        'message': f'첨부 필수: {attachment_note}'
                    })

            except json.JSONDecodeError:
                pass

        return warnings

    def _check_expiring_contract(
        self,
        billing: MonthlyBilling,
        contract: Contract
    ) -> List[dict]:
        """8. 계약 만료 임박 (1개월 이내)"""
        warnings = []

        if contract.contract_end:
            billing_date = date(billing.billing_year, billing.billing_month, 1)
            days_until_expiry = (contract.contract_end - billing_date).days

            if 0 < days_until_expiry <= 30:
                if contract.auto_renewal:
                    warnings.append({
                        'code': 'CONTRACT_EXPIRING_AUTO_RENEWAL',
                        'level': 'info',
                        'message': f'계약 만료 임박 ({contract.contract_end}) - 자동갱신 예정'
                    })
                else:
                    warnings.append({
                        'code': 'CONTRACT_EXPIRING',
                        'level': 'warning',
                        'message': f'계약 만료 임박 ({contract.contract_end}) - 갱신 확인 필요'
                    })

        return warnings

    def _check_previous_unconfirmed(self, billing: MonthlyBilling) -> List[dict]:
        """9. 이전 월 미확정 청구"""
        warnings = []

        # 이전 월 조회
        prev_month = billing.billing_month - 1
        prev_year = billing.billing_year
        if prev_month == 0:
            prev_month = 12
            prev_year -= 1

        statement = select(MonthlyBilling).where(
            MonthlyBilling.contract_id == billing.contract_id,
            MonthlyBilling.billing_year == prev_year,
            MonthlyBilling.billing_month == prev_month,
            MonthlyBilling.status == BillingStatus.DRAFT.value
        )

        prev_drafts = self.session.exec(statement).all()

        if prev_drafts:
            warnings.append({
                'code': 'PREVIOUS_UNCONFIRMED',
                'level': 'warning',
                'message': f'{prev_year}년 {prev_month}월 청구가 아직 미확정 상태입니다'
            })

        return warnings

    def _check_auto_renewal_status(
        self,
        billing: MonthlyBilling,
        contract: Contract
    ) -> List[dict]:
        """10. 자동갱신 롤링 상태 확인"""
        warnings = []

        if contract.auto_renewal and contract.contract_end:
            check_date = date(billing.billing_year, billing.billing_month, 1)

            is_active, eff_start, eff_end, status_msg = calculate_contract_period_status(
                contract.contract_start,
                contract.contract_end,
                contract.auto_renewal,
                contract.renewal_period_months or 12,
                check_date
            )

            if '자동갱신됨' in status_msg:
                warnings.append({
                    'code': 'AUTO_RENEWED',
                    'level': 'info',
                    'message': status_msg
                })

        return warnings

    def get_all_warnings_for_month(
        self,
        year: int,
        month: int
    ) -> List[dict]:
        """월별 전체 경고 조회"""
        statement = select(MonthlyBilling).where(
            MonthlyBilling.billing_year == year,
            MonthlyBilling.billing_month == month,
            MonthlyBilling.has_warnings == True
        )

        billings = self.session.exec(statement).all()
        all_warnings = []

        for billing in billings:
            if billing.warnings:
                try:
                    warnings = json.loads(billing.warnings)
                    for w in warnings:
                        w['billing_id'] = billing.id
                        w['contract_id'] = billing.contract_id
                        if billing.contract and billing.contract.company:
                            w['company_name'] = billing.contract.company.name
                        all_warnings.append(w)
                except json.JSONDecodeError:
                    pass

        return all_warnings

    def get_missing_billings(
        self,
        year: int,
        month: int
    ) -> List[Contract]:
        """누락 가능성 있는 계약 조회"""
        check_date = date(year, month, 1)

        # 활성 계약 조회
        statement = select(Contract).where(
            Contract.status.in_([
                ContractStatus.ACTIVE.value,
                ContractStatus.PERIOD_UNDEFINED.value
            ])
        )
        contracts = self.session.exec(statement).all()

        # 해당 월 청구가 있는 계약 ID
        billing_statement = select(MonthlyBilling.contract_id).where(
            MonthlyBilling.billing_year == year,
            MonthlyBilling.billing_month == month,
            MonthlyBilling.status != BillingStatus.CANCELLED.value
        )
        billed_contract_ids = set(self.session.exec(billing_statement).all())

        missing = []
        for contract in contracts:
            if contract.id in billed_contract_ids:
                continue

            # 계약기간 확인 (자동갱신 포함)
            is_active, _, _, _ = calculate_contract_period_status(
                contract.contract_start,
                contract.contract_end,
                contract.auto_renewal,
                contract.renewal_period_months or 12,
                check_date
            )

            if is_active:
                missing.append(contract)

        return missing
