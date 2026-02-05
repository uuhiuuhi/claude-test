"""보고서 페이지"""

import streamlit as st
from datetime import date
from decimal import Decimal
from sqlmodel import select
import pandas as pd

from database.connection import get_session
from database.models import MonthlyBilling, Contract, CodeMapping
from services.calculation_engine import CalculationEngine
from services.excel_engine import ExcelEngine


def render_report_page():
    """보고서 페이지 렌더링"""
    st.header("보고서")

    tab1, tab2, tab3 = st.tabs(["월별 집계", "연도별 집계", "엑셀 Export"])

    with tab1:
        render_monthly_summary()

    with tab2:
        render_yearly_summary()

    with tab3:
        render_excel_export()


def render_monthly_summary():
    """월별 집계"""
    st.subheader("월별 집계")

    col1, col2 = st.columns(2)

    with col1:
        summary_year = st.number_input(
            "년도",
            min_value=2020,
            max_value=2030,
            value=date.today().year,
            key="summary_year"
        )

    with col2:
        summary_month = st.number_input(
            "월",
            min_value=1,
            max_value=12,
            value=date.today().month,
            key="summary_month"
        )

    with get_session() as session:
        calc_engine = CalculationEngine(session)
        summary = calc_engine.calculate_monthly_summary(summary_year, summary_month)

        # 전체 합계
        st.write("### 전체 합계")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("건수", summary['count'])
        with col2:
            st.metric("매출", f"{summary['total_billing']:,.0f}원")
        with col3:
            st.metric("외주", f"{summary['total_outsourcing']:,.0f}원")
        with col4:
            st.metric("이익", f"{summary['total_profit']:,.0f}원")

        # 이익률
        if summary['total_billing'] > 0:
            profit_rate = (summary['total_profit'] / summary['total_billing']) * 100
            st.write(f"**이익률:** {profit_rate:.1f}%")

        # 창고/팀별 집계
        if summary['by_warehouse']:
            st.write("---")
            st.write("### 창고/팀별 집계")

            # 코드 매핑
            code_mappings = {
                cm.code: cm.name
                for cm in session.exec(select(CodeMapping)).all()
            }

            data = []
            for wh_code, wh_data in summary['by_warehouse'].items():
                wh_name = code_mappings.get(wh_code, wh_code)
                profit_rate = 0
                if wh_data['billing'] > 0:
                    profit_rate = (wh_data['profit'] / wh_data['billing']) * 100

                data.append({
                    '창고': f"{wh_code} ({wh_name})",
                    '건수': wh_data['count'],
                    '매출': f"{wh_data['billing']:,.0f}",
                    '외주': f"{wh_data['outsourcing']:,.0f}",
                    '이익': f"{wh_data['profit']:,.0f}",
                    '이익률': f"{profit_rate:.1f}%"
                })

            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)


def render_yearly_summary():
    """연도별 집계"""
    st.subheader("연도별 집계")

    yearly_year = st.number_input(
        "년도",
        min_value=2020,
        max_value=2030,
        value=date.today().year,
        key="yearly_year"
    )

    with get_session() as session:
        calc_engine = CalculationEngine(session)
        summary = calc_engine.calculate_yearly_summary(yearly_year)

        # 전체 합계
        st.write("### 연간 합계")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("건수", summary['count'])
        with col2:
            st.metric("매출", f"{summary['total_billing']:,.0f}원")
        with col3:
            st.metric("외주", f"{summary['total_outsourcing']:,.0f}원")
        with col4:
            st.metric("이익", f"{summary['total_profit']:,.0f}원")

        # 월별 추이
        st.write("---")
        st.write("### 월별 추이")

        monthly_data = []
        for month in range(1, 13):
            m_data = summary['by_month'].get(month, {})
            monthly_data.append({
                '월': f"{month}월",
                '매출': float(m_data.get('total_billing', 0)),
                '외주': float(m_data.get('total_outsourcing', 0)),
                '이익': float(m_data.get('total_profit', 0))
            })

        df = pd.DataFrame(monthly_data)

        # 차트
        st.bar_chart(
            df.set_index('월')[['매출', '이익']],
            use_container_width=True
        )

        # 테이블
        st.dataframe(
            df.style.format({
                '매출': '{:,.0f}',
                '외주': '{:,.0f}',
                '이익': '{:,.0f}'
            }),
            use_container_width=True,
            hide_index=True
        )


def render_excel_export():
    """엑셀 Export"""
    st.subheader("엑셀 Export")

    col1, col2 = st.columns(2)

    with col1:
        export_year = st.number_input(
            "년도",
            min_value=2020,
            max_value=2030,
            value=date.today().year,
            key="export_year"
        )

    with col2:
        export_month = st.number_input(
            "월",
            min_value=1,
            max_value=12,
            value=date.today().month,
            key="export_month"
        )

    with get_session() as session:
        # 청구 건수 확인
        billings = session.exec(
            select(MonthlyBilling).where(
                MonthlyBilling.billing_year == export_year,
                MonthlyBilling.billing_month == export_month
            )
        ).all()

        st.write(f"Export 대상: {len(billings)}건")

        if billings:
            if st.button("엑셀 파일 생성", type="primary"):
                excel_engine = ExcelEngine(session)

                # 파일 경로 생성
                from pathlib import Path
                output_dir = Path("exports")
                output_dir.mkdir(exist_ok=True)

                file_name = f"billing_{export_year}_{export_month:02d}.xlsx"
                file_path = output_dir / file_name

                try:
                    excel_engine.export_monthly_billing(
                        export_year,
                        export_month,
                        str(file_path)
                    )

                    st.success(f"파일이 생성되었습니다: {file_path}")

                    # 다운로드 버튼
                    with open(file_path, 'rb') as f:
                        st.download_button(
                            label="다운로드",
                            data=f,
                            file_name=file_name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                except Exception as e:
                    st.error(f"파일 생성 실패: {str(e)}")
        else:
            st.info("Export할 청구가 없습니다.")

    st.write("---")

    # 빈 템플릿 다운로드
    st.write("### 빈 템플릿 다운로드")

    if st.button("템플릿 생성"):
        with get_session() as session:
            excel_engine = ExcelEngine(session)

            from pathlib import Path
            output_dir = Path("exports")
            output_dir.mkdir(exist_ok=True)

            file_path = output_dir / "template.xlsx"

            try:
                excel_engine.create_template(str(file_path))
                st.success(f"템플릿이 생성되었습니다: {file_path}")

                with open(file_path, 'rb') as f:
                    st.download_button(
                        label="템플릿 다운로드",
                        data=f,
                        file_name="template.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            except Exception as e:
                st.error(f"템플릿 생성 실패: {str(e)}")
