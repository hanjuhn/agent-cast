"""Query Writer Agent for generating RAG search queries."""

from typing import Any, Dict, List
try:
    from constants import AGENT_NAMES, QUERY_WRITER_SYSTEM_PROMPT, AGENT_TIMEOUTS
    from constants.llm_client import get_llm_client
    from agents.base_agent import BaseAgent, AgentResult
    from state.state import WorkflowState
except ImportError:
    from constants import AGENT_NAMES, QUERY_WRITER_SYSTEM_PROMPT, AGENT_TIMEOUTS
    from constants.llm_client import get_llm_client
    from .base_agent import BaseAgent, AgentResult
    from state.state import WorkflowState


class QueryWriterAgent(BaseAgent):
    """개인화된 정보를 바탕으로 RAG 검색 쿼리를 생성하는 에이전트."""
    
    def __init__(self):
        super().__init__(
            name=AGENT_NAMES["QUERY_WRITER"],
            description="개인화된 정보를 바탕으로 RAG 검색 쿼리를 생성하는 에이전트"
        )
        self.required_inputs = ["current_progress", "personal_info", "research_context"]
        self.output_keys = ["primary_query", "secondary_query", "third_query", "search_scope", "research_priorities"]
        self.timeout = AGENT_TIMEOUTS["query_writer"]
        self.retry_attempts = 2
        self.priority = 3
        
        # LLM 클라이언트 초기화
        try:
            self.llm_client = get_llm_client()
        except Exception as e:
            self.log_execution(f"LLM 클라이언트 초기화 실패: {str(e)}", "WARNING")
            self.llm_client = None
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """RAG 검색 쿼리 생성을 수행합니다."""
        self.log_execution("RAG 검색 쿼리 생성 시작")
        
        try:
            # 입력 검증
            if not self.validate_inputs(state):
                raise ValueError("필수 입력이 누락되었습니다: current_progress, personal_info, research_context")
            
            # 개인화된 정보 통합
            personalized_info = {
                "personal_info": state.personal_info,
                "research_context": state.research_context,
                "current_progress": state.current_progress
            }
            
            # 그룹 요약 정보가 있다면 활용
            group_summaries = getattr(state, 'group_summaries', {})
            if group_summaries:
                self.log_execution(f"그룹 요약 정보 활용: {list(group_summaries.keys())}")
                personalized_info["group_summaries"] = group_summaries
            
            # 사용자 쿼리 (있는 경우)
            user_query = getattr(state, 'user_query', '')
            
            # LLM을 사용하여 RAG 쿼리 생성 (또는 기본 방식 사용)
            if self.llm_client is not None:
                self.log_execution("LLM을 사용한 RAG 쿼리 생성 중...")
                rag_query_data = await self.llm_client.generate_rag_queries(
                    personalized_info=personalized_info,
                    user_query=user_query
                )
            else:
                self.log_execution("LLM 클라이언트 없음, 기본 쿼리 생성 방식 사용", "WARNING")
                rag_query_data = self._generate_basic_rag_queries(personalized_info, user_query)
            
            # 결과 구조화: rag_query는 단일 문장 문자열로 정규화
            primary_query = self._extract_rag_query(rag_query_data, "primary_queries")
            secondary_query = self._extract_rag_query(rag_query_data, "secondary_queries")
            third_query = self._extract_rag_query(rag_query_data, "third_queries") # Assuming third_queries exists
            search_scope = self._extract_search_scope(rag_query_data)
            research_priorities = self._extract_research_priorities(rag_query_data)
            
            # 결과 생성
            result = AgentResult(
                success=True,
                output={
                    "primary_query": primary_query,
                    "secondary_query": secondary_query,
                    "third_query": third_query,
                    "search_scope": search_scope,
                    "research_priorities": research_priorities
                },
                metadata={
                    "query_generation_method": "llm_based",
                    "personalization_level": "high",
                    "group_summaries_used": bool(group_summaries),
                    "llm_response": rag_query_data
                }
            )
            
            # 상태 업데이트
            updated_state = self.update_workflow_status(state, "query_writing")
            updated_state.primary_query = primary_query
            updated_state.secondary_query = secondary_query
            updated_state.third_query = third_query
            updated_state.search_scope = search_scope
            updated_state.research_priorities = research_priorities
            
            self.log_execution("RAG 검색 쿼리 생성 완료")
            return updated_state
            
        except Exception as e:
            self.log_execution(f"RAG 검색 쿼리 생성 실패: {str(e)}", "ERROR")
            
            # 폴백 쿼리 생성
            fallback_query = await self._generate_fallback_query(state)
            
            result = AgentResult(
                success=False,
                output=fallback_query,
                error_message=str(e)
            )
            
            # 폴백 쿼리로 상태 업데이트
            updated_state = self.update_workflow_status(state, "query_writing")
            updated_state.primary_query = fallback_query["primary_query"]
            updated_state.secondary_query = fallback_query["secondary_query"]
            updated_state.third_query = fallback_query["third_query"]
            updated_state.search_scope = fallback_query["search_scope"]
            updated_state.research_priorities = fallback_query["research_priorities"]
            
            self.log_execution("기본 쿼리 사용으로 계속 진행")
            return updated_state
    
    def _extract_rag_query(self, rag_query_data: Dict[str, Any], key_name: str) -> str:
        """LLM 응답에서 특정 타입의 RAG 쿼리를 추출합니다."""
        try:
            if isinstance(rag_query_data, str):
                return rag_query_data.strip()
            
            # dict 형태일 때 해당 키의 첫 번째 값 추출
            queries = rag_query_data.get(key_name, []) if isinstance(rag_query_data, dict) else []
            if isinstance(queries, list) and queries:
                return str(queries[0]).strip()
            
            # 키워드 기반으로 기본 쿼리 생성
            keywords = rag_query_data.get("keywords", []) if isinstance(rag_query_data, dict) else []
            if isinstance(keywords, list) and keywords:
                if key_name == "primary_queries":
                    return f"{' '.join([str(k) for k in keywords[:3]])} 최신 연구 동향과 주요 논문, 최적화 기법"
                elif key_name == "secondary_queries":
                    return f"{' '.join([str(k) for k in keywords[:3]])} 응용 사례, 구현 방법론, 성능 분석"
                elif key_name == "third_queries":
                    return f"{' '.join([str(k) for k in keywords[:3]])} 기술 동향, 미래 전망, 산업 적용"
            
        except Exception:
            pass
        
        # 기본값 반환
        if key_name == "primary_queries":
            return "AI 최신 연구 동향과 주요 논문"
        elif key_name == "secondary_queries":
            return "AI 응용 사례와 구현 방법"
        elif key_name == "third_queries":
            return "AI 기술 동향과 미래 전망"
        
        return "AI 연구 동향과 주요 논문"
    
    def _extract_search_scope(self, rag_query_data: Dict[str, Any]) -> Dict[str, Any]:
        """LLM 응답에서 검색 범위를 추출합니다."""
        search_scope = rag_query_data.get("search_scope", {}) if isinstance(rag_query_data, dict) else {}
        return {
            "time_range": search_scope.get("time_range", "2023-2024"),
            "sources": search_scope.get("sources", ["arxiv.org", "ieee.org"]),
            "languages": search_scope.get("languages", ["en", "ko"]),
            "document_types": search_scope.get("document_types", ["research_paper"]),
            "priority_sources": search_scope.get("sources", ["arxiv.org"])[:2]  # 상위 2개를 우선 소스로
        }
    
    def _extract_research_priorities(self, rag_query_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """LLM 응답에서 연구 우선순위를 추출합니다."""
        priorities = rag_query_data.get("research_priorities", []) if isinstance(rag_query_data, dict) else []
        
        # 기본 구조 보장
        formatted_priorities = []
        for priority in priorities:
            if isinstance(priority, dict):
                formatted_priorities.append({
                    "topic": priority.get("topic", ""),
                    "priority": priority.get("priority", "medium"),
                    "source": "llm_analysis",
                    "rationale": priority.get("rationale", ""),
                    "deadline": None
                })
        
        # 우선순위별 정렬
        priority_order = {"high": 1, "medium": 2, "low": 3}
        formatted_priorities.sort(key=lambda x: priority_order.get(x["priority"], 3))
        
        return formatted_priorities
    
    def _generate_basic_rag_queries(self, personalized_info: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """LLM 없이 기본적인 RAG 쿼리를 생성합니다."""
        # 개인화 정보에서 키워드 추출
        personal_info = personalized_info.get("personal_info", {})
        research_context = personalized_info.get("research_context", {})
        
        keywords = personal_info.get("research_keywords", ["AI", "머신러닝"])
        interests = research_context.get("research_interests", ["AI 연구"])
        projects = research_context.get("current_projects", ["AI 연구 프로젝트"])
        
        # 더 구체적인 쿼리 생성
        return {
            "primary_queries": [
                f"{' '.join(keywords[:3])} 최신 연구 동향과 주요 논문, 최적화 기법",
                f"{interests[0] if interests else 'AI'} 관련 최신 연구 성과와 동향"
            ],
            "secondary_queries": [
                f"{keyword} 응용 사례, 구현 방법론, 성능 분석" for keyword in keywords[:3]
            ],
            "third_queries": [
                f"{keyword} 기술 동향, 미래 전망, 산업 적용" for keyword in keywords[:3]
            ],
            "keywords": keywords,
            "search_scope": {
                "time_range": "2023-2024",
                "sources": ["arxiv.org", "ieee.org"],
                "languages": ["en", "ko"],
                "document_types": ["research_paper"]
            },
            "research_priorities": [
                {
                    "topic": interest,
                    "priority": "high" if i == 0 else "medium",
                    "rationale": "기본 관심 주제"
                }
                for i, interest in enumerate(interests[:3])
            ],
            "expected_results": ["논문", "기술 동향"]
        }
    
    async def _generate_fallback_query(self, state: WorkflowState) -> Dict[str, Any]:
        """기본 쿼리를 생성합니다."""
        self.log_execution("폴백 쿼리 생성 중...")
        
        try:
            # 상태에서 사용 가능한 정보 추출
            user_query = getattr(state, 'user_query', '')
            
            # LLM을 사용한 기본 쿼리 생성 시도
            fallback_data = await self.llm_client.generate_rag_queries(
                personalized_info={
                    "personal_info": {"research_keywords": ["AI", "머신러닝"]},
                    "research_context": {"research_interests": ["AI 연구"]},
                    "current_progress": {"ai_conferences": []}
                },
                user_query=user_query or "AI 연구 동향에 대한 정보"
            )
            # fallback_data는 단일 문장일 수 있음
            return {
                "primary_query": self._extract_rag_query(fallback_data, "primary_queries"),
                "secondary_query": self._extract_rag_query(fallback_data, "secondary_queries"),
                "third_query": self._extract_rag_query(fallback_data, "third_queries"),
                "search_scope": self._extract_search_scope({}),
                "research_priorities": self._extract_research_priorities({})
            }
            
        except Exception as e:
            self.log_execution(f"폴백 LLM 쿼리 생성 실패: {str(e)}", "WARNING")
            # 하드코딩된 기본 쿼리
            return {
                "primary_query": "AI 연구 동향 2024와 머신러닝 최신 기법 관련 최신 논문과 리뷰",
                "secondary_query": "AI 응용 사례와 구현 방법론 관련 연구 자료",
                "third_query": "AI 기술 동향과 미래 전망 분석 보고서",
                "search_scope": {
                    "time_range": "2023-2024",
                    "sources": ["arxiv.org", "ieee.org"],
                    "languages": ["en", "ko"],
                    "document_types": ["research_paper"],
                    "priority_sources": ["arxiv.org"]
                },
                "research_priorities": [
                    {
                        "topic": "AI 연구 동향 파악",
                        "priority": "high",
                        "source": "fallback",
                        "rationale": "기본 관심 주제",
                        "deadline": None
                    }
                ]
            }
