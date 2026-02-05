"""계약 관리 페이지"""

import streamlit as st
from datetime import date, datetime
from decimal import Decimal
import json
from sqlmodel import select

from database.connection import get_session
from database.models import Contract, Company, ContractHistory, CodeMapping
from utils.constants import BillingCycle, ContractStatus
from utils.date_utils import parse_billing_timing
from utils.parsing_utils import parse_notes_for_rules


def render_contract_page():
    """계약 관리 페이지 렌더링"""
    st.header("계약 관리")

    tab1, tab2, tab3 = st.tabs(["계약 목록", "계약 등록", "계약 변경 이력"])

    with tab1:
        render_contract_list()

    with tab2:
        render_contract_form()

    with tab3:
        render_contract_history()


def render_contract_list():
    """계약 목록"""
    st.subheader("계약 목록")

    with get_session() as session:
        # 필터
        col1, col2, col3 = st.columns(3)

        with col1:
            status_filter = st.selectbox(
                "상태",
                ["전체", "활성", "만료", "해지", "계약기간 미확정"],
                key="contract_status_filter"
            )

        with col2:
            # 창고 코드 목록
            code_mappings = session.exec(select(CodeMapping)).all()
            warehouse_options = ["전체"] + [f"{cm.code} ({cm.name})" for cm in code_mappings]
            warehouse_filter = st.selectbox(
                "창고/팀",
                warehouse_options,
                key="contract_warehouse_filter"
            )

        with col3:
            search_term = st.text_input("업체명/품목명 검색", key="contract_search")

        # 계약 조회
        statement = select(Contract)

        if status_filter != "전체":
            status_map = {
                "활성": ContractStatus.ACTIVE.value,
                "만료": ContractStatus.EXPIRED.value,
                "해지": ContractStatus.TERMINATED.value,
                "계약기간 미확정": ContractStatus.PERIOD_UNDEFINED.value
            }
            statement = statement.where(Contract.status == status_map[status_filter])

        contracts = session.exec(statement).all()

        # 필터링
        filtered = []
        for contract in contracts:
            company = contract.company

            # 창고 필터
            if warehouse_filter != "전체":
                warehouse_code = warehouse_filter.split(" ")[0]
                if company and company.warehouse_code != warehouse_code:
                    continue

            # 검색어 필터
            if search_term:
                search_lower = search_term.lower()
                company_name = company.name.lower() if company else ""
                item_name = contract.item_name.lower()
                if search_lower not in company_name and search_lower not in item_name:
                    continue

            filtered.append(contract)

        st.write(f"총 {len(filtered)}건")

        # 테이블 표시
        if filtered:
            for contract in filtered:
                company = contract.company
                with st.expander(
                    f"{company.name if company else 'N/A'} - {contract.item_name}",
                    expanded=False
                ):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**업체코드:** {company.code if company else 'N/A'}")
                        st.write(f"**창고:** {company.warehouse_code if company else 'N/A'}")
                        st.write(f"**계약기간:** {contract.contract_start} ~ {contract.contract_end}")
                        st.write(f"**월 계약금액:** {contract.monthly_amount:,.0f}원")
                        st.write(f"**청구주기:** {contract.billing_cycle}")

                    with col2:
                        st.write(f"**자동갱신:** {'예' if contract.auto_renewal else '아니오'}")
                        st.write(f"**역발행:** {'예' if contract.is_reverse_billing else '아니오'}")
                        st.write(f"**상태:** {contract.status}")
                        st.write(f"**발행시기:** {contract.billing_timing or 'N/A'}")

                    if contract.notes:
                        st.write(f"**특이사항:** {contract.notes}")

                    # 수정 버튼
                    if st.button(f"수정", key=f"edit_contract_{contract.id}"):
                        st.session_state['editing_contract_id'] = contract.id
                        st.rerun()


def render_contract_form():
    """계약 등록/수정 폼"""
    st.subheader("계약 등록")

    with get_session() as session:
        # 업체 목록
        companies = session.exec(
            select(Company).where(Company.company_type == "sales")
        ).all()

        if not companies:
            st.warning("등록된 매출업체가 없습니다. 먼저 업체를 등록해주세요.")
            return

        # 폼
        with st.form("contract_form"):
            # 업체 선택
            company_options = {f"{c.code} - {c.name}": c.id for c in companies}
            selected_company = st.selectbox(
                "업체 선택*",
                options=list(company_options.keys())
            )
            company_id = company_options[selected_company]

            # 품목명
            item_name = st.text_input("품목명*")

            # 계약기간
            col1, col2 = st.columns(2)
            with col1:
                contract_start = st.date_input("계약시작일", value=None)
            with col2:
                contract_end = st.date_input("계약종료일", value=None)

            # 금액
            monthly_amount = st.number_input("월 계약금액*", min_value=0, step=10000)

            # 청구주기
            billing_cycle = st.selectbox(
                "청구주기",
                options=[
                    ("매월", BillingCycle.MONTHLY.value),
                    ("분기", BillingCycle.QUARTERLY.value),
                    ("반기", BillingCycle.SEMIANNUAL.value),
                    ("연 2회", BillingCycle.BIANNUAL.value),
                    ("비정기", BillingCycle.IRREGULAR.value)
                ],
                format_func=lambda x: x[0]
            )

            # 발행시기
            billing_timing = st.text_input("발행시기 (예: 말일, 10일, 역발행)")

            # 자동갱신
            col1, col2 = st.columns(2)
            with col1:
                auto_renewal = st.checkbox("자동갱신", value=True)
            with col2:
                renewal_period = st.number_input("갱신주기(개월)", value=12, min_value=1)

            # 외주
            st.write("**외주 설정**")
            outsourcing_companies = session.exec(
                select(Company).where(Company.company_type == "purchase")
            ).all()

            outsourcing_company_id = None
            if outsourcing_companies:
                outsourcing_options = {"없음": None}
                outsourcing_options.update({
                    f"{c.code} - {c.name}": c.id for c in outsourcing_companies
                })
                selected_outsourcing = st.selectbox(
                    "외주업체",
                    options=list(outsourcing_options.keys())
                )
                outsourcing_company_id = outsourcing_options[selected_outsourcing]

            default_outsourcing_amount = st.number_input(
                "월 외주금액", min_value=0, step=10000
            )
            outsourcing_zero = st.checkbox("외주금액 0원 명시 설정")

            # 역발행
            is_reverse_billing = st.checkbox("역발행")

            # 특이사항
            notes = st.text_area("특이사항")

            submitted = st.form_submit_button("저장")

            if submitted:
                if not item_name:
                    st.error("품목명은 필수입니다.")
                    return

                # 발행시기 파싱
                timing_parsed = parse_billing_timing(billing_timing) if billing_timing else None

                # 특이사항 파싱
                notes_parsed = parse_notes_for_rules(notes) if notes else None

                # 역발행 체크 (발행시기 또는 체크박스)
                is_reverse = is_reverse_billing
                if timing_parsed and timing_parsed.get('is_reverse_billing'):
                    is_reverse = True

                # 상태 결정
                status = ContractStatus.ACTIVE.value
                if contract_start is None and contract_end is None:
                    status = ContractStatus.PERIOD_UNDEFINED.value

                # 계약 생성
                contract = Contract(
                    company_id=company_id,
                    item_name=item_name,
                    contract_start=contract_start,
                    contract_end=contract_end,
                    monthly_amount=Decimal(str(monthly_amount)),
                    billing_cycle=billing_cycle[1],
                    billing_timing=billing_timing,
                    billing_timing_parsed=json.dumps(timing_parsed, ensure_ascii=False) if timing_parsed else None,
                    auto_renewal=auto_renewal,
                    renewal_period_months=renewal_period,
                    is_reverse_billing=is_reverse,
                    default_outsourcing_company_id=outsourcing_company_id,
                    default_outsourcing_amount=Decimal(str(default_outsourcing_amount)),
                    outsourcing_amount_zero=outsourcing_zero,
                    status=status,
                    notes=notes,
                    notes_parsed=json.dumps(notes_parsed, ensure_ascii=False) if notes_parsed else None
                )

                session.add(contract)
                session.commit()

                st.success("계약이 등록되었습니다.")
                st.rerun()


def render_contract_history():
    """계약 변경 이력"""
    st.subheader("계약 변경 이력")

    with get_session() as session:
        # 최근 변경 이력 조회
        statement = select(ContractHistory).order_by(
            ContractHistory.created_at.desc()
        ).limit(50)

        history_list = session.exec(statement).all()

        if not history_list:
            st.info("변경 이력이 없습니다.")
            return

        for history in history_list:
            contract = history.contract
            company_name = contract.company.name if contract and contract.company else "N/A"

            with st.expander(
                f"{history.created_at.strftime('%Y-%m-%d %H:%M')} - {company_name}",
                expanded=False
            ):
                st.write(f"**변경 유형:** {history.change_type}")
                st.write(f"**적용일:** {history.effective_date}")
                st.write(f"**변경 전:** {history.old_value}")
                st.write(f"**변경 후:** {history.new_value}")
                if history.reason:
                    st.write(f"**사유:** {history.reason}")


def record_contract_change(
    session,
    contract_id: int,
    change_type: str,
    effective_date: date,
    old_value: dict,
    new_value: dict,
    reason: str = None
):
    """계약 변경 이력 기록"""
    history = ContractHistory(
        contract_id=contract_id,
        change_type=change_type,
        effective_date=effective_date,
        old_value=json.dumps(old_value, ensure_ascii=False, default=str),
        new_value=json.dumps(new_value, ensure_ascii=False, default=str),
        reason=reason
    )
    session.add(history)
