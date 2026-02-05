"""외주 관리 페이지"""

import streamlit as st
from datetime import date
from decimal import Decimal
from sqlmodel import select

from database.connection import get_session
from database.models import (
    Company, Contract, Outsourcing, OutsourcingEntry,
    MonthlyBilling, OutsourcingHistory
)
from utils.constants import CompanyType


def render_outsourcing_page():
    """외주 관리 페이지 렌더링"""
    st.header("외주 관리")

    tab1, tab2, tab3 = st.tabs(["외주업체 관리", "외주 매입 등록", "외주 이력"])

    with tab1:
        render_outsourcing_company_management()

    with tab2:
        render_outsourcing_entry()

    with tab3:
        render_outsourcing_history()


def render_outsourcing_company_management():
    """외주업체 관리"""
    st.subheader("외주업체 목록")

    with get_session() as session:
        # 외주업체 목록
        statement = select(Company).where(
            Company.company_type == CompanyType.PURCHASE.value
        )
        companies = session.exec(statement).all()

        if companies:
            for company in companies:
                with st.expander(f"{company.code} - {company.name}", expanded=False):
                    st.write(f"**코드:** {company.code}")
                    st.write(f"**업체명:** {company.name}")
                    st.write(f"**활성:** {'예' if company.is_active else '아니오'}")
        else:
            st.info("등록된 외주업체가 없습니다.")

        # 새 외주업체 등록
        st.write("---")
        st.subheader("외주업체 등록")

        with st.form("outsourcing_company_form"):
            new_code = st.text_input("업체 코드*")
            new_name = st.text_input("업체명*")

            if st.form_submit_button("등록"):
                if not new_code or not new_name:
                    st.error("코드와 업체명은 필수입니다.")
                else:
                    # 중복 체크
                    existing = session.exec(
                        select(Company).where(Company.code == new_code)
                    ).first()

                    if existing:
                        st.error("이미 존재하는 업체 코드입니다.")
                    else:
                        company = Company(
                            code=new_code,
                            name=new_name,
                            company_type=CompanyType.PURCHASE.value
                        )
                        session.add(company)
                        session.commit()
                        st.success("외주업체가 등록되었습니다.")
                        st.rerun()


def render_outsourcing_entry():
    """외주 매입 등록"""
    st.subheader("외주 매입 등록")

    with get_session() as session:
        # 청구 선택
        col1, col2 = st.columns(2)

        with col1:
            entry_year = st.number_input(
                "청구년도",
                min_value=2020,
                max_value=2030,
                value=date.today().year,
                key="entry_year"
            )

        with col2:
            entry_month = st.number_input(
                "청구월",
                min_value=1,
                max_value=12,
                value=date.today().month,
                key="entry_month"
            )

        # 해당 월 청구 목록
        billings = session.exec(
            select(MonthlyBilling).where(
                MonthlyBilling.billing_year == entry_year,
                MonthlyBilling.billing_month == entry_month
            )
        ).all()

        if not billings:
            st.info("해당 월에 청구가 없습니다.")
            return

        # 청구 선택
        billing_options = {}
        for b in billings:
            contract = b.contract
            company = contract.company if contract else None
            label = f"{company.name if company else 'N/A'} - {contract.item_name if contract else 'N/A'}"
            billing_options[label] = b.id

        selected_billing_label = st.selectbox(
            "청구 선택",
            options=list(billing_options.keys())
        )
        selected_billing_id = billing_options[selected_billing_label]
        selected_billing = session.get(MonthlyBilling, selected_billing_id)

        # 현재 외주 매입건 표시
        st.write("---")
        st.write("### 현재 외주 매입건")

        entries = session.exec(
            select(OutsourcingEntry).where(
                OutsourcingEntry.billing_id == selected_billing_id
            )
        ).all()

        if entries:
            for entry in entries:
                company = entry.outsourcing_company
                st.write(
                    f"- {company.name if company else 'N/A'}: "
                    f"{entry.amount:,.0f}원 ({entry.purchase_date or 'N/A'})"
                )

            st.write(f"**합계: {sum(e.amount for e in entries):,.0f}원**")
        else:
            if selected_billing.outsourcing_amount > 0:
                st.info(
                    f"개별 매입건 없음 - 기본 외주금액 적용 중: "
                    f"{selected_billing.outsourcing_amount:,.0f}원"
                )
            else:
                st.info("외주 매입건이 없습니다.")

        # 새 매입건 등록
        st.write("---")
        st.write("### 새 매입건 등록")

        outsourcing_companies = session.exec(
            select(Company).where(Company.company_type == CompanyType.PURCHASE.value)
        ).all()

        if not outsourcing_companies:
            st.warning("등록된 외주업체가 없습니다. 먼저 외주업체를 등록해주세요.")
            return

        with st.form("outsourcing_entry_form"):
            company_options = {f"{c.code} - {c.name}": c.id for c in outsourcing_companies}
            selected_company = st.selectbox(
                "외주업체*",
                options=list(company_options.keys())
            )
            company_id = company_options[selected_company]

            entry_amount = st.number_input("매입금액*", min_value=0, step=10000)
            purchase_date = st.date_input("매입일자")
            entry_notes = st.text_input("비고")

            if st.form_submit_button("등록"):
                if entry_amount <= 0:
                    st.error("매입금액을 입력해주세요.")
                else:
                    entry = OutsourcingEntry(
                        billing_id=selected_billing_id,
                        outsourcing_company_id=company_id,
                        amount=Decimal(str(entry_amount)),
                        purchase_date=purchase_date,
                        notes=entry_notes
                    )
                    session.add(entry)

                    # 청구의 외주금액 업데이트
                    all_entries = session.exec(
                        select(OutsourcingEntry).where(
                            OutsourcingEntry.billing_id == selected_billing_id
                        )
                    ).all()
                    total_outsourcing = sum(e.amount for e in all_entries) + Decimal(str(entry_amount))

                    selected_billing.outsourcing_amount = total_outsourcing
                    selected_billing.profit = selected_billing.final_amount - total_outsourcing

                    session.commit()
                    st.success("매입건이 등록되었습니다.")
                    st.rerun()


def render_outsourcing_history():
    """외주 이력"""
    st.subheader("외주금액 변경 이력")

    with get_session() as session:
        # 외주금액 변경 이력
        statement = select(OutsourcingHistory).order_by(
            OutsourcingHistory.created_at.desc()
        ).limit(50)

        history_list = session.exec(statement).all()

        if not history_list:
            st.info("변경 이력이 없습니다.")
            return

        for history in history_list:
            st.write(
                f"- {history.created_at.strftime('%Y-%m-%d')}: "
                f"{history.old_amount:,.0f}원 → {history.new_amount:,.0f}원 "
                f"(적용일: {history.effective_date})"
            )
            if history.reason:
                st.write(f"  사유: {history.reason}")
