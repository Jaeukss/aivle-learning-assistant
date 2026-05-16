from __future__ import annotations

import json
import os
import re
import uuid
import hmac
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
# AIVLE Navigator
# - 기존 app.py의 코드 구조를 재사용하지 않고 새로 작성한 Streamlit 앱
# - 백서 기반 질의응답, 예습, 쪽지시험, 수준진단, 캘린더, 대화저장 포함
# ============================================================

APP_ROOT = Path(__file__).resolve().parent
DATA_DIR = APP_ROOT / "data"
STORE_DIR = APP_ROOT / "storage"
WHITEPAPER_PATH = DATA_DIR / "aivle_kt_learning_whitepaper_2026.docx"
CONVERSATION_PATH = STORE_DIR / "conversations.json"
RESULT_PATH = STORE_DIR / "study_results.json"
WRONG_NOTE_PATH = STORE_DIR / "wrong_notes.json"
CALENDAR_PATH = STORE_DIR / "calendar_events.json"

APP_TITLE = "AIVLE Navigator"
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBEDLESS_TOP_K = 6

MENU_OPTIONS = [
    "대시보드",
    "학습 질의",
    "예습·쪽지시험",
    "학습 분석·오답노트",
    "공고·캘린더",
    "커리큘럼",
    "설정",
]

DATA_DIR.mkdir(exist_ok=True)
STORE_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 디자인
# ============================================================

st.markdown(
    """
    <style>
    :root {
        --card-bg: rgba(255,255,255,.78);
        --line: rgba(15,23,42,.12);
        --text-soft: #64748b;
        --brand: #2563eb;
    }
    .main .block-container {padding-top: 1.2rem; max-width: 1280px;}
    [data-testid="stSidebar"] {background: #0f172a;}
    [data-testid="stSidebar"] * {color: #e5e7eb;}
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(255,255,255,.94), rgba(248,250,252,.92));
        border: 1px solid var(--line);
        padding: 14px 16px;
        border-radius: 18px;
        box-shadow: 0 10px 24px rgba(15,23,42,.06);
    }
    .hero {
        border: 1px solid rgba(37,99,235,.18);
        background: radial-gradient(circle at 0% 0%, rgba(59,130,246,.18), transparent 38%),
                    linear-gradient(135deg, rgba(15,23,42,.96), rgba(30,41,59,.96));
        color: white;
        padding: 30px 34px;
        border-radius: 28px;
        margin-bottom: 18px;
    }
    .hero h1 {font-size: 2.1rem; margin: 0 0 8px 0;}
    .hero p {color: #cbd5e1; margin: 0; font-size: 1rem;}
    .panel {
        border: 1px solid var(--line);
        background: var(--card-bg);
        border-radius: 22px;
        padding: 18px 20px;
        box-shadow: 0 12px 30px rgba(15,23,42,.05);
        margin-bottom: 14px;
    }
    .small-note {color: var(--text-soft); font-size: .9rem;}
    .tag {
        display: inline-block;
        border: 1px solid rgba(37,99,235,.22);
        background: rgba(37,99,235,.08);
        color: #1d4ed8;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: .82rem;
        margin: 2px 4px 2px 0;
    }
    .danger-note {
        border-left: 4px solid #ef4444;
        background: rgba(254,242,242,.9);
        padding: 12px 14px;
        border-radius: 14px;
        color: #7f1d1d;
        margin: 8px 0 16px 0;
    }
    .source-box {
        border: 1px dashed rgba(100,116,139,.35);
        border-radius: 14px;
        padding: 12px;
        background: rgba(248,250,252,.9);
        margin: 6px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 데이터 모델
# ============================================================

@dataclass
class SearchHit:
    index: int
    score: float
    title: str
    text: str


DEFAULT_CURRICULUM = [
    {"week": "1주", "period": "3.30~4.3", "topic": "입교식 + 분석형 AI", "kind": "curriculum", "note": "입교 오리엔테이션, 분석형 AI 시작"},
    {"week": "2주", "period": "4.6~4.10", "topic": "분석형 AI", "kind": "curriculum", "note": "데이터 분석·머신러닝 기초"},
    {"week": "3주", "period": "4.13~4.17", "topic": "분석형 AI + 분석형 AI 미니프로젝트", "kind": "project", "note": "분석형 AI 실습 산출물"},
    {"week": "4주", "period": "4.20~4.24", "topic": "분석형 AI 미니프로젝트 + 생성형 AI", "kind": "project", "note": "생성형 AI 전환"},
    {"week": "5주", "period": "4.27~5.1", "topic": "생성형 AI 미니프로젝트 + 생성형 AI", "kind": "project", "note": "5.1 휴강"},
    {"week": "6주", "period": "5.4~5.8", "topic": "생성형 AI", "kind": "curriculum", "note": "5.4~5.5 휴강"},
    {"week": "7주", "period": "5.11~5.15", "topic": "생성형 AI 미니프로젝트", "kind": "project", "note": "기타교과 포함"},
    {"week": "8주", "period": "5.18~5.22", "topic": "서비스 개발/제안 + 미니프로젝트", "kind": "project", "note": "AI/DX 트랙별 산출물"},
    {"week": "9주", "period": "5.25~5.29", "topic": "서비스 개발/제안 미니프로젝트", "kind": "project", "note": "대체휴일 포함"},
    {"week": "10주", "period": "6.1~6.5", "topic": "서비스 개발/제안", "kind": "curriculum", "note": "서비스 구현 또는 제안 전략"},
    {"week": "11주", "period": "6.8~6.12", "topic": "서비스 개발/제안 미니프로젝트", "kind": "project", "note": "산출물 개선"},
    {"week": "12주", "period": "6.15~6.19", "topic": "Cloud", "kind": "curriculum", "note": "IT Infra, Cloud Infra"},
    {"week": "13주", "period": "6.22~6.26", "topic": "Cloud + Cloud 미니프로젝트", "kind": "project", "note": "AIVLE DAY 2차"},
    {"week": "14~22주", "period": "6.29~8.28", "topic": "빅프로젝트", "kind": "project", "note": "주제 선정, 현직자 코칭, 구현, 발표"},
    {"week": "23주", "period": "8.31~9.4", "topic": "취업지원 + 수료식", "kind": "career", "note": "모의면접, 취업플랫폼, 수료식"},
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

TOPIC_ALIASES = {
    "분석형 AI": ["분석형 AI", "데이터 분석", "머신러닝", "딥러닝", "모델", "예측"],
    "생성형 AI": ["생성형 AI", "LLM", "프롬프트", "RAG", "LangChain", "이미지 모델"],
    "Cloud": ["Cloud", "클라우드", "IT Infra", "Cloud Infra", "Cloud Native"],
    "서비스 개발/제안": ["서비스 개발", "서비스 제안", "SW", "Web", "제안서", "프로젝트 관리"],
    "프로젝트 수행": ["미니프로젝트", "빅프로젝트", "MVP", "주제 선정", "발표", "현직자 코칭"],
    "출결·운영": ["출결", "지각", "조퇴", "외출", "공가", "수료", "에이블에듀"],
}

LEVEL_GUIDE = {
    "초급": {
        "range": "0~59점",
        "study": ["예습 자료의 용어 정의부터 다시 정리", "하루 20분 핵심 개념 카드 만들기", "쪽지시험 오답을 같은 날 재풀이"],
    },
    "중급": {
        "range": "60~84점",
        "study": ["틀린 주제 중심으로 미니 실습 진행", "개념을 프로젝트 산출물과 연결", "스터디에서 설명자 역할 수행"],
    },
    "고급": {
        "range": "85~100점",
        "study": ["심화 자료와 공식 문서 탐색", "동료 질문 답변으로 설명력 강화", "프로젝트 적용 아이디어 도출"],
    },
}

OFFICIAL_NOTICE_KEYWORDS = ["출결", "공가", "수료", "지원 자격", "자비부담금", "평가", "합격", "불합격", "최신", "공식"]


# ============================================================
# 저장소 유틸리티
# ============================================================

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
    login_id = get_config_value("APP_LOGIN_ID", "admin") or "admin"
    login_password = get_config_value("APP_LOGIN_PASSWORD", "aivle2026") or "aivle2026"
    return login_id, login_password


def init_session_defaults() -> None:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("login_error", "")
    st.session_state.setdefault("active_page", "대시보드")
    if st.session_state["active_page"] not in MENU_OPTIONS:
        st.session_state["active_page"] = "대시보드"


def authenticate(login_id: str, login_password: str) -> bool:
    expected_id, expected_password = get_login_credentials()
    return hmac.compare_digest(login_id, expected_id) and hmac.compare_digest(login_password, expected_password)


def get_client() -> Optional[Any]:
    key = get_api_key()
    if not key or OpenAI is None:
        return None
    return OpenAI(api_key=key)


# ============================================================
# 문서 로딩 및 검색
# ============================================================

def parse_docx(path: Path) -> str:
    if Document is None:
        return ""
    doc = Document(str(path))
    lines: List[str] = []
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text:
            lines.append(text)
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            cells = [c for c in cells if c]
            if cells:
                lines.append(" | ".join(cells))
    return "\n".join(lines)


def parse_pdf(path: Path) -> str:
    if PdfReader is None:
        return ""
    reader = PdfReader(str(path))
    chunks = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def parse_text_file(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        return parse_docx(path)
    if path.suffix.lower() == ".pdf":
        return parse_pdf(path)
    return path.read_text(encoding="utf-8", errors="ignore")


def normalize_space(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).replace("\r", "").strip()


def split_into_chunks(text: str, size: int = 950, overlap: int = 160) -> List[Dict[str, str]]:
    clean = normalize_space(text)
    section_hits = list(re.finditer(r"(?m)^(Ⅰ|Ⅱ|Ⅲ|Ⅳ|Ⅴ|Ⅵ|Ⅶ|Ⅷ|Ⅸ|Ⅹ|\d+\.|[가-힣A-Za-z].{0,30})", clean))
    paragraphs = [p.strip() for p in re.split(r"\n{2,}|(?<=다\.)\s+", clean) if p.strip()]

    chunks: List[Dict[str, str]] = []
    buffer = ""
    current_title = "백서"

    for paragraph in paragraphs:
        if re.match(r"^(Ⅰ|Ⅱ|Ⅲ|Ⅳ|Ⅴ|Ⅵ|Ⅶ|Ⅷ|Ⅸ|Ⅹ)\.", paragraph) or re.match(r"^\d+\.\s", paragraph):
            current_title = paragraph[:80]
        if len(buffer) + len(paragraph) + 2 <= size:
            buffer = f"{buffer}\n{paragraph}".strip()
            continue
        if buffer:
            chunks.append({"title": current_title, "text": buffer})
        tail = buffer[-overlap:] if overlap and buffer else ""
        buffer = f"{tail}\n{paragraph}".strip()
    if buffer:
        chunks.append({"title": current_title, "text": buffer})

    if not chunks and clean:
        for i in range(0, len(clean), max(1, size - overlap)):
            chunks.append({"title": "백서", "text": clean[i : i + size]})
    return chunks


@st.cache_resource(show_spinner=False)
def build_index(path: str, modified_at: float) -> Dict[str, Any]:
    source_path = Path(path)
    raw_text = parse_text_file(source_path)
    chunks = split_into_chunks(raw_text)
    texts = [chunk["text"] for chunk in chunks] or [""]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=9000)
    matrix = vectorizer.fit_transform(texts)
    return {"text": raw_text, "chunks": chunks, "vectorizer": vectorizer, "matrix": matrix}


def load_index() -> Optional[Dict[str, Any]]:
    if not WHITEPAPER_PATH.exists():
        return None
    return build_index(str(WHITEPAPER_PATH), WHITEPAPER_PATH.stat().st_mtime)


def search_whitepaper(query: str, k: int = EMBEDLESS_TOP_K) -> List[SearchHit]:
    index = load_index()
    if not index:
        return []
    vectorizer = index["vectorizer"]
    matrix = index["matrix"]
    query_vector = vectorizer.transform([query])
    scores = cosine_similarity(query_vector, matrix).ravel()
    top_indices = scores.argsort()[::-1][:k]
    hits = []
    for idx in top_indices:
        chunk = index["chunks"][int(idx)]
        hits.append(SearchHit(index=int(idx), score=float(scores[idx]), title=chunk["title"], text=chunk["text"]))
    return [hit for hit in hits if hit.score > 0]


def extract_links(text: str) -> List[str]:
    raw = re.findall(r"(?:https?://)?(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}(?:/[A-Za-z0-9_./?=&%-]*)?", text)
    links = []
    for item in raw:
        url = item if item.startswith("http") else "https://" + item
        if url not in links:
            links.append(url)
    return links


def link_recommendations(question: str) -> List[Dict[str, str]]:
    index = load_index()
    source_text = index["text"] if index else ""
    found = extract_links(source_text)
    defaults = [
        {"name": "KT AIVLE School 공식 홈페이지", "url": "https://aivle.kt.co.kr", "use": "모집·트랙·공식 안내 확인"},
        {"name": "AIVLE-EDU", "url": "https://aivle.edu.kt.co.kr", "use": "강의·출결·과제·커뮤니티 확인"},
        {"name": "고용24", "url": "https://www.work24.go.kr", "use": "K-DT 수강신청·국민내일배움카드 확인"},
    ]
    for url in found:
        if not any(row["url"] == url for row in defaults):
            defaults.append({"name": url.replace("https://", ""), "url": url, "use": "백서에서 추출된 참고 링크"})

    query = question.lower()
    scored = []
    for row in defaults:
        score = 0
        blob = f"{row['name']} {row['use']} {row['url']}".lower()
        for token in re.findall(r"[가-힣A-Za-z0-9]+", query):
            if token.lower() in blob:
                score += 1
        scored.append((score, row))
    return [row for _, row in sorted(scored, key=lambda x: x[0], reverse=True)[:5]]


# ============================================================
# LLM 호출 및 프롬프트
# ============================================================

def ask_llm(system_prompt: str, user_prompt: str, temperature: float = 0.15) -> Optional[str]:
    client = get_client()
    if client is None:
        return None
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        return f"LLM 호출 실패: {exc}"


def make_context(hits: List[SearchHit]) -> str:
    lines = []
    for i, hit in enumerate(hits, 1):
        lines.append(f"[근거 {i}] 제목: {hit.title}\n{hit.text}")
    return "\n\n".join(lines)


def answer_from_whitepaper(question: str) -> Tuple[str, List[SearchHit], List[Dict[str, str]]]:
    hits = search_whitepaper(question)
    links = link_recommendations(question)
    context = make_context(hits)

    system = (
        "너는 KT AIVLE School 학습 지원 앱의 백서 기반 어시스턴트다. "
        "제공된 근거 안에서만 답한다. 근거에 없으면 확인할 수 없다고 말한다. "
        "출결, 평가, 지원자격, 수료, 일정, 자비부담금처럼 기수별 변동 가능한 항목은 공식 공지 확인 필요성을 명시한다. "
        "답변은 한국어로 작성한다."
    )
    user = f"""
[사용자 질문]
{question}

[백서 검색 근거]
{context}

[출력 형식]
1. 핵심 답변
2. 백서 근거
3. 실행할 일
4. 확인 필요 사항
""".strip()
    answer = ask_llm(system, user)
    if not answer or answer.startswith("LLM 호출 실패"):
        if hits:
            preview = "\n\n".join([f"- {hit.text[:420]}..." for hit in hits[:3]])
            answer = f"### 핵심 답변\nOPENAI_API_KEY가 설정되지 않았거나 LLM 호출이 실패해 검색 요약만 표시합니다.\n\n### 백서 검색 결과\n{preview}\n\n### 확인 필요 사항\n공식 일정·출결·수료·지원 자격은 최신 공지를 기준으로 확인해야 합니다."
        else:
            answer = "백서에서 관련 내용을 찾지 못했습니다. 질문을 더 구체화하거나 백서를 업데이트해야 합니다."
    return answer, hits, links


def generate_prep_material(week: str, topic: str, minutes: int) -> Tuple[str, List[SearchHit]]:
    query = f"{week} {topic} 예습 핵심 개념 커리큘럼"
    hits = search_whitepaper(query, k=7)
    context = make_context(hits)
    system = (
        "너는 교육 과정 예습 자료를 만드는 학습 설계자다. "
        "백서 근거만 사용하고, 모르는 내용은 보완 필요라고 적는다."
    )
    user = f"""
주차: {week}
주제: {topic}
예습 가능 시간: {minutes}분

백서 근거:
{context}

아래 구조로 작성:
- 오늘의 학습 목표 3개
- 핵심 개념 정리
- 예습 순서
- 수업 전 점검 질문
- 백서에서 확인되지 않는 내용
""".strip()
    result = ask_llm(system, user, temperature=0.2)
    if not result or result.startswith("LLM 호출 실패"):
        bullet = "\n".join([f"- {hit.text[:260]}..." for hit in hits[:4]]) or "- 관련 백서 근거가 부족합니다."
        result = f"### 예습 자료\n**주제:** {topic}\n\n### 핵심 근거\n{bullet}\n\n### 예습 순서\n1. 용어를 먼저 정리합니다.\n2. 관련 커리큘럼 위치를 확인합니다.\n3. 수업 전에 모르는 단어를 질문으로 바꿉니다.\n\n### 수업 전 점검 질문\n- 이 주제가 전체 프로젝트와 어떻게 연결되는가?\n- 내가 설명할 수 없는 개념은 무엇인가?"
    return result, hits


# ============================================================
# 쪽지시험 / 수준진단
# ============================================================

def extract_json_array(text: str) -> Optional[List[Dict[str, Any]]]:
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and isinstance(parsed.get("questions"), list):
            return parsed["questions"]
    except Exception:
        pass
    match = re.search(r"\[\s*\{.*\}\s*\]", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def fallback_quiz(topic: str) -> List[Dict[str, Any]]:
    candidates = {
        "분석형 AI": [
            ("분석형 AI의 주요 학습 범위로 가장 적절한 것은?", ["데이터 분석·머신러닝·딥러닝", "출결 관리", "교육장 예약", "채용공고 발송"], 0, "백서의 STEP 1 공통 과정은 분석형 AI에서 데이터 분석, 머신러닝, 딥러닝을 다룹니다."),
            ("모델 선택이나 지표 선택 시 프로젝트에서 남겨야 할 것은?", ["의사결정 근거", "개인 감상", "출석 화면", "노트북 시리얼"], 0, "프로젝트 수행 가이드는 근거 기반 의사결정을 강조합니다."),
        ],
        "생성형 AI": [
            ("생성형 AI 세부 내용에 포함되는 항목은?", ["프롬프트 엔지니어링·LLM·RAG", "공가 신청", "면접 증빙", "국민내일배움카드 결제"], 0, "백서의 생성형 AI 항목은 프롬프트 엔지니어링, 언어 모델, 이미지 모델, RAG, LangChain을 포함합니다."),
            ("RAG 학습에서 우선 확인해야 할 것은?", ["근거 문서와 질문의 연결", "출석 인정 서류", "채용 우대 기준", "교육장 위치"], 0, "RAG는 질문에 맞는 근거 문서를 검색해 답변 근거로 사용하는 흐름입니다."),
        ],
        "Cloud": [
            ("Cloud 과정의 주요 학습 범위로 맞는 것은?", ["IT Infra와 Cloud Infra", "오답노트 작성법", "자비부담금 환불", "스터디 모집 댓글"], 0, "백서에는 Cloud 파트가 IT Infra, Cloud Infra, Cloud Native 또는 설계를 포함한다고 정리되어 있습니다."),
            ("Cloud 미니프로젝트 전에 확인할 내용은?", ["인프라 개념과 서비스 연결", "면접 일정", "지원 나이", "휴강일만"], 0, "Cloud는 서비스 개발·제안과 연결되는 기반 개념으로 이해해야 합니다."),
        ],
        "서비스 개발/제안": [
            ("AI 개발자 트랙의 STEP 2 산출물과 가까운 것은?", ["SW·Web 서비스 구현", "출석 인정 여부 판정", "KDT 환불 처리", "수료증 출력"], 0, "AI 개발자 트랙은 서비스 개발과 프레임워크를 학습합니다."),
            ("DX 컨설턴트 트랙의 STEP 2 내용과 가까운 것은?", ["제안전략수립·제안서 작성", "대리출석 확인", "코딩 마스터스 랭킹", "교육장 자유 사용"], 0, "DX 컨설턴트 트랙은 서비스 제안, 제안전략수립, 제안서 작성, 프로젝트 관리를 다룹니다."),
        ],
        "프로젝트 수행": [
            ("미니프로젝트 시작 시 가장 먼저 할 일은?", ["해결할 문제와 기대 효과 정의", "완성된 UI부터 꾸미기", "점수부터 예측하기", "자료를 외부 공개하기"], 0, "백서의 프로젝트 가이드는 문제정의 우선을 제시합니다."),
            ("빅프로젝트 주제 선정에서 먼저 합의할 것은?", ["MVP 범위와 기능 우선순위", "개인 블로그 공개 범위", "출석 횟수", "랭킹 점수"], 0, "빅프로젝트 단계에서는 MVP 범위와 기능 우선순위 문서화를 강조합니다."),
        ],
        "출결·운영": [
            ("9기 기준 지각에 해당하는 시점은?", ["훈련 시작 10분 후 입실", "점심 5분 전", "체크아웃 후", "주말 접속"], 0, "백서의 출결 기준은 09:11부터 지각으로 설명합니다."),
            ("정상 수료 기준으로 맞는 것은?", ["전체 소정훈련일수 80% 이상 출석", "모든 시험 만점", "블로그 10개 작성", "교육장 예약 5회"], 0, "백서에는 106일 중 80% 이상, 즉 85일 이상 출석 기준이 제시됩니다."),
        ],
    }
    selected_topic = topic if topic in candidates else "프로젝트 수행"
    base = candidates[selected_topic]
    questions = []
    for i, (q, choices, answer_index, explanation) in enumerate(base, 1):
        questions.append({"topic": selected_topic, "question": q, "choices": choices, "answer_index": answer_index, "explanation": explanation})
    while len(questions) < 5:
        questions.append({
            "topic": selected_topic,
            "question": f"{selected_topic} 학습 후 오답을 관리하는 가장 적절한 방식은?",
            "choices": ["틀린 이유와 관련 개념을 함께 기록한다", "점수만 저장한다", "다음 시험 전까지 보지 않는다", "정답만 외운다"],
            "answer_index": 0,
            "explanation": "오답노트는 틀린 문제, 관련 개념, 해설을 함께 정리해야 복습 효과가 있습니다.",
        })
    return questions[:5]


def generate_quiz(topic: str, prep_material: str, count: int = 5) -> List[Dict[str, Any]]:
    context = make_context(search_whitepaper(f"{topic} 커리큘럼 핵심 개념", k=5))
    system = "너는 백서 기반 쪽지시험 출제자다. 반드시 JSON 배열만 출력한다."
    user = f"""
주제: {topic}
예습 자료:
{prep_material[:3500]}

백서 근거:
{context}

{count}개의 객관식 문제를 만든다.
JSON 스키마:
[
  {{"topic":"주제명", "question":"문항", "choices":["선지1","선지2","선지3","선지4"], "answer_index":0, "explanation":"해설"}}
]
조건:
- answer_index는 0~3 정수
- 백서에 근거가 없는 사실은 내지 않음
- 정답 위치는 문항마다 섞기
""".strip()
    raw = ask_llm(system, user, temperature=0.25)
    parsed = extract_json_array(raw or "")
    if not parsed:
        parsed = fallback_quiz(topic)
    cleaned = []
    for item in parsed:
        choices = item.get("choices") or []
        if len(choices) != 4:
            continue
        answer_index = int(item.get("answer_index", 0))
        if not 0 <= answer_index <= 3:
            answer_index = 0
        cleaned.append({
            "topic": item.get("topic", topic),
            "question": item.get("question", "문항 없음"),
            "choices": choices,
            "answer_index": answer_index,
            "explanation": item.get("explanation", "해설 없음"),
        })
    return cleaned[:count] if cleaned else fallback_quiz(topic)


def judge_level(score: float) -> str:
    if score >= 85:
        return "고급"
    if score >= 60:
        return "중급"
    return "초급"


def save_result(payload: Dict[str, Any]) -> None:
    rows = read_json(RESULT_PATH, [])
    rows.append(payload)
    write_json(RESULT_PATH, rows)


def save_wrong_notes(items: List[Dict[str, Any]]) -> None:
    rows = read_json(WRONG_NOTE_PATH, [])
    rows.extend(items)
    write_json(WRONG_NOTE_PATH, rows)


def build_topic_stats(quiz: List[Dict[str, Any]], selected: Dict[int, int]) -> pd.DataFrame:
    bucket: Dict[str, Dict[str, int]] = {}
    for idx, q in enumerate(quiz):
        topic = q.get("topic", "기타")
        bucket.setdefault(topic, {"correct": 0, "total": 0})
        bucket[topic]["total"] += 1
        if selected.get(idx) == q.get("answer_index"):
            bucket[topic]["correct"] += 1
    rows = []
    for topic, stat in bucket.items():
        total = max(1, stat["total"])
        rows.append({"주제": topic, "정답률": round(stat["correct"] / total * 100, 1), "문항수": total})
    return pd.DataFrame(rows)


def study_recommendation(level: str, weak_topics: List[str]) -> str:
    lines = [f"### 수준별 스터디 추천: {level}"]
    for item in LEVEL_GUIDE[level]["study"]:
        lines.append(f"- {item}")
    if weak_topics:
        lines.append("\n### 우선 보완 주제")
        for topic in weak_topics:
            lines.append(f"- {topic}: 예습 자료 재생성 → 같은 주제 쪽지시험 재응시 → 오답노트 갱신")
    return "\n".join(lines)


# ============================================================
# 공고/공모전 추천 및 캘린더
# ============================================================

def summarize_notice(notice_text: str, interests: str) -> Dict[str, str]:
    system = "공고, 공모전, 프로젝트, 채용형 프로그램 정보를 학습자 관점으로 정리한다. JSON만 출력한다."
    user = f"""
관심 분야: {interests}
공고 내용:
{notice_text[:5000]}

JSON 스키마:
{{"title":"제목", "type":"공모전/프로젝트/채용형 프로그램/기타", "deadline":"YYYY-MM-DD 또는 미확인", "fit":"추천 이유", "actions":"바로 할 일", "risk":"확인 필요 사항"}}
""".strip()
    raw = ask_llm(system, user, temperature=0.2)
    if raw:
        try:
            return json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
        except Exception:
            pass
    deadline = re.search(r"(20\d{2})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})", notice_text)
    deadline_text = "미확인"
    if deadline:
        yyyy, mm, dd = deadline.groups()
        deadline_text = f"{yyyy}-{int(mm):02d}-{int(dd):02d}"
    title = notice_text.strip().split("\n")[0][:60] if notice_text.strip() else "공고"
    tokens = set(re.findall(r"[가-힣A-Za-z0-9]+", interests.lower()))
    overlap = [t for t in tokens if t and t in notice_text.lower()]
    return {
        "title": title,
        "type": "기타",
        "deadline": deadline_text,
        "fit": "관심 키워드와 일부 일치합니다." if overlap else "관심 분야와의 직접 관련성은 추가 확인이 필요합니다.",
        "actions": "지원 자격, 제출물, 마감일을 확인하고 캘린더에 등록합니다.",
        "risk": "공식 공고 원문 기준으로 일정과 자격을 확인해야 합니다.",
    }


def read_calendar() -> List[Dict[str, Any]]:
    rows = read_json(CALENDAR_PATH, [])
    if rows:
        return rows
    seed = [
        {"id": str(uuid.uuid4()), "date": "2026-03-31", "title": "입교식", "kind": "교육", "note": "9기 교육 시작"},
        {"id": str(uuid.uuid4()), "date": "2026-05-15", "title": "AIVLE DAY 1차", "kind": "교육", "note": "포트폴리오 강의, 코딩테스트"},
        {"id": str(uuid.uuid4()), "date": "2026-06-26", "title": "AIVLE DAY 2차", "kind": "교육", "note": "면접 특강"},
        {"id": str(uuid.uuid4()), "date": "2026-08-27", "title": "Job Fair", "kind": "취업", "note": "취업컨설팅데이 시작"},
        {"id": str(uuid.uuid4()), "date": "2026-09-03", "title": "수료식", "kind": "교육", "note": "수료증 수여"},
    ]
    write_json(CALENDAR_PATH, seed)
    return seed


def add_calendar_event(title: str, event_date: str, kind: str, note: str) -> None:
    rows = read_calendar()
    rows.append({"id": str(uuid.uuid4()), "date": event_date, "title": title, "kind": kind, "note": note})
    write_json(CALENDAR_PATH, rows)


def delete_calendar_event(event_id: str) -> None:
    rows = [row for row in read_calendar() if row.get("id") != event_id]
    write_json(CALENDAR_PATH, rows)


# ============================================================
# 대화 저장
# ============================================================

def load_conversations() -> Dict[str, Any]:
    data = read_json(CONVERSATION_PATH, {})
    if data:
        return data
    first_id = str(uuid.uuid4())
    data = {
        first_id: {
            "id": first_id,
            "title": "새 학습 대화",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "messages": [],
        }
    }
    write_json(CONVERSATION_PATH, data)
    return data


def save_conversations(data: Dict[str, Any]) -> None:
    write_json(CONVERSATION_PATH, data)


def current_conversation_id() -> str:
    conversations = load_conversations()
    if "conversation_id" not in st.session_state or st.session_state.conversation_id not in conversations:
        st.session_state.conversation_id = next(iter(conversations.keys()))
    return st.session_state.conversation_id


def create_conversation() -> str:
    conversations = load_conversations()
    conv_id = str(uuid.uuid4())
    conversations[conv_id] = {
        "id": conv_id,
        "title": "새 학습 대화",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "messages": [],
    }
    save_conversations(conversations)
    st.session_state.conversation_id = conv_id
    return conv_id


def append_message(conv_id: str, role: str, content: str, sources: Optional[List[Dict[str, Any]]] = None) -> None:
    conversations = load_conversations()
    if conv_id not in conversations:
        return
    conversations[conv_id]["messages"].append({
        "role": role,
        "content": content,
        "sources": sources or [],
        "time": datetime.now().isoformat(timespec="seconds"),
    })
    if role == "user" and conversations[conv_id]["title"] == "새 학습 대화":
        conversations[conv_id]["title"] = content[:28] + ("..." if len(content) > 28 else "")
    save_conversations(conversations)


# ============================================================
# 공통 렌더링
# ============================================================

def hero(title: str, body: str) -> None:
    st.markdown(f"<div class='hero'><h1>{title}</h1><p>{body}</p></div>", unsafe_allow_html=True)


def card(markdown_text: str) -> None:
    st.markdown(f"<div class='panel'>{markdown_text}</div>", unsafe_allow_html=True)


def render_sources(hits: List[SearchHit]) -> None:
    if not hits:
        return
    with st.expander("검색된 백서 근거", expanded=False):
        for i, hit in enumerate(hits, 1):
            st.markdown(
                f"<div class='source-box'><b>근거 {i}</b> · 유사도 {hit.score:.3f}<br>"
                f"<span class='small-note'>{hit.title}</span><br>{hit.text[:650]}{'...' if len(hit.text) > 650 else ''}</div>",
                unsafe_allow_html=True,
            )


def render_link_table(links: List[Dict[str, str]]) -> None:
    if links:
        st.markdown("#### 관련 학습 사이트 링크")
        st.dataframe(pd.DataFrame(links), hide_index=True, use_container_width=True)


def ensure_whitepaper_ready() -> bool:
    if WHITEPAPER_PATH.exists():
        return True
    st.markdown("<div class='danger-note'>백서 파일이 없습니다. 사이드바에서 DOCX/PDF/TXT 백서를 업로드해야 합니다.</div>", unsafe_allow_html=True)
    return False


def render_login_page() -> None:
    hero("AIVLE Navigator 로그인", "백서 기반 학습 어시스턴트를 사용하려면 로그인해야 합니다.")
    left, center, right = st.columns([1, 1.1, 1])
    with center:
        st.markdown("### 로그인")
        with st.form("login_form", clear_on_submit=False):
            login_id = st.text_input("아이디")
            login_password = st.text_input("비밀번호", type="password")
            submitted = st.form_submit_button("로그인", use_container_width=True)

        if submitted:
            if authenticate(login_id.strip(), login_password):
                st.session_state["authenticated"] = True
                st.session_state["login_error"] = ""
                st.session_state["active_page"] = "대시보드"
                st.rerun()
            else:
                st.session_state["login_error"] = "아이디 또는 비밀번호가 일치하지 않습니다."

        if st.session_state.get("login_error"):
            st.error(st.session_state["login_error"])

        st.caption("배포 시 Streamlit Secrets에 APP_LOGIN_ID, APP_LOGIN_PASSWORD를 설정하세요.")


def render_header_metrics() -> None:
    index = load_index()
    chunk_count = len(index["chunks"]) if index else 0
    conv_count = len(load_conversations())
    result_count = len(read_json(RESULT_PATH, []))
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("백서 파일", WHITEPAPER_PATH.name if WHITEPAPER_PATH.exists() else "없음")
    col2.metric("검색 청크", f"{chunk_count:,}")
    col3.metric("저장 대화", f"{conv_count:,}")
    col4.metric("진단 기록", f"{result_count:,}")


def render_sidebar() -> str:
    st.sidebar.markdown("## 🧭 AIVLE Navigator")
    st.sidebar.caption("로그인됨")
    if st.sidebar.button("로그아웃", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["login_error"] = ""
        st.rerun()

    st.sidebar.divider()
    page = st.sidebar.radio(
        "메뉴",
        MENU_OPTIONS,
        index=MENU_OPTIONS.index(st.session_state.get("active_page", "대시보드")),
        key="active_page",
    )
    st.sidebar.divider()

    if st.sidebar.button("새 대화 만들기", use_container_width=True):
        create_conversation()
        st.rerun()

    conversations = load_conversations()
    labels = {cid: f"{conv.get('title', '대화')}" for cid, conv in conversations.items()}
    selected = st.sidebar.selectbox(
        "대화 목록",
        options=list(conversations.keys()),
        format_func=lambda cid: labels.get(cid, cid),
        index=list(conversations.keys()).index(current_conversation_id()) if current_conversation_id() in conversations else 0,
    )
    st.session_state.conversation_id = selected

    if st.sidebar.button("현재 대화 삭제", use_container_width=True):
        data = load_conversations()
        if len(data) <= 1:
            data[selected]["messages"] = []
            data[selected]["title"] = "새 학습 대화"
        else:
            data.pop(selected, None)
            st.session_state.conversation_id = next(iter(data.keys()))
        save_conversations(data)
        st.rerun()

    st.sidebar.divider()
    uploaded = st.sidebar.file_uploader("백서 교체", type=["docx"])
    if uploaded:
        WHITEPAPER_PATH.write_bytes(uploaded.getbuffer())
        st.cache_resource.clear()
        st.sidebar.success("백서가 교체되었습니다. 앱을 새로고침하면 새 인덱스가 적용됩니다.")

    key_exists = bool(get_api_key())
    st.sidebar.caption(f"LLM 상태: {'사용 가능' if key_exists else '환경변수/Secrets 미설정'}")
    st.sidebar.caption("API 키는 파일에 저장하지 않습니다.")
    return page


# ============================================================
# 페이지
# ============================================================

def page_dashboard() -> None:
    hero("AIVLE Navigator", "백서를 기반으로 질문, 예습, 수준진단, 복습, 일정, 외부활동 관리를 한 화면에서 연결합니다.")
    render_header_metrics()
    st.markdown("### 기능 구성")
    rows = [
        ["학습 질의", "추천 질문 / 빠른 질문 버튼", "질문 작성 없이 백서 기반 답변 생성"],
        ["예습 지원", "예습 자료 생성", "주차·주제별 핵심 개념 사전 파악"],
        ["수준 진단", "쪽지시험 생성 및 등급 판별", "초급·중급·고급 기준 학습 경로 제시"],
        ["맞춤 학습", "수준별 스터디 추천", "취약 주제 중심 학습 전략 제공"],
        ["학습 분석", "부족한 주제 시각화", "주제별 정답률 확인"],
        ["복습 지원", "오답노트", "틀린 문제·개념·해설 저장"],
        ["정보 추천", "공고 정리 / 공모전 추천", "외부 경험과 학습 주제 연결"],
        ["일정 관리", "캘린더", "수업·시험·스터디·마감일 통합 관리"],
        ["커리큘럼 관리", "커리큘럼 확인", "현재 위치와 다음 학습 내용 파악"],
        ["대화 관리", "대화 목록 저장", "이전 학습 흐름 재개"],
        ["자료 추천", "학습 사이트 링크 추천", "백서 링크와 공식 사이트 연결"],
    ]
    st.dataframe(pd.DataFrame(rows, columns=["구분", "기능명", "앱 구현 방식"]), hide_index=True, use_container_width=True)

    st.markdown("### 빠른 시작")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("질문으로 시작", use_container_width=True):
            st.session_state["pending_chat"] = "에이블스쿨 전체 학습 흐름을 요약해줘"
            st.session_state["active_page"] = "학습 질의"
            st.rerun()
    with col2:
        if st.button("예습 자료 만들기", use_container_width=True):
            st.session_state["active_page"] = "예습·쪽지시험"
            st.rerun()
    with col3:
        if st.button("캘린더 보기", use_container_width=True):
            st.session_state["active_page"] = "공고·캘린더"
            st.rerun()


def page_chat() -> None:
    hero("학습 질의", "추천 질문 버튼 또는 직접 질문으로 백서 기반 답변을 생성하고 대화 목록에 저장합니다.")
    if not ensure_whitepaper_ready():
        return

    st.markdown("### 추천 질문")
    tabs = st.tabs(list(QUICK_QUESTION_GROUPS.keys()))
    for tab, (_, questions) in zip(tabs, QUICK_QUESTION_GROUPS.items()):
        with tab:
            cols = st.columns(3)
            for idx, q in enumerate(questions):
                if cols[idx % 3].button(q, key=f"quick_{q}", use_container_width=True):
                    st.session_state["pending_chat"] = q
                    st.rerun()

    conv_id = current_conversation_id()
    conversations = load_conversations()
    messages = conversations[conv_id]["messages"]
    st.divider()

    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                hits = [SearchHit(**src) for src in msg["sources"]]
                render_sources(hits)

    pending = st.session_state.pop("pending_chat", None)
    question = pending or st.chat_input("백서 기준으로 질문을 입력하세요")
    if question:
        append_message(conv_id, "user", question)
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            answer, hits, links = answer_from_whitepaper(question)
            st.markdown(answer)
            render_sources(hits)
            render_link_table(links)
        append_message(
            conv_id,
            "assistant",
            answer,
            sources=[{"index": h.index, "score": h.score, "title": h.title, "text": h.text} for h in hits],
        )
        st.rerun()


def page_prep_quiz() -> None:
    hero("예습·쪽지시험", "커리큘럼 주차와 주제를 선택해 예습 자료를 만들고, 그 자료를 기반으로 쪽지시험을 생성합니다.")
    if not ensure_whitepaper_ready():
        return

    left, right = st.columns([0.9, 1.1])
    with left:
        st.markdown("### 예습 조건")
        week_options = [f"{row['week']} · {row['topic']}" for row in DEFAULT_CURRICULUM]
        selected_week = st.selectbox("주차", week_options)
        topic = st.selectbox("주제", list(TOPIC_ALIASES.keys()))
        minutes = st.slider("예습 가능 시간", 10, 90, 30, step=10)
        if st.button("예습 자료 생성", use_container_width=True):
            material, hits = generate_prep_material(selected_week, topic, minutes)
            st.session_state["prep_material"] = material
            st.session_state["prep_topic"] = topic
            st.session_state["prep_sources"] = [{"index": h.index, "score": h.score, "title": h.title, "text": h.text} for h in hits]
            st.rerun()

    with right:
        st.markdown("### 생성된 예습 자료")
        material = st.session_state.get("prep_material")
        if material:
            st.markdown(material)
            render_sources([SearchHit(**h) for h in st.session_state.get("prep_sources", [])])
        else:
            st.info("예습 조건을 선택하고 자료를 생성하세요.")

    st.divider()
    st.markdown("### 쪽지시험")
    if st.button("현재 예습 자료로 쪽지시험 생성", disabled=not bool(st.session_state.get("prep_material")), use_container_width=True):
        topic = st.session_state.get("prep_topic", "프로젝트 수행")
        st.session_state["quiz"] = generate_quiz(topic, st.session_state.get("prep_material", ""), count=5)
        st.session_state["quiz_submitted"] = False
        st.rerun()

    quiz = st.session_state.get("quiz", [])
    if not quiz:
        return

    selected: Dict[int, int] = {}
    with st.form("quiz_form"):
        for idx, item in enumerate(quiz):
            choice = st.radio(
                f"Q{idx + 1}. {item['question']}",
                options=list(range(len(item["choices"]))),
                format_func=lambda i, item=item: item["choices"][i],
                key=f"quiz_choice_{idx}_{item['question'][:12]}",
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
        score = round(correct / len(quiz) * 100, 1)
        level = judge_level(score)
        stats = build_topic_stats(quiz, selected)
        weak_topics = stats.loc[stats["정답률"] < 70, "주제"].tolist()
        save_result({
            "time": datetime.now().isoformat(timespec="seconds"),
            "topic": st.session_state.get("prep_topic", "기타"),
            "score": score,
            "level": level,
            "stats": stats.to_dict(orient="records"),
        })
        save_wrong_notes(wrong_items)
        st.session_state["last_quiz_result"] = {"score": score, "level": level, "stats": stats.to_dict(orient="records"), "weak_topics": weak_topics, "wrong_items": wrong_items}
        st.rerun()

    result = st.session_state.get("last_quiz_result")
    if result:
        st.success(f"점수: {result['score']}점 / 학습 등급: {result['level']}")
        stats_df = pd.DataFrame(result["stats"])
        if not stats_df.empty:
            st.bar_chart(stats_df.set_index("주제")["정답률"])
        st.markdown(study_recommendation(result["level"], result["weak_topics"]))
        if result["wrong_items"]:
            st.markdown("### 방금 생성된 오답노트")
            for item in result["wrong_items"]:
                st.markdown(f"**{item['topic']}** · {item['question']}\n\n- 내 답: {item['my_answer']}\n- 정답: {item['correct_answer']}\n- 해설: {item['explanation']}")


def page_analysis() -> None:
    hero("학습 분석·오답노트", "쪽지시험 결과를 누적해 등급과 취약 주제를 확인하고 오답을 복습합니다.")
    results = read_json(RESULT_PATH, [])
    wrong_notes = read_json(WRONG_NOTE_PATH, [])

    if not results:
        st.info("아직 저장된 쪽지시험 결과가 없습니다.")
    else:
        df = pd.DataFrame(results)
        col1, col2, col3 = st.columns(3)
        col1.metric("응시 횟수", len(df))
        col2.metric("평균 점수", f"{df['score'].mean():.1f}")
        col3.metric("최근 등급", df.iloc[-1]["level"])
        trend = df[["time", "score"]].copy()
        trend["time"] = pd.to_datetime(trend["time"])
        st.line_chart(trend.set_index("time")["score"])

        topic_rows = []
        for row in results:
            for stat in row.get("stats", []):
                topic_rows.append({"time": row.get("time"), **stat})
        if topic_rows:
            topic_df = pd.DataFrame(topic_rows)
            summary = topic_df.groupby("주제", as_index=False).agg({"정답률": "mean", "문항수": "sum"})
            summary["정답률"] = summary["정답률"].round(1)
            st.markdown("### 부족한 주제 시각화")
            st.bar_chart(summary.set_index("주제")["정답률"])
            st.dataframe(summary, hide_index=True, use_container_width=True)

    st.divider()
    st.markdown("### 오답노트")
    if not wrong_notes:
        st.info("저장된 오답이 없습니다.")
        return
    topic_filter = st.selectbox("주제 필터", ["전체"] + sorted({item.get("topic", "기타") for item in wrong_notes}))
    filtered = wrong_notes if topic_filter == "전체" else [item for item in wrong_notes if item.get("topic") == topic_filter]
    for item in reversed(filtered[-30:]):
        with st.expander(f"{item.get('topic')} · {item.get('question')}"):
            st.markdown(f"- 내 답: {item.get('my_answer')}\n- 정답: {item.get('correct_answer')}\n- 해설: {item.get('explanation')}\n- 기록 시각: {item.get('time')}")
            links = link_recommendations(item.get("topic", ""))
            render_link_table(links)


def page_opportunities_calendar() -> None:
    hero("공고·캘린더", "공모전, 프로젝트, 채용형 프로그램 정보를 정리하고 마감일을 학습 캘린더에 연결합니다.")
    left, right = st.columns([1, 1])

    with left:
        st.markdown("### 공고 정리 / 공모전 추천")
        interests = st.text_input("관심 분야", value="AI, DX, Cloud, 데이터 분석, 서비스 기획")
        notice = st.text_area("공고 내용 또는 링크 주변 텍스트", height=220, placeholder="공고명, 지원 자격, 마감일, 제출물, URL 등을 붙여넣으세요.")
        if st.button("공고 정리", use_container_width=True, disabled=not bool(notice.strip())):
            summary = summarize_notice(notice, interests)
            st.session_state["notice_summary"] = summary
        summary = st.session_state.get("notice_summary")
        if summary:
            st.json(summary)
            if summary.get("deadline") and summary["deadline"] != "미확인":
                if st.button("마감일을 캘린더에 추가", use_container_width=True):
                    add_calendar_event(summary.get("title", "공고 마감"), summary["deadline"], summary.get("type", "공고"), summary.get("actions", ""))
                    st.success("캘린더에 추가되었습니다.")

    with right:
        st.markdown("### 일정 추가")
        with st.form("calendar_add"):
            title = st.text_input("일정명")
            event_date = st.date_input("날짜", value=date.today())
            kind = st.selectbox("구분", ["수업", "시험", "스터디", "공모전", "채용", "개인"])
            note = st.text_area("메모", height=90)
            ok = st.form_submit_button("일정 저장")
            if ok and title:
                add_calendar_event(title, event_date.isoformat(), kind, note)
                st.success("일정이 저장되었습니다.")

    st.divider()
    st.markdown("### 캘린더")
    events = read_calendar()
    event_df = pd.DataFrame(events)
    if event_df.empty:
        st.info("등록된 일정이 없습니다.")
        return
    event_df["date"] = pd.to_datetime(event_df["date"], errors="coerce")
    month = st.selectbox("월 필터", ["전체"] + sorted(event_df["date"].dt.strftime("%Y-%m").dropna().unique().tolist()))
    display_df = event_df if month == "전체" else event_df[event_df["date"].dt.strftime("%Y-%m") == month]
    display_df = display_df.sort_values("date")
    st.dataframe(display_df[["date", "kind", "title", "note"]], hide_index=True, use_container_width=True)

    delete_target = st.selectbox("삭제할 일정", [""] + display_df["id"].tolist(), format_func=lambda eid: "선택 안 함" if not eid else display_df.loc[display_df["id"] == eid, "title"].iloc[0])
    if delete_target and st.button("선택 일정 삭제"):
        delete_calendar_event(delete_target)
        st.rerun()


def page_curriculum() -> None:
    hero("커리큘럼", "전체 교육 과정과 주차별 학습 내용을 확인하고 관련 백서 근거를 검색합니다.")
    df = pd.DataFrame(DEFAULT_CURRICULUM)
    kind_filter = st.multiselect("구분", sorted(df["kind"].unique()), default=sorted(df["kind"].unique()))
    keyword = st.text_input("커리큘럼 검색", placeholder="예: 생성형 AI, 빅프로젝트, Cloud")
    filtered = df[df["kind"].isin(kind_filter)]
    if keyword:
        mask = filtered.apply(lambda row: keyword.lower() in " ".join(map(str, row.values)).lower(), axis=1)
        filtered = filtered[mask]
    st.dataframe(filtered, hide_index=True, use_container_width=True)

    st.divider()
    st.markdown("### 백서에서 추가 확인")
    query = st.text_input("백서 검색어", value=keyword or "커리큘럼")
    if st.button("백서 근거 검색", use_container_width=True):
        hits = search_whitepaper(query, k=8)
        render_sources(hits)


def page_settings() -> None:
    hero("설정", "백서 파일, API 키 설정 방식, 저장 데이터 상태를 확인합니다.")
    st.markdown("### 백서")
    st.write(f"앱 내부 백서명: `{WHITEPAPER_PATH.name}`")
    st.write(f"존재 여부: `{WHITEPAPER_PATH.exists()}`")
    if WHITEPAPER_PATH.exists():
        st.download_button("현재 백서 다운로드", data=WHITEPAPER_PATH.read_bytes(), file_name=WHITEPAPER_PATH.name, use_container_width=True)

    st.markdown("### API 키")
    st.markdown(
        "OPENAI_API_KEY는 코드나 저장소에 넣지 말고 Streamlit Secrets, Hugging Face Space Secrets, 또는 서버 환경변수로 설정하세요."
    )
    st.code("OPENAI_API_KEY=sk-...", language="bash")
    st.write(f"현재 감지 상태: {'설정됨' if get_api_key() else '미설정'}")

    st.markdown("### 로그인 설정")
    st.markdown("기본값은 `admin / aivle2026`입니다. 배포 시 Secrets에서 반드시 바꾸는 것을 권장합니다.")
    st.code('APP_LOGIN_ID="admin"\nAPP_LOGIN_PASSWORD="원하는_비밀번호"', language="toml")

    st.markdown("### 저장 데이터")
    for path in [CONVERSATION_PATH, RESULT_PATH, WRONG_NOTE_PATH, CALENDAR_PATH]:
        size = path.stat().st_size if path.exists() else 0
        st.write(f"`{path.name}` · {size} bytes")
    if st.button("캐시 초기화", use_container_width=True):
        st.cache_resource.clear()
        st.success("캐시가 초기화되었습니다.")


def main() -> None:
    init_session_defaults()

    if not st.session_state.get("authenticated"):
        render_login_page()
        return

    page = render_sidebar()

    if page == "대시보드":
        page_dashboard()
    elif page == "학습 질의":
        page_chat()
    elif page == "예습·쪽지시험":
        page_prep_quiz()
    elif page == "학습 분석·오답노트":
        page_analysis()
    elif page == "공고·캘린더":
        page_opportunities_calendar()
    elif page == "커리큘럼":
        page_curriculum()
    else:
        page_settings()


if __name__ == "__main__":
    main()
