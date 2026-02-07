"""Apple iOS 스타일 전역 CSS 정의 및 주입"""

import streamlit as st

GLOBAL_CSS = """
/* ===== Typography ===== */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text',
                 'Helvetica Neue', 'Apple SD Gothic Neo', sans-serif;
}
h1 {
    font-size: 34px !important;
    font-weight: 600 !important;
    letter-spacing: -0.5px !important;
    color: #1C1C1E !important;
}
h2 {
    font-size: 22px !important;
    font-weight: 600 !important;
    letter-spacing: -0.3px !important;
    color: #1C1C1E !important;
}
h3 {
    font-size: 17px !important;
    font-weight: 600 !important;
    color: #1C1C1E !important;
}

/* ===== Sidebar ===== */
[data-testid="stSidebar"] {
    background-color: #F2F2F7 !important;
    border-right: 1px solid #E5E5EA !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdown"] p {
    color: #8E8E93;
    font-size: 13px;
}
[data-testid="stSidebar"] .stRadio > div {
    gap: 2px !important;
}
[data-testid="stSidebar"] .stRadio label {
    padding: 10px 16px !important;
    border-radius: 10px !important;
    margin: 2px 0 !important;
    transition: background-color 0.2s ease !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(0, 122, 255, 0.1) !important;
}
[data-testid="stSidebar"] .stRadio label[data-checked="true"] {
    background: rgba(0, 122, 255, 0.15) !important;
    color: #007AFF !important;
}

/* ===== Buttons ===== */
.stButton > button {
    border-radius: 10px !important;
    padding: 10px 24px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
    border: none !important;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    background-color: #007AFF !important;
    color: #FFFFFF !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
    background-color: #0056CC !important;
    box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3) !important;
}
.stButton > button[kind="secondary"],
.stButton > button[data-testid="baseButton-secondary"] {
    background-color: #E5E5EA !important;
    color: #1C1C1E !important;
}
.stButton > button[kind="secondary"]:hover,
.stButton > button[data-testid="baseButton-secondary"]:hover {
    background-color: #D1D1D6 !important;
}
.stDownloadButton > button {
    border-radius: 10px !important;
    padding: 10px 24px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}

/* ===== Input Fields ===== */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius: 10px !important;
    border: 1px solid #C7C7CC !important;
    padding: 12px !important;
    font-size: 15px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #007AFF !important;
    box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.2) !important;
}
.stSelectbox > div > div {
    border-radius: 10px !important;
}
.stDateInput > div > div > input {
    border-radius: 10px !important;
}

/* ===== Tabs ===== */
.stTabs [data-baseweb="tab-list"] {
    background-color: #F2F2F7 !important;
    padding: 4px !important;
    border-radius: 10px !important;
    gap: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    padding: 10px 20px !important;
    font-weight: 500 !important;
    height: auto !important;
}
.stTabs [aria-selected="true"] {
    background-color: #FFFFFF !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    display: none !important;
}
.stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

/* ===== Metrics ===== */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 16px 20px;
    border: 1px solid #E5E5EA;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
[data-testid="stMetric"] label {
    font-size: 13px !important;
    color: #8E8E93 !important;
    font-weight: 500 !important;
}
[data-testid="stMetricValue"] {
    font-size: 28px !important;
    font-weight: 600 !important;
    color: #1C1C1E !important;
}

/* ===== Alerts ===== */
[data-testid="stAlert"] {
    border-radius: 12px !important;
    padding: 14px 16px !important;
}

/* ===== Expanders ===== */
[data-testid="stExpander"] {
    border: 1px solid #E5E5EA !important;
    border-radius: 12px !important;
    background: #FFFFFF !important;
    margin: 6px 0 !important;
    overflow: hidden;
}
[data-testid="stExpander"] summary {
    padding: 14px 16px !important;
    font-weight: 500 !important;
}
[data-testid="stExpander"] summary:hover {
    background: #F2F2F7 !important;
}

/* ===== DataFrames ===== */
[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid #E5E5EA !important;
}

/* ===== Dividers ===== */
hr {
    border-color: #E5E5EA !important;
    margin: 16px 0 !important;
}

/* ===== Form Submit Button ===== */
[data-testid="stFormSubmitButton"] > button {
    border-radius: 10px !important;
    padding: 10px 24px !important;
    font-weight: 500 !important;
    background-color: #007AFF !important;
    color: #FFFFFF !important;
    border: none !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFormSubmitButton"] > button:hover {
    background-color: #0056CC !important;
    box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3) !important;
}

/* ===== File Uploader ===== */
[data-testid="stFileUploader"] {
    border-radius: 12px !important;
}
[data-testid="stFileUploader"] section {
    border-radius: 12px !important;
    border: 2px dashed #C7C7CC !important;
    padding: 20px !important;
}

/* ===== Checkbox ===== */
.stCheckbox label {
    font-weight: 400 !important;
}

/* ===== Spinner ===== */
.stSpinner > div {
    border-top-color: #007AFF !important;
}
"""


def inject_global_css():
    """전역 Apple iOS 스타일 CSS를 Streamlit에 주입"""
    st.markdown(f"<style>{GLOBAL_CSS}</style>", unsafe_allow_html=True)
