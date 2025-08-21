"""Google Docs MCP for uploading reports to Google Drive."""

import os
from typing import Dict, Any, Optional
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
import pickle

from .base_mcp import BaseMCP

# Google Docs API를 위한 권한 범위 설정
SCOPES = [
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

class DocsMCP(BaseMCP):
    """Google Docs MCP for handling document creation and updates."""
    
    def __init__(self, config: dict = None):
        """Initialize the Google Docs MCP."""
        super().__init__(server_type='docs', config=config or {})
        self.service = None
        self.drive_service = None
        self.credentials = None
        self._is_connected = False
        # 토큰 파일 경로 설정
        self.token_path = os.getenv('DOCS_TOKEN_FILE', 'token.json')
        self.credentials_path = os.getenv('DOCS_CREDENTIALS_FILE', 'credentials.json')

    def connect(self) -> bool:
        """MCP 연결을 수행합니다."""
        return self.authenticate()
    
    def disconnect(self) -> bool:
        """MCP 연결을 해제합니다."""
        self.service = None
        self.drive_service = None
        self.credentials = None
        self._is_connected = False
        return True
    
    def health_check(self) -> bool:
        """MCP 상태를 확인합니다."""
        return self.service is not None and self.drive_service is not None
    
    def is_connected(self) -> bool:
        """MCP 연결 상태를 반환합니다."""
        return self._is_connected and self.health_check()
        
        # 토큰 파일 경로 설정
        self.token_path = os.getenv('DOCS_TOKEN_FILE', 'docs_token.json')  # docs용 별도 토큰
        self.credentials_path = os.getenv('CREDENTIALS_FILE', 'credentials.json')  # 공통 credentials

    def authenticate(self) -> bool:
        """Google Docs API 인증을 수행합니다."""
        try:
            print("[DEBUG] Google Docs 인증 시작")
            if os.path.exists(self.token_path):
                print("[DEBUG] 기존 토큰 파일 발견")
                self.credentials = Credentials.from_authorized_user_file(
                    self.token_path, SCOPES)
            
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    print("[DEBUG] 토큰 갱신 중")
                    self.credentials.refresh(Request())
                else:
                    print("[DEBUG] 새로운 인증 흐름 시작")
                    if not os.path.exists(self.credentials_path):
                        raise ValueError(f"Credentials file not found: {self.credentials_path}")
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    self.credentials = flow.run_local_server(port=0)
                
                # 토큰 저장
                with open(self.token_path, 'w') as token:
                    token.write(self.credentials.to_json())
                print("[DEBUG] 새 토큰 저장됨")
            
            # Google Docs와 Drive API 서비스 생성
            self.service = build('docs', 'v1', credentials=self.credentials)
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            print("[DEBUG] Google API 서비스 초기화 완료")
            return True
            
        except Exception as e:
            print(f"[ERROR] Google Docs 인증 실패: {str(e)}")
            return False
    
    def upload_report(self, title: str, content: str, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """텍스트 보고서를 Google Docs 문서로 업로드합니다."""
        try:
            if not self.service or not self.drive_service:
                if not self.authenticate():
                    raise ValueError("Google Docs 인증이 필요합니다.")
            
            print(f"[DEBUG] 문서 생성 시작: {title}")
            # 빈 문서 생성
            doc = self.service.documents().create(body={'title': title}).execute()
            doc_id = doc.get('documentId')
            
            print(f"[DEBUG] 문서 내용 업데이트 중")
            # 문서 내용 업데이트
            requests = [{
                'insertText': {
                    'location': {
                        'index': 1
                    },
                    'text': content
                }
            }]
            
            self.service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            
            # 특정 폴더로 이동 (옵션)
            if folder_id:
                print(f"[DEBUG] 문서를 지정된 폴더로 이동")
                file = self.drive_service.files().get(
                    fileId=doc_id,
                    fields='parents'
                ).execute()
                
                previous_parents = ",".join(file.get('parents', []))
                
                self.drive_service.files().update(
                    fileId=doc_id,
                    addParents=folder_id,
                    removeParents=previous_parents,
                    fields='id, parents'
                ).execute()
            
            print(f"[DEBUG] 문서 업로드 완료: {doc_id}")
            return {
                'success': True,
                'doc_id': doc_id,
                'url': f'https://docs.google.com/document/d/{doc_id}/edit'
            }
            
        except Exception as e:
            print(f"[ERROR] 문서 업로드 실패: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

from mcp.docs_mcp import DocsMCP

def main():
    # 마크다운 파일 읽기
    with open('output/docs/research_report.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # DocsMCP 인스턴스 생성
    docs_mcp = DocsMCP()
    
    # 구글 독스에 업로드
    result = docs_mcp.upload_report(
        title="AI 기술 동향 심층 분석 보고서",
        content=content
    )
    
    if result['success']:
        print(f"문서가 성공적으로 업로드되었습니다.")
        print(f"문서 URL: {result['url']}")
    else:
        print(f"업로드 실패: {result['error']}")

if __name__ == "__main__":
    main()