# AIVLE 학습도우미

Streamlit 기반 AIVLE 학습자용 보조 앱입니다.

## 핵심 메뉴

- 대시보드: 오늘의 체크리스트, 학습 흐름
- 학습 질의: 백서 기반 Q&A, 추천 질문, 학습 사이트 링크
- 예습·진단: 예습 자료 생성, 쪽지시험, 수준 판별
- 복습·분석: 취약 주제, 오답노트, AI 학습 코치
- 취업 준비: 포트폴리오 파일 분석, 면접 질문, 채용공고 분석, 문장 정리
- 일정·커리큘럼: 커리큘럼, 학습 플래너, 캘린더
- 내 학습 현황: 저장 기록 확인

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Secrets 예시

```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"
APP_LOGIN_ID = "admin"
APP_LOGIN_PASSWORD = "aivle2026"
```
