"""데이터베이스 연결 및 세션 관리"""

from sqlmodel import SQLModel, Session, create_engine
from pathlib import Path

# 데이터베이스 파일 경로
DATABASE_PATH = Path(__file__).parent.parent / "data" / "maintenance_billing.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# 엔진 생성 (SQLite 전용 설정)
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)


def ensure_data_directory():
    """데이터 디렉토리 생성"""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_database():
    """데이터베이스 초기화 (테이블 생성)"""
    ensure_data_directory()
    SQLModel.metadata.create_all(engine)


def get_session():
    """세션 생성"""
    return Session(engine)


def get_engine():
    """엔진 반환"""
    return engine
