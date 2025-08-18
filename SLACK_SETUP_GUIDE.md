# Slack 통합 설정 가이드

이 가이드는 Agent-Cast에서 Slack API를 사용하여 워크스페이스 데이터를 수집하는 방법을 안내합니다.

## 📋 사전 요구사항

1. Slack 워크스페이스에 대한 관리자 권한
2. Python 3.8 이상
3. 필요한 Python 패키지 설치

## 🔧 Slack App 설정

### 1단계: Slack App 생성

1. [Slack API 웹사이트](https://api.slack.com/apps)에 접속
2. "Create New App" 클릭
3. "From scratch" 선택
4. App 이름 입력 (예: "Agent-Cast Data Collector")
5. 워크스페이스 선택
6. "Create App" 클릭

### 2단계: Bot Token Scopes 설정

1. 왼쪽 메뉴에서 "OAuth & Permissions" 클릭
2. "Scopes" 섹션의 "Bot Token Scopes"에서 다음 권한들을 추가:

**필수 권한:**
- `channels:history` - 공개 채널의 메시지 읽기
- `channels:read` - 공개 채널 정보 읽기
- `users:read` - 사용자 정보 읽기
- `team:read` - 워크스페이스 정보 읽기

**선택 권한 (비공개 채널 액세스용):**
- `groups:history` - 비공개 채널의 메시지 읽기
- `groups:read` - 비공개 채널 정보 읽기
- `im:history` - 다이렉트 메시지 읽기
- `im:read` - 다이렉트 메시지 정보 읽기
- `mpim:history` - 그룹 다이렉트 메시지 읽기
- `mpim:read` - 그룹 다이렉트 메시지 정보 읽기
- `search:read` - 메시지 검색

### 3단계: 워크스페이스에 앱 설치

1. "OAuth & Permissions" 페이지에서 "Install to Workspace" 클릭
2. 권한 요청을 검토하고 "Allow" 클릭
3. "Bot User OAuth Token" 복사 (xoxb-로 시작하는 토큰)

### 3.5단계: 봇을 채널에 초대 (중요!)

메시지를 수집하려는 채널에 봇을 초대해야 합니다:

1. Slack 워크스페이스에서 수집하려는 채널로 이동
2. 채널 멤버 목록에서 "+" 버튼 클릭
3. 생성한 앱 이름을 검색하여 초대
4. 또는 채널에서 `/invite @your-app-name` 명령 사용

**주의**: 봇이 채널에 참여하지 않으면 `not_in_channel` 에러가 발생합니다.

### 4단계: Socket Mode 활성화 (선택사항)

실시간 이벤트가 필요한 경우:

1. 왼쪽 메뉴에서 "Socket Mode" 클릭
2. "Enable Socket Mode" 토글 활성화
3. Token Name 입력 (예: "Agent-Cast Socket Token")
4. "Generate" 클릭
5. "App-Level Token" 복사 (xapp-로 시작하는 토큰)

## 🔐 환경 변수 설정

`.env` 파일에 다음 환경 변수를 추가:

```bash
# Slack MCP 설정
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_WORKSPACE_ID=T1234567890  # 선택사항 (API에서 자동 감지)
SLACK_APP_TOKEN=xapp-your-app-token-here  # Socket Mode 사용 시만 필요
```

### 토큰 값 찾기:

1. **Bot Token**: OAuth & Permissions → Bot User OAuth Token
2. **Workspace ID**: 워크스페이스 URL에서 확인 (예: `https://yourworkspace.slack.com` → Workspace ID)
3. **App Token**: Socket Mode → App-Level Tokens

## 📦 의존성 설치

```bash
pip install -r requirements.txt
```

## 🧪 테스트 실행

설정이 완료되면 다음 명령으로 연동을 테스트:

```bash
python test_slack_integration.py
```

## 📊 데이터 수집

### 기본 사용법

```python
import asyncio
from mcp.slack_mcp import SlackMCP

async def collect_slack_data():
    config = {
        "output_dir": "output/slack_data"
    }
    
    slack_mcp = SlackMCP(config)
    
    # 연결
    await slack_mcp.connect()
    
    # 워크스페이스 정보
    workspace_info = await slack_mcp.get_workspace_info()
    
    # 채널 목록
    channels = await slack_mcp.get_channels(include_private=True)
    
    # 특정 채널의 메시지
    messages = await slack_mcp.get_channel_messages(channel_id, limit=100)
    
    # 전체 데이터 수집
    full_data = await slack_mcp.collect_all_data()
    
    # 연결 해제
    await slack_mcp.disconnect()

asyncio.run(collect_slack_data())
```

### 수집되는 데이터

1. **워크스페이스 정보**
   - 이름, 도메인, 멤버 수, 플랜 정보

2. **채널 정보**
   - 채널 이름, ID, 멤버 수, 토픽, 목적

3. **메시지 데이터**
   - 텍스트, 작성자, 시간, 반응, 첨부 파일

4. **사용자 정보**
   - 이름, 이메일, 프로필, 상태

5. **활동 분석**
   - 최근 활동 통계, 인기 채널, 활성 사용자

## 📁 출력 파일

수집된 데이터는 `output/slack_data/` 디렉토리에 JSON 형식으로 저장됩니다:

```
output/slack_data/
├── workspace_info.json
├── channels.json
├── messages_C1234567890_20241216_143022.json
├── activity_24h_20241216_143025.json
└── slack_full_data_20241216_143030.json
```

## ⚠️ 주의사항

1. **레이트 리미팅**: Slack API는 레이트 제한이 있으므로 대량 데이터 수집 시 시간이 오래 걸릴 수 있습니다.

2. **권한 관리**: 수집하려는 데이터에 맞는 최소한의 권한만 요청하세요.

3. **데이터 보안**: 수집된 데이터에는 민감한 정보가 포함될 수 있으므로 적절히 보호하세요.

4. **저장소 용량**: 대용량 워크스페이스의 경우 수집된 데이터가 많은 용량을 차지할 수 있습니다.

## 🔧 문제 해결

### 일반적인 오류들

1. **"invalid_auth" 오류**
   - Bot Token이 올바른지 확인
   - 앱이 워크스페이스에 설치되었는지 확인

2. **"missing_scope" 오류**
   - 필요한 권한이 Bot Token Scopes에 추가되었는지 확인
   - 권한 추가 후 앱을 다시 설치

3. **"not_in_channel" 오류**
   - 봇을 해당 채널에 초대하지 않았음
   - 채널에서 `/invite @your-app-name` 명령 사용
   - 또는 채널 멤버 목록에서 직접 초대

4. **"channel_not_found" 오류**
   - 채널 ID가 올바른지 확인
   - 봇이 해당 채널에 접근 권한이 있는지 확인

4. **"rate_limited" 오류**
   - API 요청이 너무 많을 때 발생
   - 잠시 기다린 후 다시 시도

### 디버깅

로그 레벨을 DEBUG로 설정하여 자세한 정보 확인:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📞 지원

추가 도움이 필요한 경우:
- [Slack API 문서](https://api.slack.com/methods)
- [Agent-Cast GitHub 리포지토리](https://github.com/your-repo/agent-cast)
