# 유지보수 관리 시스템

관리팀 내부용 유지보수 계약·청구·외주·이익 관리 시스템

## 핵심 목표

1. **매월 유지보수 청구 누락 0건**
2. **계약/외주/금액 변동이 있어도 월별 매출·외주·실이익이 항상 정확**

## 시스템 요구사항

- Python 3.11
- Windows 10/11

## 설치 방법 (Windows)

### 1. Python 설치 확인

```cmd
python --version
```

Python 3.11이 설치되어 있지 않다면 [python.org](https://www.python.org/downloads/)에서 다운로드

### 2. 가상환경 생성 (권장)

```cmd
cd C:\Users\user\claude-test
python -m venv venv
venv\Scripts\activate
```

### 3. 의존성 설치

```cmd
pip install -r requirements.txt
```

### 4. 데이터베이스 초기화

```cmd
python -c "from database.init_db import initialize_all; initialize_all()"
```

## 실행 방법

```cmd
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

## 테스트 실행

### 전체 테스트

```cmd
pytest
```

### 특정 테스트 파일

```cmd
pytest tests/test_billing_engine.py -v
```

### 특정 테스트 함수

```cmd
pytest tests/test_billing_engine.py::TestAutoRenewal::test_auto_renewal_generates_billing -v
```

### 커버리지 리포트

```cmd
pip install pytest-cov
pytest --cov=. --cov-report=html
```

## 주요 기능

### 1. 계약 관리
- 계약 등록/수정/조회
- 자동갱신 설정
- 역발행 설정
- 계약 변경 이력 관리

### 2. 월 청구 생성
- 청구 대상 자동 산출 (자동갱신 포함)
- 청구주기별 처리 (매월/분기/반기/연2회/비정기)
- 발행일자 자동 제안 (휴일 보정)
- 금액 오버라이드 가능
- 청구 확정/잠금

### 3. 외주 관리
- 외주업체 관리
- 월별 다건 매입 등록
- 기본 외주금액 설정

### 4. 검증/경고
- 계약기간 미확정 경고
- 발행시기 파싱 불가 경고
- 금액 급변 탐지 (30% 이상)
- 중복 청구 검증
- 누락 점검

### 5. 보고서
- 월별/연도별 집계
- 창고(팀)별 집계
- 엑셀 Export

## 사내 표준 규칙

### 계약 기본 규칙
- 자동갱신이 기본 (true)
- 갱신주기 기본값 12개월
- 계약기간 미확정 시에도 청구 가능 (경고 표시)

### 청구 규칙
- 청구금액은 항상 수동 오버라이드 가능
- 분기/반기 청구: 월 계약금액 × 커버 개월 수

### 발행일 규칙
- 휴일인 경우 직전 영업일로 자동 보정
- 역발행 계약: 발행 프로세스 비활성

### 외주 규칙
- 매입건 있으면 합산
- 매입건 없으면 기본 외주금액 적용
- 외주금액 0 명시 설정 가능

### 실제이익 계산
- 실제이익 = 청구금액(매출) - 외주금액(매입)

## 폴더 구조

```
maintenance_billing/
├── app.py                    # Streamlit 메인
├── requirements.txt
├── README.md
├── CLAUDE.md
├── database/
│   ├── connection.py         # DB 연결
│   ├── models.py             # SQLModel 모델
│   └── init_db.py            # DB 초기화
├── services/
│   ├── billing_engine.py     # 청구 생성 엔진
│   ├── validation_engine.py  # 검증 엔진
│   ├── calculation_engine.py # 계산 엔진
│   └── excel_engine.py       # 엑셀 처리
├── ui/
│   ├── contract_page.py      # 계약 관리
│   ├── billing_page.py       # 월 청구 생성
│   ├── outsourcing_page.py   # 외주 관리
│   ├── validation_page.py    # 검증/경고
│   ├── report_page.py        # 보고서
│   └── settings_page.py      # 설정
├── utils/
│   ├── constants.py          # 상수
│   ├── date_utils.py         # 날짜 유틸
│   └── parsing_utils.py      # 파싱 유틸
├── tests/
│   ├── conftest.py           # pytest 설정
│   ├── test_date_utils.py
│   ├── test_calculation_engine.py
│   ├── test_billing_engine.py
│   ├── test_validation_engine.py
│   └── test_excel_engine.py
└── data/
    └── maintenance_billing.db  # SQLite DB (자동 생성)
```

## 문제 해결

### ModuleNotFoundError

```cmd
set PYTHONPATH=%PYTHONPATH%;C:\Users\user\claude-test
```

### Streamlit 실행 안됨

```cmd
pip install --upgrade streamlit
```

### DB 초기화 오류

data 폴더와 DB 파일 삭제 후 재초기화:

```cmd
rmdir /s data
python -c "from database.init_db import initialize_all; initialize_all()"
```
