# AIVLE 학습도우미

Streamlit 기반 학습자용 AI 학습 보조 앱입니다.

## v13 수정 사항

- HTML 카드 코드가 화면에 그대로 노출되는 문제 수정
- 요약 카드를 Streamlit 네이티브 컨테이너로 변경
- 학습 질의 화면에 고정 높이 대화창 추가
- 대화 초기화 버튼 추가
- 대화 기록이 페이지 전체에 계속 길게 쌓이지 않도록 최근 30개 메시지만 대화창에 표시
- 사용자 입력값/파일명이 HTML로 노출되지 않도록 이스케이프 처리

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
