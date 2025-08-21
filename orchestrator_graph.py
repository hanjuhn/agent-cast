"""Orchestrator Graph for the multi-agent workflow system."""

from typing import Dict, Any
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages

try:
    from state import WorkflowState
    from constants import AGENT_NAMES, WORKFLOW_STEP_ORDER
    from agents import (
        OrchestratorAgent,
        PersonalizeAgent,
        QueryWriterAgent,
        SearcherAgent,
        KnowledgeGraphAgent,
        KGSearchAgent,
        DBConstructorAgent,
        ResearcherAgent,
        CriticAgent,
        ScriptWriterAgent,
        TTSAgent
    )
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from state import WorkflowState
    from constants import AGENT_NAMES, WORKFLOW_STEP_ORDER
    from agents import (
        OrchestratorAgent,
        PersonalizeAgent,
        QueryWriterAgent,
        SearcherAgent,
        KnowledgeGraphAgent,
        KGSearchAgent,
        DBConstructorAgent,
        ResearcherAgent,
        CriticAgent,
        ScriptWriterAgent,
        TTSAgent
    )


def create_orchestrator_graph() -> StateGraph:
    """멀티 에이전트 워크플로우를 위한 오케스트레이터 그래프를 생성합니다."""
    
    # 워크플로우 그래프 생성
    workflow = StateGraph(WorkflowState)
    
    # 에이전트 인스턴스 생성
    orchestrator = OrchestratorAgent()
    personalize = PersonalizeAgent()
    query_writer = QueryWriterAgent()
    searcher = SearcherAgent()
    if KnowledgeGraphAgent is not None:
        knowledge_graph = KnowledgeGraphAgent()
    else:
        knowledge_graph = None
    kg_search = KGSearchAgent()
    db_constructor = DBConstructorAgent()
    researcher = ResearcherAgent()
    critic = CriticAgent()
    script_writer = ScriptWriterAgent()
    tts = TTSAgent()
    
    # 노드 추가
    workflow.add_node(AGENT_NAMES["ORCHESTRATOR"], orchestrator.process)
    workflow.add_node(AGENT_NAMES["PERSONALIZE"], personalize.process)
    workflow.add_node(AGENT_NAMES["QUERY_WRITER"], query_writer.process)
    workflow.add_node(AGENT_NAMES["SEARCHER"], searcher.process)
    if knowledge_graph is not None:
        workflow.add_node(AGENT_NAMES["KNOWLEDGE_GRAPH"], knowledge_graph.process)
    else:
        # Mock knowledge graph process
        async def mock_kg_process(state: WorkflowState) -> WorkflowState:
            print("⚠️ KnowledgeGraphAgent not available, using mock process")
            return state
        workflow.add_node(AGENT_NAMES["KNOWLEDGE_GRAPH"], mock_kg_process)
    workflow.add_node(AGENT_NAMES["KG_SEARCH"], kg_search.process)
    workflow.add_node(AGENT_NAMES["DB_CONSTRUCTOR"], db_constructor.process)
    workflow.add_node(AGENT_NAMES["RESEARCHER"], researcher.process)
    workflow.add_node(AGENT_NAMES["CRITIC"], critic.process)
    workflow.add_node(AGENT_NAMES["SCRIPT_WRITER"], script_writer.process)
    workflow.add_node(AGENT_NAMES["TTS"], tts.process)
    
    # 엣지 추가 - 순차적 실행
    workflow.add_edge(START, AGENT_NAMES["ORCHESTRATOR"])
    workflow.add_edge(AGENT_NAMES["ORCHESTRATOR"], AGENT_NAMES["PERSONALIZE"])
    workflow.add_edge(AGENT_NAMES["PERSONALIZE"], AGENT_NAMES["SEARCHER"])
    workflow.add_edge(AGENT_NAMES["SEARCHER"], AGENT_NAMES["KNOWLEDGE_GRAPH"])
    workflow.add_edge(AGENT_NAMES["KNOWLEDGE_GRAPH"], AGENT_NAMES["QUERY_WRITER"])
    workflow.add_edge(AGENT_NAMES["QUERY_WRITER"], AGENT_NAMES["KG_SEARCH"])
    workflow.add_edge(AGENT_NAMES["KG_SEARCH"], AGENT_NAMES["DB_CONSTRUCTOR"])
    workflow.add_edge(AGENT_NAMES["DB_CONSTRUCTOR"], AGENT_NAMES["RESEARCHER"])
    workflow.add_edge(AGENT_NAMES["RESEARCHER"], AGENT_NAMES["CRITIC"])
    workflow.add_edge(AGENT_NAMES["CRITIC"], AGENT_NAMES["SCRIPT_WRITER"])
    workflow.add_edge(AGENT_NAMES["SCRIPT_WRITER"], AGENT_NAMES["TTS"])
    workflow.add_edge(AGENT_NAMES["TTS"], END)
    
    # 워크플로우 컴파일
    app = workflow.compile()
    
    # 워크플로우 정보 출력
    print(f"워크플로우 생성 완료:")
    print(f"총 단계 수: {len(WORKFLOW_STEP_ORDER)}")
    print(f"단계 순서: {' -> '.join(WORKFLOW_STEP_ORDER)}")
    
    return app


# 메인 워크플로우 인스턴스
main_workflow = create_orchestrator_graph()
