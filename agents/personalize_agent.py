"""Personalize Agent for collecting personalized information from MCP sources."""

import asyncio
from typing import Any, Dict, List, Optional
try:
    from constants import AGENT_NAMES, PERSONALIZE_SYSTEM_PROMPT
    from constants.llm_client import get_llm_client
    from agents.base_agent import BaseAgent, AgentResult
    from state import WorkflowState
    from mcp import MCPManager
except ImportError:
    from ..constants import AGENT_NAMES, PERSONALIZE_SYSTEM_PROMPT
    from ..constants.llm_client import get_llm_client
    from .base_agent import BaseAgent, AgentResult
    from ..state import WorkflowState
    from ..mcp import MCPManager


class PersonalizeAgent(BaseAgent):
    """Slack, Notion, Gmail에서 개인화된 정보를 수집하는 에이전트."""
    
    def __init__(self):
        super().__init__(
            name=AGENT_NAMES["PERSONALIZE"],
            description="Slack, Notion, Gmail에서 개인화된 정보를 수집하는 에이전트"
        )
        self.required_inputs = ["workflow_status"]
        self.output_keys = ["personal_info", "research_context", "current_progress"]
        self.timeout = 120
        self.retry_attempts = 3
        self.priority = 2
        
        # MCP 매니저 초기화 (환경변수가 없어도 작동하도록)
        try:
            self.mcp_manager = MCPManager()
        except Exception as e:
            self.log_execution(f"MCP 매니저 초기화 실패: {str(e)}", "WARNING")
            self.mcp_manager = None
        
        # LLM 클라이언트 초기화
        try:
            self.llm_client = get_llm_client()
        except Exception as e:
            self.log_execution(f"LLM 클라이언트 초기화 실패: {str(e)}", "WARNING")
            self.llm_client = None
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """개인화된 정보 수집을 수행합니다."""
        self.log_execution("개인화 정보 수집 시작")
        
        try:
            # 입력 검증
            if not self.validate_inputs(state):
                raise ValueError("필수 입력이 누락되었습니다: workflow_status")
            
            # MCP 연결 확인 및 설정
            await self._ensure_mcp_connections()
            
            # MCP 소스에서 원시 데이터 수집
            slack_data = await self._collect_slack_data()
            notion_data = await self._collect_notion_data()
            gmail_data = await self._collect_gmail_data()
            
            self.log_execution("원시 데이터 수집 완료, LLM 분석 시작")
            
            # LLM을 사용하여 개인화된 정보 분석
            if self.llm_client is not None:
                analyzed_data = await self.llm_client.analyze_personalized_data(
                    slack_data=slack_data,
                    notion_data=notion_data,
                    gmail_data=gmail_data
                )
            else:
                self.log_execution("LLM 클라이언트 없음, 기본 분석 사용", "WARNING")
                analyzed_data = self._get_default_analyzed_data()
            
            # 분석된 데이터를 구조화된 형태로 변환
            personal_info = self._structure_personal_info(analyzed_data)
            research_context = self._structure_research_context(analyzed_data)
            current_progress = self._structure_current_progress(analyzed_data)
            
            # 결과 생성
            result = AgentResult(
                success=True,
                output={
                    "personal_info": personal_info,
                    "research_context": research_context,
                    "current_progress": current_progress
                },
                metadata={
                    "sources_accessed": ["slack", "notion", "gmail"],
                    "llm_analysis": True,
                    "collection_time": asyncio.get_running_loop().time(),
                    "analyzed_data": analyzed_data
                }
            )
            
            # 상태 업데이트
            updated_state = self.update_workflow_status(state, "personalization")
            updated_state.personal_info = personal_info
            updated_state.research_context = research_context
            updated_state.current_progress = current_progress
            
            self.log_execution("개인화 정보 수집 및 분석 완료")
            return updated_state
            
        except Exception as e:
            self.log_execution(f"개인화 정보 수집 실패: {str(e)}", "ERROR")
            
            # 폴백 데이터 사용
            fallback_data = await self._get_fallback_data()
            
            result = AgentResult(
                success=False,
                output=fallback_data,
                error_message=str(e)
            )
            
            # 폴백 데이터로 상태 업데이트
            updated_state = self.update_workflow_status(state, "personalization")
            updated_state.personal_info = fallback_data["personal_info"]
            updated_state.research_context = fallback_data["research_context"]
            updated_state.current_progress = fallback_data["current_progress"]
            
            self.log_execution("폴백 데이터 사용으로 계속 진행")
            return updated_state
    
    async def _ensure_mcp_connections(self):
        """MCP 연결을 확인하고 필요시 연결합니다."""
        if self.mcp_manager is None:
            self.log_execution("MCP 매니저가 초기화되지 않음, 폴백 모드 사용", "WARNING")
            return
            
        try:
            connection_results = await self.mcp_manager.connect_all()
            connected_count = sum(1 for success in connection_results.values() if success)
            self.log_execution(f"MCP 연결 상태: {connected_count}/{len(connection_results)} 연결됨")
        except Exception as e:
            self.log_execution(f"MCP 연결 확인 실패: {str(e)}", "WARNING")
    
    async def _collect_slack_data(self) -> Dict[str, Any]:
        """Slack에서 원시 데이터를 수집합니다."""
        if self.mcp_manager is None:
            self.log_execution("MCP 매니저 없음, 기본 Slack 데이터 사용", "INFO")
            return self._get_default_slack_data()
            
        try:
            self.log_execution("Slack 데이터 수집 중...")
            slack_info = await self.mcp_manager.get_slack_info()
            self.log_execution("Slack 데이터 수집 완료")
            return slack_info
        except Exception as e:
            self.log_execution(f"Slack 데이터 수집 실패: {str(e)}", "WARNING")
            return self._get_default_slack_data()
    
    async def _collect_notion_data(self) -> Dict[str, Any]:
        """Notion에서 원시 데이터를 수집합니다."""
        if self.mcp_manager is None:
            self.log_execution("MCP 매니저 없음, 기본 Notion 데이터 사용", "INFO")
            return self._get_default_notion_data()
            
        try:
            self.log_execution("Notion 데이터 수집 중...")
            notion_info = await self.mcp_manager.get_notion_info()
            self.log_execution("Notion 데이터 수집 완료")
            return notion_info
        except Exception as e:
            self.log_execution(f"Notion 데이터 수집 실패: {str(e)}", "WARNING")
            return self._get_default_notion_data()
    
    async def _collect_gmail_data(self) -> Dict[str, Any]:
        """Gmail에서 원시 데이터를 수집합니다."""
        if self.mcp_manager is None:
            self.log_execution("MCP 매니저 없음, 기본 Gmail 데이터 사용", "INFO")
            return self._get_default_gmail_data()
            
        try:
            self.log_execution("Gmail 데이터 수집 중...")
            gmail_info = await self.mcp_manager.get_gmail_info()
            self.log_execution("Gmail 데이터 수집 완료")
            return gmail_info
        except Exception as e:
            self.log_execution(f"Gmail 데이터 수집 실패: {str(e)}", "WARNING")
            return self._get_default_gmail_data()
    
    def _structure_personal_info(self, analyzed_data: Dict[str, Any]) -> Dict[str, Any]:
        """분석된 데이터에서 개인 정보를 구조화합니다."""
        return {
            "research_keywords": analyzed_data.get("research_keywords", []),
            "communication_patterns": analyzed_data.get("communication_patterns", {}),
            "collaboration_opportunities": analyzed_data.get("collaboration_opportunities", []),
            "preferred_topics": analyzed_data.get("preferred_topics", []),
            "frequent_collaborators": analyzed_data.get("communication_patterns", {}).get("frequent_collaborators", [])
        }
    
    def _structure_research_context(self, analyzed_data: Dict[str, Any]) -> Dict[str, Any]:
        """분석된 데이터에서 연구 컨텍스트를 구조화합니다."""
        return {
            "research_interests": analyzed_data.get("research_interests", []),
            "current_projects": analyzed_data.get("current_projects", []),
            "research_direction": " ".join(analyzed_data.get("research_interests", [])[:3]),
            "preferred_research_areas": analyzed_data.get("research_interests", [])
        }
    
    def _structure_current_progress(self, analyzed_data: Dict[str, Any]) -> Dict[str, Any]:
        """분석된 데이터에서 현재 진행상황을 구조화합니다."""
        deadlines = analyzed_data.get("upcoming_deadlines", [])
        
        # 마감일이 있는 항목들을 컨퍼런스 형태로 변환
        ai_conferences = []
        for deadline in deadlines:
            if any(keyword in deadline.get("task", "").lower() for keyword in ["conference", "submission", "paper"]):
                ai_conferences.append({
                    "name": deadline.get("task", "Conference"),
                    "deadline": deadline.get("deadline", ""),
                    "relevance": deadline.get("priority", "medium"),
                    "topics": analyzed_data.get("research_keywords", [])[:2]
                })
        
        return {
            "upcoming_deadlines": deadlines,
            "ai_conferences": ai_conferences,
            "research_priorities": [
                {
                    "topic": interest,
                    "priority": "high" if i < 2 else "medium",
                    "source": "llm_analysis"
                }
                for i, interest in enumerate(analyzed_data.get("research_interests", [])[:5])
            ]
        }
    
    async def _get_fallback_data(self) -> Dict[str, Any]:
        """MCP 연결 실패 시 사용할 폴백 데이터를 반환합니다."""
        if self.llm_client is not None:
            self.log_execution("LLM을 사용한 기본 분석 수행")
            
            # 기본 분석 데이터 생성
            try:
                fallback_analyzed = await self.llm_client.analyze_personalized_data(
                    slack_data={"error": "연결 실패"},
                    notion_data={"error": "연결 실패"},
                    gmail_data={"error": "연결 실패"}
                )
            except Exception as e:
                self.log_execution(f"폴백 LLM 분석 실패: {str(e)}", "WARNING")
                fallback_analyzed = self.llm_client._get_default_analysis()
        else:
            self.log_execution("LLM 클라이언트 없음, 하드코딩된 기본 분석 사용", "WARNING")
            fallback_analyzed = self._get_default_analyzed_data()
        
        return {
            "personal_info": self._structure_personal_info(fallback_analyzed),
            "research_context": self._structure_research_context(fallback_analyzed),
            "current_progress": self._structure_current_progress(fallback_analyzed)
        }

    def _get_default_slack_data(self) -> Dict[str, Any]:
        """기본 Slack 데이터를 반환합니다."""
        return {
            "workspace_info": {"workspace_name": "AI Research Team (Default)", "status": "default"},
            "channels": [{"name": "research-discussion", "topic": "AI 연구 논의"}],
            "recent_activity": {"trending_topics": ["AI 최적화", "머신러닝"]},
            "ai_research_messages": [{"text": "AI 연구에 대한 기본 메시지"}],
            "connection_status": False
        }

    def _get_default_notion_data(self) -> Dict[str, Any]:
        """기본 Notion 데이터를 반환합니다."""
        return {
            "workspace_info": {"workspace_name": "AI Research (Default)", "status": "default"},
            "databases": [{"title": "AI Research Projects", "description": "기본 연구 프로젝트"}],
            "ai_research_pages": [{"title": "AI 연구 방향", "status": "default"}],
            "recent_changes": [{"page_title": "기본 페이지", "change_type": "default"}],
            "connection_status": False
        }

    def _get_default_gmail_data(self) -> Dict[str, Any]:
        """기본 Gmail 데이터를 반환합니다."""
        return {
            "profile_info": {"email_address": "researcher@example.com", "status": "default"},
            "labels": [{"name": "AI Research", "messagesTotal": 10}],
            "ai_research_messages": [{"snippet": "기본 AI 연구 메시지"}],
            "conference_messages": [{"snippet": "기본 컨퍼런스 메시지"}],
            "recent_activity": {"trending_topics": ["AI Research"]},
            "connection_status": False
        }

    def _get_default_analyzed_data(self) -> Dict[str, Any]:
        """기본 분석 데이터를 반환합니다."""
        return {
            "research_interests": ["AI", "머신러닝", "최적화"],
            "current_projects": ["AI 연구 프로젝트"],
            "collaboration_opportunities": ["연구 협력"],
            "upcoming_deadlines": [],
            "research_keywords": ["AI", "머신러닝", "최적화", "데이터"],
            "preferred_topics": ["AI 연구", "머신러닝"],
            "communication_patterns": {
                "active_channels": ["research-discussion"],
                "frequent_collaborators": ["연구팀"],
                "communication_style": "협력적"
            }
        }
    

