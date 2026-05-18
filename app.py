from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from docx import Document
except Exception:  # pragma: no cover
    Document = None

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


# ============================================================
# 기본 경로 / 앱 설정
# ============================================================

APP_ROOT = Path(__file__).resolve().parent
DATA_DIR = APP_ROOT / "data"
STORE_DIR = APP_ROOT / "storage"
DATA_DIR.mkdir(exist_ok=True)
STORE_DIR.mkdir(exist_ok=True)

APP_TITLE = "AIVLE 학습도우미"
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_WHITEPAPER_PATH = DATA_DIR / "aivle_kt_learning_whitepaper_2026.docx"
WHITEPAPER_META_PATH = STORE_DIR / "whitepaper_meta.json"
CONVERSATION_PATH = STORE_DIR / "conversations.json"
RESULT_PATH = STORE_DIR / "study_results.json"
WRONG_NOTE_PATH = STORE_DIR / "wrong_notes.json"
CALENDAR_PATH = STORE_DIR / "calendar_events.json"

MENU_OPTIONS = [
    "대시보드",
    "학습 질의",
    "예습·쪽지시험",
    "학습 분석·오답노트",
    "공고·캘린더",
    "커리큘럼",
    "내 학습 현황",
]

TOPIC_ALIASES = {
    "분석형 AI": ["분석형 AI", "데이터 분석", "머신러닝", "딥러닝", "모델", "예측", "분류", "회귀"],
    "생성형 AI": ["생성형 AI", "LLM", "프롬프트", "RAG", "LangChain", "이미지 모델", "언어 모델"],
    "Cloud": ["Cloud", "클라우드", "IT Infra", "Cloud Infra", "Cloud Native", "서버", "인프라"],
    "서비스 개발/제안": ["서비스 개발", "서비스 제안", "SW", "Web", "제안서", "기획", "프로젝트 관리"],
    "프로젝트 수행": ["미니프로젝트", "빅프로젝트", "MVP", "주제 선정", "발표", "현직자 코칭", "포트폴리오"],
    "출결·운영": ["출결", "지각", "조퇴", "외출", "공가", "수료", "에이블에듀", "체크인", "체크아웃"],
}

OFFICIAL_NOTICE_KEYWORDS = ["출결", "공가", "수료", "지원 자격", "자비부담금", "평가", "합격", "불합격", "최신", "공식", "일정"]

DEFAULT_CURRICULUM = [
    {"week": "1주", "period": "3.30~4.3", "topic": "입교식 + 분석형 AI", "kind": "수업", "note": "입교 오리엔테이션, 분석형 AI 시작"},
    {"week": "2주", "period": "4.6~4.10", "topic": "분석형 AI", "kind": "수업", "note": "데이터 분석·머신러닝 기초"},
    {"week": "3주", "period": "4.13~4.17", "topic": "분석형 AI + 분석형 AI 미니프로젝트", "kind": "프로젝트", "note": "분석형 AI 실습 산출물"},
    {"week": "4주", "period": "4.20~4.24", "topic": "분석형 AI 미니프로젝트 + 생성형 AI", "kind": "프로젝트", "note": "생성형 AI 전환"},
    {"week": "5주", "period": "4.27~5.1", "topic": "생성형 AI 미니프로젝트 + 생성형 AI", "kind": "프로젝트", "note": "5.1 휴강"},
    {"week": "6주", "period": "5.4~5.8", "topic": "생성형 AI", "kind": "수업", "note": "5.4~5.5 휴강"},
    {"week": "7주", "period": "5.11~5.15", "topic": "생성형 AI 미니프로젝트", "kind": "프로젝트", "note": "기타교과 포함"},
    {"week": "8주", "period": "5.18~5.22", "topic": "서비스 개발/제안 + 미니프로젝트", "kind": "프로젝트", "note": "AI/DX 트랙별 산출물"},
    {"week": "9주", "period": "5.25~5.29", "topic": "서비스 개발/제안 미니프로젝트", "kind": "프로젝트", "note": "대체휴일 포함"},
    {"week": "10주", "period": "6.1~6.5", "topic": "서비스 개발/제안", "kind": "수업", "note": "서비스 구현 또는 제안 전략"},
    {"week": "11주", "period": "6.8~6.12", "topic": "서비스 개발/제안 미니프로젝트", "kind": "프로젝트", "note": "산출물 개선"},
    {"week": "12주", "period": "6.15~6.19", "topic": "Cloud", "kind": "수업", "note": "IT Infra, Cloud Infra"},
    {"week": "13주", "period": "6.22~6.26", "topic": "Cloud + Cloud 미니프로젝트", "kind": "프로젝트", "note": "AIVLE DAY 2차"},
    {"week": "14~22주", "period": "6.29~8.28", "topic": "빅프로젝트", "kind": "프로젝트", "note": "주제 선정, 현직자 코칭, 구현, 발표"},
    {"week": "23주", "period": "8.31~9.4", "topic": "취업지원 + 수료식", "kind": "취업", "note": "모의면접, 취업플랫폼, 수료식"},
]

QUICK_QUESTION_GROUPS = {
    "과정 이해": [
        "AI 개발자 트랙과 DX 컨설턴트 트랙의 차이를 정리해줘",
        "에이블스쿨 9기 전체 학습 흐름을 요약해줘",
        "비전공자가 먼저 확인해야 할 내용을 알려줘",
    ],
    "학습 전략": [
        "분석형 AI 예습은 무엇부터 하면 돼?",
        "생성형 AI 수업 전에 알아야 할 핵심 개념을 정리해줘",
        "Cloud 파트에서 어려워질 수 있는 부분을 알려줘",
    ],
    "프로젝트": [
        "미니프로젝트를 시작할 때 가장 먼저 해야 할 일을 알려줘",
        "빅프로젝트 주제 선정 기준을 정리해줘",
        "포트폴리오에 프로젝트를 정리할 때 주의할 점을 알려줘",
    ],
    "운영·일정": [
        "출결 기준에서 지각과 조퇴 기준을 알려줘",
        "수료 기준을 백서 기준으로 설명해줘",
        "에이블에듀에서 자주 쓰는 메뉴를 정리해줘",
    ],
}

LEVEL_GUIDE = {
    "초급": ["핵심 용어를 다시 정리", "예습 자료를 10분 단위로 나누어 재학습", "오답 문항을 같은 날 다시 풀기"],
    "중급": ["틀린 주제 중심으로 짧은 실습 진행", "개념을 미니프로젝트 산출물과 연결", "스터디에서 설명자 역할 수행"],
    "고급": ["심화 자료와 공식 문서 확인", "동료 질문 답변으로 설명력 강화", "프로젝트 적용 아이디어 도출"],
}

st.set_page_config(page_title=APP_TITLE, page_icon="📘", layout="wide", initial_sidebar_state="expanded")


# ============================================================
# 디자인: 밝은 학습 플랫폼 UI + Pretendard
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css');

    :root {
        --bg: #f4f7fb;
        --surface: #ffffff;
        --surface-soft: #f8fafc;
        --line: #dbe3ef;
        --text: #111827;
        --muted: #64748b;
        --brand: #2563eb;
        --brand-2: #0ea5e9;
        --brand-soft: #eff6ff;
        --green-soft: #ecfdf5;
        --orange-soft: #fff7ed;
        --shadow: 0 14px 34px rgba(15, 23, 42, .08);
    }

    html, body, [class*="css"], .stApp, .stMarkdown, .stTextInput, .stTextArea,
    .stSelectbox, .stButton, .stDataFrame, .stChatMessage, input, textarea, button {
        font-family: 'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }

    .stApp {
        background:
            radial-gradient(circle at 0% 0%, rgba(37, 99, 235, .10), transparent 32%),
            linear-gradient(180deg, #f8fbff 0%, #eef4fb 100%) !important;
        color: var(--text);
    }

    .main .block-container {
        max-width: 1240px;
        padding-top: 1.25rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3, h4, h5, h6,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        color: #111827 !important;
        letter-spacing: -0.035em;
        font-weight: 850 !important;
    }

    p, li, label, .stMarkdown, .stCaption, .stText {
        color: #1f2937;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f3f7fc 100%) !important;
        border-right: 1px solid var(--line);
        min-width: 18rem;
    }
    section[data-testid="stSidebar"] * { color: #111827 !important; }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #111827 !important; }

    [data-testid="stToolbar"], [data-testid="stStatusWidget"], [data-testid="stDeployButton"], .stDeployButton {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }
    header[data-testid="stHeader"] { background: transparent !important; }

    .app-hero {
        background: linear-gradient(135deg, #ffffff 0%, #eef6ff 56%, #e0f2fe 100%);
        border: 1px solid rgba(37, 99, 235, .15);
        border-radius: 30px;
        box-shadow: var(--shadow);
        padding: 30px 34px;
        margin-bottom: 20px;
        position: relative;
        overflow: hidden;
    }
    .app-hero::after {
        content: "";
        position: absolute;
        right: -70px;
        top: -80px;
        width: 230px;
        height: 230px;
        border-radius: 999px;
        background: rgba(37, 99, 235, .12);
    }
    .hero-kicker {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        color: #1d4ed8;
        background: #dbeafe;
        border: 1px solid #bfdbfe;
        padding: 6px 11px;
        border-radius: 999px;
        font-size: .82rem;
        font-weight: 800;
        margin-bottom: 10px;
    }
    .app-hero h1 {
        margin: 0 0 9px 0;
        font-size: 2.05rem;
        line-height: 1.2;
        color: #0f172a !important;
    }
    .app-hero p {
        margin: 0;
        color: #475569;
        font-size: 1.02rem;
        line-height: 1.65;
        max-width: 780px;
    }

    .section-title {
        color: #111827 !important;
        font-size: 1.22rem;
        font-weight: 900;
        margin: 20px 0 10px 0;
        letter-spacing: -0.03em;
    }
    .section-sub {
        color: var(--muted);
        margin-top: -6px;
        margin-bottom: 12px;
        font-size: .92rem;
    }

    .stat-card, div[data-testid="stMetric"] {
        background: rgba(255,255,255,.96) !important;
        border: 1px solid var(--line) !important;
        border-radius: 22px !important;
        box-shadow: 0 10px 26px rgba(15,23,42,.06) !important;
        padding: 15px 16px !important;
    }
    div[data-testid="stMetric"] * { color: #111827 !important; }

    .learn-card {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 20px;
        min-height: 166px;
        box-shadow: 0 10px 24px rgba(15,23,42,.06);
        transition: all .15s ease;
    }
    .learn-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 18px 36px rgba(15,23,42,.10);
        border-color: rgba(37,99,235,.35);
    }
    .learn-card .badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        font-weight: 850;
        font-size: .78rem;
        color: #1d4ed8;
        background: #dbeafe;
        margin-bottom: 12px;
    }
    .learn-card h3 { font-size: 1.07rem; margin: 0 0 8px 0; color: #111827 !important; }
    .learn-card p { margin: 0; color: #64748b; line-height: 1.55; font-size: .94rem; }

    .routine-strip {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin: 12px 0 20px 0;
    }
    .routine-item {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 15px;
        min-height: 110px;
        box-shadow: 0 8px 22px rgba(15,23,42,.05);
    }
    .routine-item b { display:block; color: #111827; margin-bottom: 6px; }
    .routine-item span { color: #2563eb; font-size: .78rem; font-weight: 900; }
    .routine-item p { color: #64748b; font-size: .88rem; line-height: 1.45; margin: 6px 0 0 0; }

    .info-panel {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: 18px 20px;
        box-shadow: 0 8px 22px rgba(15,23,42,.05);
        margin-bottom: 14px;
    }
    .source-box {
        background: #f8fafc;
        border: 1px dashed #cbd5e1;
        border-radius: 16px;
        padding: 14px;
        margin: 8px 0;
    }
    .source-box b { color: #111827; }
    .source-box p { color: #475569; }

    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 12px;
        border-radius: 22px;
        padding: 15px 13px;
        background: linear-gradient(135deg, #eff6ff, #ffffff);
        border: 1px solid #bfdbfe;
        box-shadow: 0 10px 24px rgba(37,99,235,.08);
        margin: 4px 0 14px 0;
    }
    .brand-mark {
        width: 43px;
        height: 43px;
        display: grid;
        place-items: center;
        border-radius: 15px;
        color: white !important;
        background: linear-gradient(135deg, #2563eb, #0ea5e9);
        font-weight: 950;
    }
    .brand-title { color: #0f172a !important; font-size: 1.05rem; font-weight: 950; line-height: 1.2; }
    .brand-sub { color: #2563eb !important; font-size: .8rem; font-weight: 800; margin-top: 2px; }
    .current-pill {
        border-radius: 999px;
        padding: 9px 12px;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #1d4ed8 !important;
        font-weight: 800;
        font-size: .86rem;
        margin: 8px 0 10px 0;
    }
    .side-label {
        color: #64748b !important;
        font-size: .80rem;
        font-weight: 900;
        letter-spacing: .02em;
        margin: 12px 0 6px 0;
    }

    div.stButton > button {
        border-radius: 14px !important;
        border: 1px solid rgba(37,99,235,.20) !important;
        background: linear-gradient(180deg, #2563eb, #1d4ed8) !important;
        color: #ffffff !important;
        font-weight: 850 !important;
        min-height: 2.8rem;
        box-shadow: 0 8px 18px rgba(37,99,235,.18);
    }
    div.stButton > button:hover {
        transform: translateY(-1px);
        border-color: #60a5fa !important;
        box-shadow: 0 12px 24px rgba(37,99,235,.25);
    }
    div.stButton > button[kind="secondary"] {
        background: #ffffff !important;
        color: #1d4ed8 !important;
    }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 999px;
        padding: 8px 14px;
        color: #111827;
    }
    .stTabs [aria-selected="true"] {
        background: #dbeafe !important;
        color: #1d4ed8 !important;
        border-color: #93c5fd !important;
    }

    [data-testid="stChatMessage"] {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 10px 12px;
        box-shadow: 0 6px 18px rgba(15,23,42,.04);
    }

    .notice-box {
        border-left: 5px solid #2563eb;
        background: #eff6ff;
        border-radius: 16px;
        padding: 12px 14px;
        color: #1e3a8a;
        margin: 10px 0 14px 0;
    }

    @media (max-width: 980px) {
        .routine-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 640px) {
        .routine-strip { grid-template-columns: 1fr; }
        .app-hero { padding: 24px 20px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 데이터 모델 / 저장소
# ============================================================

@dataclass
class SearchHit:
    index: int
    score: float
    title: str
    text: str


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_config_value(name: str, default: Optional[str] = None) -> Optional[str]:
    value = None
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    return value or os.getenv(name) or default


def get_api_key() -> Optional[str]:
    return get_config_value("OPENAI_API_KEY")


def get_login_credentials() -> Tuple[str, str]:
    return (
        get_config_value("APP_LOGIN_ID", "admin") or "admin",
        get_config_value("APP_LOGIN_PASSWORD", "aivle2026") or "aivle2026",
    )


def get_whitepaper_meta() -> Dict[str, Any]:
    default = {
        "display_name": DEFAULT_WHITEPAPER_PATH.name,
        "storage_path": str(DEFAULT_WHITEPAPER_PATH),
        "updated_at": "",
        "size_bytes": DEFAULT_WHITEPAPER_PATH.stat().st_size if DEFAULT_WHITEPAPER_PATH.exists() else 0,
    }
    meta = read_json(WHITEPAPER_META_PATH, default)
    if not isinstance(meta, dict):
        return default
    merged = {**default, **meta}
    if not Path(str(merged.get("storage_path", ""))).exists() and DEFAULT_WHITEPAPER_PATH.exists():
        merged["storage_path"] = str(DEFAULT_WHITEPAPER_PATH)
        merged["display_name"] = DEFAULT_WHITEPAPER_PATH.name
    return merged


def get_whitepaper_path() -> Path:
    meta = get_whitepaper_meta()
    path = Path(str(meta.get("storage_path", DEFAULT_WHITEPAPER_PATH)))
    if path.exists():
        return path
    return DEFAULT_WHITEPAPER_PATH


def save_whitepaper_meta(display_name: str, path: Path, size_bytes: int) -> None:
    write_json(
        WHITEPAPER_META_PATH,
        {
            "display_name": display_name,
            "storage_path": str(path),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "size_bytes": size_bytes,
        },
    )


def init_state() -> None:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("login_error", "")
    st.session_state.setdefault("active_page", "대시보드")
    st.session_state.setdefault("nav_version", 0)
    st.session_state.setdefault("last_upload_sig", "")
    if st.session_state["active_page"] not in MENU_OPTIONS:
        st.session_state["active_page"] = "대시보드"


def navigate(page: str) -> None:
    if page not in MENU_OPTIONS:
        page = "대시보드"
    st.session_state["active_page"] = page
    st.session_state["nav_version"] = int(st.session_state.get("nav_version", 0)) + 1
    st.rerun()


def authenticate(login_id: str, login_password: str) -> bool:
    expected_id, expected_pw = get_login_credentials()
    return hmac.compare_digest(login_id, expected_id) and hmac.compare_digest(login_password, expected_pw)


# ============================================================
# 문서 파싱 / 검색 인덱스
# ============================================================


def parse_docx(path: Path) -> str:
    if Document is None:
        return ""
    doc = Document(str(path))
    lines: List[str] = []

    # 문단과 표를 문서에 나타난 순서 그대로 읽습니다.
    # doc.paragraphs + doc.tables를 따로 읽으면 표가 뒤로 밀려 검색 정확도가 떨어집니다.
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    for child in doc.element.body.iterchildren():
        if isinstance(child, CT_P):
            text = Paragraph(child, doc).text.strip()
            if text:
                lines.append(text)
        elif isinstance(child, CT_Tbl):
            table = Table(child, doc)
            for row in table.rows:
                cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                cells = [cell for cell in cells if cell]
                if cells:
                    lines.append(" | ".join(cells))
    return "\n".join(lines)


def parse_pdf(path: Path) -> str:
    if PdfReader is None:
        return ""
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def parse_text_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return parse_docx(path)
    if suffix == ".pdf":
        return parse_pdf(path)
    return path.read_text(encoding="utf-8", errors="ignore")


def normalize_text(text: str) -> str:
    text = text.replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_chunks(text: str, size: int = 620, overlap: int = 70) -> List[Dict[str, str]]:
    clean = normalize_text(text)
    if not clean:
        return []
    # DOCX에서 추출한 표와 문단은 대부분 한 줄 단위로 의미가 나뉩니다.
    # 그래서 한 줄을 기본 단위로 묶어 검색 청크가 특정 주제에 더 가깝게 잡히도록 합니다.
    paragraphs = [p.strip() for p in re.split(r"\n+", clean) if p.strip()]
    chunks: List[Dict[str, str]] = []
    title = "백서"
    buf = ""
    for para in paragraphs:
        if re.match(r"^(Ⅰ|Ⅱ|Ⅲ|Ⅳ|Ⅴ|Ⅵ|Ⅶ|Ⅷ|Ⅸ|Ⅹ)\.", para) or re.match(r"^\d+\.\s", para):
            title = para[:70]
        if len(buf) + len(para) + 1 <= size:
            buf = f"{buf}\n{para}".strip()
        else:
            if buf:
                chunks.append({"title": title, "text": buf})
            # 줄 단위 검색 정확도를 위해 새 청크에는 앞 청크 일부를 짧게만 겹칩니다.
            tail = buf[-overlap:] if overlap and buf else ""
            buf = f"{tail}\n{para}".strip()
    if buf:
        chunks.append({"title": title, "text": buf})
    return chunks


@st.cache_resource(show_spinner=False)
def build_index(path_string: str, modified_at: float, file_size: int) -> Dict[str, Any]:
    path = Path(path_string)
    raw_text = parse_text_file(path)
    chunks = split_into_chunks(raw_text)
    if not chunks:
        return {"text": raw_text, "chunks": [], "vectorizer": None, "matrix": None}
    texts = [chunk["text"] for chunk in chunks]
    try:
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), max_features=30000)
        matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return {"text": raw_text, "chunks": chunks, "vectorizer": None, "matrix": None}
    return {"text": raw_text, "chunks": chunks, "vectorizer": vectorizer, "matrix": matrix}


def load_index() -> Optional[Dict[str, Any]]:
    path = get_whitepaper_path()
    if not path.exists():
        return None
    stat = path.stat()
    return build_index(str(path), stat.st_mtime, stat.st_size)


def search_whitepaper(query: str, k: int = 6) -> List[SearchHit]:
    index = load_index()
    if not index or not index.get("chunks"):
        return []
    chunks = index["chunks"]
    vectorizer = index.get("vectorizer")
    matrix = index.get("matrix")
    if vectorizer is None or matrix is None:
        return [SearchHit(i, 0.0, chunk["title"], chunk["text"]) for i, chunk in enumerate(chunks[:k])]
    query_vector = vectorizer.transform([query])
    base_scores = cosine_similarity(query_vector, matrix).ravel()

    # TF-IDF 점수에 사용자가 입력한 핵심 단어 직접 포함 여부를 보정합니다.
    # 한국어 문서는 띄어쓰기와 표 추출 상태에 따라 순수 TF-IDF만으로는 원하는 행이 밀릴 수 있습니다.
    tokens = [t for t in re.findall(r"[가-힣A-Za-z0-9]+", query) if len(t) >= 2]
    adjusted: List[Tuple[float, int]] = []
    for idx, chunk in enumerate(chunks):
        blob = f"{chunk['title']} {chunk['text']}".lower()
        token_hits = sum(1 for token in tokens if token.lower() in blob)
        exact_bonus = 0.10 if query.replace(" ", "") in blob.replace(" ", "") else 0.0
        title_bonus = sum(1 for token in tokens if token.lower() in chunk['title'].lower()) * 0.035
        score = float(base_scores[idx]) + token_hits * 0.035 + exact_bonus + title_bonus
        adjusted.append((score, idx))

    ranked = sorted(adjusted, key=lambda item: item[0], reverse=True)[:k]
    hits = []
    for score, idx in ranked:
        if score <= 0 and hits:
            continue
        chunk = chunks[idx]
        hits.append(SearchHit(index=idx, score=float(score), title=chunk["title"], text=chunk["text"]))
    return hits


# ============================================================
# LLM / 학습 기능
# ============================================================


def get_client() -> Optional[Any]:
    key = get_api_key()
    if not key or OpenAI is None:
        return None
    return OpenAI(api_key=key)


def ask_llm(system_prompt: str, user_prompt: str, temperature: float = 0.15) -> Optional[str]:
    client = get_client()
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return None


def make_context(hits: List[SearchHit]) -> str:
    lines = []
    for i, hit in enumerate(hits, start=1):
        lines.append(f"[근거 {i}] 제목: {hit.title}\n내용:\n{hit.text}")
    return "\n\n---\n\n".join(lines)


def official_notice_needed(question: str) -> bool:
    return any(keyword in question for keyword in OFFICIAL_NOTICE_KEYWORDS)


def fallback_answer(question: str, hits: List[SearchHit]) -> str:
    if not hits:
        return "백서에서 직접 확인할 수 있는 근거를 찾지 못했습니다. 질문 표현을 더 구체화하거나 학습 자료를 다시 업로드해 주세요."
    context = hits[0].text[:900]
    notice = "\n\n**주의사항**\n- 일정, 출결, 수료, 지원 자격처럼 변동 가능한 항목은 최신 공식 공지와 담당자 안내를 최종 기준으로 확인해야 합니다." if official_notice_needed(question) else ""
    return (
        "### 핵심 답변\n"
        f"백서에서 가장 관련성이 높은 내용은 다음입니다.\n\n{context}\n\n"
        "### 바로 할 일\n"
        "1. 위 내용에서 본인에게 해당하는 항목을 먼저 표시합니다.\n"
        "2. 모르는 용어를 학습 질의에 다시 질문합니다.\n"
        "3. 예습·쪽지시험 메뉴에서 같은 주제로 이해도를 확인합니다."
        f"{notice}"
    )


def answer_from_whitepaper(question: str) -> Tuple[str, List[SearchHit], List[Dict[str, str]]]:
    hits = search_whitepaper(question, k=6)
    context = make_context(hits)
    system = (
        "당신은 KT AIVLE School 학습자를 돕는 백서 기반 학습 도우미입니다. "
        "반드시 제공된 백서 근거 안에서만 답변하고, 근거가 부족하면 부족하다고 말합니다. "
        "일정, 출결, 수료, 지원 자격, 평가처럼 변동 가능한 내용은 최신 공식 공지 확인이 필요하다고 안내합니다. "
        "답변은 한국어 마크다운으로 작성합니다."
    )
    user = f"""
[백서 근거]
{context}

[질문]
{question}

[답변 형식]
### 핵심 답변
### 상세 설명
### 바로 할 일
### 주의사항
"""
    answer = ask_llm(system, user, temperature=0.1) or fallback_answer(question, hits)
    return answer, hits, link_recommendations(question)


def extract_links(text: str) -> List[str]:
    raw = re.findall(r"(?:https?://)?(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}(?:/[A-Za-z0-9_./?=&%-]*)?", text)
    links: List[str] = []
    for item in raw:
        url = item if item.startswith("http") else "https://" + item
        if url not in links:
            links.append(url)
    return links


def link_recommendations(question: str) -> List[Dict[str, str]]:
    index = load_index()
    source_text = index.get("text", "") if index else ""
    base = [
        {"name": "KT AIVLE School 공식 홈페이지", "url": "https://aivle.kt.co.kr", "use": "모집·트랙·공식 안내 확인"},
        {"name": "AIVLE-EDU", "url": "https://aivle.edu.kt.co.kr", "use": "강의·출결·과제·커뮤니티 확인"},
        {"name": "고용24", "url": "https://www.work24.go.kr", "use": "K-DT 수강신청·국민내일배움카드 확인"},
    ]
    for url in extract_links(source_text):
        if not any(item["url"] == url for item in base):
            base.append({"name": url.replace("https://", ""), "url": url, "use": "백서에서 추출된 참고 링크"})
    tokens = re.findall(r"[가-힣A-Za-z0-9]+", question.lower())
    scored = []
    for row in base:
        blob = f"{row['name']} {row['url']} {row['use']}".lower()
        score = sum(1 for token in tokens if token and token in blob)
        scored.append((score, row))
    return [row for _, row in sorted(scored, key=lambda x: x[0], reverse=True)[:5]]


def generate_prep_material(week: str, topic: str, minutes: int) -> Tuple[str, List[SearchHit]]:
    query = f"{week} {topic} {' '.join(TOPIC_ALIASES.get(topic, []))}"
    hits = search_whitepaper(query, k=6)
    context = make_context(hits)
    system = "백서 근거로 수업 전 예습 자료를 만드는 학습 코치입니다. 근거 밖 추측은 하지 않습니다."
    user = f"""
[백서 근거]
{context}

[조건]
- 주차: {week}
- 주제: {topic}
- 예습 가능 시간: {minutes}분

[형식]
### 오늘의 예습 목표
### 핵심 개념 5개
### {minutes}분 예습 순서
### 수업 전 체크 질문
### 헷갈리기 쉬운 부분
"""
    fallback = (
        f"### 오늘의 예습 목표\n{topic}의 핵심 용어와 수업 흐름을 미리 확인합니다.\n\n"
        "### 핵심 개념 5개\n"
        + "\n".join([f"- {word}" for word in TOPIC_ALIASES.get(topic, [topic])[:5]])
        + f"\n\n### {minutes}분 예습 순서\n- 10분: 용어 훑기\n- 10분: 백서 관련 내용 읽기\n- 10분: 질문 3개 만들기\n\n"
        "### 수업 전 체크 질문\n- 이 주제가 프로젝트 산출물과 어떻게 연결되는가?\n- 내가 모르는 용어는 무엇인가?\n\n"
        "### 헷갈리기 쉬운 부분\n- 세부 일정과 운영 기준은 기수별로 달라질 수 있으므로 공식 공지를 확인해야 합니다."
    )
    return ask_llm(system, user, temperature=0.2) or fallback, hits


def fallback_quiz(topic: str) -> List[Dict[str, Any]]:
    aliases = TOPIC_ALIASES.get(topic, [topic])
    return [
        {
            "topic": topic,
            "question": f"{topic} 예습에서 가장 먼저 확인할 항목은 무엇인가?",
            "choices": ["핵심 용어", "무관한 후기", "임의의 일정", "확정되지 않은 평가 기준"],
            "answer_index": 0,
            "explanation": "수업 전에는 핵심 용어와 학습 흐름을 먼저 확인해야 합니다.",
        },
        {
            "topic": topic,
            "question": "백서 기반 답변에서 가장 중요한 태도는 무엇인가?",
            "choices": ["근거 없는 추측", "백서 근거 확인", "결과 보장", "일정 단정"],
            "answer_index": 1,
            "explanation": "백서에 있는 근거를 기준으로 답변해야 합니다.",
        },
        {
            "topic": topic,
            "question": f"{aliases[0]} 학습 후 이해도를 확인하는 데 적절한 기능은?",
            "choices": ["쪽지시험", "파일 삭제", "로그아웃", "테마 변경"],
            "answer_index": 0,
            "explanation": "쪽지시험은 예습 자료 기반 이해도 점검에 사용됩니다.",
        },
        {
            "topic": topic,
            "question": "틀린 문제를 반복 복습하기 위한 기능은?",
            "choices": ["오답노트", "공고 정리", "로그인", "백서명 변경"],
            "answer_index": 0,
            "explanation": "오답노트는 틀린 문항과 해설을 누적해 복습하는 기능입니다.",
        },
        {
            "topic": topic,
            "question": "출결·수료 같은 변동 가능 정보는 어떻게 확인해야 하는가?",
            "choices": ["최신 공식 공지 확인", "추측으로 판단", "친구 말만 기준", "오래된 자료만 사용"],
            "answer_index": 0,
            "explanation": "기수별로 달라질 수 있는 정보는 최신 공식 공지를 최종 기준으로 봐야 합니다.",
        },
    ]


def extract_json_array(text: str) -> Optional[List[Dict[str, Any]]]:
    if not text:
        return None
    candidates = re.findall(r"```json\s*(.*?)\s*```", text, flags=re.S)
    candidates.append(text)
    for candidate in candidates:
        start = candidate.find("[")
        end = candidate.rfind("]")
        if start == -1 or end == -1 or start >= end:
            continue
        try:
            data = json.loads(candidate[start : end + 1])
        except Exception:
            continue
        if isinstance(data, list):
            return data
    return None


def normalize_quiz(data: Any, topic: str, count: int) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    if not isinstance(data, list):
        return fallback_quiz(topic)[:count]
    for item in data:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        choices = item.get("choices")
        answer_index = item.get("answer_index", 0)
        explanation = str(item.get("explanation", "")).strip() or "백서 기반 핵심 개념을 확인합니다."
        if not question or not isinstance(choices, list) or len(choices) < 4:
            continue
        choices = [str(c).strip() for c in choices[:4]]
        try:
            answer_index = int(answer_index)
        except Exception:
            answer_index = 0
        if answer_index < 0 or answer_index >= len(choices):
            answer_index = 0
        normalized.append({"topic": str(item.get("topic", topic)), "question": question, "choices": choices, "answer_index": answer_index, "explanation": explanation})
    if len(normalized) < count:
        normalized.extend(fallback_quiz(topic))
    return normalized[:count]


def generate_quiz(topic: str, prep_material: str, count: int = 5) -> List[Dict[str, Any]]:
    system = "학습 자료를 기반으로 객관식 쪽지시험을 JSON 배열로만 생성합니다."
    user = f"""
[주제]
{topic}

[예습 자료]
{prep_material[:3500]}

[{count}문항 JSON 배열 형식]
[
  {{"topic":"주제", "question":"문제", "choices":["보기1","보기2","보기3","보기4"], "answer_index":0, "explanation":"해설"}}
]
"""
    response = ask_llm(system, user, temperature=0.2)
    parsed = extract_json_array(response or "")
    return normalize_quiz(parsed, topic, count)


def judge_level(score: float) -> str:
    if score >= 85:
        return "고급"
    if score >= 60:
        return "중급"
    return "초급"


def build_topic_stats(quiz: List[Dict[str, Any]], selected: Dict[int, int]) -> pd.DataFrame:
    rows: Dict[str, Dict[str, int]] = {}
    for i, item in enumerate(quiz):
        topic = item.get("topic", "기타")
        rows.setdefault(topic, {"문항수": 0, "정답수": 0})
        rows[topic]["문항수"] += 1
        if selected.get(i) == item.get("answer_index"):
            rows[topic]["정답수"] += 1
    result = []
    for topic, stat in rows.items():
        rate = round(stat["정답수"] / max(1, stat["문항수"]) * 100, 1)
        result.append({"주제": topic, "문항수": stat["문항수"], "정답수": stat["정답수"], "정답률": rate})
    return pd.DataFrame(result)


def save_result(payload: Dict[str, Any]) -> None:
    data = read_json(RESULT_PATH, [])
    if not isinstance(data, list):
        data = []
    data.append(payload)
    write_json(RESULT_PATH, data)


def save_wrong_notes(items: List[Dict[str, Any]]) -> None:
    data = read_json(WRONG_NOTE_PATH, [])
    if not isinstance(data, list):
        data = []
    data.extend(items)
    write_json(WRONG_NOTE_PATH, data)


def study_recommendation(level: str, weak_topics: List[str]) -> str:
    weak = ", ".join(weak_topics) if weak_topics else "현재 뚜렷한 취약 주제 없음"
    actions = LEVEL_GUIDE.get(level, LEVEL_GUIDE["초급"])
    return "\n".join([f"### 수준별 스터디 추천", f"- 현재 등급: **{level}**", f"- 보완 주제: **{weak}**"] + [f"- {a}" for a in actions])


def summarize_notice(notice_text: str, interests: str) -> Dict[str, str]:
    system = "공고/공모전/채용형 프로그램 정보를 학습자 관점으로 정리합니다. JSON 객체만 반환합니다."
    user = f"""
관심 분야: {interests}
공고 내용:
{notice_text[:3500]}

다음 JSON 형식으로만 반환:
{{"title":"공고명", "type":"공모전/프로젝트/채용/기타", "deadline":"YYYY-MM-DD 또는 미확인", "fit":"관심 분야와의 관련성", "actions":"다음 행동 2~3개"}}
"""
    response = ask_llm(system, user, temperature=0.1)
    if response:
        try:
            start = response.find("{")
            end = response.rfind("}")
            parsed = json.loads(response[start : end + 1])
            if isinstance(parsed, dict):
                return {"title": str(parsed.get("title", "미확인")), "type": str(parsed.get("type", "기타")), "deadline": str(parsed.get("deadline", "미확인")), "fit": str(parsed.get("fit", "미확인")), "actions": str(parsed.get("actions", "미확인"))}
        except Exception:
            pass
    date_match = re.search(r"(20\d{2})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})", notice_text)
    deadline = "미확인"
    if date_match:
        y, m, d = map(int, date_match.groups())
        deadline = f"{y:04d}-{m:02d}-{d:02d}"
    first_line = next((line.strip() for line in notice_text.splitlines() if line.strip()), "공고")
    return {"title": first_line[:60], "type": "기타", "deadline": deadline, "fit": f"관심 분야({interests})와 직접 비교가 필요합니다.", "actions": "지원 자격 확인, 마감일 등록, 제출물 목록 작성"}


# ============================================================
# 대화 / 캘린더 저장
# ============================================================


def load_conversations() -> Dict[str, Any]:
    data = read_json(CONVERSATION_PATH, {})
    if not isinstance(data, dict) or not data:
        cid = str(uuid.uuid4())
        data = {cid: {"title": "새 학습 대화", "created_at": datetime.now().isoformat(timespec="seconds"), "messages": []}}
        write_json(CONVERSATION_PATH, data)
    if st.session_state.get("conversation_id") not in data:
        st.session_state["conversation_id"] = next(iter(data.keys()))
    return data


def save_conversations(data: Dict[str, Any]) -> None:
    write_json(CONVERSATION_PATH, data)


def current_conversation_id() -> str:
    data = load_conversations()
    cid = st.session_state.get("conversation_id")
    if cid not in data:
        cid = next(iter(data.keys()))
        st.session_state["conversation_id"] = cid
    return cid


def create_conversation() -> str:
    data = load_conversations()
    cid = str(uuid.uuid4())
    data[cid] = {"title": "새 학습 대화", "created_at": datetime.now().isoformat(timespec="seconds"), "messages": []}
    save_conversations(data)
    st.session_state["conversation_id"] = cid
    return cid


def append_message(conv_id: str, role: str, content: str, sources: Optional[List[Dict[str, Any]]] = None) -> None:
    data = load_conversations()
    conv = data.setdefault(conv_id, {"title": "새 학습 대화", "created_at": datetime.now().isoformat(timespec="seconds"), "messages": []})
    conv["messages"].append({"role": role, "content": content, "sources": sources or [], "time": datetime.now().isoformat(timespec="seconds")})
    if role == "user" and conv.get("title") == "새 학습 대화":
        conv["title"] = content[:24] + ("..." if len(content) > 24 else "")
    save_conversations(data)


def read_calendar() -> List[Dict[str, Any]]:
    data = read_json(CALENDAR_PATH, [])
    if not isinstance(data, list):
        data = []
    default_events = [
        {"id": "default_1", "title": "AIVLE DAY 1차", "date": "2026-05-15", "kind": "시험", "note": "포트폴리오 강의, 코딩테스트"},
        {"id": "default_2", "title": "AIVLE DAY 2차", "date": "2026-06-26", "kind": "시험", "note": "면접 특강"},
        {"id": "default_3", "title": "Job-Fair", "date": "2026-08-27", "kind": "채용", "note": "취업지원 프로그램"},
    ]
    default_ids = {item["id"] for item in default_events}
    user_events = [item for item in data if item.get("id") not in default_ids]
    return default_events + user_events


def add_calendar_event(title: str, event_date: str, kind: str, note: str) -> None:
    data = read_json(CALENDAR_PATH, [])
    if not isinstance(data, list):
        data = []
    data.append({"id": str(uuid.uuid4()), "title": title, "date": event_date, "kind": kind, "note": note})
    write_json(CALENDAR_PATH, data)


def delete_calendar_event(event_id: str) -> None:
    data = read_json(CALENDAR_PATH, [])
    if not isinstance(data, list):
        return
    data = [item for item in data if item.get("id") != event_id]
    write_json(CALENDAR_PATH, data)


# ============================================================
# 렌더링 공통
# ============================================================


def hero(title: str, body: str, kicker: str = "AIVLE 학습도우미") -> None:
    st.markdown(
        f"""
        <div class='app-hero'>
            <div class='hero-kicker'>{kicker}</div>
            <h1>{title}</h1>
            <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, subtitle: str = "") -> None:
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<div class='section-sub'>{subtitle}</div>", unsafe_allow_html=True)


def ensure_whitepaper_ready() -> bool:
    path = get_whitepaper_path()
    if not path.exists():
        st.error("학습 자료가 없습니다. 왼쪽 사이드바에서 DOCX 또는 PDF 백서를 업로드해 주세요.")
        return False
    return True


def render_sources(hits: List[SearchHit]) -> None:
    if not hits:
        st.info("표시할 백서 근거가 없습니다.")
        return
    with st.expander("백서 근거 보기", expanded=False):
        for idx, hit in enumerate(hits, start=1):
            preview = hit.text.replace("\n", " ")[:520]
            st.markdown(
                f"""
                <div class='source-box'>
                    <b>근거 {idx} · {hit.title}</b><br>
                    <span style='color:#64748b;font-size:.86rem;'>유사도 {hit.score:.3f} · 청크 {hit.index}</span>
                    <p>{preview}{'...' if len(hit.text) > 520 else ''}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_link_table(links: List[Dict[str, str]]) -> None:
    if not links:
        return
    with st.expander("추천 학습 사이트", expanded=False):
        st.dataframe(pd.DataFrame(links), hide_index=True, use_container_width=True)


def render_header_metrics() -> None:
    index = load_index()
    chunk_count = len(index.get("chunks", [])) if index else 0
    conv_count = len(load_conversations())
    result_count = len(read_json(RESULT_PATH, []))
    wrong_count = len(read_json(WRONG_NOTE_PATH, []))
    meta = get_whitepaper_meta()
    display_name = meta.get("display_name") or get_whitepaper_path().name
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("학습 자료", display_name)
    c2.metric("검색 청크", f"{chunk_count:,}")
    c3.metric("저장 대화", f"{conv_count:,}")
    c4.metric("진단 / 오답", f"{result_count:,} / {wrong_count:,}")


def upload_signature(uploaded: Any) -> str:
    payload = uploaded.getvalue()
    digest = hashlib.sha256(payload).hexdigest()[:16]
    return f"{uploaded.name}:{uploaded.size}:{digest}"


def render_login_page() -> None:
    st.markdown("<br><br>", unsafe_allow_html=True)
    left, center, right = st.columns([1, 1.15, 1])
    with center:
        st.markdown(
            """
            <div class='info-panel' style='padding:28px;'>
                <div class='hero-kicker'>학습자 로그인</div>
                <h2 style='margin:4px 0 8px 0;color:#111827;'>AIVLE 학습도우미</h2>
                <p style='color:#64748b;'>제공받은 계정으로 로그인해 학습 질의, 예습, 쪽지시험, 오답노트를 이용하세요.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            login_id = st.text_input("아이디")
            login_pw = st.text_input("비밀번호", type="password")
            submitted = st.form_submit_button("로그인", use_container_width=True)
        if submitted:
            if authenticate(login_id, login_pw):
                st.session_state["authenticated"] = True
                st.session_state["login_error"] = ""
                st.rerun()
            st.session_state["login_error"] = "아이디 또는 비밀번호가 올바르지 않습니다."
        if st.session_state.get("login_error"):
            st.error(st.session_state["login_error"])


def render_sidebar() -> str:
    st.sidebar.markdown(
        """
        <div class='sidebar-brand'>
            <div class='brand-mark'>A</div>
            <div>
                <div class='brand-title'>AIVLE 학습도우미</div>
                <div class='brand-sub'>학습자 모드</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    current_page = st.session_state.get("active_page", "대시보드")
    if current_page not in MENU_OPTIONS:
        current_page = "대시보드"
        st.session_state["active_page"] = current_page

    radio_key = f"nav_radio_{st.session_state.get('nav_version', 0)}"
    page = st.sidebar.radio("학습 메뉴", MENU_OPTIONS, index=MENU_OPTIONS.index(current_page), key=radio_key)
    st.session_state["active_page"] = page
    st.sidebar.markdown(f"<div class='current-pill'>현재 화면 · {page}</div>", unsafe_allow_html=True)

    if st.sidebar.button("새 학습 대화", use_container_width=True):
        create_conversation()
        navigate("학습 질의")

    conversations = load_conversations()
    conv_ids = list(conversations.keys())
    current_conv = current_conversation_id()
    selected = st.sidebar.selectbox(
        "학습 대화 목록",
        conv_ids,
        index=conv_ids.index(current_conv) if current_conv in conv_ids else 0,
        format_func=lambda cid: conversations.get(cid, {}).get("title", "대화"),
    )
    st.session_state["conversation_id"] = selected

    if st.sidebar.button("현재 학습 대화 삭제", use_container_width=True):
        data = load_conversations()
        if len(data) <= 1:
            data[selected]["messages"] = []
            data[selected]["title"] = "새 학습 대화"
        else:
            data.pop(selected, None)
            st.session_state["conversation_id"] = next(iter(data.keys()))
        save_conversations(data)
        st.rerun()

    st.sidebar.markdown("<div class='side-label'>학습 자료</div>", unsafe_allow_html=True)
    uploaded = st.sidebar.file_uploader("DOCX/PDF/TXT 업로드", type=["docx", "pdf", "txt"])
    if uploaded is not None:
        sig = upload_signature(uploaded)
        if sig != st.session_state.get("last_upload_sig"):
            suffix = Path(uploaded.name).suffix.lower() or ".docx"
            target = DATA_DIR / f"current_whitepaper{suffix}"
            payload = uploaded.getvalue()
            target.write_bytes(payload)
            save_whitepaper_meta(uploaded.name, target, len(payload))
            st.session_state["last_upload_sig"] = sig
            st.cache_resource.clear()
            st.sidebar.success("학습 자료가 반영되었습니다.")
            st.rerun()

    st.sidebar.divider()
    if st.sidebar.button("로그아웃", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["login_error"] = ""
        st.rerun()

    return page


# ============================================================
# 페이지
# ============================================================


def page_dashboard() -> None:
    hero("AIVLE 학습도우미", "질문, 예습, 쪽지시험, 오답노트, 일정 관리를 한 흐름으로 연결한 학습자용 화면입니다.")
    render_header_metrics()

    section("오늘의 학습 루틴", "처음 사용하는 경우 아래 순서대로 진행하면 됩니다.")
    st.markdown(
        """
        <div class='routine-strip'>
            <div class='routine-item'><span>STEP 01</span><b>질문하기</b><p>추천 질문으로 막힌 개념을 빠르게 확인합니다.</p></div>
            <div class='routine-item'><span>STEP 02</span><b>예습하기</b><p>주차와 주제를 선택해 수업 전 핵심 내용을 정리합니다.</p></div>
            <div class='routine-item'><span>STEP 03</span><b>진단하기</b><p>쪽지시험으로 현재 이해도를 점수와 등급으로 확인합니다.</p></div>
            <div class='routine-item'><span>STEP 04</span><b>복습하기</b><p>오답노트와 취약 주제로 반복 학습합니다.</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    section("바로 시작")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='learn-card'><div class='badge'>질문</div><h3>백서 기반 질의응답</h3><p>추천 질문 또는 직접 질문으로 필요한 내용을 바로 확인합니다.</p></div>", unsafe_allow_html=True)
        if st.button("질문 화면으로 이동", use_container_width=True):
            st.session_state["pending_chat"] = "에이블스쿨 전체 학습 흐름을 요약해줘"
            navigate("학습 질의")
    with c2:
        st.markdown("<div class='learn-card'><div class='badge'>예습</div><h3>예습 자료 생성</h3><p>커리큘럼 주차별 핵심 개념, 체크 질문, 예습 순서를 만듭니다.</p></div>", unsafe_allow_html=True)
        if st.button("예습 화면으로 이동", use_container_width=True):
            navigate("예습·쪽지시험")
    with c3:
        st.markdown("<div class='learn-card'><div class='badge'>복습</div><h3>학습 분석 확인</h3><p>쪽지시험 결과와 오답노트를 통해 취약 주제를 확인합니다.</p></div>", unsafe_allow_html=True)
        if st.button("분석 화면으로 이동", use_container_width=True):
            navigate("학습 분석·오답노트")

    section("전체 기능 흐름")
    flow = pd.DataFrame(
        [
            ["학습 질의", "추천 질문 / 직접 질문", "백서 근거로 빠르게 이해"],
            ["예습", "주차별 예습 자료", "수업 전 개념 선파악"],
            ["진단", "쪽지시험 / 등급 판별", "현재 수준 확인"],
            ["복습", "오답노트 / 취약 주제", "약점 보완"],
            ["확장", "공고 정리 / 캘린더", "실전 경험 연결"],
        ],
        columns=["단계", "사용 기능", "목표"],
    )
    st.dataframe(flow, hide_index=True, use_container_width=True)


def page_chat() -> None:
    hero("학습 질의", "자주 묻는 질문을 버튼으로 선택하거나 직접 질문해 백서 기반 답변을 확인합니다.")
    if not ensure_whitepaper_ready():
        return

    section("추천 질문", "버튼을 누르면 바로 답변이 생성됩니다.")
    tabs = st.tabs(list(QUICK_QUESTION_GROUPS.keys()))
    for tab, (group, questions) in zip(tabs, QUICK_QUESTION_GROUPS.items()):
        with tab:
            cols = st.columns(3)
            for idx, question in enumerate(questions):
                if cols[idx % 3].button(question, key=f"quick_{group}_{idx}", use_container_width=True):
                    st.session_state["pending_chat"] = question
                    st.rerun()

    conv_id = current_conversation_id()
    conversations = load_conversations()
    messages = conversations[conv_id].get("messages", [])
    st.divider()

    for msg in messages:
        with st.chat_message(msg.get("role", "assistant")):
            st.markdown(msg.get("content", ""))
            sources = msg.get("sources") or []
            if sources:
                render_sources([SearchHit(**src) for src in sources])

    pending = st.session_state.pop("pending_chat", None)
    question = pending or st.chat_input("백서 기준으로 질문을 입력하세요")
    if question:
        append_message(conv_id, "user", question)
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("백서에서 근거를 찾고 답변을 생성하는 중입니다."):
                answer, hits, links = answer_from_whitepaper(question)
            st.markdown(answer)
            render_sources(hits)
            render_link_table(links)
        append_message(conv_id, "assistant", answer, sources=[hit.__dict__ for hit in hits])
        st.rerun()


def page_prep_quiz() -> None:
    hero("예습·쪽지시험", "주차와 주제를 선택해 예습 자료를 만들고, 쪽지시험으로 이해도를 점검합니다.")
    if not ensure_whitepaper_ready():
        return

    left, right = st.columns([0.92, 1.08])
    with left:
        section("예습 조건")
        week_options = [f"{row['week']} · {row['topic']}" for row in DEFAULT_CURRICULUM]
        selected_week = st.selectbox("주차", week_options)
        topic = st.selectbox("주제", list(TOPIC_ALIASES.keys()))
        minutes = st.slider("예습 가능 시간", 10, 90, 30, step=10)
        if st.button("예습 자료 생성", use_container_width=True):
            with st.spinner("예습 자료를 생성하는 중입니다."):
                material, hits = generate_prep_material(selected_week, topic, minutes)
            st.session_state["prep_material"] = material
            st.session_state["prep_topic"] = topic
            st.session_state["prep_sources"] = [hit.__dict__ for hit in hits]
            st.rerun()
    with right:
        section("생성된 예습 자료")
        material = st.session_state.get("prep_material")
        if material:
            st.markdown(material)
            render_sources([SearchHit(**src) for src in st.session_state.get("prep_sources", [])])
        else:
            st.info("예습 조건을 선택하고 자료를 생성하세요.")

    st.divider()
    section("쪽지시험")
    if st.button("현재 예습 자료로 쪽지시험 생성", use_container_width=True, disabled=not bool(st.session_state.get("prep_material"))):
        with st.spinner("쪽지시험을 생성하는 중입니다."):
            st.session_state["quiz"] = generate_quiz(st.session_state.get("prep_topic", "프로젝트 수행"), st.session_state.get("prep_material", ""), count=5)
            st.session_state["last_quiz_result"] = None
        st.rerun()

    quiz = st.session_state.get("quiz") or []
    if not quiz:
        return

    selected: Dict[int, int] = {}
    with st.form("quiz_form"):
        for idx, item in enumerate(quiz):
            choice = st.radio(
                f"Q{idx + 1}. {item['question']}",
                options=list(range(len(item["choices"]))),
                format_func=lambda i, item=item: item["choices"][i],
                key=f"quiz_{idx}_{hashlib.md5(item['question'].encode()).hexdigest()[:8]}",
            )
            selected[idx] = int(choice)
        submitted = st.form_submit_button("채점하고 수준 판별")

    if submitted:
        correct = 0
        wrong_items = []
        for idx, item in enumerate(quiz):
            is_correct = selected[idx] == item["answer_index"]
            correct += int(is_correct)
            if not is_correct:
                wrong_items.append({
                    "time": datetime.now().isoformat(timespec="seconds"),
                    "topic": item.get("topic", "기타"),
                    "question": item["question"],
                    "my_answer": item["choices"][selected[idx]],
                    "correct_answer": item["choices"][item["answer_index"]],
                    "explanation": item["explanation"],
                })
        score = round(correct / max(1, len(quiz)) * 100, 1)
        level = judge_level(score)
        stats = build_topic_stats(quiz, selected)
        weak_topics = stats.loc[stats["정답률"] < 70, "주제"].tolist() if not stats.empty else []
        result = {"time": datetime.now().isoformat(timespec="seconds"), "topic": st.session_state.get("prep_topic", "기타"), "score": score, "level": level, "stats": stats.to_dict(orient="records")}
        save_result(result)
        save_wrong_notes(wrong_items)
        st.session_state["last_quiz_result"] = {**result, "weak_topics": weak_topics, "wrong_items": wrong_items}
        st.rerun()

    result = st.session_state.get("last_quiz_result")
    if result:
        st.success(f"점수: {result['score']}점 / 학습 등급: {result['level']}")
        stats_df = pd.DataFrame(result.get("stats", []))
        if not stats_df.empty:
            st.bar_chart(stats_df.set_index("주제")["정답률"])
        st.markdown(study_recommendation(result["level"], result.get("weak_topics", [])))
        if result.get("wrong_items"):
            section("방금 생성된 오답노트")
            for item in result["wrong_items"]:
                st.markdown(f"**{item['topic']}** · {item['question']}\n\n- 내 답: {item['my_answer']}\n- 정답: {item['correct_answer']}\n- 해설: {item['explanation']}")


def page_analysis() -> None:
    hero("학습 분석·오답노트", "쪽지시험 결과를 누적해 점수 추이, 취약 주제, 오답을 확인합니다.")
    results = read_json(RESULT_PATH, [])
    wrong_notes = read_json(WRONG_NOTE_PATH, [])

    section("학습 진단 요약")
    if not results:
        st.info("아직 저장된 쪽지시험 결과가 없습니다.")
    else:
        df = pd.DataFrame(results)
        c1, c2, c3 = st.columns(3)
        c1.metric("응시 횟수", len(df))
        c2.metric("평균 점수", f"{df['score'].mean():.1f}")
        c3.metric("최근 등급", str(df.iloc[-1].get("level", "-")))
        trend = df[["time", "score"]].copy()
        trend["time"] = pd.to_datetime(trend["time"], errors="coerce")
        st.line_chart(trend.dropna().set_index("time")["score"])

        topic_rows = []
        for row in results:
            for stat in row.get("stats", []):
                topic_rows.append(stat)
        if topic_rows:
            topic_df = pd.DataFrame(topic_rows)
            summary = topic_df.groupby("주제", as_index=False).agg({"정답률": "mean", "문항수": "sum"})
            summary["정답률"] = summary["정답률"].round(1)
            section("부족한 주제 시각화")
            st.bar_chart(summary.set_index("주제")["정답률"])
            st.dataframe(summary, hide_index=True, use_container_width=True)

    st.divider()
    section("오답노트")
    if not wrong_notes:
        st.info("저장된 오답이 없습니다.")
        return
    topic_filter = st.selectbox("주제 필터", ["전체"] + sorted({item.get("topic", "기타") for item in wrong_notes}))
    filtered = wrong_notes if topic_filter == "전체" else [item for item in wrong_notes if item.get("topic") == topic_filter]
    for item in reversed(filtered[-30:]):
        with st.expander(f"{item.get('topic', '기타')} · {item.get('question', '')}"):
            st.markdown(f"- 내 답: {item.get('my_answer')}\n- 정답: {item.get('correct_answer')}\n- 해설: {item.get('explanation')}\n- 기록 시각: {item.get('time')}")
            render_link_table(link_recommendations(item.get("topic", "")))


def page_opportunities_calendar() -> None:
    hero("공고·캘린더", "공모전, 프로젝트, 채용형 프로그램 정보를 정리하고 마감일을 캘린더에 연결합니다.")
    left, right = st.columns(2)
    with left:
        section("공고 정리 / 공모전 추천")
        interests = st.text_input("관심 분야", value="AI, DX, Cloud, 데이터 분석, 서비스 기획")
        notice = st.text_area("공고 내용", height=220, placeholder="공고명, 지원 자격, 마감일, 제출물, URL 등을 붙여넣으세요.")
        if st.button("공고 정리", use_container_width=True, disabled=not bool(notice.strip())):
            st.session_state["notice_summary"] = summarize_notice(notice, interests)
        summary = st.session_state.get("notice_summary")
        if summary:
            st.dataframe(pd.DataFrame([summary]), hide_index=True, use_container_width=True)
            if summary.get("deadline") and summary.get("deadline") != "미확인":
                if st.button("마감일을 캘린더에 추가", use_container_width=True):
                    add_calendar_event(summary.get("title", "공고 마감"), summary["deadline"], summary.get("type", "공고"), summary.get("actions", ""))
                    st.success("캘린더에 추가되었습니다.")
    with right:
        section("일정 추가")
        with st.form("calendar_add"):
            title = st.text_input("일정명")
            event_date = st.date_input("날짜", value=date.today())
            kind = st.selectbox("구분", ["수업", "시험", "스터디", "공모전", "채용", "개인"])
            note = st.text_area("메모", height=90)
            ok = st.form_submit_button("일정 저장")
            if ok and title.strip():
                add_calendar_event(title.strip(), event_date.isoformat(), kind, note)
                st.success("일정이 저장되었습니다.")

    st.divider()
    section("캘린더")
    events = read_calendar()
    if not events:
        st.info("등록된 일정이 없습니다.")
        return
    df = pd.DataFrame(events)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    months = sorted(df["date"].dt.strftime("%Y-%m").dropna().unique().tolist())
    month = st.selectbox("월 필터", ["전체"] + months)
    display = df if month == "전체" else df[df["date"].dt.strftime("%Y-%m") == month]
    display = display.sort_values("date")
    st.dataframe(display[["date", "kind", "title", "note"]], hide_index=True, use_container_width=True)
    deletable = display[~display["id"].astype(str).str.startswith("default_")]
    if not deletable.empty:
        target = st.selectbox("삭제할 일정", [""] + deletable["id"].tolist(), format_func=lambda eid: "선택 안 함" if not eid else deletable.loc[deletable["id"] == eid, "title"].iloc[0])
        if target and st.button("선택 일정 삭제"):
            delete_calendar_event(target)
            st.rerun()


def page_curriculum() -> None:
    hero("커리큘럼", "전체 교육 과정과 주차별 학습 내용을 확인하고 관련 백서 근거를 검색합니다.")
    df = pd.DataFrame(DEFAULT_CURRICULUM)
    c1, c2 = st.columns([.8, 1.2])
    with c1:
        kind_filter = st.multiselect("구분", sorted(df["kind"].unique()), default=sorted(df["kind"].unique()))
    with c2:
        keyword = st.text_input("커리큘럼 검색", placeholder="예: 생성형 AI, 빅프로젝트, Cloud")
    filtered = df[df["kind"].isin(kind_filter)]
    if keyword:
        filtered = filtered[filtered.apply(lambda row: keyword.lower() in " ".join(map(str, row.values)).lower(), axis=1)]
    st.dataframe(filtered, hide_index=True, use_container_width=True)

    st.divider()
    section("백서에서 추가 확인")
    query = st.text_input("백서 검색어", value=keyword or "커리큘럼")
    if st.button("백서 근거 검색", use_container_width=True):
        render_sources(search_whitepaper(query, k=8))


def page_learning_status() -> None:
    hero("내 학습 현황", "저장된 대화, 진단 결과, 오답노트, 일정 현황을 확인합니다.")
    render_header_metrics()

    section("현재 학습 자료")
    meta = get_whitepaper_meta()
    path = get_whitepaper_path()
    c1, c2 = st.columns(2)
    c1.markdown(f"**자료명**  \n{meta.get('display_name', path.name)}")
    c2.markdown(f"**반영 시각**  \n{meta.get('updated_at') or '기본 학습 자료'}")

    section("최근 진단 기록")
    results = read_json(RESULT_PATH, [])
    if results:
        st.dataframe(pd.DataFrame(results[-8:])[['time', 'topic', 'score', 'level']], hide_index=True, use_container_width=True)
    else:
        st.info("최근 진단 기록이 없습니다.")

    section("최근 일정")
    events = read_calendar()
    if events:
        df = pd.DataFrame(events)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        st.dataframe(df.sort_values("date").head(10)[["date", "kind", "title", "note"]], hide_index=True, use_container_width=True)
    else:
        st.info("등록된 일정이 없습니다.")


# ============================================================
# 라우터
# ============================================================

PAGES = {
    "대시보드": page_dashboard,
    "학습 질의": page_chat,
    "예습·쪽지시험": page_prep_quiz,
    "학습 분석·오답노트": page_analysis,
    "공고·캘린더": page_opportunities_calendar,
    "커리큘럼": page_curriculum,
    "내 학습 현황": page_learning_status,
}


def main() -> None:
    init_state()
    if not st.session_state.get("authenticated"):
        render_login_page()
        return
    page = render_sidebar()
    PAGES.get(page, page_dashboard)()


if __name__ == "__main__":
    main()
