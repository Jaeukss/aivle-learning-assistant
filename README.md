# AIVLE 학습도우미

Streamlit 기반 AIVLE 학습자용 학습·진단·취업 준비 보조 앱입니다.

## 주요 개편 내용

- 따뜻한 아이보리 배경과 딥 그린 중심의 학습 플랫폼 UI
- Pretendard 계열 폰트 적용
- 대시보드에서 오늘의 학습 진행률, 추천 행동, 학습 자료 상태 확인
- 학습 질의, 예습·진단, 복습·분석, 취업 준비, 일정·커리큘럼, 내 학습 현황 유지
- 포트폴리오·면접·채용공고 분석은 사용자 업로드 자료 기반으로 처리
- 백서/커리큘럼 업로드 시 텍스트 추출 실패 파일은 앱을 중단하지 않고 안내
- API 키가 없어도 검색·기본 답변·기본 시험 기능은 동작

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

## GitHub 적용 파일

아래 파일을 교체하면 됩니다.

```text
app.py
requirements.txt
README.md
.streamlit/config.toml
```

`data/aivle_kt_learning_whitepaper_2026.docx`가 이미 있으면 다시 올리지 않아도 됩니다.
