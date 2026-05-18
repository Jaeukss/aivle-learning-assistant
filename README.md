# AIVLE 학습도우미

Streamlit 기반 학습자용 AI 학습 보조 앱입니다.

## v15 수정 사항

- 백서 검색 RAG에 Query Rewriting 추가
- Multi Query 검색 추가
- 복합 질문용 Sub Query 분해 추가
- HyDE는 요청에 따라 제외
- API 키가 없어도 fallback 쿼리 확장으로 앱이 중단되지 않도록 처리
- 학습 질의와 예습 자료 생성에서 정밀 검색 경로 사용


## 이번 수정 사항

- 새로고침 시 로그인 상태가 유지되도록 HMAC 기반 URL 토큰 처리 추가
- 사이드바 메뉴를 한 번만 클릭해도 바로 이동되도록 상태 동기화 수정
- 사이드바를 닫아도 다시 열 수 있도록 header/toolbar 전체 숨김 CSS 제거
- 일정·커리큘럼 > 캘린더 탭에 월간 달력형 화면 적용
- 기존 Query Rewriting, Multi Query, Sub Query 기반 RAG 검색 구조 유지

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
OPENAI_API_KEY = "본인 OpenAI API 키"
OPENAI_MODEL = "gpt-4o-mini"
APP_LOGIN_ID = "admin"
APP_LOGIN_PASSWORD = "aivle2026"
```
