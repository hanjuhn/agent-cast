"""Personalize Agent for collecting personalized information from MCP sources."""

import asyncio
from typing import Any, Dict, List, Optional

from constants import AGENT_NAMES, AGENT_TIMEOUTS, OPENAI_PERSONALIZE_PARAMS
from constants.llm_client import get_llm_client
from ..base_agent import BaseAgent, AgentResult
from state.state import WorkflowState
from mcp import MCPManager


class PersonalizeAgent(BaseAgent):
    """Slack, Notion, Gmail에서 개인화된 정보를 수집하는 에이전트."""
    
    def __init__(self):
        super().__init__(
            name=AGENT_NAMES["PERSONALIZE"],
            description="Slack, Notion, Gmail에서 개인화된 정보를 수집하는 에이전트"
        )
        self.required_inputs = ["workflow_status"]
        self.output_keys = ["personal_info", "research_context", "current_progress"]
        self.timeout = AGENT_TIMEOUTS["personalize"]
        self.retry_attempts = 3
        self.priority = 2
        
        # MCP 매니저 초기화
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
            
            # MCP 연결 확인
            await self._ensure_mcp_connections()
            
            # MCP 소스에서 데이터 수집
            slack_data = await self._collect_slack_data()
            notion_data = await self._collect_notion_data()
            gmail_data = await self._collect_gmail_data()
            
            self.log_execution("데이터 수집 완료, 분석 시작")
            
            # 데이터 그룹화
            grouped_data = self.mcp_manager.group_by_titles(slack_data, notion_data, gmail_data)
            self.log_execution(f"데이터 그룹화 완료: {list(grouped_data.keys())}")
            
            # 그룹별 요약
            group_summaries = {}
            if self.llm_client is not None:
                for group_name, group_items in grouped_data.items():
                    try:
                        summary = await self._summarize_group(group_name, group_items)
                        group_summaries[group_name] = summary
                        self.log_execution(f"그룹 '{group_name}' 요약 완료")
                    except Exception as e:
                        self.log_execution(f"그룹 '{group_name}' 요약 실패: {str(e)}", "WARNING")
                        group_summaries[group_name] = f"요약 실패: {str(e)}"
            
            # 최종 분석
            if self.llm_client is not None:
                analyzed_data = await self._analyze_group_summaries(group_summaries)
            else:
                analyzed_data = self._extract_info_from_text("AI 연구 관련 활동")
            
            # 데이터 구조화
            personal_info = self._structure_personal_info(analyzed_data)
            research_context = self._structure_research_context(analyzed_data)
            current_progress = self._structure_current_progress(analyzed_data)
            
            # 상태 업데이트
            updated_state = self.update_workflow_status(state, "personalization")
            updated_state.personal_info = personal_info
            updated_state.research_context = research_context
            updated_state.current_progress = current_progress
            
            self.log_execution("개인화 정보 수집 완료")
            return updated_state
            
        except Exception as e:
            self.log_execution(f"개인화 정보 수집 실패: {str(e)}", "ERROR")
            raise
    
    async def _ensure_mcp_connections(self):
        """MCP 연결을 확인합니다."""
        if self.mcp_manager is None:
            return
            
        try:
            connection_results = await self.mcp_manager.connect_all()
            connected_count = sum(1 for success in connection_results.values() if success)
            self.log_execution(f"MCP 연결 상태: {connected_count}/{len(connection_results)} 연결됨")
        except Exception as e:
            self.log_execution(f"MCP 연결 확인 실패: {str(e)}", "WARNING")
    
    async def _collect_slack_data(self) -> Dict[str, Any]:
        """Slack에서 데이터를 수집합니다."""
        if self.mcp_manager is None:
            return {}
            
        try:
            self.log_execution("Slack 데이터 수집 중...")
            slack_info = await self.mcp_manager.get_slack_info()
            self.log_execution("Slack 데이터 수집 완료")
            return slack_info
        except Exception as e:
            self.log_execution(f"Slack 데이터 수집 실패: {str(e)}", "WARNING")
            return {}
    
    async def _collect_notion_data(self) -> Dict[str, Any]:
        """Notion에서 데이터를 수집합니다."""
        if self.mcp_manager is None:
            return {}
            
        try:
            self.log_execution("Notion 데이터 수집 중...")
            notion_info = await self.mcp_manager.get_notion_info()
            self.log_execution("Notion 데이터 수집 완료")
            return notion_info
        except Exception as e:
            self.log_execution(f"Notion 데이터 수집 실패: {str(e)}", "WARNING")
            return {}
    
    async def _collect_gmail_data(self) -> Dict[str, Any]:
        """Gmail에서 데이터를 수집합니다."""
        if self.mcp_manager is None:
            return {}
            
        try:
            self.log_execution("Gmail 데이터 수집 중...")
            gmail_info = await self.mcp_manager.get_gmail_info()
            self.log_execution("Gmail 데이터 수집 완료")
            return gmail_info
        except Exception as e:
            self.log_execution(f"Gmail 데이터 수집 실패: {str(e)}", "WARNING")
            return {}
    
    async def _summarize_group(self, group_name: str, group_items: List[Dict[str, Any]]) -> str:
        """각 그룹을 LLM으로 요약합니다."""
        if not self.llm_client:
            return f"그룹 {group_name}: {len(group_items)}개 항목"
        
        prompt = f"'{group_name}' 그룹의 활동을 한 문장으로 요약해주세요. 주요 내용을 포함하여 50자 이내로 작성하세요."
        group_text = self._format_group_for_summary(group_name, group_items)
        
        try:
            summary = await self.llm_client.generate_response(
                prompt=f"{prompt}\n\n데이터:\n{group_text}",
                max_tokens=OPENAI_PERSONALIZE_PARAMS["max_tokens"],
                temperature=OPENAI_PERSONALIZE_PARAMS["temperature"]
            )
            return summary.strip()
        except Exception as e:
            self.log_execution(f"그룹 '{group_name}' LLM 요약 실패: {str(e)}", "WARNING")
            return f"그룹 {group_name}: {len(group_items)}개 항목 (요약 실패)"
    
    def _format_group_for_summary(self, group_name: str, group_items: List[Dict[str, Any]]) -> str:
        """그룹 데이터를 요약용 텍스트로 변환합니다."""
        if not group_items:
            return "데이터 없음"
        
        formatted_items = []
        for item in group_items[:10]:
            if item.get("source") == "slack":
                formatted_items.append(f"Slack({item.get('channel', 'Unknown')}): {item.get('content', '')[:100]}...")
            elif item.get("source") == "notion":
                formatted_items.append(f"Notion: {item.get('title', 'Unknown')} ({item.get('content_count', 0)}개 블록)")
            elif item.get("source") == "gmail":
                formatted_items.append(f"Gmail: {item.get('subject', 'Unknown')} - {item.get('snippet', '')[:100]}...")
        
        return f"그룹: {group_name}\n항목 수: {len(group_items)}\n\n주요 항목:\n" + "\n".join(formatted_items)
    
    async def _analyze_group_summaries(self, group_summaries: Dict[str, str]) -> Dict[str, Any]:
        """그룹 요약들을 바탕으로 최종 분석을 수행합니다."""
        if not self.llm_client:
            return self._extract_info_from_text("AI 연구 관련 활동")
        
        prompt = """다음 그룹별 요약을 바탕으로 사용자의 연구 컨텍스트를 분석해주세요.

분석 결과를 다음 JSON 형식으로 반환하세요:
{
    "research_interests": ["관심 연구 분야 1", "관심 연구 분야 2"],
    "current_projects": ["진행 중인 프로젝트 1", "진행 중인 프로젝트 2"],
    "research_keywords": ["키워드1", "키워드2"],
    "preferred_topics": ["선호 주제 1", "선호 주제 2"]
}

그룹 요약:
{group_summaries}"""

        try:
            response = await self.llm_client.generate_response(
                prompt=prompt.format(group_summaries="\n".join([f"- {k}: {v}" for k, v in group_summaries.items()])),
                max_tokens=OPENAI_PERSONALIZE_PARAMS["max_tokens"],
                temperature=OPENAI_PERSONALIZE_PARAMS["temperature"]
            )
            
            import json
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return self._extract_info_from_text(response)
                
        except Exception as e:
            self.log_execution(f"그룹 요약 분석 실패: {str(e)}", "WARNING")
            return self._extract_info_from_text("AI 연구 관련 활동")
    
    def _extract_info_from_text(self, text: str) -> Dict[str, Any]:
        """텍스트에서 정보를 추출합니다."""
        import re
        
        keywords = re.findall(r'\b(?:AI|머신러닝|딥러닝|최적화|데이터|연구|알고리즘|신경망|LLM)\b', text, re.IGNORECASE)
        
        return {
            "research_interests": keywords[:3] if keywords else ["AI 연구"],
            "current_projects": ["AI 연구 프로젝트"],
            "research_keywords": keywords[:5] if keywords else ["AI", "머신러닝"],
            "preferred_topics": keywords[:3] if keywords else ["AI 연구"]
        }
    
    def _structure_personal_info(self, analyzed_data: Dict[str, Any]) -> Dict[str, Any]:
        """분석된 데이터에서 개인 정보를 구조화합니다."""
        return {
            "research_keywords": analyzed_data.get("research_keywords", []),
            "preferred_topics": analyzed_data.get("preferred_topics", [])
        }
    
    def _structure_research_context(self, analyzed_data: Dict[str, Any]) -> Dict[str, Any]:
        """분석된 데이터에서 연구 컨텍스트를 구조화합니다."""
        return {
            "research_interests": analyzed_data.get("research_interests", []),
            "current_projects": analyzed_data.get("current_projects", [])
        }
    
    def _structure_current_progress(self, analyzed_data: Dict[str, Any]) -> Dict[str, Any]:
        """분석된 데이터에서 현재 진행상황을 구조화합니다."""
        return {
            "research_priorities": [
                {
                    "topic": interest,
                    "priority": "high" if i < 2 else "medium"
                }
                for i, interest in enumerate(analyzed_data.get("research_interests", [])[:5])
            ]
        }


