# AIVLE 학습도우미

Streamlit 기반 학습자용 AI 학습 보조 앱입니다.

## v17 수정 사항

- 새로고침 후에도 로그인 상태가 유지되도록 HMAC query token 기반 자동 인증 추가
- 사이드바 메뉴를 한 번 클릭하면 즉시 이동되도록 session_state 동기화 수정
- 사이드바 닫힘 후 다시 열 수 있도록 사이드바 토글 표시 보완
- 일정·커리큘럼 > 캘린더 탭에 월간 달력형 캘린더 적용
- streamlit-calendar가 없거나 실패하면 HTML 달력으로 대체

## v15 수정 사항

- 백서 검색 RAG에 Query Rewriting 추가
- Multi Query 검색 추가
- 복합 질문용 Sub Query 분해 추가
- HyDE는 요청에 따라 제외
- API 키가 없어도 fallback 쿼리 확장으로 앱이 중단되지 않도록 처리
- 학습 질의와 예습 자료 생성에서 정밀 검색 경로 사용

## 주요 기능

- 로그인
- 대시보드
- 학습 질의
- 예습·진단
- 복습·분석
- 취업 준비
- 일정·커리큘럼
- 내 학습 현황
- 백서/커리큘럼 업로드
- 백서 기반 검색
- AI 답변 생성
- 쪽지시험 생성
- 오답노트 저장
- 포트폴리오/공고/면접 분석

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 환경변수 또는 Streamlit Secrets

```toml
OPENROUTER_API_KEY = "본인 OpenRouter API 키"
APP_LOGIN_ID = "admin"
APP_LOGIN_PASSWORD = "aivle2026"
```

LLM 생성은 OpenRouter API를 사용합니다. 기본 모델은 `nvidia/nemotron-3-super-120b-a12b:free` 단일 모델입니다.
API key가 없으면 백서 검색과 로컬 fallback 답변은 계속 동작하지만, 생성형 답변 품질은 제한됩니다.
