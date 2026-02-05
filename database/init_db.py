"""데이터베이스 초기화 스크립트 - 기본 데이터 포함"""

from datetime import date
from decimal import Decimal
from database.connection import init_database, get_session
from database.models import CodeMapping, Company, Holiday


def create_default_code_mappings(session):
    """기본 창고/팀 코드 매핑 생성"""
    default_mappings = [
        {"code": "105", "name": "1팀", "category": "warehouse"},
        {"code": "106", "name": "2팀", "category": "warehouse"},
    ]

    for mapping in default_mappings:
        existing = session.query(CodeMapping).filter(
            CodeMapping.code == mapping["code"]
        ).first()

        if not existing:
            session.add(CodeMapping(**mapping))

    session.commit()


def create_default_holidays(session):
    """기본 휴일 데이터 생성 (2024-2025)"""
    holidays_2024 = [
        {"date": date(2024, 1, 1), "name": "신정", "is_recurring": True},
        {"date": date(2024, 2, 9), "name": "설날 연휴", "is_recurring": False},
        {"date": date(2024, 2, 10), "name": "설날", "is_recurring": False},
        {"date": date(2024, 2, 11), "name": "설날 연휴", "is_recurring": False},
        {"date": date(2024, 2, 12), "name": "대체공휴일", "is_recurring": False},
        {"date": date(2024, 3, 1), "name": "삼일절", "is_recurring": True},
        {"date": date(2024, 5, 5), "name": "어린이날", "is_recurring": True},
        {"date": date(2024, 5, 6), "name": "대체공휴일", "is_recurring": False},
        {"date": date(2024, 5, 15), "name": "부처님오신날", "is_recurring": False},
        {"date": date(2024, 6, 6), "name": "현충일", "is_recurring": True},
        {"date": date(2024, 8, 15), "name": "광복절", "is_recurring": True},
        {"date": date(2024, 9, 16), "name": "추석 연휴", "is_recurring": False},
        {"date": date(2024, 9, 17), "name": "추석", "is_recurring": False},
        {"date": date(2024, 9, 18), "name": "추석 연휴", "is_recurring": False},
        {"date": date(2024, 10, 3), "name": "개천절", "is_recurring": True},
        {"date": date(2024, 10, 9), "name": "한글날", "is_recurring": True},
        {"date": date(2024, 12, 25), "name": "성탄절", "is_recurring": True},
    ]

    holidays_2025 = [
        {"date": date(2025, 1, 1), "name": "신정", "is_recurring": True},
        {"date": date(2025, 1, 28), "name": "설날 연휴", "is_recurring": False},
        {"date": date(2025, 1, 29), "name": "설날", "is_recurring": False},
        {"date": date(2025, 1, 30), "name": "설날 연휴", "is_recurring": False},
        {"date": date(2025, 3, 1), "name": "삼일절", "is_recurring": True},
        {"date": date(2025, 5, 5), "name": "어린이날/부처님오신날", "is_recurring": False},
        {"date": date(2025, 5, 6), "name": "대체공휴일", "is_recurring": False},
        {"date": date(2025, 6, 6), "name": "현충일", "is_recurring": True},
        {"date": date(2025, 8, 15), "name": "광복절", "is_recurring": True},
        {"date": date(2025, 10, 3), "name": "개천절", "is_recurring": True},
        {"date": date(2025, 10, 5), "name": "추석 연휴", "is_recurring": False},
        {"date": date(2025, 10, 6), "name": "추석", "is_recurring": False},
        {"date": date(2025, 10, 7), "name": "추석 연휴", "is_recurring": False},
        {"date": date(2025, 10, 8), "name": "대체공휴일", "is_recurring": False},
        {"date": date(2025, 10, 9), "name": "한글날", "is_recurring": True},
        {"date": date(2025, 12, 25), "name": "성탄절", "is_recurring": True},
    ]

    for holiday in holidays_2024 + holidays_2025:
        existing = session.query(Holiday).filter(
            Holiday.date == holiday["date"]
        ).first()

        if not existing:
            session.add(Holiday(**holiday))

    session.commit()


def create_sample_data(session):
    """샘플 데이터 생성 (개발/테스트용)"""
    # 샘플 매출업체
    sales_companies = [
        {"code": "C001", "name": "테스트고객A", "company_type": "sales", "warehouse_code": "105"},
        {"code": "C002", "name": "테스트고객B", "company_type": "sales", "warehouse_code": "106"},
    ]

    # 샘플 매입업체 (외주)
    purchase_companies = [
        {"code": "V001", "name": "외주업체A", "company_type": "purchase"},
        {"code": "V002", "name": "외주업체B", "company_type": "purchase"},
    ]

    for company_data in sales_companies + purchase_companies:
        existing = session.query(Company).filter(
            Company.code == company_data["code"]
        ).first()

        if not existing:
            session.add(Company(**company_data))

    session.commit()


def initialize_all():
    """전체 초기화 실행"""
    print("데이터베이스 초기화 시작...")

    # 테이블 생성
    init_database()
    print("- 테이블 생성 완료")

    # 기본 데이터 생성
    with get_session() as session:
        create_default_code_mappings(session)
        print("- 코드 매핑 생성 완료")

        create_default_holidays(session)
        print("- 휴일 데이터 생성 완료")

        create_sample_data(session)
        print("- 샘플 데이터 생성 완료")

    print("데이터베이스 초기화 완료!")


if __name__ == "__main__":
    initialize_all()
