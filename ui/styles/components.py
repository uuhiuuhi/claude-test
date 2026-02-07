"""Apple iOS 스타일 재사용 컴포넌트"""

import streamlit as st

# ===== 상태 도트 배지 설정 =====
STATUS_BADGE_CONFIG = {
    'draft':     {'color': '#8E8E93', 'label': '초안'},
    'confirmed': {'color': '#34C759', 'label': '확정'},
    'locked':    {'color': '#007AFF', 'label': '잠금'},
    'cancelled': {'color': '#FF3B30', 'label': '취소'},
}

# ===== 경고 pill 배지 설정 =====
ALERT_BADGE_CONFIG = {
    'error':   {'bg': 'rgba(255, 59, 48, 0.15)',  'text': '#FF3B30', 'label': '오류'},
    'warning': {'bg': 'rgba(255, 149, 0, 0.15)',   'text': '#FF9500', 'label': '경고'},
    'info':    {'bg': 'rgba(0, 122, 255, 0.15)',    'text': '#007AFF', 'label': '정보'},
    'success': {'bg': 'rgba(52, 199, 89, 0.15)',    'text': '#34C759', 'label': '성공'},
}

# ===== 경고 레벨별 스타일 =====
ALERT_STYLES = {
    'success': {'bg': 'rgba(52, 199, 89, 0.1)',  'border': '#34C759'},
    'warning': {'bg': 'rgba(255, 149, 0, 0.1)',   'border': '#FF9500'},
    'error':   {'bg': 'rgba(255, 59, 48, 0.1)',   'border': '#FF3B30'},
    'info':    {'bg': 'rgba(0, 122, 255, 0.1)',    'border': '#007AFF'},
}


def status_badge(status: str) -> str:
    """상태 도트 배지 HTML 반환"""
    config = STATUS_BADGE_CONFIG.get(status, {'color': '#8E8E93', 'label': status})
    return (
        f'<span style="display:inline-flex;align-items:center;gap:6px;">'
        f'<span style="width:10px;height:10px;border-radius:50%;'
        f'background-color:{config["color"]};display:inline-block;"></span>'
        f'<span style="font-size:14px;font-weight:500;color:#1C1C1E;">'
        f'{config["label"]}</span></span>'
    )


def status_label(status: str) -> str:
    """상태 텍스트 라벨 반환 (expander 제목용)"""
    config = STATUS_BADGE_CONFIG.get(status, {'label': status})
    return config['label']


def alert_badge(level: str) -> str:
    """경고 레벨 pill 배지 HTML 반환"""
    config = ALERT_BADGE_CONFIG.get(level, ALERT_BADGE_CONFIG['info'])
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:20px;'
        f'background-color:{config["bg"]};color:{config["text"]};'
        f'font-size:12px;font-weight:600;">{config["label"]}</span>'
    )


def render_status_badge(status: str):
    """상태 도트 배지 렌더링"""
    st.markdown(status_badge(status), unsafe_allow_html=True)


def render_alert_badge(level: str):
    """경고 pill 배지 렌더링"""
    st.markdown(alert_badge(level), unsafe_allow_html=True)


def warning_list_item(level: str, code: str, company_name: str, message: str):
    """경고 목록 항목 렌더링 (배지 + 좌측 색상 테두리)"""
    style = ALERT_STYLES.get(level, ALERT_STYLES['info'])
    badge = alert_badge(level)
    code_text = f"[{code}] " if code else ""

    st.markdown(
        f'<div style="display:flex;align-items:flex-start;gap:10px;'
        f'padding:12px 16px;border-radius:12px;'
        f'border-left:4px solid {style["border"]};'
        f'background-color:{style["bg"]};margin:6px 0;">'
        f'{badge}'
        f'<div style="flex:1;">'
        f'<span style="font-weight:600;font-size:14px;color:#1C1C1E;">'
        f'{code_text}{company_name}</span><br/>'
        f'<span style="font-size:13px;color:#3C3C43;">{message}</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )


def styled_alert(message: str, level: str = 'info'):
    """스타일 알림 박스 렌더링"""
    style = ALERT_STYLES.get(level, ALERT_STYLES['info'])
    badge = alert_badge(level)

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;'
        f'padding:14px 16px;border-radius:12px;'
        f'border-left:4px solid {style["border"]};'
        f'background-color:{style["bg"]};margin:8px 0;">'
        f'{badge}'
        f'<span style="font-size:15px;color:#1C1C1E;">{message}</span>'
        f'</div>',
        unsafe_allow_html=True
    )


def styled_card(content_html: str):
    """카드 컨테이너 렌더링"""
    st.markdown(
        f'<div style="background:#FFFFFF;border-radius:16px;'
        f'border:1px solid #E5E5EA;box-shadow:0 1px 3px rgba(0,0,0,0.08);'
        f'padding:20px;margin:12px 0;transition:all 0.2s ease;">'
        f'{content_html}</div>',
        unsafe_allow_html=True
    )


def section_header(title: str, subtitle: str = None):
    """섹션 헤더 렌더링"""
    sub_html = (
        f'<p style="font-size:13px;color:#8E8E93;margin:4px 0 0 0;">'
        f'{subtitle}</p>'
    ) if subtitle else ''

    st.markdown(
        f'<div style="margin:16px 0 12px 0;">'
        f'<h3 style="margin:0;padding:0;">{title}</h3>'
        f'{sub_html}</div>',
        unsafe_allow_html=True
    )
