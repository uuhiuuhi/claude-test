"""검증/경고 페이지"""

import streamlit as st
from datetime import date
import json
from sqlmodel import select

from database.connection import get_session
from database.models import MonthlyBilling, Contract
from services.validation_engine import ValidationEngine


def render_validation_page():
    """검증/경고 페이지 렌더링"""
    st.header("검증 및 경고")

    tab1, tab2 = st.tabs(["월별 경고", "누락 점검"])

    with tab1:
        render_monthly_warnings()

    with tab2:
        render_missing_check()


def render_monthly_warnings():
    """월별 경고"""
    st.subheader("월별 경고 목록")

    col1, col2 = st.columns(2)

    with col1:
        warn_year = st.number_input(
            "년도",
            min_value=2020,
            max_value=2030,
            value=date.today().year,
            key="warn_year"
        )

    with col2:
        warn_month = st.number_input(
            "월",
            min_value=1,
            max_value=12,
            value=date.today().month,
            key="warn_month"
        )

    with get_session() as session:
        validation_engine = ValidationEngine(session)
        warnings = validation_engine.get_all_warnings_for_month(warn_year, warn_month)

        # 경고 레벨별 집계
        error_count = sum(1 for w in warnings if w.get('level') == 'error')
        warning_count = sum(1 for w in warnings if w.get('level') == 'warning')
        info_count = sum(1 for w in warnings if w.get('level') == 'info')

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("오류", error_count, delta=None, delta_color="inverse")
        with col2:
            st.metric("경고", warning_count)
        with col3:
            st.metric("정보", info_count)

        if not warnings:
            st.success("경고가 없습니다.")
            return

        # 경고 레벨 필터
        level_filter = st.selectbox(
            "레벨 필터",
            ["전체", "오류", "경고", "정보"]
        )

        filtered_warnings = warnings
        if level_filter != "전체":
            level_map = {"오류": "error", "경고": "warning", "정보": "info"}
            filtered_warnings = [w for w in warnings if w.get('level') == level_map[level_filter]]

        st.write(f"총 {len(filtered_warnings)}건")

        # 경고 목록
        for w in filtered_warnings:
            level = w.get('level', 'info')
            level_emoji = {
                'error': '❌',
                'warning': '⚠️',
                'info': 'ℹ️'
            }.get(level, '❓')

            level_color = {
                'error': '#ff4444',
                'warning': '#ffaa00',
                'info': '#4488ff'
            }.get(level, '#888888')

            company_name = w.get('company_name', 'N/A')
            code = w.get('code', '')
            message = w.get('message', '')

            st.markdown(
                f"<div style='border-left: 4px solid {level_color}; padding-left: 10px; margin: 5px 0;'>"
                f"<strong>{level_emoji} [{code}] {company_name}</strong><br/>"
                f"{message}</div>",
                unsafe_allow_html=True
            )


def render_missing_check():
    """누락 점검"""
    st.subheader("청구 누락 점검")

    col1, col2 = st.columns(2)

    with col1:
        missing_year = st.number_input(
            "년도",
            min_value=2020,
            max_value=2030,
            value=date.today().year,
            key="missing_year"
        )

    with col2:
        missing_month = st.number_input(
            "월",
            min_value=1,
            max_value=12,
            value=date.today().month,
            key="missing_month"
        )

    if st.button("누락 점검 실행", type="primary"):
        with get_session() as session:
            validation_engine = ValidationEngine(session)
            missing_contracts = validation_engine.get_missing_billings(
                missing_year, missing_month
            )

            if not missing_contracts:
                st.success("누락된 청구가 없습니다.")
            else:
                st.error(f"⚠️ 청구 누락 가능성: {len(missing_contracts)}건")

                for contract in missing_contracts:
                    company = contract.company

                    with st.expander(
                        f"{company.name if company else 'N/A'} - {contract.item_name}",
                        expanded=True
                    ):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**업체코드:** {company.code if company else 'N/A'}")
                            st.write(f"**계약기간:** {contract.contract_start} ~ {contract.contract_end}")
                            st.write(f"**청구주기:** {contract.billing_cycle}")

                        with col2:
                            st.write(f"**월 계약금액:** {contract.monthly_amount:,.0f}원")
                            st.write(f"**자동갱신:** {'예' if contract.auto_renewal else '아니오'}")
                            st.write(f"**상태:** {contract.status}")

                        # 누락 원인 분석
                        st.write("**가능한 원인:**")
                        if contract.status == 'period_undefined':
                            st.write("- 계약기간 미확정 상태")
                        if contract.billing_cycle == 'irregular':
                            st.write("- 비정기 청구 (수동 생성 필요)")
                        if contract.billing_timing:
                            st.write(f"- 발행시기: {contract.billing_timing}")


def get_warning_summary(session, year: int, month: int) -> dict:
    """경고 요약 조회"""
    validation_engine = ValidationEngine(session)
    warnings = validation_engine.get_all_warnings_for_month(year, month)
    missing = validation_engine.get_missing_billings(year, month)

    return {
        'total_warnings': len(warnings),
        'errors': sum(1 for w in warnings if w.get('level') == 'error'),
        'warnings': sum(1 for w in warnings if w.get('level') == 'warning'),
        'info': sum(1 for w in warnings if w.get('level') == 'info'),
        'missing_count': len(missing)
    }
