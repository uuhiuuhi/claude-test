"""파싱 유틸리티 - 엑셀 데이터 파싱"""

import re
from datetime import date, datetime
from typing import Optional, List, Tuple, Any
from decimal import Decimal, InvalidOperation


def parse_date(value: Any) -> Tuple[Optional[date], str]:
    """날짜 파싱 (다양한 형식 지원)

    Returns:
        (parsed_date, error_message)
    """
    if value is None:
        return (None, "")

    if isinstance(value, date):
        return (value, "")

    if isinstance(value, datetime):
        return (value.date(), "")

    text = str(value).strip()
    if not text:
        return (None, "")

    # 다양한 날짜 형식 시도
    formats = [
        '%Y-%m-%d',
        '%Y.%m.%d',
        '%Y/%m/%d',
        '%Y%m%d',
        '%d-%m-%Y',
        '%d.%m.%Y',
        '%d/%m/%Y',
    ]

    for fmt in formats:
        try:
            return (datetime.strptime(text, fmt).date(), "")
        except ValueError:
            continue

    return (None, f"날짜 파싱 실패: {text}")


def parse_amount(value: Any) -> Tuple[Optional[Decimal], str, Optional[str]]:
    """금액 파싱 (수식 결과 + 원본 보존)

    Returns:
        (amount, error_message, original_formula)
    """
    if value is None:
        return (None, "", None)

    # 수식인 경우 (openpyxl에서 값은 이미 계산됨)
    original_formula = None

    if isinstance(value, (int, float)):
        try:
            return (Decimal(str(value)), "", original_formula)
        except InvalidOperation:
            return (None, f"금액 변환 실패: {value}", original_formula)

    text = str(value).strip()
    if not text:
        return (None, "", None)

    # 쉼표 제거, 통화 기호 제거
    cleaned = re.sub(r'[,원₩\s]', '', text)

    try:
        return (Decimal(cleaned), "", original_formula)
    except InvalidOperation:
        return (None, f"금액 파싱 실패: {text}", None)


def parse_boolean(value: Any) -> bool:
    """불리언 파싱 (자동갱신 등)"""
    if value is None:
        return True  # 사내 표준: 자동갱신 기본값 = True

    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    true_values = ['true', 'yes', 'y', '1', 'o', 'ㅇ', '예', '자동', '자동갱신']
    false_values = ['false', 'no', 'n', '0', 'x', 'ㅌ', '아니오', '수동', '해지']

    if text in true_values:
        return True
    if text in false_values:
        return False

    return True  # 기본값


def parse_warehouse_code(value: Any) -> Tuple[Optional[str], str]:
    """창고 코드 파싱

    Returns:
        (code, error_message)
    """
    if value is None:
        return (None, "창고 코드 없음")

    text = str(value).strip()
    if not text:
        return (None, "창고 코드 없음")

    # 숫자만 추출
    code = re.sub(r'[^0-9]', '', text)
    if code:
        return (code, "")

    return (text, "")


def parse_purchase_dates(value: Any) -> Tuple[List[date], str]:
    """매입일자 파싱 (다건 허용)

    예: "2024-01-15, 2024-01-20" 또는 "15일, 20일"

    Returns:
        (dates_list, error_message)
    """
    if value is None:
        return ([], "")

    if isinstance(value, date):
        return ([value], "")

    if isinstance(value, datetime):
        return ([value.date()], "")

    text = str(value).strip()
    if not text:
        return ([], "")

    dates = []
    errors = []

    # 쉼표 또는 슬래시로 분리
    parts = re.split(r'[,/]', text)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        parsed, error = parse_date(part)
        if parsed:
            dates.append(parsed)
        elif error:
            errors.append(error)

    error_msg = "; ".join(errors) if errors else ""
    return (dates, error_msg)


def parse_notes_for_rules(notes: str) -> dict:
    """특이사항에서 발행/메일/PO/첨부 규칙 추출

    Returns:
        {
            'requires_po': bool,
            'po_number': str or None,
            'requires_attachment': bool,
            'attachment_note': str or None,
            'email_recipients': List[str],
            'is_reverse_billing': bool,
            'other_rules': List[str],
            'original_text': str
        }
    """
    result = {
        'requires_po': False,
        'po_number': None,
        'requires_attachment': False,
        'attachment_note': None,
        'email_recipients': [],
        'is_reverse_billing': False,
        'other_rules': [],
        'original_text': notes or ""
    }

    if not notes:
        return result

    text = notes.strip()

    # PO 번호 필수
    if 'PO' in text.upper() or '피오' in text:
        result['requires_po'] = True
        # PO 번호 추출 시도
        po_match = re.search(r'PO[:#\s]*([A-Za-z0-9-]+)', text, re.IGNORECASE)
        if po_match:
            result['po_number'] = po_match.group(1)

    # 첨부 필수
    if '첨부' in text:
        result['requires_attachment'] = True
        # 첨부 관련 내용 추출
        attach_match = re.search(r'첨부[:\s]*(.+?)(?:[,.]|$)', text)
        if attach_match:
            result['attachment_note'] = attach_match.group(1).strip()

    # 이메일 수신자
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    result['email_recipients'] = emails

    # 역발행
    if any(kw in text for kw in ['역발행', '역발급', '상대발행']):
        result['is_reverse_billing'] = True

    return result


def extract_period_from_item_name(item_name: str) -> Tuple[Optional[int], Optional[str]]:
    """품목명에서 기간 정보 추출 (다개월 선청구 대응)

    예: "유지보수비(1~3월)", "2024년 상반기 유지보수"

    Returns:
        (months_count, period_description)
    """
    if not item_name:
        return (None, None)

    text = item_name.strip()

    # N~M월 패턴
    range_match = re.search(r'(\d+)~(\d+)월', text)
    if range_match:
        start_month = int(range_match.group(1))
        end_month = int(range_match.group(2))
        months = end_month - start_month + 1
        return (months, f"{start_month}~{end_month}월")

    # 상반기/하반기
    if '상반기' in text:
        return (6, "상반기")
    if '하반기' in text:
        return (6, "하반기")

    # N개월 패턴
    months_match = re.search(r'(\d+)개월', text)
    if months_match:
        return (int(months_match.group(1)), f"{months_match.group(1)}개월")

    return (None, None)


def is_total_row(row_data: dict) -> bool:
    """합계 행인지 확인"""
    # 업체명이나 품목명에 '합계' 포함
    company_name = str(row_data.get('company_name', '')).strip()
    item_name = str(row_data.get('item_name', '')).strip()

    if '합계' in company_name or '합계' in item_name:
        return True

    # 코드 없이 금액만 있는 경우
    if not row_data.get('company_code') and row_data.get('billing_amount'):
        return True

    return False
