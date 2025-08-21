"""Gmail MCP integration for collecting email information."""

import asyncio
import os
import json
import base64
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .base_mcp import BaseMCP


class GmailMCP(BaseMCP):
    """Gmail MCP 서버 연결을 담당하는 클래스."""
    
    # Gmail API에 필요한 권한 범위
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("gmail", config)
        
        # Gmail 특정 설정
        self.user_id = config.get("user_id", "me")
        self.labels = config.get("labels", [])
        self.filters = config.get("filters", [])
        self.credentials_file = config.get("credentials_file", os.getenv('CREDENTIALS_FILE', 'credentials.json'))  # 공통 credentials
        self.token_file = config.get("token_file", os.getenv('GMAIL_TOKEN_FILE', 'gmail_token.json'))  # gmail용 별도 토큰
        
        # 연결 상태
        self._connected = False
        self._service = None
        self._credentials = None
    
    async def connect(self) -> bool:
        """Gmail API에 연결합니다."""
        try:
            self.logger.info("Connecting to Gmail API...")
            
            # Gmail API 인증 처리
            await self._authenticate()
            
            if self._credentials:
                # Gmail API 서비스 빌드
                self._service = build('gmail', 'v1', credentials=self._credentials)
                self._connected = True
                self.update_connection_status("connected")
                self.logger.info("Successfully connected to Gmail API")
                return True
            else:
                self.logger.error("Failed to get valid credentials")
                self.update_connection_status("failed", "Invalid credentials")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Gmail API: {e}")
            self.update_connection_status("failed", str(e))
            return False
    
    async def _authenticate(self):
        """Gmail API 인증을 처리합니다."""
        creds = None
        
        # 토큰 파일이 있으면 기존 인증 정보 로드
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        
        # 유효한 인증 정보가 없으면 새로 인증
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # 토큰 갱신
                creds.refresh(Request())
            else:
                # 새로운 인증 플로우
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # 토큰 저장
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self._credentials = creds
    
    async def disconnect(self) -> bool:
        """Gmail API 연결을 해제합니다."""
        try:
            self.logger.info("Disconnecting from Gmail API...")
            
            self._service = None
            self._credentials = None
            self._connected = False
            self.update_connection_status("disconnected")
            self.logger.info("Successfully disconnected from Gmail API")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to disconnect from Gmail API: {e}")
            return False
    
    async def is_connected(self) -> bool:
        """연결 상태를 확인합니다."""
        return self._connected
    
    async def health_check(self) -> Dict[str, Any]:
        """Gmail MCP 서버 상태를 확인합니다."""
        try:
            if not await self.is_connected():
                return {
                    "status": "disconnected",
                    "message": "Not connected to Gmail MCP server",
                    "timestamp": self._get_current_timestamp()
                }
            
            # 실제 구현에서는 서버 상태 확인
            await asyncio.sleep(0.1)
            
            return {
                "status": "healthy",
                "message": "Gmail MCP server is responding",
                "timestamp": self._get_current_timestamp(),
                "user_id": self.user_id,
                "labels_count": len(self.labels),
                "filters_count": len(self.filters)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)}",
                "timestamp": self._get_current_timestamp()
            }
    
    async def get_profile_info(self) -> Dict[str, Any]:
        """Gmail 프로필 정보를 가져옵니다."""
        return await self.execute_with_retry(self._get_profile_info_impl)
    
    async def _get_profile_info_impl(self) -> Dict[str, Any]:
        """Gmail 프로필 정보를 가져오는 실제 구현."""
        if not self._service:
            raise Exception("Gmail API service not initialized. Please connect first.")
        
        try:
            # Gmail API를 사용하여 프로필 정보 가져오기
            profile = self._service.users().getProfile(userId=self.user_id).execute()
            
            return {
                "user_id": self.user_id,
                "email_address": profile.get('emailAddress', ''),
                "messages_total": profile.get('messagesTotal', 0),
                "threads_total": profile.get('threadsTotal', 0),
                "history_id": profile.get('historyId', '')
            }
            
        except HttpError as error:
            self.logger.error(f"Gmail API error: {error}")
            raise Exception(f"Failed to fetch profile info: {error}")
    
    async def get_labels(self) -> List[Dict[str, Any]]:
        """Gmail 라벨 목록을 가져옵니다."""
        return await self.execute_with_retry(self._get_labels_impl)
    
    async def _get_labels_impl(self) -> List[Dict[str, Any]]:
        """Gmail 라벨 목록을 가져오는 실제 구현."""
        if not self._service:
            raise Exception("Gmail API service not initialized. Please connect first.")
        
        try:
            # Gmail API를 사용하여 라벨 목록 가져오기
            results = self._service.users().labels().list(userId=self.user_id).execute()
            labels = results.get('labels', [])
            
            return labels
            
        except HttpError as error:
            self.logger.error(f"Gmail API error: {error}")
            raise Exception(f"Failed to fetch labels: {error}")
    
    async def get_messages(self, query: str = "", label_ids: Optional[List[str]] = None, max_results: int = 30) -> List[Dict[str, Any]]:
        """Gmail 메시지를 가져옵니다."""
        return await self.execute_with_retry(self._get_messages_impl, query, label_ids, max_results)
    
    async def _get_messages_impl(self, query: str = "", label_ids: Optional[List[str]] = None, max_results: int = 30) -> List[Dict[str, Any]]:
        """Gmail 메시지를 가져오는 실제 구현."""
        if not self._service:
            raise Exception("Gmail API service not initialized. Please connect first.")
        
        try:
            # Gmail API를 사용하여 메시지 목록 가져오기
            messages_result = self._service.users().messages().list(
                userId=self.user_id,
                q=query,
                labelIds=label_ids,
                maxResults=max_results
            ).execute()
            
            messages = messages_result.get('messages', [])
            detailed_messages = []
            
            # 각 메시지의 상세 정보 가져오기
            for message in messages:
                try:
                    msg_detail = self._service.users().messages().get(
                        userId=self.user_id,
                        id=message['id'],
                        format='full'
                    ).execute()
                    
                    # 메시지 정보 파싱
                    parsed_message = self._parse_message(msg_detail)
                    detailed_messages.append(parsed_message)
                    
                except HttpError as error:
                    self.logger.error(f"Error fetching message {message['id']}: {error}")
                    continue
            
            self.logger.info(f"Successfully fetched {len(detailed_messages)} messages")
            return detailed_messages
            
        except HttpError as error:
            self.logger.error(f"Gmail API error: {error}")
            raise Exception(f"Failed to fetch messages: {error}")
    
    def _parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Gmail API 응답을 파싱하여 통일된 형식으로 변환합니다."""
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        
        # 헤더에서 주요 정보 추출
        header_dict = {}
        for header in headers:
            header_dict[header['name'].lower()] = header['value']
        
        # 메시지 본문 추출
        body = self._extract_message_body(payload)
        
        return {
            "id": message.get('id'),
            "threadId": message.get('threadId'),
            "labelIds": message.get('labelIds', []),
            "snippet": message.get('snippet', ''),
            "historyId": message.get('historyId'),
            "internalDate": message.get('internalDate'),
            "sizeEstimate": message.get('sizeEstimate'),
            "payload": {
                "mimeType": payload.get('mimeType'),
                "headers": headers,
                "body": body
            },
            "parsed_headers": {
                "from": header_dict.get('from', ''),
                "to": header_dict.get('to', ''),
                "subject": header_dict.get('subject', ''),
                "date": header_dict.get('date', ''),
                "cc": header_dict.get('cc', ''),
                "bcc": header_dict.get('bcc', '')
            }
        }
    
    def _extract_message_body(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """메시지 본문을 추출합니다."""
        body = {"text": "", "html": ""}
        
        def extract_parts(part):
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    body["text"] = base64.urlsafe_b64decode(data).decode('utf-8')
            elif part.get('mimeType') == 'text/html':
                data = part.get('body', {}).get('data', '')
                if data:
                    body["html"] = base64.urlsafe_b64decode(data).decode('utf-8')
            elif 'parts' in part:
                for subpart in part['parts']:
                    extract_parts(subpart)
        
        # 본문이 직접 있는 경우
        if payload.get('body', {}).get('data'):
            data = payload['body']['data']
            try:
                decoded_body = base64.urlsafe_b64decode(data).decode('utf-8')
                if payload.get('mimeType') == 'text/html':
                    body["html"] = decoded_body
                else:
                    body["text"] = decoded_body
            except Exception as e:
                self.logger.error(f"Error decoding message body: {e}")
        
        # 멀티파트 메시지인 경우
        if 'parts' in payload:
            for part in payload['parts']:
                extract_parts(part)
        
        return body
    
    async def get_message_details(self, message_id: str) -> Dict[str, Any]:
        """메시지 상세 정보를 가져옵니다."""
        return await self.execute_with_retry(self._get_message_details_impl, message_id)
    
    async def _get_message_details_impl(self, message_id: str) -> Dict[str, Any]:
        """메시지 상세 정보를 가져오는 실제 구현."""
        # 실제 구현에서는 MCP를 통해 메시지 상세 정보를 가져옵니다
        # 현재는 시뮬레이션된 데이터를 반환
        
        await asyncio.sleep(0.4)
        
        # 메시지 ID에 따른 상세 정보 생성
        if "AI Research Meeting" in message_id:
            return {
                "id": message_id,
                "threadId": "thread_1234567890",
                "labelIds": ["INBOX", "Label_1234567890"],
                "snippet": "AI 연구 논의를 위한 미팅 일정 조율",
                "historyId": "1234567890",
                "internalDate": "1734345600000",
                "payload": {
                    "mimeType": "text/plain",
                    "headers": [
                        {"name": "From", "value": "research.team@company.com"},
                        {"name": "To", "value": "ai.researcher@gmail.com"},
                        {"name": "Subject", "value": "AI Research Meeting Schedule"},
                        {"name": "Date", "value": "Mon, 16 Aug 2024 10:00:00 +0900"}
                    ],
                    "body": {
                        "data": "안녕하세요, AI 연구팀입니다.\n\n다음 주 AI 연구 논의를 위한 미팅 일정을 조율하고자 합니다.\n\n가능한 시간:\n- 8월 20일 (화) 오후 2-4시\n- 8월 22일 (목) 오전 10-12시\n\n어떤 시간이 편하신지 알려주세요.\n\n감사합니다."
                    }
                },
                "sizeEstimate": 1024
            }
        else:
            return {
                "id": message_id,
                "threadId": "thread_1234567893",
                "labelIds": ["INBOX"],
                "snippet": "일반적인 이메일 메시지",
                "historyId": "1234567893",
                "internalDate": "1734086400000",
                "payload": {
                    "mimeType": "text/plain",
                    "headers": [
                        {"name": "From", "value": "general@example.com"},
                        {"name": "To", "value": "ai.researcher@gmail.com"},
                        {"name": "Subject", "value": "General Information"},
                        {"name": "Date", "value": "Fri, 13 Aug 2024 10:00:00 +0900"}
                    ],
                    "body": {
                        "data": "일반적인 이메일 내용입니다."
                    }
                },
                "sizeEstimate": 512
            }
    
    async def search_messages(self, query: str, label_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """메시지를 검색합니다."""
        return await self.execute_with_retry(self._search_messages_impl, query, label_ids)
    
    async def _search_messages_impl(self, query: str, label_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """메시지 검색의 실제 구현."""
        # 실제 구현에서는 MCP를 통해 메시지 검색을 수행
        # 현재는 시뮬레이션된 검색 결과를 반환
        
        await asyncio.sleep(0.6)
        
        # 쿼리에 따른 검색 결과 생성
        if "AI" in query or "ai" in query:
            return [
                {
                    "id": "msg_1234567890",
                    "threadId": "thread_1234567890",
                    "snippet": "AI 연구 논의를 위한 미팅 일정 조율",
                    "score": 0.95,
                    "labelIds": ["INBOX", "Label_1234567890"]
                }
            ]
        elif "conference" in query or "컨퍼런스" in query:
            return [
                {
                    "id": "msg_1234567892",
                    "threadId": "thread_1234567892",
                    "snippet": "ICML 2024 컨퍼런스 참가 등록 마감일 안내",
                    "score": 0.88,
                    "labelIds": ["INBOX", "Label_1234567891"]
                }
            ]
        else:
            return []
    
    async def get_threads(self, query: str = "", label_ids: Optional[List[str]] = None, max_results: int = 100) -> List[Dict[str, Any]]:
        """Gmail 스레드를 가져옵니다."""
        return await self.execute_with_retry(self._get_threads_impl, query, label_ids, max_results)
    
    async def _get_threads_impl(self, query: str = "", label_ids: Optional[List[str]] = None, max_results: int = 100) -> List[Dict[str, Any]]:
        """Gmail 스레드를 가져오는 실제 구현."""
        # 실제 구현에서는 MCP를 통해 스레드 정보를 가져옵니다
        # 현재는 시뮬레이션된 데이터를 반환
        
        await asyncio.sleep(0.4)
        
        return [
            {
                "id": "thread_1234567890",
                "snippet": "AI Research Meeting Schedule",
                "historyId": "1234567890",
                "messages": [
                    {
                        "id": "msg_1234567890",
                        "threadId": "thread_1234567890",
                        "labelIds": ["INBOX", "Label_1234567890"],
                        "snippet": "AI 연구 논의를 위한 미팅 일정 조율"
                    }
                ]
            },
            {
                "id": "thread_1234567891",
                "snippet": "Paper Review Request: ML Optimization",
                "historyId": "1234567891",
                "messages": [
                    {
                        "id": "msg_1234567891",
                        "threadId": "thread_1234567891",
                        "labelIds": ["INBOX", "Label_1234567890"],
                        "snippet": "머신러닝 최적화 알고리즘 논문 리뷰 요청"
                    }
                ]
            }
        ][:max_results]
    
    async def get_recent_activity(self, hours: int = 24) -> Dict[str, Any]:
        """최근 활동을 가져옵니다."""
        return await self.execute_with_retry(self._get_recent_activity_impl, hours)
    
    async def _get_recent_activity_impl(self, hours: int = 24) -> Dict[str, Any]:
        """최근 활동을 가져오는 실제 구현."""
        # 실제 구현에서는 MCP를 통해 최근 활동을 가져옵니다
        # 현재는 시뮬레이션된 데이터를 반환
        
        await asyncio.sleep(0.3)
        
        return {
            "period_hours": hours,
            "total_messages": 45,
            "total_threads": 23,
            "labels_activity": [
                {"label": "INBOX", "message_count": 25},
                {"label": "AI Research", "message_count": 12},
                {"label": "Conference", "message_count": 8}
            ],
            "top_senders": [
                {"email": "research.team@company.com", "message_count": 8},
                {"email": "reviewer@journal.com", "message_count": 5},
                {"email": "registration@icml.cc", "message_count": 3}
            ],
            "trending_topics": ["AI Research", "Conference Registration", "Paper Review"]
        }
    
    async def collect_and_save_simplified_data(self, max_emails: int = 30, output_dir: str = "output/gmail_data") -> Dict[str, Any]:
        """Gmail 데이터를 수집하고 간소화된 형태로 저장합니다."""
        result = {
            "success": False,
            "message": "",
            "saved_files": [],
            "total_emails": 0
        }
        
        try:
            # 출력 디렉토리 생성
            os.makedirs(output_dir, exist_ok=True)
            
            # 1. 연결 확인
            if not await self.is_connected():
                if not await self.connect():
                    result["message"] = "Gmail API 연결 실패"
                    return result
            
            # 2. 최신 메시지 가져오기
            self.logger.info(f"최신 {max_emails}개 메시지 수집 중...")
            messages = await self.get_messages(max_results=max_emails)
            
            if not messages:
                result["message"] = "메시지를 가져올 수 없음"
                return result
            
            # 3. 간소화된 데이터 생성
            simplified_emails = []
            
            for i, message in enumerate(messages):
                headers = message.get('parsed_headers', {})
                
                # 이메일 본문 추출
                content = ""
                payload = message.get('payload', {})
                body = payload.get('body', {})
                
                if body.get('text'):
                    content = body.get('text', '')
                elif body.get('html'):
                    # HTML 태그 제거
                    html_content = body.get('html', '')
                    content = re.sub(r'<[^>]+>', '', html_content)
                    content = re.sub(r'\s+', ' ', content).strip()
                else:
                    content = message.get('snippet', '')
                
                # 내용이 너무 길면 자르기 (1000자 제한)
                if len(content) > 1000:
                    content = content[:1000] + "..."
                
                simplified_email = {
                    "index": i + 1,
                    "email_id": message.get('id', ''),
                    "from": headers.get('from', '알 수 없음'),
                    "date": headers.get('date', '날짜 없음'),
                    "subject": headers.get('subject', '제목 없음'),
                    "content": content.strip() if content else message.get('snippet', '내용 없음')
                }
                simplified_emails.append(simplified_email)
            
            # 4. Gmail 프로필 정보 가져오기 (파일명에 사용)
            try:
                profile = await self.get_profile_info()
                email_address = profile.get('email_address', 'unknown')
                # 이메일에서 @ 앞부분만 추출하여 파일명으로 사용
                gmail_id = email_address.split('@')[0] if '@' in email_address else 'unknown'
            except Exception as e:
                self.logger.warning(f"프로필 정보 가져오기 실패, 기본값 사용: {e}")
                gmail_id = 'unknown'
            
            # 5. 간소화된 데이터 구조 생성
            simplified_data = {
                "collection_info": {
                    "collection_time": datetime.now().isoformat(),
                    "total_emails": len(simplified_emails),
                    "max_requested": max_emails,
                    "source": "gmail_mcp",
                    "gmail_id": gmail_id,
                    "simplified": True
                },
                "emails": simplified_emails
            }
            
            # 6. 파일 저장 (Gmail ID 기반)
            saved_files = []
            
            # Gmail ID 기반 파일명으로 저장
            gmail_file = os.path.join(output_dir, f"{gmail_id}_gmail.json")
            with open(gmail_file, 'w', encoding='utf-8') as f:
                json.dump(simplified_data, f, ensure_ascii=False, indent=2)
            saved_files.append(gmail_file)
            
            # 결과 업데이트
            result.update({
                "success": True,
                "message": f"성공적으로 {len(simplified_emails)}개의 이메일 데이터를 저장했습니다",
                "saved_files": saved_files,
                "total_emails": len(simplified_emails)
            })
            
            self.logger.info(f"간소화된 Gmail 데이터 저장 완료: {len(simplified_emails)}개 이메일")
            for file_path in saved_files:
                self.logger.info(f"저장된 파일: {file_path}")
            
            return result
            
        except Exception as e:
            error_msg = f"Gmail 데이터 수집 및 저장 실패: {str(e)}"
            self.logger.error(error_msg)
            result["message"] = error_msg
            return result


async def main():
    """Gmail MCP를 실행하여 데이터를 수집합니다."""
    # Gmail MCP 설정
    config = {
        "user_id": os.getenv("GMAIL_USER_ID", "me"),
        "credentials_file": os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json"),
        "token_file": os.getenv("GMAIL_TOKEN_FILE", "token.json")
    }
    
    # Gmail MCP 인스턴스 생성
    gmail_mcp = GmailMCP(config)
    
    try:
        # 데이터 수집 및 저장
        result = await gmail_mcp.collect_and_save_simplified_data(max_emails=30)
        
        if result["success"]:
            print(f"✅ {result['message']}")
            for file_path in result["saved_files"]:
                print(f"📄 {file_path}")
        else:
            print(f"❌ {result['message']}")
    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    
    finally:
        # 연결 해제
        await gmail_mcp.disconnect()


if __name__ == "__main__":
    # 환경 변수 로드
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    asyncio.run(main())
