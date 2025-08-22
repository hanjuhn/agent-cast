"""Agent names and related constants for the multi-agent workflow system."""

# 에이전트 이름 딕셔너리
AGENT_NAMES = {
    "ORCHESTRATOR": "orchestrator",
    "PERSONALIZE": "personalize",
    "QUERY_WRITER": "query_writer",
    "SEARCHER": "searcher",
    "DB_CONSTRUCTOR": "db_constructor",
    "RESEARCHER": "researcher",
    "CRITIC": "critic",
    "SCRIPT_WRITER": "script_writer",
    "TTS": "tts",
    "KNOWLEDGE_GRAPH": "knowledge_graph",
    "KG_SEARCH": "kg_search"
}

# 에이전트 실행 순서
AGENT_EXECUTION_ORDER = [
    "orchestrator",
    "personalize", 
    "query_writer",
    "searcher",
    "db_constructor",
    "knowledge_graph",
    "kg_search",
    "researcher",
    "critic",
    "script_writer",
    "tts"
]

# 에이전트 타임아웃 (초)
AGENT_TIMEOUTS = {
    "orchestrator": 30,
    "personalize": 120,
    "query_writer": 60,
    "searcher": 180,
    "db_constructor": 300,
    "knowledge_graph": 300,
    "kg_search": 120,
    "researcher": 180,
    "critic": 120,
    "script_writer": 300,
    "tts": 180
}

# 에이전트 재시도 횟수
AGENT_RETRY_ATTEMPTS = {
    "orchestrator": 1,
    "personalize": 3,
    "query_writer": 2,
    "searcher": 2,
    "db_constructor": 1,
    "knowledge_graph": 1,
    "kg_search": 2,
    "researcher": 2,
    "critic": 2,
    "script_writer": 2,
    "tts": 2
}

# 에이전트 우선순위
AGENT_PRIORITIES = {
    "orchestrator": 1,
    "personalize": 2,
    "query_writer": 3,
    "searcher": 4,
    "db_constructor": 5,
    "knowledge_graph": 6,
    "kg_search": 7,
    "researcher": 8,
    "critic": 9,
    "script_writer": 10,
    "tts": 11
}

# 에이전트 필수 입력
AGENT_REQUIRED_INPUTS = {
    "orchestrator": ["user_query"],
    "personalize": ["workflow_status"],
    "query_writer": ["current_progress", "personal_info", "research_context"],
    "searcher": ["search_query", "search_scope"],
    "db_constructor": ["data_chunks", "search_scope"],
    "knowledge_graph": ["search_results", "personal_info"],
    "kg_search": ["search_query", "knowledge_graph"],
    "researcher": ["search_results", "search_query"],
    "critic": ["research_result"],
    "script_writer": ["research_result"],
    "tts": ["podcast_script"]
}

# 에이전트 출력 키
AGENT_OUTPUT_KEYS = {
    "orchestrator": ["workflow_status", "next_agents"],
    "personalize": ["personal_info", "research_context", "current_progress"],
    "query_writer": ["primary_query", "secondary_query", "third_query", "search_scope", "research_priorities"],
    "searcher": ["search_results", "search_metadata"],
    "db_constructor": ["vector_db", "embedding_stats", "db_metadata"],
    "knowledge_graph": ["knowledge_graph", "document_store"],
    "kg_search": ["kg_search_results", "kg_stats"],
    "researcher": ["research_result", "research_metadata"],
    "critic": ["evaluation_results", "critic_feedback", "quality_score"],
    "script_writer": ["podcast_script", "script_metadata"],
    "tts": ["audio_file", "audio_metadata"]
}

# 에이전트 설명
AGENT_DESCRIPTIONS = {
    "orchestrator": "전체 워크플로우를 조정하고 다음 단계를 결정하는 에이전트",
    "personalize": "Slack, Notion, Gmail에서 개인화된 정보를 수집하는 에이전트",
    "query_writer": "개인화된 정보를 바탕으로 RAG 검색 쿼리를 생성하는 에이전트",
    "searcher": "웹 크롤링을 통해 최신 AI 연구 정보를 수집하는 에이전트",
    "db_constructor": "수집된 정보를 벡터 데이터베이스로 구축하는 에이전트",
    "knowledge_graph": "실시간 지식 그래프 구축을 위한 HippoRAG 에이전트",
    "kg_search": "지식 그래프에서 정보를 검색하는 에이전트",
    "researcher": "AI 기술 동향을 분석하여 심층 보고서를 생성하는 에이전트",
    "critic": "리서치 결과를 평가하고 품질을 검토하는 에이전트",
    "script_writer": "리서치 결과를 바탕으로 팟캐스트 대본을 생성하는 에이전트",
    "tts": "팟캐스트 대본을 오디오로 변환하는 에이전트"
}

# 개별 에이전트 이름 상수
KNOWLEDGE_GRAPH_AGENT_NAME = "knowledge_graph"
KG_SEARCH_AGENT_NAME = "kg_search"
