# Google Docs 설정 가이드

이 가이드는 agent-cast 프로젝트에서 Google Docs API를 사용하기 위한 설정 방법을 설명합니다.

## 1. Google Cloud Console 설정

### 1.1 프로젝트 생성
1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 상단의 프로젝트 선택 드롭다운 메뉴 클릭
3. "새 프로젝트" 선택
4. 프로젝트 이름 입력 (예: "agent-cast")
5. "만들기" 클릭

### 1.2 API 활성화
1. 왼쪽 메뉴에서 "API 및 서비스" > "라이브러리" 선택
2. 다음 API들을 검색하여 각각 활성화:
   - Google Docs API
   - Google Drive API

### 1.3 OAuth 동의 화면 구성
1. "API 및 서비스" > "OAuth 동의 화면" 선택
2. 사용자 유형 "외부"선택 (테스트용)
3. 앱 정보 입력:
   - 앱 이름: "Agent Cast"
   - 사용자 지원 이메일: 본인 이메일
   - 개발자 연락처 정보: 본인 이메일
4. "저장 후 계속" 클릭
5. 테스트 사용자에 본인 Google 계정 추가

### 1.4 사용자 인증 정보 설정
1. "API 및 서비스" > "사용자 인증 정보" 선택
2. "사용자 인증 정보 만들기" > "OAuth 클라이언트 ID" 선택
3. 애플리케이션 유형: "데스크톱 앱" 선택
4. 이름 입력 (예: "Agent Cast Desktop Client")
5. "만들기" 클릭
6. 생성된 클라이언트 ID의 JSON 파일 다운로드

## 2. 프로젝트 설정

### 2.1 인증 파일 설정
1. 다운로드한 OAuth 클라이언트 JSON 파일을 프로젝트 루트 디렉토리에 `credentials_docs.json`으로 저장
   ```bash
   mv ~/Downloads/client_secret_*.json credentials_docs.json
   ```

### 2.2 환경 변수 설정
1. 프로젝트의 `.env` 파일에 다음 내용 추가:
   ```
   # Google Docs MCP
   DOCS_CREDENTIALS_FILE=credentials_docs.json
   DOCS_TOKEN_FILE=token_docs.json
   ```

## 3. 초기 실행 및 인증

### 3.1 첫 실행
1. upload_to_docs.py 실행:
   ```bash
   python upload_to_docs.py
   ```
2. 브라우저가 자동으로 열리면서 Google 계정 로그인 요청
3. 계정 선택 후 권한 허용
4. "안전하지 않은 앱" 경고가 표시되면:
   - "고급" 클릭
   - "Agent Cast(안전하지 않음)으로 이동" 클릭
   - "계속" 클릭

### 3.2 인증 확인
- 인증이 성공하면 `token_docs.json` 파일이 생성됨
- 이후 실행에서는 저장된 토큰을 재사용

## 4. 문제 해결

### 4.1 자주 발생하는 오류
- "Token has been expired or revoked":
  - `token_docs.json` 파일 삭제 후 재실행
- "Invalid client secret":
  - `credentials_docs.json` 파일이 올바른지 확인
- "API has not been enabled":
  - Google Cloud Console에서 필요한 API가 모두 활성화되었는지 확인

### 4.2 권한 범위
현재 설정된 권한:
- `https://www.googleapis.com/auth/documents`: 문서 생성 및 수정
- `https://www.googleapis.com/auth/drive.file`: 앱이 생성한 파일 관리

## 5. 보안 주의사항

- `credentials_docs.json`과 `token_docs.json`은 민감한 정보를 포함하므로 `.gitignore`에 추가
- 토큰 파일은 로컬에만 저장하고 공유하지 않음
- 프로덕션 환경에서는 OAuth 동의 화면을 "내부"로 설정하고 정식 검토 받을 것을 권장
