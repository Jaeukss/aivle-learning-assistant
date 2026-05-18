# AIVLE 학습도우미

Streamlit 기반 백서 학습 지원 앱입니다.

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

## 주요 기능

- 백서 기반 학습 질의응답
- 추천 질문 버튼
- 예습 자료 생성
- 쪽지시험 생성
- 학습 등급 판별
- 부족한 주제 시각화
- 오답노트
- 공고 정리 / 캘린더
- 커리큘럼 확인
- 대화 목록 저장

## 폴더 구조

```text
app.py
requirements.txt
.streamlit/config.toml
data/aivle_kt_learning_whitepaper_2026.docx
storage/
```
