"""설정 페이지"""

import streamlit as st
from datetime import date
from sqlmodel import select

from database.connection import get_session
from database.models import CodeMapping, Holiday, Company
from services.excel_engine import ExcelEngine
from utils.constants import CompanyType


def render_settings_page():
    """설정 페이지 렌더링"""
    st.header("설정")

    tab1, tab2, tab3, tab4 = st.tabs([
        "창고/팀 코드", "휴일 관리", "업체 관리", "데이터 Import"
    ])

    with tab1:
        render_code_mapping_settings()

    with tab2:
        render_holiday_settings()

    with tab3:
        render_company_settings()

    with tab4:
        render_data_import()


def render_code_mapping_settings():
    """창고/팀 코드 설정"""
    st.subheader("창고/팀 코드 매핑")

    with get_session() as session:
        # 현재 매핑 목록
        mappings = session.exec(select(CodeMapping)).all()

        if mappings:
            st.write("### 현재 코드 매핑")
            for mapping in mappings:
                col1, col2, col3 = st.columns([2, 3, 1])
                with col1:
                    st.write(f"**{mapping.code}**")
                with col2:
                    st.write(mapping.name)
                with col3:
                    if st.button("삭제", key=f"del_mapping_{mapping.id}"):
                        session.delete(mapping)
                        session.commit()
                        st.rerun()
        else:
            st.info("등록된 코드 매핑이 없습니다.")

        # 새 매핑 등록
        st.write("---")
        st.write("### 새 코드 매핑 등록")

        with st.form("code_mapping_form"):
            new_code = st.text_input("코드* (예: 105)")
            new_name = st.text_input("이름* (예: 1팀)")
            category = st.selectbox("카테고리", ["warehouse", "team", "other"])

            if st.form_submit_button("등록"):
                if not new_code or not new_name:
                    st.error("코드와 이름은 필수입니다.")
                else:
                    # 중복 체크
                    existing = session.exec(
                        select(CodeMapping).where(CodeMapping.code == new_code)
                    ).first()

                    if existing:
                        st.error("이미 존재하는 코드입니다.")
                    else:
                        mapping = CodeMapping(
                            code=new_code,
                            name=new_name,
                            category=category
                        )
                        session.add(mapping)
                        session.commit()
                        st.success("코드 매핑이 등록되었습니다.")
                        st.rerun()


def render_holiday_settings():
    """휴일 관리"""
    st.subheader("휴일 관리")

    with get_session() as session:
        # 연도 선택
        holiday_year = st.number_input(
            "년도",
            min_value=2020,
            max_value=2030,
            value=date.today().year,
            key="holiday_year"
        )

        # 해당 연도 휴일 조회
        holidays = session.exec(
            select(Holiday).where(
                Holiday.holiday_date >= date(holiday_year, 1, 1),
                Holiday.holiday_date <= date(holiday_year, 12, 31)
            ).order_by(Holiday.holiday_date)
        ).all()

        if holidays:
            st.write(f"### {holiday_year}년 휴일 목록")
            for holiday in holidays:
                col1, col2, col3 = st.columns([2, 3, 1])
                with col1:
                    st.write(f"**{holiday.holiday_date}**")
                with col2:
                    st.write(holiday.name)
                with col3:
                    if st.button("삭제", key=f"del_holiday_{holiday.id}"):
                        session.delete(holiday)
                        session.commit()
                        st.rerun()
        else:
            st.info(f"{holiday_year}년에 등록된 휴일이 없습니다.")

        # 새 휴일 등록
        st.write("---")
        st.write("### 새 휴일 등록")

        with st.form("holiday_form"):
            new_date = st.date_input("날짜")
            new_name = st.text_input("휴일명")
            is_recurring = st.checkbox("매년 반복")

            if st.form_submit_button("등록"):
                if not new_name:
                    st.error("휴일명은 필수입니다.")
                else:
                    # 중복 체크
                    existing = session.exec(
                        select(Holiday).where(Holiday.holiday_date == new_date)
                    ).first()

                    if existing:
                        st.error("이미 등록된 날짜입니다.")
                    else:
                        holiday = Holiday(
                            holiday_date=new_date,
                            name=new_name,
                            is_recurring=is_recurring
                        )
                        session.add(holiday)
                        session.commit()
                        st.success("휴일이 등록되었습니다.")
                        st.rerun()


def render_company_settings():
    """업체 관리"""
    st.subheader("업체 관리")

    with get_session() as session:
        # 업체 유형 선택
        company_type = st.selectbox(
            "업체 유형",
            [("매출업체", "sales"), ("매입업체(외주)", "purchase")],
            format_func=lambda x: x[0]
        )

        # 해당 유형 업체 목록
        companies = session.exec(
            select(Company).where(Company.company_type == company_type[1])
        ).all()

        if companies:
            st.write(f"### {company_type[0]} 목록")
            for company in companies:
                with st.expander(f"{company.code} - {company.name}"):
                    st.write(f"**코드:** {company.code}")
                    st.write(f"**업체명:** {company.name}")
                    st.write(f"**창고:** {company.warehouse_code or 'N/A'}")
                    st.write(f"**활성:** {'예' if company.is_active else '아니오'}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("비활성화" if company.is_active else "활성화",
                                    key=f"toggle_{company.id}"):
                            company.is_active = not company.is_active
                            session.commit()
                            st.rerun()
        else:
            st.info(f"등록된 {company_type[0]}가 없습니다.")

        # 새 업체 등록
        st.write("---")
        st.write(f"### 새 {company_type[0]} 등록")

        with st.form("company_form"):
            new_code = st.text_input("업체 코드*")
            new_name = st.text_input("업체명*")

            warehouse_code = None
            if company_type[1] == "sales":
                code_mappings = session.exec(select(CodeMapping)).all()
                warehouse_options = ["없음"] + [f"{cm.code} ({cm.name})" for cm in code_mappings]
                selected_warehouse = st.selectbox("창고/팀", warehouse_options)
                if selected_warehouse != "없음":
                    warehouse_code = selected_warehouse.split(" ")[0]

            if st.form_submit_button("등록"):
                if not new_code or not new_name:
                    st.error("코드와 업체명은 필수입니다.")
                else:
                    existing = session.exec(
                        select(Company).where(Company.code == new_code)
                    ).first()

                    if existing:
                        st.error("이미 존재하는 업체 코드입니다.")
                    else:
                        company = Company(
                            code=new_code,
                            name=new_name,
                            company_type=company_type[1],
                            warehouse_code=warehouse_code
                        )
                        session.add(company)
                        session.commit()
                        st.success("업체가 등록되었습니다.")
                        st.rerun()


def render_data_import():
    """데이터 Import"""
    st.subheader("엑셀 데이터 Import")

    st.warning(
        "Import 전 주의사항:\n"
        "- 기존 데이터와 중복되는 경우 오류가 발생할 수 있습니다.\n"
        "- 반드시 백업 후 진행하세요."
    )

    uploaded_file = st.file_uploader(
        "엑셀 파일 선택",
        type=['xlsx', 'xls']
    )

    if uploaded_file is not None:
        # 임시 파일로 저장
        from pathlib import Path
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        with get_session() as session:
            excel_engine = ExcelEngine(session)

            # 미리보기
            if st.button("데이터 미리보기"):
                try:
                    records, errors = excel_engine.import_from_excel(tmp_path)

                    st.write(f"총 {len(records)}건 발견")

                    if errors:
                        st.warning(f"오류 {len(errors)}건")
                        for err in errors[:10]:
                            st.write(f"- Row {err['row']}: {err['error']}")

                    # 미리보기 테이블
                    preview_data = []
                    for record in records[:20]:
                        parsed = record['parsed_data']
                        preview_data.append({
                            'Row': record['row'],
                            '업체명': parsed.get('company_name', ''),
                            '품목명': parsed.get('item_name', ''),
                            '월계약금액': f"{parsed.get('monthly_amount', 0):,.0f}",
                            '오류': '있음' if record['errors'] else ''
                        })

                    import pandas as pd
                    df = pd.DataFrame(preview_data)
                    st.dataframe(df, use_container_width=True)

                except Exception as e:
                    st.error(f"파일 읽기 실패: {str(e)}")

            # Import 실행
            update_existing = st.checkbox("기존 계약 업데이트 허용")

            if st.button("Import 실행", type="primary"):
                try:
                    records, errors = excel_engine.import_from_excel(tmp_path)
                    created, updated, save_errors = excel_engine.save_imported_data(
                        records, update_existing
                    )

                    st.success(
                        f"Import 완료:\n"
                        f"- 생성: {created}건\n"
                        f"- 업데이트: {updated}건"
                    )

                    if save_errors:
                        st.warning(f"저장 오류: {len(save_errors)}건")
                        for err in save_errors:
                            st.write(f"- {err}")

                except Exception as e:
                    st.error(f"Import 실패: {str(e)}")

        # 임시 파일 삭제
        Path(tmp_path).unlink(missing_ok=True)
