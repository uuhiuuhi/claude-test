"""
관리팀 내부용 유지보수 계약·청구·외주·이익 관리 시스템
메인 애플리케이션
"""

import streamlit as st
from pathlib import Path

# 페이지 설정 (반드시 첫 번째로 실행)
st.set_page_config(
    page_title="유지보수 관리 시스템",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

from database.connection import init_database, get_session
from database.init_db import initialize_all
from ui.contract_page import render_contract_page
from ui.billing_page import render_billing_page
from ui.outsourcing_page import render_outsourcing_page
from ui.validation_page import render_validation_page
from ui.report_page import render_report_page
from ui.settings_page import render_settings_page


def check_and_init_database():
    """데이터베이스 초기화 확인"""
    db_path = Path(__file__).parent / "data" / "maintenance_billing.db"

    if not db_path.exists():
        with st.spinner("데이터베이스 초기화 중..."):
            initialize_all()
        st.success("데이터베이스가 초기화되었습니다.")
    else:
        # 테이블 확인
        init_database()


def main():
    """메인 함수"""
    # 데이터베이스 초기화
    check_and_init_database()

    # 사이드바 메뉴
    st.sidebar.title("유지보수 관리 시스템")
    st.sidebar.write("관리팀 내부용")

    menu = st.sidebar.radio(
        "메뉴",
        [
            "대시보드",
            "계약 관리",
            "월 청구 생성",
            "외주 관리",
            "검증/경고",
            "보고서",
            "설정"
        ]
    )

    st.sidebar.write("---")

    # 현재 상태 요약
    with get_session() as session:
        from datetime import date
        from sqlmodel import select, func
        from database.models import MonthlyBilling, Contract
        from utils.constants import BillingStatus, ContractStatus

        today = date.today()

        # 활성 계약 수
        active_contracts = session.exec(
            select(func.count(Contract.id)).where(
                Contract.status.in_([
                    ContractStatus.ACTIVE.value,
                    ContractStatus.PERIOD_UNDEFINED.value
                ])
            )
        ).one()

        # 이번 달 청구 수
        monthly_billings = session.exec(
            select(func.count(MonthlyBilling.id)).where(
                MonthlyBilling.billing_year == today.year,
                MonthlyBilling.billing_month == today.month
            )
        ).one()

        # 초안 상태 청구 수
        draft_billings = session.exec(
            select(func.count(MonthlyBilling.id)).where(
                MonthlyBilling.billing_year == today.year,
                MonthlyBilling.billing_month == today.month,
                MonthlyBilling.status == BillingStatus.DRAFT.value
            )
        ).one()

        st.sidebar.metric("활성 계약", active_contracts)
        st.sidebar.metric(f"{today.month}월 청구", monthly_billings)

        if draft_billings > 0:
            st.sidebar.warning(f"미확정: {draft_billings}건")

    # 페이지 라우팅
    if menu == "대시보드":
        render_dashboard()
    elif menu == "계약 관리":
        render_contract_page()
    elif menu == "월 청구 생성":
        render_billing_page()
    elif menu == "외주 관리":
        render_outsourcing_page()
    elif menu == "검증/경고":
        render_validation_page()
    elif menu == "보고서":
        render_report_page()
    elif menu == "설정":
        render_settings_page()


def render_dashboard():
    """대시보드"""
    st.header("대시보드")

    from datetime import date
    from sqlmodel import select
    from database.models import MonthlyBilling, Contract
    from services.calculation_engine import CalculationEngine
    from services.validation_engine import ValidationEngine
    from utils.constants import BillingStatus, ContractStatus

    today = date.today()

    with get_session() as session:
        # 이번 달 요약
        st.subheader(f"{today.year}년 {today.month}월 현황")

        calc_engine = CalculationEngine(session)
        validation_engine = ValidationEngine(session)

        summary = calc_engine.calculate_monthly_summary(today.year, today.month)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("청구 건수", summary['count'])

        with col2:
            st.metric("총 매출", f"{summary['total_billing']:,.0f}원")

        with col3:
            st.metric("총 외주", f"{summary['total_outsourcing']:,.0f}원")

        with col4:
            st.metric("총 이익", f"{summary['total_profit']:,.0f}원")

        # 경고/누락 현황
        st.write("---")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("경고 현황")
            warnings = validation_engine.get_all_warnings_for_month(today.year, today.month)

            if warnings:
                error_count = sum(1 for w in warnings if w.get('level') == 'error')
                warning_count = sum(1 for w in warnings if w.get('level') == 'warning')

                if error_count > 0:
                    st.error(f"오류: {error_count}건")
                if warning_count > 0:
                    st.warning(f"경고: {warning_count}건")

                # 최근 경고 5개
                for w in warnings[:5]:
                    level_emoji = {'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}.get(w.get('level', 'info'), '❓')
                    st.write(f"{level_emoji} {w.get('company_name', '')}: {w.get('message', '')}")
            else:
                st.success("경고 없음")

        with col2:
            st.subheader("누락 점검")
            missing = validation_engine.get_missing_billings(today.year, today.month)

            if missing:
                st.error(f"누락 가능: {len(missing)}건")
                for contract in missing[:5]:
                    company = contract.company
                    st.write(f"- {company.name if company else 'N/A'}: {contract.item_name}")
            else:
                st.success("누락 없음")

        # 상태별 현황
        st.write("---")
        st.subheader("청구 상태별 현황")

        billings = session.exec(
            select(MonthlyBilling).where(
                MonthlyBilling.billing_year == today.year,
                MonthlyBilling.billing_month == today.month
            )
        ).all()

        status_counts = {
            'draft': 0,
            'confirmed': 0,
            'locked': 0,
            'cancelled': 0
        }

        for b in billings:
            status_counts[b.status] = status_counts.get(b.status, 0) + 1

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("초안", status_counts['draft'])

        with col2:
            st.metric("확정", status_counts['confirmed'])

        with col3:
            st.metric("잠금", status_counts['locked'])

        with col4:
            st.metric("취소", status_counts['cancelled'])

        # 빠른 액션
        st.write("---")
        st.subheader("빠른 액션")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("이번 달 청구 생성", use_container_width=True):
                st.switch_page = "월 청구 생성"  # Streamlit 1.30+ 에서 지원

        with col2:
            if st.button("누락 점검", use_container_width=True):
                st.switch_page = "검증/경고"

        with col3:
            if st.button("엑셀 Export", use_container_width=True):
                st.switch_page = "보고서"


if __name__ == "__main__":
    main()
