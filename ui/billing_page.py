"""월 청구 생성 페이지"""

import streamlit as st
from datetime import date, datetime
from decimal import Decimal
import json
from sqlmodel import select

from database.connection import get_session
from database.models import MonthlyBilling, Contract, Company
from services.billing_engine import BillingEngine
from services.validation_engine import ValidationEngine
from utils.constants import BillingStatus


def render_billing_page():
    """월 청구 생성 페이지 렌더링"""
    st.header("월 청구 생성")

    tab1, tab2, tab3 = st.tabs(["청구 생성", "청구 목록", "청구 확정/잠금"])

    with tab1:
        render_billing_generator()

    with tab2:
        render_billing_list()

    with tab3:
        render_billing_confirmation()


def render_billing_generator():
    """청구 생성"""
    st.subheader("월 청구 자동 생성")

    col1, col2 = st.columns(2)

    with col1:
        billing_year = st.number_input(
            "청구년도",
            min_value=2020,
            max_value=2030,
            value=date.today().year
        )

    with col2:
        billing_month = st.number_input(
            "청구월",
            min_value=1,
            max_value=12,
            value=date.today().month
        )

    with get_session() as session:
        billing_engine = BillingEngine(session)
        validation_engine = ValidationEngine(session)

        # 기존 청구 확인
        existing = billing_engine.get_billings_for_month(billing_year, billing_month)

        if existing:
            st.info(f"이미 {len(existing)}건의 청구가 생성되어 있습니다.")

            # 상태별 집계
            status_counts = {}
            for b in existing:
                status_counts[b.status] = status_counts.get(b.status, 0) + 1

            cols = st.columns(len(status_counts))
            for idx, (status, count) in enumerate(status_counts.items()):
                with cols[idx]:
                    st.metric(status, count)

        # 누락 가능성 확인
        missing_contracts = validation_engine.get_missing_billings(
            billing_year, billing_month
        )

        if missing_contracts:
            st.warning(f"청구 누락 가능성: {len(missing_contracts)}건")

            with st.expander("누락 가능 계약 목록"):
                for contract in missing_contracts:
                    company = contract.company
                    st.write(f"- {company.name if company else 'N/A'}: {contract.item_name}")

        # 청구 생성 버튼
        if st.button("청구 생성", type="primary"):
            with st.spinner("청구 생성 중..."):
                billings, warnings = billing_engine.generate_monthly_billings(
                    billing_year, billing_month
                )

                if billings:
                    # 저장
                    saved = billing_engine.save_billings(billings)
                    st.success(f"{len(saved)}건의 청구가 생성되었습니다.")

                    # 경고 표시
                    if warnings:
                        st.warning(f"확인 필요: {len(warnings)}건")
                        for w in warnings[:10]:  # 최대 10개만 표시
                            level_emoji = "⚠️" if w['level'] == 'warning' else "ℹ️"
                            if w['level'] == 'error':
                                level_emoji = "❌"
                            st.write(f"{level_emoji} {w.get('company_name', '')}: {w['message']}")

                        if len(warnings) > 10:
                            st.write(f"... 외 {len(warnings) - 10}건")
                else:
                    st.info("생성할 청구가 없습니다.")

            st.rerun()


def render_billing_list():
    """청구 목록"""
    st.subheader("청구 목록")

    col1, col2, col3 = st.columns(3)

    with col1:
        list_year = st.number_input(
            "년도",
            min_value=2020,
            max_value=2030,
            value=date.today().year,
            key="billing_list_year"
        )

    with col2:
        list_month = st.number_input(
            "월",
            min_value=1,
            max_value=12,
            value=date.today().month,
            key="billing_list_month"
        )

    with col3:
        status_filter = st.selectbox(
            "상태",
            ["전체", "초안", "확정", "잠금", "취소"],
            key="billing_status_filter"
        )

    with get_session() as session:
        statement = select(MonthlyBilling).where(
            MonthlyBilling.billing_year == list_year,
            MonthlyBilling.billing_month == list_month
        )

        if status_filter != "전체":
            status_map = {
                "초안": BillingStatus.DRAFT.value,
                "확정": BillingStatus.CONFIRMED.value,
                "잠금": BillingStatus.LOCKED.value,
                "취소": BillingStatus.CANCELLED.value
            }
            statement = statement.where(
                MonthlyBilling.status == status_map[status_filter]
            )

        billings = session.exec(statement).all()

        st.write(f"총 {len(billings)}건")

        # 합계
        if billings:
            total_amount = sum(b.final_amount for b in billings)
            total_outsourcing = sum(b.outsourcing_amount for b in billings)
            total_profit = sum(b.profit for b in billings)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("총 청구금액", f"{total_amount:,.0f}원")
            with col2:
                st.metric("총 외주금액", f"{total_outsourcing:,.0f}원")
            with col3:
                st.metric("총 이익", f"{total_profit:,.0f}원")

        # 목록
        for billing in billings:
            contract = billing.contract
            company = contract.company if contract else None

            status_emoji = {
                'draft': '📝',
                'confirmed': '✅',
                'locked': '🔒',
                'cancelled': '❌'
            }.get(billing.status, '❓')

            warning_indicator = "⚠️" if billing.has_warnings else ""

            with st.expander(
                f"{status_emoji} {warning_indicator} {company.name if company else 'N/A'} - {contract.item_name if contract else 'N/A'} ({billing.final_amount:,.0f}원)",
                expanded=False
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**청구금액:** {billing.final_amount:,.0f}원")
                    st.write(f"**부가세:** {billing.vat_amount:,.0f}원")
                    st.write(f"**합계:** {billing.total_amount:,.0f}원")
                    st.write(f"**커버 개월:** {billing.cover_months}개월")

                with col2:
                    st.write(f"**외주금액:** {billing.outsourcing_amount:,.0f}원")
                    st.write(f"**이익:** {billing.profit:,.0f}원")
                    st.write(f"**매출일자:** {billing.sales_date or 'N/A'}")
                    st.write(f"**요청일자:** {billing.request_date or 'N/A'}")

                # 오버라이드 수정 (잠금 상태가 아닌 경우)
                if billing.status != BillingStatus.LOCKED.value:
                    st.write("---")
                    st.write("**금액 수정**")

                    new_amount = st.number_input(
                        "청구금액 오버라이드",
                        value=float(billing.final_amount),
                        key=f"override_{billing.id}"
                    )

                    new_sales_date = st.date_input(
                        "매출일자",
                        value=billing.sales_date,
                        key=f"sales_date_{billing.id}"
                    )

                    new_request_date = st.date_input(
                        "요청일자",
                        value=billing.request_date,
                        key=f"request_date_{billing.id}"
                    )

                    if st.button("수정 저장", key=f"save_override_{billing.id}"):
                        billing_engine = BillingEngine(session)
                        billing_engine.update_billing_override(
                            billing.id,
                            override_amount=Decimal(str(new_amount)) if new_amount != float(billing.final_amount) else None,
                            sales_date=new_sales_date,
                            request_date=new_request_date
                        )
                        st.success("수정되었습니다.")
                        st.rerun()

                # 경고 표시
                if billing.warnings:
                    st.write("---")
                    st.write("**경고/확인 필요**")
                    try:
                        warnings = json.loads(billing.warnings)
                        for w in warnings:
                            level_emoji = "⚠️" if w['level'] == 'warning' else "ℹ️"
                            if w['level'] == 'error':
                                level_emoji = "❌"
                            st.write(f"{level_emoji} {w['message']}")
                    except:
                        pass


def render_billing_confirmation():
    """청구 확정/잠금"""
    st.subheader("청구 확정 및 잠금")

    col1, col2 = st.columns(2)

    with col1:
        confirm_year = st.number_input(
            "년도",
            min_value=2020,
            max_value=2030,
            value=date.today().year,
            key="confirm_year"
        )

    with col2:
        confirm_month = st.number_input(
            "월",
            min_value=1,
            max_value=12,
            value=date.today().month,
            key="confirm_month"
        )

    with get_session() as session:
        billing_engine = BillingEngine(session)

        # 상태별 조회
        drafts = billing_engine.get_billings_for_month(
            confirm_year, confirm_month, BillingStatus.DRAFT.value
        )
        confirmed = billing_engine.get_billings_for_month(
            confirm_year, confirm_month, BillingStatus.CONFIRMED.value
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("초안", len(drafts))

        with col2:
            st.metric("확정", len(confirmed))

        with col3:
            locked = billing_engine.get_billings_for_month(
                confirm_year, confirm_month, BillingStatus.LOCKED.value
            )
            st.metric("잠금", len(locked))

        st.write("---")

        # 일괄 확정
        st.write("### 일괄 확정")

        if drafts:
            st.write(f"초안 상태 {len(drafts)}건을 확정 처리합니다.")

            if st.button("일괄 확정", type="primary"):
                for billing in drafts:
                    billing_engine.confirm_billing(billing.id)
                st.success(f"{len(drafts)}건이 확정되었습니다.")
                st.rerun()
        else:
            st.info("확정 대기 중인 청구가 없습니다.")

        st.write("---")

        # 일괄 잠금
        st.write("### 일괄 잠금")

        if confirmed:
            st.write(f"확정 상태 {len(confirmed)}건을 잠금 처리합니다.")
            st.warning("잠금 후에는 수정이 불가능합니다.")

            if st.button("일괄 잠금", type="secondary"):
                for billing in confirmed:
                    billing_engine.lock_billing(billing.id)
                st.success(f"{len(confirmed)}건이 잠금되었습니다.")
                st.rerun()
        else:
            st.info("잠금 대기 중인 청구가 없습니다.")
