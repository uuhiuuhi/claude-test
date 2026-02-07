"""SQLModel 데이터 모델 정의 - 사내 표준 스키마"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Text, JSON
import json


class CodeMapping(SQLModel, table=True):
    """창고/팀 코드 매핑 (확장 가능)"""
    __tablename__ = "code_mappings"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)  # 예: "105", "106"
    name: str  # 예: "1팀", "2팀"
    category: str = Field(default="warehouse")  # warehouse, team, etc.
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Company(SQLModel, table=True):
    """업체 정보 (매출업체/매입업체)"""
    __tablename__ = "companies"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True)  # 업체 코드 (이카운트 참조)
    name: str = Field(index=True)
    company_type: str  # 'sales' (매출) or 'purchase' (매입/외주)
    warehouse_code: Optional[str] = None  # 창고 코드 (팀 구분)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    contracts: List["Contract"] = Relationship(
        back_populates="company",
        sa_relationship_kwargs={"foreign_keys": "Contract.company_id"}
    )


class Contract(SQLModel, table=True):
    """유지보수 계약"""
    __tablename__ = "contracts"

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")
    item_name: str  # 품목명

    # 계약기간
    contract_start: Optional[date] = None  # None 허용 (계약기간 미확정)
    contract_end: Optional[date] = None

    # 금액
    monthly_amount: Decimal = Field(default=Decimal("0"))  # 월 계약금액

    # 청구 설정
    billing_cycle: str = Field(default="monthly")  # monthly, quarterly, semiannual, biannual, irregular
    billing_timing: Optional[str] = None  # 발행시기 원문
    billing_timing_parsed: Optional[str] = Field(default=None, sa_column=Column(JSON))  # 파싱 결과 JSON

    # 자동갱신
    auto_renewal: bool = Field(default=True)  # 사내 표준: 기본값 True
    renewal_period_months: int = Field(default=12)  # 갱신 주기

    # 역발행
    is_reverse_billing: bool = Field(default=False)

    # 외주 기본값
    default_outsourcing_company_id: Optional[int] = Field(default=None, foreign_key="companies.id")
    default_outsourcing_amount: Decimal = Field(default=Decimal("0"))  # 월 기준 외주금액
    outsourcing_amount_zero: bool = Field(default=False)  # 외주금액 0 명시 설정

    # 상태
    status: str = Field(default="active")  # active, expired, terminated, period_undefined

    # 특이사항
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    notes_parsed: Optional[str] = Field(default=None, sa_column=Column(JSON))  # 파싱된 규칙

    # 메타
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    company: Optional[Company] = Relationship(
        back_populates="contracts",
        sa_relationship_kwargs={"foreign_keys": "[Contract.company_id]"}
    )
    history: List["ContractHistory"] = Relationship(back_populates="contract")
    billings: List["MonthlyBilling"] = Relationship(back_populates="contract")
    outsourcings: List["Outsourcing"] = Relationship(back_populates="contract")


class ContractHistory(SQLModel, table=True):
    """계약 변경 이력 (금액/기간 변경 추적)"""
    __tablename__ = "contract_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="contracts.id")

    # 변경 내용
    change_type: str  # 'amount', 'period', 'outsourcing', 'status', 'other'
    effective_date: date  # 적용일

    # 변경 전/후 값 (JSON)
    old_value: Optional[str] = Field(default=None, sa_column=Column(JSON))
    new_value: Optional[str] = Field(default=None, sa_column=Column(JSON))

    # 변경 사유
    reason: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[str] = None  # 변경자

    # Relationships
    contract: Optional[Contract] = Relationship(back_populates="history")


class MonthlyBilling(SQLModel, table=True):
    """월별 청구 레코드"""
    __tablename__ = "monthly_billings"

    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="contracts.id")

    # 청구 기간
    billing_year: int
    billing_month: int
    cover_months: int = Field(default=1)  # 커버 개월 수 (분기=3, 반기=6 등)

    # 금액 (자동계산 + 오버라이드)
    calculated_amount: Decimal = Field(default=Decimal("0"))  # 시스템 계산값
    override_amount: Optional[Decimal] = None  # 사용자 오버라이드
    final_amount: Decimal = Field(default=Decimal("0"))  # 최종 청구금액

    # 부가세/합계
    vat_amount: Decimal = Field(default=Decimal("0"))
    total_amount: Decimal = Field(default=Decimal("0"))

    # 외주/이익
    outsourcing_amount: Decimal = Field(default=Decimal("0"))  # 외주금액 합계
    profit: Decimal = Field(default=Decimal("0"))  # 실제이익

    # 발행일자
    sales_date: Optional[date] = None  # 매출일자 (계산서작성일)
    request_date: Optional[date] = None  # 요청일자 (실제 발행일)
    suggested_date: Optional[date] = None  # 시스템 제안 발행일

    # 상태
    status: str = Field(default="draft")  # draft, confirmed, locked, cancelled

    # 검증/경고
    warnings: Optional[str] = Field(default=None, sa_column=Column(JSON))  # 경고 목록 JSON
    has_warnings: bool = Field(default=False)

    # 메타
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    locked_at: Optional[datetime] = None
    locked_by: Optional[str] = None

    # Relationships
    contract: Optional[Contract] = Relationship(back_populates="billings")
    outsourcing_entries: List["OutsourcingEntry"] = Relationship(back_populates="billing")


class Outsourcing(SQLModel, table=True):
    """외주 계약 정보"""
    __tablename__ = "outsourcings"

    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="contracts.id")
    outsourcing_company_id: int = Field(foreign_key="companies.id")

    # 기본 외주금액 (월 기준)
    monthly_amount: Decimal = Field(default=Decimal("0"))

    # 적용 기간
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None

    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    contract: Optional[Contract] = Relationship(back_populates="outsourcings")
    outsourcing_company: Optional[Company] = Relationship()


class OutsourcingEntry(SQLModel, table=True):
    """외주 매입 건별 기록 (월별 다건 허용)"""
    __tablename__ = "outsourcing_entries"

    id: Optional[int] = Field(default=None, primary_key=True)
    billing_id: int = Field(foreign_key="monthly_billings.id")
    outsourcing_company_id: int = Field(foreign_key="companies.id")

    # 매입 정보
    amount: Decimal
    purchase_date: Optional[date] = None

    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    billing: Optional[MonthlyBilling] = Relationship(back_populates="outsourcing_entries")
    outsourcing_company: Optional[Company] = Relationship()


class OutsourcingHistory(SQLModel, table=True):
    """외주금액 변경 이력"""
    __tablename__ = "outsourcing_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    outsourcing_id: int = Field(foreign_key="outsourcings.id")

    effective_date: date
    old_amount: Decimal
    new_amount: Decimal
    reason: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.now)


class Holiday(SQLModel, table=True):
    """휴일 관리 (발행일 보정용)"""
    __tablename__ = "holidays"

    id: Optional[int] = Field(default=None, primary_key=True)
    holiday_date: date = Field(index=True, unique=True)
    name: str
    is_recurring: bool = Field(default=False)  # 매년 반복 (음력 제외)
    created_at: datetime = Field(default_factory=datetime.now)


class BillingRule(SQLModel, table=True):
    """고객별 발행 규칙"""
    __tablename__ = "billing_rules"

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")

    # 규칙 유형
    rule_type: str  # 'po_required', 'attachment_required', 'email', 'reverse_billing', etc.
    rule_value: Optional[str] = Field(default=None, sa_column=Column(JSON))

    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    company: Optional[Company] = Relationship()
