# Agent-Cast | 에이전트 기반 AI 트렌드 팟캐스트

## 🌟 **Project Overview | 프로젝트 개요**
Agent-Cast는 멀티 에이전트 간의 협업을 통해 개인 맞춤형으로 AI 트렌드 팟캐스트를 생성하는 서비스입니다. 웹 크롤링, RAG 검색, AI 분석을 통해 최신 AI 트렌드를 수집하고 MCP를 사용하여 개인화된 정보와 결합하여 고품질의 팟캐스트 콘텐츠를 자동으로 제작합니다. 주요 기능으로는 실시간 웹 크롤링, 지식 그래프 구축, AI 기반 콘텐츠 평가, TTS 등이 있으며 연구자들이 AI 트렌드를 쉽게 파악하고 공유할 수 있도록 지원합니다.

![pipeline.png](https://github.com/user-attachments/assets/75233fe1-d716-4a4a-80e0-a668df4f47f5)

---

## 🧑‍🤝‍🧑 **Team Members | 팀원**
- **14기**: 김민열, 김영홍, 김홍재, 배한준

---

## 📅 **Progress Period | 진행 기간**
- **2025.06.28 ~ 2025.08.23**

---

## 📊 **Data Collection | 데이터 수집**
- **웹 크롤링 데이터**: 파이토치 한국 사용자 모임, AI타임스 등 기술 커뮤니티
- **개인화 데이터**: Slack, Notion, Gmail을 통한 MCP 연동

---

## 🧠 **Data Processing | 데이터 처리**
- **지식 그래프**: HippoRAG 기반의 구조화된 지식 베이스 구축
- **벡터 데이터베이스**: FAISS를 통한 의미론적 검색 인덱스
- **엔티티 추출**: NER 및 Triple Extraction을 통한 관계 분석

---

## 🤖 **Agents | 에이전트 설명**

| 에이전트 | 역할 | 주요 기능 | 사용 기술 |
|---------|------|-----------|-----------|
| **Orchestrator** | 워크플로우 조율 | 전체 프로세스 관리 및 단계별 진행 | LangGraph, Python asyncio |
| **Personalize** | 사용자 맞춤화 | Slack/Notion/Gmail MCP 연동, 개인 관심사 분석 | MCP, OpenAI GPT |
| **Searcher** | 웹 크롤링 | 파이토치 한국, AI타임스 크롤링, Perplexity API 검색 | Selenium, BeautifulSoup, Perplexity API |
| **Query Writer** | 쿼리 생성 | RAG 검색을 위한 최적화된 쿼리 생성 | OpenAI GPT-4, LangChain |
| **Knowledge Graph** | 지식 그래프 | HippoRAG 기반 지식 구조화, 엔티티 추출 | HippoRAG, NER, Triple Extraction |
| **DB Constructor** | 벡터 DB | 문서 임베딩, 벡터 저장, 유사도 검색 | FAISS, OpenAI Embeddings |
| **Researcher** | AI 분석 | AI 기술 동향 분석, 통합 보고서 작성 | OpenAI GPT-4, Google Docs API |
| **Critic** | 품질 평가 | 콘텐츠 품질 평가, 정량적 지표 계산 | OpenAI GPT-4, BERTScore, ROUGE |
| **Script Writer** | 대본 생성 | 팟캐스트 대본 작성, 호스트 캐릭터 설정 | Claude Sonnet, OpenAI GPT |
| **TTS** | 음성 변환 | 텍스트를 자연스러운 음성으로 변환 | OpenAI TTS, 오디오 처리 |

---

## 📁 **Key Directories and Files | 주요 디렉토리 및 파일**
- `agents/`: 멀티 에이전트 시스템 (Orchestrator, Searcher, Researcher, Critic, ScriptWriter, TTS 등)
- `constants/`: 시스템 설정, 프롬프트, AI 모델 파라미터
- `state/`: 워크플로우 상태 관리
- `graph/`: LangGraph 기반 워크플로우 정의
- `mcp/`: MCP 서비스 연동 (Slack, Notion, Gmail)
- `output/`: 생성된 콘텐츠 (검색 결과, 스크립트, 오디오, 리포트)
- `run.py`: 메인 실행 파일

---

## 🛠️ **Installation and Execution | 설치 및 실행 방법**
1. **Clone the repository | 저장소 클론**:
    ```bash
    git clone https://github.com/hanjuhn/agent-cast.git
    cd agent-cast
    ```

2. **Install required packages | 필수 패키지 설치**:
    ```bash
    pip install -r requirements.txt
    ```

3. **Set environment variables | 환경 변수 설정**:
    ```bash
    cp env_example.txt .env
    # .env 파일에 API 키 입력
    ```

4. **Run the main script | 실행**:
    ```bash
    python run.py "AI 연구 동향에 대한 팟캐스트를 만들어주세요"
    ```
    
---

## 🎯 **Project Impact | 프로젝트 효용**
- **콘텐츠 제작 자동화**: 수동 작업 대비 시간 단축 및 효율성 증대
- **실시간 트렌드 분석**: 최신 AI 동향의 신속한 파악 및 공유
- **개인화된 콘텐츠**: 사용자 관심사 기반의 맞춤형 정보 제공
- **접근성 향상**: 기술적 배경에 관계없이 AI 트렌드 정보 접근 가능
- **지식 공유 촉진**: AI 연구 동향의 대중적 이해 및 확산
