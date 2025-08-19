# Gmail API 설정 가이드

Gmail MCP를 사용하여 실제 Gmail 데이터에 액세스하려면 Google Cloud Console에서 Gmail API를 설정해야 합니다.

## 1. Google Cloud Console 설정

### 1.1 프로젝트 생성
1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. 프로젝트 이름을 `agent-cast-gmail` 등으로 설정

### 1.2 Gmail API 활성화
1. 좌측 메뉴에서 "API 및 서비스" > "라이브러리" 선택
2. "Gmail API" 검색 후 선택
3. "사용" 버튼 클릭하여 API 활성화

### 1.3 OAuth 동의 화면 설정 ⚠️ **필수!**
**이 단계를 건너뛰면 403 access_denied 오류가 발생합니다.**

1. 좌측 메뉴에서 "API 및 서비스" > "OAuth 동의 화면" 선택
2. 사용자 유형 선택:
   - **외부**: 개인 Gmail 계정 사용 시 (권장)
   - **내부**: Google Workspace 조직 내부에서만 사용 시
3. "만들기" 클릭

#### 📝 OAuth 동의 화면 정보 입력:
- **앱 이름**: `Agent Cast Gmail Integration`
- **사용자 지원 이메일**: 본인의 Gmail 주소
- **앱 도메인** (선택사항): 비워둘 수 있음
- **승인된 도메인** (선택사항): 비워둘 수 있음
- **개발자 연락처 정보**: 본인의 Gmail 주소
- "저장 후 계속" 클릭

#### 🔒 범위(Scopes) 설정:
1. "범위 추가 또는 삭제" 클릭
2. "Gmail API" 검색
3. `https://www.googleapis.com/auth/gmail.readonly` 범위 선택
4. "업데이트" 클릭
5. "저장 후 계속" 클릭

#### 👥 테스트 사용자 추가 (가장 중요!):
1. "테스트 사용자 추가" 클릭
2. **본인의 Gmail 주소** 입력 (꼭 추가해야 함!)
3. "추가" 클릭
4. "저장 후 계속" 클릭

### 1.4 OAuth 2.0 인증 정보 생성
1. 좌측 메뉴에서 "API 및 서비스" > "사용자 인증 정보" 선택
2. "사용자 인증 정보 만들기" > "OAuth 클라이언트 ID" 선택
3. 애플리케이션 유형: "데스크톱 애플리케이션" 선택
4. 이름: `Gmail MCP Client` 등으로 설정
5. "만들기" 클릭

### 1.5 인증 정보 다운로드
1. 생성된 OAuth 클라이언트 ID 옆의 다운로드 아이콘 클릭
2. JSON 파일을 `credentials.json` 이름으로 프로젝트 루트 디렉토리에 저장

## 2. 환경 설정

### 2.1 환경 변수 설정
`.env` 파일을 생성하고 다음 내용을 추가:

```env
# Gmail MCP
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json
GMAIL_USER_ID=me
```

### 2.2 의존성 설치
```bash
pip install -r requirements.txt
```

## 3. 첫 실행 및 인증

### 3.1 테스트 실행
```bash
python test_gmail_integration.py
```

### 3.2 인증 과정
1. 첫 실행 시 브라우저가 자동으로 열림
2. Google 계정으로 로그인
3. Gmail 읽기 권한 허용
4. 인증이 완료되면 `token.json` 파일이 자동 생성됨

## 4. 사용 예시

```python
import asyncio
from mcp.gmail_mcp import GmailMCP

async def main():
    config = {
        "user_id": "me",
        "credentials_file": "credentials.json",
        "token_file": "token.json"
    }
    
    gmail_mcp = GmailMCP(config)
    
    # 연결
    await gmail_mcp.connect()
    
    # 최신 메시지 30개 가져오기
    messages = await gmail_mcp.get_messages(max_results=30)
    
    for message in messages[:5]:
        headers = message.get('parsed_headers', {})
        print(f"From: {headers.get('from')}")
        print(f"Subject: {headers.get('subject')}")
        print(f"Snippet: {message.get('snippet')}")
        print("---")
    
    # 연결 해제
    await gmail_mcp.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## 5. 주요 기능

### 5.1 지원되는 메서드
- `connect()`: Gmail API 연결
- `get_messages(max_results=30)`: 최신 메시지 가져오기
- `get_profile_info()`: 계정 프로필 정보
- `get_labels()`: 라벨 목록
- `search_messages(query)`: 메시지 검색
- `disconnect()`: 연결 해제

### 5.2 메시지 데이터 구조
```python
{
    "id": "메시지 ID",
    "threadId": "스레드 ID",
    "snippet": "메시지 요약",
    "parsed_headers": {
        "from": "발신자",
        "subject": "제목",
        "date": "날짜"
    },
    "payload": {
        "body": {
            "text": "텍스트 본문",
            "html": "HTML 본문"
        }
    }
}
```

## 6. 문제 해결

### 6.1 일반적인 오류
- **credentials.json 파일이 없음**: Google Cloud Console에서 다시 다운로드
- **권한 거부**: OAuth 설정에서 테스트 사용자 추가 필요
- **API 할당량 초과**: Google Cloud Console에서 할당량 확인

### 6.2 보안 고려사항
- `credentials.json`과 `token.json` 파일은 절대로 Git에 커밋하지 마세요
- `.gitignore`에 해당 파일들을 추가하세요
- 프로덕션 환경에서는 서비스 계정 사용을 권장합니다

## 7. 제한사항

- Gmail API는 사용자당 일일 할당량이 있습니다 (기본: 1,000,000,000 할당량 단위)
- 메시지 읽기는 읽기 전용 권한만 사용합니다
- 대량의 메시지 처리 시 API 속도 제한을 고려해야 합니다
