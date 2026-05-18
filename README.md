# AIVLE 학습도우미

Streamlit 기반 학습자용 AI 학습 도우미입니다.

## 주요 기능

- 백서 기반 학습 질의응답
- Query Rewriting, Multi Query, Sub Query 기반 백서 검색 고도화
- 예습 자료 생성 및 쪽지시험
- 오답노트 및 학습 분석
- 포트폴리오, 면접, 채용공고, 공모전 분석
- 백서 업로드와 사용자 업로드 자료 분리
- 로그인 유지 토큰
- 사이드바가 닫혀도 사용할 수 있는 상단 빠른 이동 / 학습 자료 관리
- streamlit-calendar 기반 월간 달력형 캘린더

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Secrets 예시

```toml
OPENAI_API_KEY = "본인 OpenAI API 키"
OPENAI_MODEL = "gpt-4o-mini"
APP_LOGIN_ID = "admin"
APP_LOGIN_PASSWORD = "aivle2026"
APP_LOGIN_SECRET = "로그인 토큰 서명용 긴 문자열"
```

`APP_LOGIN_SECRET`은 선택값입니다. 없으면 `APP_LOGIN_PASSWORD`를 기반으로 로그인 유지 토큰을 서명합니다.
