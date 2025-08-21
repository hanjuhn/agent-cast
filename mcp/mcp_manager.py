"""MCP Manager for coordinating multiple MCP integrations."""

import asyncio
from typing import Any, Dict, List, Optional
from .base_mcp import BaseMCP
from .slack_mcp import SlackMCP
from .notion_mcp import NotionMCP
from .gmail_mcp import GmailMCP


class MCPManager:
    """여러 MCP 통합을 조정하는 매니저 클래스."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.integrations: Dict[str, BaseMCP] = {}
        self.connection_status: Dict[str, str] = {}
        
        # 기본 통합 초기화
        self._initialize_integrations()
    
    def _initialize_integrations(self):
        """MCP 통합들을 초기화합니다."""
        # Slack 통합
        slack_config = self.config.get("slack", {})
        self.integrations["slack"] = SlackMCP(slack_config)
        
        # Notion 통합
        notion_config = self.config.get("notion", {})
        self.integrations["notion"] = NotionMCP(notion_config)
        
        # Gmail 통합
        gmail_config = self.config.get("gmail", {})
        self.integrations["gmail"] = GmailMCP(gmail_config)
    
    async def connect_all(self) -> Dict[str, bool]:
        """모든 MCP 통합에 연결합니다."""
        results = {}
        
        for name, integration in self.integrations.items():
            try:
                success = await integration.connect()
                results[name] = success
                self.connection_status[name] = "connected" if success else "failed"
            except Exception as e:
                results[name] = False
                self.connection_status[name] = "failed"
                print(f"Failed to connect to {name}: {e}")
        
        return results
    
    async def disconnect_all(self) -> Dict[str, bool]:
        """모든 MCP 통합 연결을 해제합니다."""
        results = {}
        
        for name, integration in self.integrations.items():
            try:
                success = await integration.disconnect()
                results[name] = success
                self.connection_status[name] = "disconnected" if success else "failed"
            except Exception as e:
                results[name] = False
                print(f"Failed to disconnect from {name}: {e}")
        
        return results
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """모든 MCP 통합의 상태를 확인합니다."""
        results = {}
        
        for name, integration in self.integrations.items():
            try:
                health = await integration.health_check()
                results[name] = health
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "message": f"Health check failed: {str(e)}",
                    "timestamp": self._get_current_timestamp()
                }
        
        return results
    
    def get_integration(self, name: str) -> Optional[BaseMCP]:
        """지정된 이름의 MCP 통합을 반환합니다."""
        return self.integrations.get(name)
    
    def get_connection_status(self) -> Dict[str, str]:
        """모든 통합의 연결 상태를 반환합니다."""
        return self.connection_status.copy()
    
    async def is_any_connected(self) -> bool:
        """하나라도 연결된 통합이 있는지 확인합니다."""
        for integration in self.integrations.values():
            if await integration.is_connected():
                return True
        return False
    
    # Slack 관련 메서드들
    async def get_slack_info(self) -> Dict[str, Any]:
        """Slack 정보를 가져옵니다."""
        slack_integration = self.integrations.get("slack")
        if not slack_integration:
            raise ValueError("Slack integration not available")
        
        try:
            # 워크스페이스 정보
            workspace_info = await slack_integration.get_workspace_info()
            
            # 채널 정보 (전체)
            channels = await slack_integration.get_channels(include_private=True)
            
            # 최근 활동 (전체)
            recent_activity = await slack_integration.get_recent_activity(hours=168)  # 1주일
            
            # 모든 채널의 메시지 수집 (전체 범위)
            all_messages = {}
            total_message_count = 0
            
            for channel in channels:
                try:
                    # 각 채널의 메시지를 최대한 수집 (Slack API 제한 고려)
                    messages = await slack_integration.get_channel_messages(channel["id"], limit=1000)
                    all_messages[channel["name"]] = messages
                    total_message_count += len(messages)
                except Exception as e:
                    print(f"채널 {channel['name']} 메시지 수집 실패: {e}")
                    all_messages[channel["name"]] = []
            
            # AI 연구 관련 메시지 검색 (키워드 확장)
            ai_keywords = ["AI", "research", "optimization", "machine learning", "deep learning", "논문", "연구", "최적화"]
            ai_messages = []
            
            for keyword in ai_keywords:
                try:
                    keyword_messages = await slack_integration.search_messages(keyword)
                    ai_messages.extend(keyword_messages)
                except Exception as e:
                    print(f"키워드 '{keyword}' 검색 실패: {e}")
                    continue
            
            # 중복 제거
            unique_ai_messages = []
            seen_ids = set()
            for msg in ai_messages:
                if msg.get("id") not in seen_ids:
                    unique_ai_messages.append(msg)
                    seen_ids.add(msg.get("id"))
            
            return {
                "workspace_info": workspace_info,
                "channels": channels,
                "recent_activity": recent_activity,
                "all_channel_messages": all_messages,
                "total_message_count": total_message_count,
                "ai_research_messages": unique_ai_messages,
                "connection_status": await slack_integration.is_connected()
            }
            
        except Exception as e:
            print(f"Failed to get Slack info: {e}")
            # 폴백 데이터 반환
            return self._get_fallback_slack_info()
    
    def _get_fallback_slack_info(self) -> Dict[str, Any]:
        """Slack 연결 실패 시 사용할 폴백 데이터를 반환합니다."""
        return {
            "workspace_info": {
                "workspace_name": "AI Research Team (Fallback)",
                "member_count": 25,
                "status": "fallback"
            },
            "channels": [
                {
                    "name": "research-discussion",
                    "topic": "AI 연구 논의 및 아이디어 공유",
                    "member_count": 15
                }
            ],
            "recent_activity": {
                "total_messages": 45,
                "active_channels": 3,
                "trending_topics": ["AI 최적화", "동적 배칭", "머신러닝 성능"]
            },
            "all_channel_messages": {},
            "total_message_count": 0,
            "ai_research_messages": [
                {
                    "text": "AI 최적화 알고리즘에 대한 논의가 정말 흥미로웠어요.",
                    "channel": "research-discussion",
                    "timestamp": "2024-08-16T09:30:00Z"
                }
            ],
            "connection_status": False
        }
    
    # Notion 관련 메서드들
    async def get_notion_info(self) -> Dict[str, Any]:
        """Notion 정보를 가져옵니다."""
        notion_integration = self.integrations.get("notion")
        if not notion_integration:
            raise ValueError("Notion integration not available")
        
        try:
            # 워크스페이스 정보
            workspace_info = await notion_integration.get_workspace_info()
            
            # 데이터베이스 정보 (전체)
            databases = await notion_integration.get_databases()
            
            # 각 데이터베이스의 모든 항목 수집 (전체 범위)
            for db in databases:
                try:
                    entries = await notion_integration.get_database_entries(db['id'])
                    db['entries'] = entries  # 전체 항목 포함
                    print(f"데이터베이스 '{db.get('title', 'Unknown')}': {len(entries)}개 항목 수집")
                except Exception as e:
                    print(f"데이터베이스 '{db.get('title', 'Unknown')}' 항목 수집 실패: {e}")
                    db['entries'] = []
            
            # 전체 페이지 검색 (키워드 제한 없음)
            all_pages = await notion_integration.search_pages("", None)
            
            # 각 페이지의 전체 내용 수집
            pages_with_content = []
            for page in all_pages:
                try:
                    page_content = await notion_integration.get_page_content(page['id'])
                    pages_with_content.append(page_content)
                    print(f"페이지 '{page_content.get('title', 'Unknown')}': {len(page_content.get('content', []))}개 블록")
                except Exception as e:
                    print(f"페이지 '{page.get('title', 'Unknown')}' 내용 수집 실패: {e}")
                    continue
            
            # 최근 변경사항 (전체)
            recent_changes = await notion_integration.get_recent_changes(hours=168)  # 1주일
            
            return {
                "workspace_info": workspace_info,
                "databases": databases,
                "total_databases": len(databases),
                "total_database_entries": sum(len(db.get('entries', [])) for db in databases),
                "all_pages": pages_with_content,
                "total_pages": len(pages_with_content),
                "recent_changes": recent_changes,
                "connection_status": await notion_integration.is_connected()
            }
            
        except Exception as e:
            print(f"Failed to get Notion info: {e}")
            # 폴백 데이터 반환
            return self._get_fallback_notion_info()
    
    def _get_fallback_notion_info(self) -> Dict[str, Any]:
        """Notion 연결 실패 시 사용할 폴백 데이터를 반환합니다."""
        return {
            "workspace_info": {
                "workspace_name": "AI Research Workspace (Fallback)",
                "member_count": 15,
                "status": "fallback"
            },
            "databases": [
                {
                    "title": "AI Research Projects",
                    "description": "AI 연구 프로젝트 관리",
                    "last_edited": "2024-08-16T10:00:00Z"
                }
            ],
            "total_databases": 1,
            "total_database_entries": 0,
            "all_pages": [
                {
                    "title": "AI 연구 방향 및 계획",
                    "last_edited": "2024-08-16T10:00:00Z",
                    "status": "fallback"
                }
            ],
            "total_pages": 1,
            "recent_changes": [
                {
                    "page_title": "AI 연구 방향 및 계획",
                    "change_type": "content_updated",
                    "timestamp": "2024-08-16T10:00:00Z"
                }
            ],
            "connection_status": False
        }
    
    # Gmail 관련 메서드들
    async def get_gmail_info(self) -> Dict[str, Any]:
        """Gmail 정보를 가져옵니다."""
        gmail_integration = self.integrations.get("gmail")
        if not gmail_integration:
            raise ValueError("Gmail integration not available")
        
        try:
            # 프로필 정보
            profile_info = await gmail_integration.get_profile_info()
            
            # 라벨 정보 (전체)
            labels = await gmail_integration.get_labels()
            
            # 전체 메시지 수집 (최근 1000개)
            all_messages = await gmail_integration.get_messages(limit=1000)
            
            # AI 연구 관련 메시지 검색 (키워드 확장)
            ai_keywords = ["AI", "research", "machine learning", "deep learning", "논문", "연구", "최적화", "conference", "paper"]
            ai_messages = []
            
            for keyword in ai_keywords:
                try:
                    keyword_messages = await gmail_integration.search_messages(keyword)
                    ai_messages.extend(keyword_messages)
                except Exception as e:
                    print(f"키워드 '{keyword}' 검색 실패: {e}")
                    continue
            
            # 컨퍼런스 관련 메시지 검색 (키워드 확장)
            conference_keywords = ["conference", "workshop", "symposium", "컨퍼런스", "워크샵", "심포지엄", "deadline", "submission", "CFP"]
            conference_messages = []
            
            for keyword in conference_keywords:
                try:
                    keyword_messages = await gmail_integration.search_messages(keyword)
                    conference_messages.extend(keyword_messages)
                except Exception as e:
                    print(f"키워드 '{keyword}' 검색 실패: {e}")
                    continue
            
            # 중복 제거
            unique_ai_messages = []
            unique_conference_messages = []
            seen_ai_ids = set()
            seen_conf_ids = set()
            
            for msg in ai_messages:
                if msg.get("id") not in seen_ai_ids:
                    unique_ai_messages.append(msg)
                    seen_ai_ids.add(msg.get("id"))
            
            for msg in conference_messages:
                if msg.get("id") not in seen_conf_ids:
                    unique_conference_messages.append(msg)
                    seen_conf_ids.add(msg.get("id"))
            
            # 최근 활동 (전체)
            recent_activity = await gmail_integration.get_recent_activity()
            
            return {
                "profile_info": profile_info,
                "labels": labels,
                "total_labels": len(labels),
                "all_messages": all_messages,
                "total_messages": len(all_messages),
                "ai_research_messages": unique_ai_messages,
                "conference_messages": unique_conference_messages,
                "recent_activity": recent_activity,
                "connection_status": await gmail_integration.is_connected()
            }
            
        except Exception as e:
            print(f"Failed to get Gmail info: {e}")
            # 폴백 데이터 반환
            return self._get_fallback_gmail_info()
    
    def _get_fallback_gmail_info(self) -> Dict[str, Any]:
        """Gmail 연결 실패 시 사용할 폴백 데이터를 반환합니다."""
        return {
            "profile_info": {
                "email_address": "ai.researcher@gmail.com",
                "name": "AI Researcher (Fallback)",
                "messages_total": 15420,
                "status": "fallback"
            },
            "labels": [
                {
                    "name": "AI Research",
                    "messagesTotal": 234,
                    "messagesUnread": 12
                }
            ],
            "total_labels": 1,
            "all_messages": [],
            "total_messages": 0,
            "ai_research_messages": [
                {
                    "snippet": "AI 연구 논의를 위한 미팅 일정 조율",
                    "labelIds": ["INBOX", "Label_1234567890"]
                }
            ],
            "conference_messages": [
                {
                    "snippet": "ICML 2024 컨퍼런스 참가 등록 마감일 안내",
                    "labelIds": ["INBOX", "Label_1234567891"]
                }
            ],
            "recent_activity": {
                "total_messages": 45,
                "trending_topics": ["AI Research", "Conference Registration"]
            },
            "connection_status": False
        }
    
    async def get_all_info(self) -> Dict[str, Any]:
        """모든 MCP 통합에서 정보를 가져옵니다."""
        try:
            # 병렬로 모든 정보 수집
            tasks = [
                self.get_slack_info(),
                self.get_notion_info(),
                self.get_gmail_info()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            return {
                "slack": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
                "notion": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
                "gmail": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
                "overall_status": {
                    "total_integrations": len(self.integrations),
                    "connected_count": sum(1 for status in self.connection_status.values() if status == "connected"),
                    "connection_status": self.connection_status
                }
            }
            
        except Exception as e:
            print(f"Failed to get all info: {e}")
            return {
                "error": f"Failed to collect information: {str(e)}",
                "overall_status": {
                    "total_integrations": len(self.integrations),
                    "connected_count": 0,
                    "connection_status": self.connection_status
                }
            }
    
    def _get_current_timestamp(self) -> str:
        """현재 타임스탬프를 반환합니다."""
        import datetime
        return datetime.datetime.now().isoformat()
    
    def get_summary(self) -> Dict[str, Any]:
        """MCP 매니저의 요약 정보를 반환합니다."""
        return {
            "total_integrations": len(self.integrations),
            "integration_names": list(self.integrations.keys()),
            "connection_status": self.connection_status,
            "config_keys": list(self.config.keys()) if self.config else []
        }
    
    def group_by_titles(self, slack_data: Dict[str, Any], notion_data: Dict[str, Any], gmail_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """제목 기반으로 데이터를 동적으로 그룹화합니다."""
        # 모든 데이터를 수집
        all_items = []
        
        # Slack 메시지 전체 추가
        if slack_data and slack_data.get("connection_status") is not False:
            slack_messages = slack_data.get("all_channel_messages", {})
            for channel_name, messages in slack_messages.items():
                for msg in messages:
                    all_items.append({
                        "source": "slack",
                        "channel": channel_name,
                        "content": msg.get("text", ""),
                        "timestamp": msg.get("timestamp", ""),
                        "type": "message"
                    })
        
        # Notion 페이지 제목 추가
        if notion_data and notion_data.get("connection_status") is not False:
            pages = notion_data.get("all_pages", [])
            for page in pages:
                title = page.get("title", "")
                all_items.append({
                    "source": "notion",
                    "title": title,
                    "content_count": len(page.get("content", [])),
                    "last_edited": page.get("last_edited", ""),
                    "type": "page"
                })
        
        # Gmail 메시지 제목 추가
        if gmail_data and gmail_data.get("connection_status") is not False:
            messages = gmail_data.get("all_messages", [])
            for msg in messages:
                subject = msg.get("subject", msg.get("snippet", ""))
                all_items.append({
                    "source": "gmail",
                    "subject": subject,
                    "snippet": msg.get("snippet", ""),
                    "timestamp": msg.get("timestamp", ""),
                    "type": "email"
                })
        
        # 데이터가 없으면 기본 그룹 반환
        if not all_items:
            return {
                "General": []
            }
        
        # 동적 그룹 생성 (LLM 없이 규칙 기반으로 먼저 시도)
        dynamic_groups = self._create_dynamic_groups(all_items)
        
        return dynamic_groups
    
    def _create_dynamic_groups(self, all_items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """데이터를 분석하여 동적으로 그룹을 생성합니다."""
        # 키워드 기반으로 그룹 분류
        groups = {}
        
        for item in all_items:
            # 아이템의 텍스트 추출
            text = ""
            if item.get("source") == "slack":
                text = item.get("content", "")
            elif item.get("source") == "notion":
                text = item.get("title", "")
            elif item.get("source") == "gmail":
                text = f"{item.get('subject', '')} {item.get('snippet', '')}"
            
            if not text:
                continue
            
            # 그룹 분류
            group_name = self._classify_item_to_group(text)
            
            # 그룹이 없으면 생성
            if group_name not in groups:
                groups[group_name] = []
            
            groups[group_name].append(item)
        
        # 빈 그룹 제거
        return {k: v for k, v in groups.items() if v}
    
    def _classify_item_to_group(self, text: str) -> str:
        """텍스트를 분석하여 적절한 그룹명을 반환합니다."""
        text_lower = text.lower()
        
        # AI/ML 관련
        if any(keyword in text_lower for keyword in [
            "ai", "artificial intelligence", "machine learning", "ml", "deep learning", "dl",
            "neural network", "신경망", "머신러닝", "딥러닝", "인공지능", "논문", "연구", 
            "optimization", "최적화", "algorithm", "알고리즘", "bert", "gpt", "transformer",
            "lora", "diffusion", "gan", "cnn", "rnn", "lstm"
        ]):
            return "AI_Research"
        
        # 프로젝트/개발 관련
        if any(keyword in text_lower for keyword in [
            "project", "프로젝트", "development", "개발", "implementation", "구현",
            "code", "코드", "programming", "프로그래밍", "software", "소프트웨어",
            "repository", "repo", "git", "github", "deployment", "배포",
            "testing", "테스트", "debug", "디버그", "refactor", "리팩토링"
        ]):
            return "Development_Projects"
        
        # 학습/교육 관련
        if any(keyword in text_lower for keyword in [
            "study", "학습", "learning", "education", "교육", "course", "강의",
            "tutorial", "튜토리얼", "workshop", "워크샵", "training", "훈련",
            "book", "책", "documentation", "문서", "guide", "가이드",
            "3주차", "4주차", "week", "chapter", "챕터"
        ]):
            return "Learning_Study"
        
        # 컨퍼런스/이벤트 관련
        if any(keyword in text_lower for keyword in [
            "conference", "컨퍼런스", "workshop", "워크샵", "symposium", "심포지엄",
            "cfp", "call for papers", "submission", "제출", "deadline", "마감",
            "registration", "등록", "icml", "neurips", "aaai", "ijcai",
            "presentation", "발표", "poster", "포스터", "demo", "데모"
        ]):
            return "Conference_Events"
        
        # 데이터/분석 관련
        if any(keyword in text_lower for keyword in [
            "data", "데이터", "dataset", "데이터셋", "analysis", "분석",
            "statistics", "통계", "visualization", "시각화", "chart", "차트",
            "graph", "그래프", "table", "테이블", "csv", "json", "xml"
        ]):
            return "Data_Analysis"
        
        # 협업/커뮤니케이션 관련
        if any(keyword in text_lower for keyword in [
            "collaboration", "협업", "team", "팀", "meeting", "미팅", "회의",
            "discussion", "논의", "chat", "채팅", "communication", "소통",
            "feedback", "피드백", "review", "리뷰", "comment", "코멘트"
        ]):
            return "Collaboration_Communication"
        
        # 회고/계획 관련
        if any(keyword in text_lower for keyword in [
            "retrospective", "회고", "planning", "계획", "goal", "목표",
            "milestone", "마일스톤", "timeline", "타임라인", "schedule", "일정",
            "progress", "진행", "status", "상태", "update", "업데이트"
        ]):
            return "Planning_Retrospective"
        
        # 도구/기술 관련
        if any(keyword in text_lower for keyword in [
            "tool", "도구", "framework", "프레임워크", "library", "라이브러리",
            "api", "sdk", "platform", "플랫폼", "service", "서비스",
            "docker", "kubernetes", "cloud", "클라우드", "aws", "azure"
        ]):
            return "Tools_Technologies"
        
        # 기타/일반
        return "General_Discussion"
