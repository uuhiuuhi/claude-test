"""pytest 설정 및 공통 fixture"""

import pytest
from datetime import date
from decimal import Decimal
from sqlmodel import SQLModel, Session, create_engine

from database.models import (
    Company, Contract, ContractHistory, MonthlyBilling,
    Outsourcing, OutsourcingEntry, CodeMapping, Holiday
)
from utils.constants import CompanyType, BillingCycle, ContractStatus, BillingStatus


@pytest.fixture
def engine():
    """테스트용 인메모리 데이터베이스 엔진"""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """테스트용 세션"""
    with Session(engine) as session:
        yield session


@pytest.fixture
def sample_company(session):
    """샘플 매출업체"""
    company = Company(
        code="C001",
        name="테스트고객",
        company_type=CompanyType.SALES.value,
        warehouse_code="105"
    )
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


@pytest.fixture
def sample_outsourcing_company(session):
    """샘플 외주업체"""
    company = Company(
        code="V001",
        name="외주업체A",
        company_type=CompanyType.PURCHASE.value
    )
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


@pytest.fixture
def sample_contract(session, sample_company):
    """샘플 계약 (월 청구, 자동갱신)"""
    contract = Contract(
        company_id=sample_company.id,
        item_name="유지보수비",
        contract_start=date(2024, 1, 1),
        contract_end=date(2024, 12, 31),
        monthly_amount=Decimal("1000000"),
        billing_cycle=BillingCycle.MONTHLY.value,
        billing_timing="말일",
        auto_renewal=True,
        renewal_period_months=12,
        status=ContractStatus.ACTIVE.value
    )
    session.add(contract)
    session.commit()
    session.refresh(contract)
    return contract


@pytest.fixture
def sample_quarterly_contract(session, sample_company):
    """샘플 분기 청구 계약"""
    contract = Contract(
        company_id=sample_company.id,
        item_name="분기 유지보수",
        contract_start=date(2024, 1, 1),
        contract_end=date(2024, 12, 31),
        monthly_amount=Decimal("500000"),
        billing_cycle=BillingCycle.QUARTERLY.value,
        billing_timing="분기말",
        auto_renewal=True,
        status=ContractStatus.ACTIVE.value
    )
    session.add(contract)
    session.commit()
    session.refresh(contract)
    return contract


@pytest.fixture
def sample_semiannual_contract(session, sample_company):
    """샘플 반기 청구 계약"""
    contract = Contract(
        company_id=sample_company.id,
        item_name="반기 유지보수",
        contract_start=date(2024, 1, 1),
        contract_end=date(2024, 12, 31),
        monthly_amount=Decimal("800000"),
        billing_cycle=BillingCycle.SEMIANNUAL.value,
        auto_renewal=True,
        status=ContractStatus.ACTIVE.value
    )
    session.add(contract)
    session.commit()
    session.refresh(contract)
    return contract


@pytest.fixture
def sample_reverse_billing_contract(session, sample_company):
    """샘플 역발행 계약"""
    contract = Contract(
        company_id=sample_company.id,
        item_name="역발행 유지보수",
        contract_start=date(2024, 1, 1),
        contract_end=date(2024, 12, 31),
        monthly_amount=Decimal("600000"),
        billing_cycle=BillingCycle.MONTHLY.value,
        billing_timing="역발행",
        is_reverse_billing=True,
        auto_renewal=True,
        status=ContractStatus.ACTIVE.value
    )
    session.add(contract)
    session.commit()
    session.refresh(contract)
    return contract


@pytest.fixture
def sample_contract_with_outsourcing(session, sample_company, sample_outsourcing_company):
    """샘플 외주 포함 계약"""
    contract = Contract(
        company_id=sample_company.id,
        item_name="외주 포함 유지보수",
        contract_start=date(2024, 1, 1),
        contract_end=date(2024, 12, 31),
        monthly_amount=Decimal("2000000"),
        billing_cycle=BillingCycle.MONTHLY.value,
        auto_renewal=True,
        default_outsourcing_company_id=sample_outsourcing_company.id,
        default_outsourcing_amount=Decimal("500000"),
        status=ContractStatus.ACTIVE.value
    )
    session.add(contract)
    session.commit()
    session.refresh(contract)
    return contract


@pytest.fixture
def sample_holidays(session):
    """샘플 휴일 데이터"""
    holidays = [
        Holiday(date=date(2024, 1, 1), name="신정"),
        Holiday(date=date(2024, 3, 1), name="삼일절"),
        Holiday(date=date(2024, 5, 5), name="어린이날"),
        Holiday(date=date(2024, 12, 25), name="성탄절"),
    ]
    for h in holidays:
        session.add(h)
    session.commit()
    return [h.date for h in holidays]


@pytest.fixture
def sample_code_mappings(session):
    """샘플 코드 매핑"""
    mappings = [
        CodeMapping(code="105", name="1팀", category="warehouse"),
        CodeMapping(code="106", name="2팀", category="warehouse"),
    ]
    for m in mappings:
        session.add(m)
    session.commit()
    return mappings
