"""Slack MCP integration for collecting workspace information."""

import asyncio
import os
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
try:
    from .base_mcp import BaseMCP
except ImportError:
    # 직접 실행할 때를 위한 절대 경로
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base_mcp import BaseMCP


class SlackMCP(BaseMCP):
    """Slack MCP 서버 연결을 담당하는 클래스."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("slack", config)
        
        # Slack 특정 설정
        self.workspace_id = config.get("workspace_id") or os.getenv("SLACK_WORKSPACE_ID")
        self.bot_token = config.get("bot_token") or os.getenv("SLACK_BOT_TOKEN")
        self.app_token = config.get("app_token") or os.getenv("SLACK_APP_TOKEN")
        self.channels = config.get("channels", [])
        self.users = config.get("users", [])
        
        # 데이터 저장 경로
        self.output_dir = config.get("output_dir", "output/slack_data")
        
        # 연결 상태
        self._connected = False
        self._client = None
        
        # Slack 클라이언트 초기화
        if self.bot_token:
            self._client = AsyncWebClient(token=self.bot_token)
    
    async def connect(self) -> bool:
        """Slack API에 연결하고 인증을 확인합니다."""
        try:
            self.logger.info("Connecting to Slack API...")
            
            if not self._client:
                raise ValueError("Slack 클라이언트가 초기화되지 않았습니다. 토큰을 확인해주세요.")
            
            # API 테스트 및 인증 확인
            response = await self._client.auth_test()
            
            if response["ok"]:
                self.workspace_id = response.get("team_id", self.workspace_id)
                self.user_id = response.get("user_id")
                self.bot_id = response.get("bot_id")
                
                self._connected = True
                self.update_connection_status("connected")
                self.logger.info(f"Successfully connected to Slack workspace: {response.get('team')}")
                
                # 출력 디렉토리 생성
                os.makedirs(self.output_dir, exist_ok=True)
                
                return True
            else:
                raise SlackApiError("인증 실패", response)
            
        except SlackApiError as e:
            self.logger.error(f"Slack API 에러: {e.response.get('error', str(e))}")
            self.update_connection_status("failed", str(e))
            return False
        except Exception as e:
            self.logger.error(f"Slack 연결 실패: {e}")
            self.update_connection_status("failed", str(e))
            return False
    
    async def disconnect(self) -> bool:
        """Slack MCP 서버 연결을 해제합니다."""
        try:
            self.logger.info("Disconnecting from Slack MCP server...")
            
            # 실제 구현에서는 연결 해제 로직
            await asyncio.sleep(0.5)
            
            self._connected = False
            self.update_connection_status("disconnected")
            self.logger.info("Successfully disconnected from Slack MCP server")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to disconnect from Slack MCP server: {e}")
            return False
    
    async def is_connected(self) -> bool:
        """연결 상태를 확인합니다."""
        return self._connected
    
    async def health_check(self) -> Dict[str, Any]:
        """Slack MCP 서버 상태를 확인합니다."""
        try:
            if not await self.is_connected():
                return {
                    "status": "disconnected",
                    "message": "Not connected to Slack MCP server",
                    "timestamp": self._get_current_timestamp()
                }
            
            # 실제 구현에서는 서버 상태 확인
            await asyncio.sleep(0.1)
            
            return {
                "status": "healthy",
                "message": "Slack MCP server is responding",
                "timestamp": self._get_current_timestamp(),
                "workspace_id": self.workspace_id,
                "channels_count": len(self.channels),
                "users_count": len(self.users)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)}",
                "timestamp": self._get_current_timestamp()
            }
    
    async def get_workspace_info(self) -> Dict[str, Any]:
        """워크스페이스 정보를 가져옵니다."""
        return await self.execute_with_retry(self._get_workspace_info_impl)
    
    async def _get_workspace_info_impl(self) -> Dict[str, Any]:
        """워크스페이스 정보를 가져오는 실제 구현."""
        try:
            # 팀 정보 가져오기
            team_info = await self._client.team_info()
            
            if not team_info["ok"]:
                raise SlackApiError("팀 정보 조회 실패", team_info)
            
            team = team_info["team"]
            
            # 사용자 목록 가져오기 (멤버 수 계산용) - Rate Limiting 방지를 위해 선택적으로
            member_count = "N/A"
            try:
                users_list = await self._client.users_list()
                if users_list["ok"]:
                    member_count = len([u for u in users_list.get("members", []) if not u.get("deleted", False)])
            except Exception as e:
                self.logger.warning(f"사용자 목록 조회 건너뜀 (Rate Limiting 방지): {e}")
            
            workspace_info = {
                "workspace_id": team["id"],
                "workspace_name": team["name"],
                "workspace_domain": team["domain"],
                "member_count": member_count,
                "plan": team.get("plan", "Unknown"),
                "created": datetime.fromtimestamp(team.get("date_created", 0)).isoformat() + "Z" if team.get("date_created") else "N/A",
                "enterprise_id": team.get("enterprise_id"),
                "enterprise_name": team.get("enterprise_name")
            }
            
            # 개별 저장 제거 - 통합 저장에서 처리
            
            return workspace_info
            
        except SlackApiError as e:
            self.logger.error(f"워크스페이스 정보 조회 실패: {e}")
            raise
        except Exception as e:
            self.logger.error(f"워크스페이스 정보 처리 실패: {e}")
            raise
    
    async def get_channels(self, include_private: bool = False) -> List[Dict[str, Any]]:
        """채널 목록을 가져옵니다."""
        return await self.execute_with_retry(self._get_channels_impl, include_private)
    
    async def _get_channels_impl(self, include_private: bool = False) -> List[Dict[str, Any]]:
        """채널 목록을 가져오는 실제 구현."""
        try:
            channels = []
            
            # 채널 가져오기 - 권한에 따라 조정
            try:
                if include_private:
                    # 비공개 채널도 포함하려고 시도
                    conversations = await self._client.conversations_list(
                        types="public_channel,private_channel"
                    )
                else:
                    # 공개 채널만
                    conversations = await self._client.conversations_list(
                        types="public_channel"
                    )
            except SlackApiError as e:
                if "missing_scope" in str(e) and "groups:read" in str(e):
                    # groups:read 권한이 없으면 공개 채널만 조회 (조용히 처리)
                    conversations = await self._client.conversations_list(
                        types="public_channel"
                    )
                else:
                    raise
            
            if not conversations["ok"]:
                raise SlackApiError("채널 목록 조회 실패", conversations)
            
            for channel in conversations.get("channels", []):
                # 채널 상세 정보 가져오기
                channel_info = await self._client.conversations_info(channel=channel["id"])
                
                if channel_info["ok"]:
                    ch = channel_info["channel"]
                    
                    # 채널 멤버 수 가져오기
                    try:
                        members = await self._client.conversations_members(channel=channel["id"])
                        member_count = len(members.get("members", [])) if members["ok"] else 0
                    except SlackApiError as e:
                        if "not_in_channel" in str(e):
                            # 봇이 채널에 참여하지 않은 경우 (조용히 처리)
                            member_count = "N/A"
                        else:
                            member_count = 0
                    except Exception:
                        member_count = 0
                    
                    channel_data = {
                        "id": ch["id"],
                        "name": ch["name"],
                        "is_private": ch.get("is_private", False),
                        "is_archived": ch.get("is_archived", False),
                        "member_count": member_count,
                        "topic": ch.get("topic", {}).get("value", ""),
                        "purpose": ch.get("purpose", {}).get("value", ""),
                        "created": datetime.fromtimestamp(ch["created"]).isoformat() + "Z" if ch.get("created") else None,
                        "creator": ch.get("creator")
                    }
                    channels.append(channel_data)
            
            # 개별 저장 제거 - 통합 저장에서 처리
            
            return channels
            
        except SlackApiError as e:
            self.logger.error(f"채널 목록 조회 실패: {e}")
            raise
        except Exception as e:
            self.logger.error(f"채널 정보 처리 실패: {e}")
            raise
    
    async def get_channel_messages(self, channel_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """채널의 메시지를 가져옵니다."""
        return await self.execute_with_retry(self._get_channel_messages_impl, channel_id, limit)
    
    async def _get_channel_messages_impl(self, channel_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """채널 메시지를 가져오는 실제 구현."""
        try:
            messages = []
            
            # 채널 히스토리 가져오기 (최근 메시지부터)
            try:
                history = await self._client.conversations_history(
                    channel=channel_id,
                    limit=min(limit, 1000)  # Slack API 제한
                )
                
                if not history["ok"]:
                    if history.get("error") == "not_in_channel":
                        # 봇이 채널에 참여하지 않은 경우 조용히 처리
                        return []
                    else:
                        raise SlackApiError("메시지 히스토리 조회 실패", history)
            except SlackApiError as e:
                if "not_in_channel" in str(e):
                    # 봇이 채널에 참여하지 않은 경우 조용히 빈 리스트 반환
                    return []
                else:
                    raise
            
            for message in history.get("messages", []):
                # 메시지 데이터 정리
                message_data = {
                    "id": message.get("ts"),
                    "channel_id": channel_id,
                    "user_id": message.get("user"),
                    "text": message.get("text", ""),
                    "timestamp": datetime.fromtimestamp(float(message["ts"])).isoformat() + "Z",
                    "thread_ts": message.get("thread_ts"),
                    "reply_count": message.get("reply_count", 0),
                    "reactions": []
                }
                
                # 반응(이모지) 정보 추가
                if "reactions" in message:
                    for reaction in message["reactions"]:
                        message_data["reactions"].append({
                            "name": reaction["name"],
                            "count": reaction["count"],
                            "users": reaction.get("users", [])
                        })
                
                # 첨부 파일 정보 추가
                if "files" in message:
                    message_data["files"] = []
                    for file in message["files"]:
                        message_data["files"].append({
                            "id": file.get("id"),
                            "name": file.get("name"),
                            "mimetype": file.get("mimetype"),
                            "size": file.get("size"),
                            "url": file.get("url_private")
                        })
                
                messages.append(message_data)
            
            # 개별 저장 제거 - 통합 저장에서 처리
            
            return messages[:limit]
            
        except SlackApiError as e:
            self.logger.error(f"채널 메시지 조회 실패: {e}")
            raise
        except Exception as e:
            self.logger.error(f"메시지 처리 실패: {e}")
            raise
    
    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자 정보를 가져옵니다."""
        return await self.execute_with_retry(self._get_user_info_impl, user_id)
    
    async def _get_user_info_impl(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자 정보를 가져오는 실제 구현."""
        try:
            # 사용자 정보 가져오기
            user_info = await self._client.users_info(user=user_id)
            
            if not user_info["ok"]:
                if user_info.get("error") == "user_not_found":
                    return None
                raise SlackApiError("사용자 정보 조회 실패", user_info)
            
            user = user_info["user"]
            profile = user.get("profile", {})
            
            user_data = {
                "id": user["id"],
                "name": user.get("name"),
                "real_name": user.get("real_name"),
                "display_name": profile.get("display_name") or profile.get("real_name"),
                "email": profile.get("email"),
                "phone": profile.get("phone"),
                "is_bot": user.get("is_bot", False),
                "is_admin": user.get("is_admin", False),
                "is_owner": user.get("is_owner", False),
                "timezone": user.get("tz"),
                "timezone_label": user.get("tz_label"),
                "status_emoji": profile.get("status_emoji"),
                "status_text": profile.get("status_text"),
                "title": profile.get("title"),
                "avatar_hash": profile.get("avatar_hash"),
                "image_original": profile.get("image_original"),
                "deleted": user.get("deleted", False),
                "updated": datetime.fromtimestamp(user["updated"]).isoformat() + "Z" if user.get("updated") else None
            }
            
            return user_data
            
        except SlackApiError as e:
            self.logger.error(f"사용자 정보 조회 실패: {e}")
            return None
        except Exception as e:
            self.logger.error(f"사용자 정보 처리 실패: {e}")
            return None
    
    async def search_messages(self, query: str, channel_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """메시지를 검색합니다."""
        return await self.execute_with_retry(self._search_messages_impl, query, channel_ids)
    
    async def _search_messages_impl(self, query: str, channel_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """메시지 검색의 실제 구현."""
        try:
            # 검색 쿼리 구성
            search_query = query
            if channel_ids:
                # 특정 채널에서만 검색
                channel_filter = " ".join([f"in:#{ch_id}" for ch_id in channel_ids])
                search_query = f"{query} {channel_filter}"
            
            # 메시지 검색
            search_result = await self._client.search_messages(
                query=search_query,
                sort="timestamp",
                sort_dir="desc"
            )
            
            if not search_result["ok"]:
                raise SlackApiError("메시지 검색 실패", search_result)
            
            messages = []
            search_messages = search_result.get("messages", {})
            
            for match in search_messages.get("matches", []):
                # 채널 정보 가져오기
                channel_name = "unknown"
                if match.get("channel", {}).get("name"):
                    channel_name = match["channel"]["name"]
                
                message_data = {
                    "id": match.get("ts"),
                    "channel_id": match.get("channel", {}).get("id"),
                    "channel_name": channel_name,
                    "user_id": match.get("user"),
                    "text": match.get("text", ""),
                    "timestamp": datetime.fromtimestamp(float(match["ts"])).isoformat() + "Z",
                    "score": match.get("score", 0),
                    "permalink": match.get("permalink"),
                    "type": match.get("type")
                }
                messages.append(message_data)
            
            # 검색 결과 저장
            search_data = {
                "query": query,
                "channel_ids": channel_ids,
                "timestamp": datetime.now().isoformat() + "Z",
                "total_results": search_messages.get("total", 0),
                "messages": messages
            }
            # 개별 저장 제거 - 통합 저장에서 처리
            
            return messages
            
        except SlackApiError as e:
            self.logger.error(f"메시지 검색 실패: {e}")
            return []
        except Exception as e:
            self.logger.error(f"검색 처리 실패: {e}")
            return []
    
    async def get_recent_activity(self, hours: int = 24) -> Dict[str, Any]:
        """최근 활동을 가져옵니다."""
        return await self.execute_with_retry(self._get_recent_activity_impl, hours)
    
    async def _get_recent_activity_impl(self, hours: int = 24) -> Dict[str, Any]:
        """최근 활동을 가져오는 실제 구현."""
        try:
            # 시간 범위 계산
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            oldest_ts = str(start_time.timestamp())
            
            # 채널 목록 가져오기
            channels = await self.get_channels(include_private=True)
            
            activity_data = {
                "period_hours": hours,
                "start_time": start_time.isoformat() + "Z",
                "end_time": end_time.isoformat() + "Z",
                "total_messages": 0,
                "active_channels": 0,
                "active_users": set(),
                "channel_activity": {},
                "user_activity": {}
            }
            
            # 각 채널의 최근 활동 분석
            for channel in channels:
                try:
                    # Rate Limiting 방지를 위한 지연
                    await asyncio.sleep(1.0)  # Rate Limiting 방지를 위해 딜레이 증가
                    
                    # 채널의 최근 메시지 가져오기
                    history = await self._client.conversations_history(
                        channel=channel["id"],
                        oldest=oldest_ts,
                        limit=1000
                    )
                    
                    if history["ok"]:
                        messages = history.get("messages", [])
                        if messages:
                            activity_data["active_channels"] += 1
                            activity_data["total_messages"] += len(messages)
                            activity_data["channel_activity"][channel["name"]] = len(messages)
                            
                            # 사용자별 메시지 수 계산
                            for message in messages:
                                user_id = message.get("user")
                                if user_id:
                                    activity_data["active_users"].add(user_id)
                                    if user_id not in activity_data["user_activity"]:
                                        activity_data["user_activity"][user_id] = 0
                                    activity_data["user_activity"][user_id] += 1
                                    
                except Exception as e:
                    self.logger.warning(f"채널 {channel['name']} 활동 분석 실패: {e}")
                    continue
            
            # 상위 채널 및 사용자 정렬
            top_channels = sorted(
                activity_data["channel_activity"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            top_users = sorted(
                activity_data["user_activity"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # 최종 결과 구성
            result = {
            "period_hours": hours,
                "start_time": activity_data["start_time"],
                "end_time": activity_data["end_time"],
                "total_messages": activity_data["total_messages"],
                "active_channels": activity_data["active_channels"],
                "active_users": len(activity_data["active_users"]),
                "top_channels": [{"channel": ch, "message_count": count} for ch, count in top_channels],
                "top_users": [{"user_id": user, "message_count": count} for user, count in top_users]
            }
            
            # 개별 저장 제거 - 통합 저장에서 처리
            
            return result
            
        except Exception as e:
            self.logger.error(f"최근 활동 분석 실패: {e}")
            raise
    
    async def _save_data(self, data: Any, filename: str) -> None:
        """데이터를 JSON 파일로 저장합니다."""
        try:
            # 출력 디렉토리 생성
            os.makedirs(self.output_dir, exist_ok=True)
            
            # 파일 경로 생성
            file_path = os.path.join(self.output_dir, filename)
            
            # JSON으로 저장
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"데이터 저장 완료: {file_path}")
            
        except Exception as e:
            self.logger.error(f"데이터 저장 실패 ({filename}): {e}")
    
    async def save_slack_data(self, workspace_info, channels, all_messages):
        """Slack 데이터를 직관적인 구조로 저장"""
        try:
            # 1. 채널 정보 저장
            channels_data = {
                "timestamp": datetime.now().isoformat() + "Z",
                "workspace": workspace_info,
                "channels": channels
            }
            
            channels_file = os.path.join(self.output_dir, "channels_info.json")
            with open(channels_file, 'w', encoding='utf-8') as f:
                json.dump(channels_data, f, ensure_ascii=False, indent=2)
            
            # 2. 각 채널별 메시지 저장
            saved_files = [channels_file]
            for channel_name, messages in all_messages.items():
                if messages:  # 메시지가 있는 채널만 저장
                    message_file = os.path.join(self.output_dir, f"messages_{channel_name}.json")
                    message_data = {
                        "channel": channel_name,
                        "timestamp": datetime.now().isoformat() + "Z",
                        "message_count": len(messages),
                        "messages": messages
                    }
                    
                    with open(message_file, 'w', encoding='utf-8') as f:
                        json.dump(message_data, f, ensure_ascii=False, indent=2)
                    saved_files.append(message_file)
            
            return saved_files
            
        except Exception as e:
            self.logger.error(f"데이터 저장 실패: {e}")
            return None
    
    async def collect_all_data(self) -> Dict[str, Any]:
        """모든 Slack 데이터를 수집하고 저장합니다."""
        try:
            self.logger.info("Slack 데이터 수집 시작...")
            
            collected_data = {
                "timestamp": datetime.now().isoformat() + "Z",
                "workspace_info": None,
                "channels": [],
                "messages": {},
                "recent_activity": None
            }
            
            # 1. 워크스페이스 정보 수집
            self.logger.info("워크스페이스 정보 수집 중...")
            collected_data["workspace_info"] = await self.get_workspace_info()
            
            # 2. 채널 목록 수집
            self.logger.info("채널 목록 수집 중...")
            channels = await self.get_channels(include_private=True)
            collected_data["channels"] = channels
            
            # 3. 각 채널의 메시지 수집
            for channel in channels:
                try:
                    self.logger.info(f"채널 '{channel['name']}' 메시지 수집 중...")
                    messages = await self.get_channel_messages(channel["id"], limit=500)
                    collected_data["messages"][channel["name"]] = messages
                    
                    # 사용자 정보 수집 제거 (Rate Limiting 방지)
                                
                except Exception as e:
                    self.logger.error(f"채널 '{channel['name']}' 데이터 수집 실패: {e}")
                    continue
            
            # 4. 최근 활동 분석
            self.logger.info("최근 활동 분석 중...")
            collected_data["recent_activity"] = await self.get_recent_activity(24)
            
            # 5. 새로운 구조로 데이터 저장
            saved_files = await self.save_slack_data(
                collected_data["workspace_info"],
                collected_data["channels"], 
                collected_data["messages"]
            )
            
            collected_data["saved_files"] = saved_files
            
            self.logger.info("Slack 데이터 수집 완료!")
            return collected_data
            
        except Exception as e:
            self.logger.error(f"Slack 데이터 수집 실패: {e}")
            raise


def print_separator(title: str):
    """섹션 구분자를 출력합니다."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


async def main():
    """메인 함수 - Slack 데이터 수집"""
    load_dotenv()
    
    config = {"output_dir": "output/slack_data"}
    slack_mcp = SlackMCP(config)
    
    print("🚀 Slack 데이터 수집 시작...")
    
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    if not bot_token:
        print("❌ SLACK_BOT_TOKEN이 설정되지 않았습니다.")
        return
    
    try:
        # 연결
        if not await slack_mcp.connect():
            print("❌ 연결 실패")
            return
        print("✅ 연결 성공!")
        
        # 전체 데이터 수집
        print("📊 데이터 수집 중...")
        full_data = await slack_mcp.collect_all_data()
        
        # 결과 요약
        channels_count = len(full_data.get('channels', []))
        messages_count = sum(len(msgs) for msgs in full_data.get('messages', {}).values())
        saved_files = full_data.get('saved_files', [])
        
        print(f"✅ 수집 완료!")
        print(f"📂 채널: {channels_count}개")
        print(f"💬 메시지: {messages_count}개")
        print(f"📁 생성된 파일:")
        print(f"   📄 channels_info.json (채널 정보)")
        
        # 메시지 파일들 표시
        message_files = [f for f in saved_files if f.endswith('.json') and 'messages_' in f]
        for file_path in message_files:
            filename = os.path.basename(file_path)
            channel_name = filename.replace('messages_', '').replace('.json', '')
            print(f"   💬 messages_{channel_name}.json")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        
    finally:
        await slack_mcp.disconnect()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
