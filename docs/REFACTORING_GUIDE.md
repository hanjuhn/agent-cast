# Agent-Cast 리팩토링 가이드

## 🔄 리팩토링 개요

PersonalizeAgent와 QueryWriterAgent가 GPT-4를 사용하여 더 지능적으로 데이터를 수집하고 RAG 쿼리를 생성하도록 리팩토링되었습니다.

## 🆕 주요 변경사항

### 1. PersonalizeAgent 개선
- **이전**: 시뮬레이션된 데이터와 간단한 룰 기반 처리
- **현재**: MCP를 통한 실제 데이터 수집 + GPT-4를 통한 지능적 분석

#### 새로운 기능:
- MCP 연결 상태 자동 확인 및 관리
- Slack, Notion, Gmail에서 실제 데이터 수집
- GPT-4를 사용한 개인화된 정보 분석
- 구조화된 연구 컨텍스트 추출

### 2. QueryWriterAgent 개선
- **이전**: 하드코딩된 룰 기반 쿼리 생성
- **현재**: GPT-4를 사용한 지능적 RAG 쿼리 생성

#### 새로운 기능:
- 개인화된 정보를 기반으로 한 컨텍스트 인식 쿼리 생성
- 동적 검색 범위 설정
- 지능적 연구 우선순위 결정
- 폴백 메커니즘 개선

### 3. 새로운 LLM 클라이언트
- **파일**: `constants/llm_client.py`
- OpenAI GPT-4 API 통합
- 재시도 로직 및 오류 처리
- 개인화된 데이터 분석 전용 메서드

## 🛠️ 설치 및 설정

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정
`.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# OpenAI API (필수)
OPENAI_API_KEY=sk-your_openai_api_key_here

# MCP 서비스 (선택사항 - 없으면 폴백 모드)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
NOTION_INTEGRATION_TOKEN=secret_your_integration_token_here
GMAIL_CREDENTIALS_FILE=credentials.json
```

### 3. 테스트 실행
```bash
python test_refactored_agents.py
```

## 📋 새로운 워크플로우

```
1. PersonalizeAgent:
   ├── MCP 연결 확인
   ├── Slack/Notion/Gmail 데이터 수집
   ├── GPT-4로 데이터 분석
   └── 구조화된 개인화 정보 생성

2. QueryWriterAgent:
   ├── 개인화된 정보 통합
   ├── GPT-4로 RAG 쿼리 생성
   ├── 검색 범위 동적 설정
   └── 연구 우선순위 결정
```

## 🎯 주요 장점

### 1. 지능적 데이터 처리
- GPT-4가 수집된 원시 데이터를 분석하여 의미 있는 정보 추출
- 사용자의 실제 관심사와 연구 방향 파악

### 2. 개인화된 쿼리 생성
- 사용자별 맞춤형 RAG 검색 쿼리
- 동적 검색 범위 및 우선순위 설정

### 3. 견고한 폴백 시스템
- MCP 연결 실패 시에도 기본 기능 제공
- OpenAI API 실패 시 하드코딩된 기본값 사용

### 4. 확장 가능한 구조
- 새로운 MCP 소스 쉽게 추가 가능
- LLM 클라이언트를 통한 일관된 AI 기능 접근

## 🔧 코드 구조

### LLM 클라이언트 (`constants/llm_client.py`)
```python
class LLMClient:
    async def analyze_personalized_data(slack_data, notion_data, gmail_data)
    async def generate_rag_queries(personalized_info, user_query)
```

### PersonalizeAgent (`agents/personalize_agent.py`)
```python
class PersonalizeAgent:
    async def _collect_slack_data()      # MCP를 통한 Slack 데이터 수집
    async def _collect_notion_data()     # MCP를 통한 Notion 데이터 수집
    async def _collect_gmail_data()      # MCP를 통한 Gmail 데이터 수집
    def _structure_personal_info()       # LLM 분석 결과 구조화
```

### QueryWriterAgent (`agents/query_writer_agent.py`)
```python
class QueryWriterAgent:
    def _extract_rag_query()           # LLM 응답에서 쿼리 추출
    def _extract_search_scope()        # 검색 범위 추출
    def _extract_research_priorities() # 연구 우선순위 추출
```

## 🚀 사용법 예시

### 기본 실행
```python
import asyncio
from agents.personalize_agent import PersonalizeAgent
from agents.query_writer_agent import QueryWriterAgent
from state import WorkflowState

async def run_pipeline():
    # 1단계: 개인화 정보 수집
    personalize_agent = PersonalizeAgent()
    state = WorkflowState(user_query="AI 연구 동향 분석")
    state = await personalize_agent.process(state)
    
    # 2단계: RAG 쿼리 생성
    query_writer = QueryWriterAgent()
    state = await query_writer.process(state)
    
    print(f"생성된 쿼리: {state.rag_query}")

asyncio.run(run_pipeline())
```

## ⚠️ 주의사항

1. **OpenAI API 키**: GPT-4 사용을 위해 반드시 필요
2. **MCP 설정**: 선택사항이지만, 실제 데이터 수집을 위해 권장
3. **네트워크 연결**: API 호출을 위한 안정적인 인터넷 연결 필요
4. **비용**: OpenAI API 사용에 따른 비용 발생

## 🔍 문제 해결

### 1. OpenAI API 오류
```bash
Error: OpenAI API key is required
```
**해결방법**: `.env` 파일에 `OPENAI_API_KEY` 설정

### 2. MCP 연결 실패
```bash
Warning: MCP 연결 확인 실패
```
**해결방법**: MCP 설정을 확인하거나 폴백 모드로 계속 진행

### 3. JSON 파싱 오류
```bash
Error: JSON 파싱 실패
```
**해결방법**: 자동으로 텍스트 파싱 모드로 전환됨

## 📈 성능 최적화

1. **병렬 처리**: MCP 데이터 수집이 병렬로 실행됨
2. **캐싱**: LLM 클라이언트 인스턴스 재사용
3. **재시도 로직**: 일시적 오류에 대한 자동 재시도
4. **폴백 메커니즘**: 단계별 오류 처리

## 🔮 향후 개선사항

1. **캐싱 시스템**: LLM 응답 캐싱으로 성능 향상
2. **다양한 LLM 지원**: Claude, Gemini 등 추가 모델 지원
3. **실시간 업데이트**: MCP 데이터 실시간 동기화
4. **사용자 피드백**: 쿼리 품질 개선을 위한 피드백 시스템
