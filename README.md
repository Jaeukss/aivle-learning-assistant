# AIVLE Navigator

KT AIVLE School 백서를 기반으로 학습 질의, 예습 자료 생성, 쪽지시험, 수준 진단, 오답노트, 공고 정리, 캘린더, 커리큘럼 확인, 대화 저장을 제공하는 Streamlit 앱입니다.

## 파일 구성

```text
app.py
requirements.txt
.streamlit/config.toml
data/aivle_kt_learning_whitepaper_2026.docx
storage/                 # 실행 중 자동 생성되는 JSON 저장소
```

## 실행 방법

```bash
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
streamlit run app.py
```

Streamlit Cloud 또는 Hugging Face Spaces에서는 `OPENAI_API_KEY`를 Secrets에 등록하세요. API 키를 코드에 직접 넣지 마세요.

## 구현 기능

- 추천 질문 / 빠른 질문 버튼
- 백서 기반 학습 질의응답
- 주차·주제별 예습 자료 생성
- 예습 자료 기반 쪽지시험 생성
- 시험 결과 기반 초급·중급·고급 판별
- 수준별 스터디 추천
- 부족한 주제 시각화
- 오답노트 저장 및 복습
- 공고 정리 / 공모전 추천
- 캘린더 일정 관리
- 커리큘럼 확인
- ChatGPT식 대화 목록 저장
- 학습 사이트 링크 추천

## 보안 메모

업로드한 `api_key.txt`는 패키지에 포함하지 않았습니다. 실제 키가 외부에 노출되었다면 OpenAI, Hugging Face, SendGrid 콘솔에서 즉시 폐기·재발급하세요.
