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
    from constants import AGENT_NAMES, PERSONALIZE_SYSTEM_PROMPT
    from constants.llm_client import get_llm_client
    from .base_agent import BaseAgent, AgentResult
    from state import WorkflowState
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
            
            self.log_execution("원시 데이터 수집 완료, 3단계 분석 시작")
            
            # 1단계: 제목 기반 그룹화
            grouped_data = self.mcp_manager.group_by_titles(slack_data, notion_data, gmail_data)
            self.log_execution(f"데이터 그룹화 완료: {list(grouped_data.keys())}")
            
            # 2단계: 각 그룹별로 LLM 요약
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
            else:
                self.log_execution("LLM 클라이언트 없음, 기본 분석 사용", "WARNING")
                group_summaries = self._get_default_group_summaries(grouped_data)
            
            # 3단계: 요약문들로 최종 분석
            if self.llm_client is not None:
                analyzed_data = await self._analyze_group_summaries(group_summaries)
            else:
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
                    "grouped_data": grouped_data,
                    "group_summaries": group_summaries,
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
    
    async def _summarize_group(self, group_name: str, group_items: List[Dict[str, Any]]) -> str:
        """각 그룹을 LLM으로 요약합니다."""
        if not self.llm_client:
            return f"그룹 {group_name}: {len(group_items)}개 항목"
        
        # 동적 그룹별 요약 프롬프트
        group_prompts = {
            "AI_Research": "AI 연구 관련 활동을 한 문장으로 요약해주세요. 논문 리뷰, 연구 주제, 최적화 관련 내용을 포함하여 50자 이내로 작성하세요.",
            "Development_Projects": "개발 프로젝트 활동을 한 문장으로 요약해주세요. 코드 구현, 개발 진행상황, 기술적 도전과제를 포함하여 50자 이내로 작성하세요.",
            "Learning_Study": "학습 및 스터디 활동을 한 문장으로 요약해주세요. 강의, 튜토리얼, 학습 내용을 포함하여 50자 이내로 작성하세요.",
            "Conference_Events": "컨퍼런스 및 이벤트 관련 활동을 한 문장으로 요약해주세요. 참가 예정, CFP, 등록 등을 포함하여 50자 이내로 작성하세요.",
            "Data_Analysis": "데이터 분석 활동을 한 문장으로 요약해주세요. 데이터 처리, 시각화, 통계 분석을 포함하여 50자 이내로 작성하세요.",
            "Collaboration_Communication": "협업 및 커뮤니케이션 활동을 한 문장으로 요약해주세요. 팀 미팅, 피드백, 협력 활동을 포함하여 50자 이내로 작성하세요.",
            "Planning_Retrospective": "계획 및 회고 활동을 한 문장으로 요약해주세요. 목표 설정, 진행상황, 마일스톤을 포함하여 50자 이내로 작성하세요.",
            "Tools_Technologies": "도구 및 기술 관련 활동을 한 문장으로 요약해주세요. 프레임워크, 라이브러리, 플랫폼 사용을 포함하여 50자 이내로 작성하세요.",
            "General_Discussion": "일반적인 논의 활동을 한 문장으로 요약해주세요. 주요 주제, 협력 활동 등을 포함하여 50자 이내로 작성하세요."
        }
        
        # 동적 그룹명에 맞는 프롬프트 선택 (없으면 기본값)
        prompt = group_prompts.get(group_name, f"'{group_name}' 그룹의 활동을 한 문장으로 요약해주세요. 주요 내용을 포함하여 50자 이내로 작성하세요.")
        
        # 그룹 데이터를 텍스트로 변환
        group_text = self._format_group_for_summary(group_name, group_items)
        
        try:
            summary = await self.llm_client.generate_response(
                prompt=f"{prompt}\n\n데이터:\n{group_text}",
                max_tokens=100,
                temperature=0.3
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
        for item in group_items[:10]:  # 상위 10개만
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
            return self._get_default_analyzed_data()
        
        # 모든 그룹 요약을 하나의 텍스트로 결합
        summaries_text = "\n".join([f"{group}: {summary}" for group, summary in group_summaries.items()])
        
        system_prompt = """당신은 사용자의 개인화된 정보를 분석하는 AI 어시스턴트입니다.
그룹별 요약을 바탕으로 사용자의 연구 방향과 관심사를 파악하세요.

분석 결과를 다음 JSON 형식으로 반환하세요:
{
    "research_interests": ["관심 연구 분야 1", "관심 연구 분야 2"],
    "current_projects": ["진행 중인 프로젝트 1", "진행 중인 프로젝트 2"],
    "collaboration_opportunities": ["협력 기회 1", "협력 기회 2"],
    "upcoming_deadlines": [
        {"task": "할 일", "deadline": "마감일", "priority": "high/medium/low"}
    ],
    "research_keywords": ["키워드1", "키워드2"],
    "preferred_topics": ["선호 주제 1", "선호 주제 2"],
    "communication_patterns": {
        "active_channels": ["채널1", "채널2"],
        "frequent_collaborators": ["협력자1", "협력자2"],
        "communication_style": "설명"
    }
}"""

        user_prompt = f"""다음 그룹별 요약을 바탕으로 사용자의 연구 컨텍스트를 분석해주세요:

{summaries_text}

위 요약들을 종합하여 사용자의 연구 방향과 관심사를 분석하고 JSON 형식으로 결과를 반환해주세요."""

        try:
            response = await self.llm_client.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            # JSON 파싱 시도
            import json
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return self._extract_info_from_text(response)
                
        except Exception as e:
            self.log_execution(f"그룹 요약 분석 실패: {str(e)}", "WARNING")
            return self._get_default_analyzed_data()
    
    def _get_default_group_summaries(self, grouped_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
        """기본 그룹 요약을 생성합니다."""
        summaries = {}
        for group_name, group_items in grouped_data.items():
            summaries[group_name] = f"그룹 {group_name}: {len(group_items)}개 항목"
        return summaries
    
    def _extract_info_from_text(self, text: str) -> Dict[str, Any]:
        """텍스트에서 정보를 추출하여 기본 구조로 변환합니다."""
        # 간단한 키워드 추출 로직
        import re
        
        keywords = re.findall(r'\b(?:AI|머신러닝|딥러닝|최적화|데이터|연구|알고리즘|신경망)\b', text, re.IGNORECASE)
        
        return {
            "research_interests": keywords[:3] if keywords else ["AI", "머신러닝"],
            "current_projects": ["AI 연구 프로젝트"],
            "collaboration_opportunities": [],
            "upcoming_deadlines": [],
            "research_keywords": keywords[:5] if keywords else ["AI", "머신러닝", "최적화"],
            "preferred_topics": keywords[:3] if keywords else ["AI 연구"],
            "communication_patterns": {
                "active_channels": [],
                "frequent_collaborators": [],
                "communication_style": "협력적"
            }
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
                fallback_analyzed = self._get_default_analyzed_data()
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
            "recent_changes": [{"page_title": "AI 연구 방향 및 계획", "change_type": "default"}],
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
            "research_interests": ["AI 연구", "머신러닝", "최적화", "데이터 분석", "LLM 최적화"],
            "current_projects": ["메모리 구현 프로젝트", "vllm 서빙 가이드 개발", "LLM 성능 최적화 연구"],
            "collaboration_opportunities": ["AI 연구팀 협력", "최적화 알고리즘 공동 연구"],
            "upcoming_deadlines": [
                {"task": "vllm 서빙 가이드 완성", "deadline": "2024-09-15", "priority": "high"},
                {"task": "메모리 구현 최적화", "deadline": "2024-09-30", "priority": "medium"}
            ],
            "research_keywords": ["AI", "머신러닝", "최적화", "데이터", "LLM", "vllm", "메모리", "서빙", "성능"],
            "preferred_topics": ["AI 연구", "머신러닝", "최적화", "LLM 최적화"],
            "communication_patterns": {
                "active_channels": ["research-discussion", "ai-optimization"],
                "frequent_collaborators": ["AI 연구팀", "최적화 전문가"],
                "communication_style": "협력적"
            }
        }


