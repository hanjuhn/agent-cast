"""Interactive Report Generator Agent for creating web-based reports from research content."""

import os
import re
import json
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import anthropic
from dotenv import load_dotenv

from .base_agent import BaseAgent, AgentResult
from ..state import WorkflowState
from ..constants.ai_models import ANTHROPIC_MODELS

# 환경 변수 로드
load_dotenv()


@dataclass
class ReportConfig:
    """리포트 생성 설정을 위한 데이터 클래스."""
    title: str = "Interactive Research Report"
    theme: str = "modern"
    color_scheme: str = "orange"
    include_charts: bool = True
    include_navigation: bool = True
    responsive: bool = True
    max_tokens: int = 4096
    temperature: float = 0.1


class ReporterAgent(BaseAgent):
    """인터랙티브 리포트 생성 에이전트."""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            name="Interactive Reporter",
            description="리서치 결과를 바탕으로 인터랙티브 웹 기반 리포트를 생성하는 에이전트"
        )
        
        # API 키 설정
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY 환경변수 또는 직접 제공된 API 키가 필요합니다.")
        
        # Claude 클라이언트 초기화
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"  # Claude 4 Sonnet 최신 모델
        
        # 에이전트 설정
        self.required_inputs = ["research_result"]
        self.output_keys = ["html_report", "report_filename", "report_metadata"]
        self.timeout = 120
        self.retry_attempts = 3
        
        # 기본 리포트 설정
        self.default_config = ReportConfig()
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """리서치 결과를 바탕으로 인터랙티브 리포트를 생성합니다."""
        try:
            self.log_execution("리포트 생성 시작")
            
            # 입력 검증
            if not self.validate_inputs(state):
                raise ValueError("필수 입력 데이터가 누락되었습니다.")
            
            # 리서치 결과 가져오기
            research_result = getattr(state, 'research_result', '')
            if not research_result:
                raise ValueError("리서치 결과가 비어있습니다.")
            
            # 개선 프롬프트 확인 (검수 실패 시 재생성)
            improvement_prompt = getattr(state, 'improvement_prompt', None)
            is_improvement = bool(improvement_prompt)
            
            if is_improvement:
                self.log_execution("🔄 개선 프롬프트를 사용하여 리포트 재생성")
                html_content = await self._generate_improved_report(improvement_prompt)
            else:
                # 리포트 설정 가져오기 (기본값 사용)
                report_config = getattr(state, 'report_config', self.default_config)
                
                # HTML 리포트 생성
                html_content = await self._generate_html_report(research_result, report_config)
            
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"interactive_report_{timestamp}.html"
            
            # 메타데이터 생성
            metadata = {
                "generated_at": datetime.now().isoformat(),
                "filename": filename,
                "config": getattr(state, 'report_config', self.default_config).__dict__,
                "research_length": len(research_result),
                "html_size": len(html_content),
                "is_improvement": is_improvement
            }
            
            # 결과 준비
            result = AgentResult(
                success=True,
                output={
                    "html_report": html_content,
                    "report_filename": filename,
                    "report_metadata": metadata
                },
                execution_time=None,
                metadata=metadata
            )
            
            # 상태 업데이트
            output_data = self.prepare_output(result)
            updated_state = WorkflowState(
                **{k: v for k, v in state.__dict__.items()},
                **output_data
            )
            
            # 워크플로우 상태 업데이트
            updated_state = self.update_workflow_status(updated_state, "report_generation")
            
            self.log_execution("리포트 생성 완료")
            return updated_state
            
        except Exception as e:
            self.log_execution(f"리포트 생성 실패: {str(e)}", "ERROR")
            raise
    
    async def _generate_html_report(self, research_result: str, config: ReportConfig) -> str:
        """HTML 리포트를 생성합니다."""
        enhanced_prompt = self._create_enhanced_prompt(research_result, config)
        
        for attempt in range(self.retry_attempts):
            try:
                self.log_execution(f"HTML 생성 시도 {attempt + 1}/{self.retry_attempts}")
                
                # API 호출 전 검증
                if not research_result or len(research_result.strip()) < 10:
                    raise ValueError("리서치 결과가 너무 짧거나 비어있습니다.")
                
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    messages=[
                        {
                            "role": "user",
                            "content": enhanced_prompt
                        }
                    ]
                )
                
                # 응답 검증
                if not response.content or len(response.content) == 0:
                    raise ValueError("API 응답이 비어있습니다.")
                
                html_content = response.content[0].text
                
                # 응답 내용 검증
                if not html_content or len(html_content.strip()) < 100:
                    raise ValueError("생성된 HTML 콘텐츠가 너무 짧습니다.")
                
                # HTML 코드 추출 및 검증
                html_content = self._extract_and_validate_html(html_content)
                
                # 최종 HTML 검증
                if len(html_content) < 200:
                    raise ValueError("최종 HTML이 너무 짧습니다.")
                
                self.log_execution("HTML 리포트 생성 성공")
                return html_content
                
            except Exception as e:
                self.log_execution(f"시도 {attempt + 1} 실패: {str(e)}", "WARNING")
                
                # 마지막 시도가 아니면 잠시 대기 후 재시도
                if attempt < self.retry_attempts - 1:
                    import time
                    time.sleep(2 ** attempt)  # 지수 백오프
                
                if attempt == self.retry_attempts - 1:
                    # 모든 시도 실패 시 기본 HTML 템플릿 반환
                    self.log_execution("모든 시도 실패, 기본 템플릿 사용", "WARNING")
                    return self._generate_fallback_html(research_result, config)
    
    async def _generate_improved_report(self, improvement_prompt: str) -> str:
        """개선 프롬프트를 사용하여 리포트를 재생성합니다."""
        try:
            self.log_execution("개선된 리포트 생성 시작")
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,  # 개선 시 더 많은 토큰 사용
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": improvement_prompt
                    }
                ]
            )
            
            if not response.content or len(response.content) == 0:
                raise ValueError("API 응답이 비어있습니다.")
            
            html_content = response.content[0].text
            
            # HTML 코드 추출 및 검증
            html_content = self._extract_and_validate_html(html_content)
            
            self.log_execution("개선된 리포트 생성 성공")
            return html_content
            
        except Exception as e:
            self.log_execution(f"개선된 리포트 생성 실패: {str(e)}", "ERROR")
            raise
    
    def _generate_fallback_html(self, research_result: str, config: ReportConfig) -> str:
        """API 실패 시 사용할 기본 HTML 템플릿을 생성합니다."""
        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #FF6B35, #F7931E);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #FF6B35, #F7931E);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .content {{
            padding: 40px;
            line-height: 1.6;
        }}
        .research-content {{
            background: #f8f9fa;
            border-left: 4px solid #FF6B35;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
        }}
        @media (max-width: 768px) {{
            .container {{ margin: 10px; }}
            .header, .content {{ padding: 20px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {config.title}</h1>
            <p>Interactive Research Report</p>
        </div>
        <div class="content">
            <h2>🔍 리서치 결과</h2>
            <div class="research-content">
                <pre style="white-space: pre-wrap; font-family: inherit;">{research_result}</pre>
            </div>
            <p><strong>생성일:</strong> {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}</p>
        </div>
        <div class="footer">
            <p>Generated by Interactive Reporter Agent</p>
        </div>
    </div>
</body>
</html>"""
    
    def _create_enhanced_prompt(self, research_result: str, config: ReportConfig) -> str:
        """최적화된 프롬프트를 생성합니다."""
        return f"""
# 미션: 전문가급 Interactive Research Report 생성

당신은 데이터 분석 전문가이자 UX/UI 디자이너입니다. 제공된 리서치 결과를 바탕으로 시각적으로 매력적이고 상호작용이 가능한 HTML 기반 보고서를 생성해주세요.

## 핵심 요구사항

### 1. 페이지 구조 (16:9 비율)
- **표지 페이지**: 제목, 부제목, 생성일, 간단한 개요
- **목차 페이지**: 전체 목차와 네비게이션 가이드
- **내용 페이지들**: 리서치의 각 섹션별로 별도 페이지 (16:9 화면 하나씩)
- **마무리 페이지**: 요약, 결론, 액션 아이템

### 2. 인터랙티브 네비게이션
- **좌측 사이드바**: 고정된 목차 네비게이션
- **스무스 스크롤**: 클릭 시 해당 섹션으로 부드럽게 이동
- **현재 위치 표시**: 현재 보고 있는 섹션 하이라이트
- **반응형**: 모바일에서는 햄버거 메뉴로 변환

### 3. 마크다운 렌더링
- **표(Tables)**: HTML 테이블로 변환하여 스타일링
- **제목(Headers)**: 적절한 HTML 태그(h1, h2, h3)로 변환
- **리스트**: ul, ol 태그로 변환
- **강조**: bold, italic 텍스트 스타일링
- **코드 블록**: syntax highlighting 적용

### 4. 데이터 시각화
- **Chart.js 차트**: 비교 데이터를 막대/파이/라인 차트로 표현
- **SVG 다이어그램**: 아키텍처, 플로우차트 등
- **인포그래픽**: 핵심 데이터를 시각적으로 강조
- **인터랙티브 요소**: 호버 시 추가 정보 표시

### 5. 디자인 가이드라인
- **색상 팔레트**: 주황색 계열 (#FF6B35, #F7931E, #FFB84D) + 보완색
- **타이포그래피**: 모던하고 가독성 높은 폰트
- **레이아웃**: 깔끔한 카드 기반 디자인, 적절한 여백
- **애니메이션**: 부드러운 전환 효과, 호버 상태 반응

## 기술적 구현 요구사항

### HTML 구조
```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <!-- 메타태그, 제목, CSS -->
</head>
<body>
    <!-- 좌측 사이드바 네비게이션 -->
    <nav class="sidebar">
        <!-- 목차 네비게이션 -->
    </nav>
    
    <!-- 메인 콘텐츠 -->
    <main class="main-content">
        <!-- 표지 페이지 -->
        <section id="cover" class="page">
            <!-- 표지 내용 -->
        </section>
        
        <!-- 목차 페이지 -->
        <section id="toc" class="page">
            <!-- 목차 내용 -->
        </section>
        
        <!-- 각 섹션별 페이지들 -->
        <section id="section-1" class="page">
            <!-- 섹션 1 내용 -->
        </section>
        
        <!-- 마무리 페이지 -->
        <section id="conclusion" class="page">
            <!-- 결론 내용 -->
        </section>
    </main>
    
    <!-- JavaScript -->
    <script>
        // 네비게이션, 스크롤, 차트 기능
    </script>
</body>
</html>
```

### CSS 요구사항
- **16:9 비율**: 각 페이지가 화면 높이에 맞춰 표시
- **스크롤 스냅**: 페이지별로 스크롤 스냅 적용
- **반응형**: 모바일/태블릿/데스크톱 대응
- **애니메이션**: 부드러운 전환 효과

### JavaScript 요구사항
- **스무스 스크롤**: 네비게이션 클릭 시 부드러운 이동
- **현재 섹션 감지**: 스크롤 위치에 따른 네비게이션 하이라이트
- **Chart.js 통합**: 데이터 시각화
- **반응형 네비게이션**: 모바일 햄버거 메뉴

## 리포트 설정
- 제목: {config.title}
- 테마: {config.theme}
- 색상 스키마: {config.color_scheme}
- 차트 포함: {config.include_charts}
- 네비게이션 포함: {config.include_navigation}
- 반응형: {config.responsive}

## 리서치 결과 데이터
---
{research_result}
---

## 최종 결과물
완전히 작동하는 단일 HTML 파일을 생성해주세요. 다음 사항을 반드시 포함해주세요:

1. **마크다운 변환**: 모든 마크다운 문법을 적절한 HTML로 변환
2. **페이지 분할**: 16:9 비율로 명확한 페이지 구분
3. **인터랙티브 네비게이션**: 좌측 사이드바에 클릭 가능한 목차
4. **데이터 시각화**: Chart.js를 활용한 차트와 다이어그램
5. **반응형 디자인**: 모든 디바이스에서 최적화

모든 CSS와 JavaScript를 HTML 파일 내에 포함시켜주세요. HTML 코드 블록(```html ... ```)으로만 응답해주세요.
"""
    
    def _extract_and_validate_html(self, content: str) -> str:
        """HTML 콘텐츠를 추출하고 검증합니다."""
        # HTML 코드 블록에서 추출 (```html ... ``` 형식)
        html_match = re.search(r'```html\s*(.*?)\s*```', content, re.DOTALL | re.IGNORECASE)
        if html_match:
            html_content = html_match.group(1).strip()
        else:
            # 직접 HTML 태그 찾기 (DOCTYPE 또는 html 태그로 시작)
            html_match = re.search(r'(<!doctype html>.*?</html>|<html.*?</html>)', content, re.DOTALL | re.IGNORECASE)
            if html_match:
                html_content = html_match.group(1)
            else:
                # HTML 태그가 포함된 모든 내용 추출
                html_match = re.search(r'(<.*>)', content, re.DOTALL)
                if html_match:
                    html_content = content.strip()
                else:
                    raise ValueError("HTML 콘텐츠를 찾을 수 없습니다.")
        
        # HTML 구조 검증 및 정리
        html_content = html_content.strip()
        
        # DOCTYPE이 없으면 추가
        if not html_content.lower().startswith('<!doctype'):
            if html_content.lower().startswith('<html'):
                html_content = '<!DOCTYPE html>\n' + html_content
            else:
                # HTML 태그가 없으면 전체를 HTML로 감싸기
                html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interactive Research Report</title>
</head>
<body>
{html_content}
</body>
</html>"""
        
        return html_content
    
    def save_report(self, html_content: str, filename: Optional[str] = None) -> str:
        """생성된 리포트를 파일로 저장합니다."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"interactive_report_{timestamp}.html"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.log_execution(f"리포트가 '{filename}'으로 저장되었습니다.")
            return filename
            
        except Exception as e:
            self.log_execution(f"파일 저장 실패: {str(e)}", "ERROR")
            raise
    
    def create_report_package(self, html_content: str, research_result: str, 
                            package_name: Optional[str] = None) -> str:
        """리포트 패키지를 생성합니다."""
        if package_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            package_name = f"interactive_report_package_{timestamp}.zip"
        
        html_filename = f"interactive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        try:
            with zipfile.ZipFile(package_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.writestr(html_filename, html_content.encode('utf-8'))
                zipf.writestr('original_research.txt', research_result.encode('utf-8'))
                
                readme_content = f"""
# Interactive Report Package

생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 포함 파일
- {html_filename}: 인터랙티브 HTML 리포트
- original_research.txt: 원본 리서치 데이터

## 사용법
1. HTML 파일을 웹 브라우저에서 열어보세요
2. 모든 기능이 포함된 단일 파일입니다
3. 인터넷 연결이 필요할 수 있습니다 (외부 CDN 사용)

## 기술 스택
- HTML5, CSS3, JavaScript
- Chart.js (CDN)
- 반응형 디자인
- 모던 브라우저 지원
                """.strip()
                
                zipf.writestr('README.md', readme_content.encode('utf-8'))
            
            self.log_execution(f"패키지가 '{package_name}'으로 생성되었습니다.")
            return package_name
            
        except Exception as e:
            self.log_execution(f"패키지 생성 실패: {str(e)}", "ERROR")
            raise
    
    def get_report_preview(self, html_content: str) -> str:
        """리포트 미리보기 HTML을 생성합니다."""
        preview_html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>리포트 미리보기</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .preview-container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .preview-header {{
            background: linear-gradient(135deg, #FF6B35, #F7931E);
            color: white;
            padding: 20px;
            text-align: center;
        }}
        .preview-content {{
            padding: 20px;
        }}
        .preview-notice {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        iframe {{
            width: 100%;
            height: 600px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="preview-container">
        <div class="preview-header">
            <h1>📊 Interactive Research Report Preview</h1>
            <p>생성된 리포트 미리보기</p>
        </div>
        <div class="preview-content">
            <div class="preview-notice">
                <strong>💡 미리보기 안내:</strong> 아래는 생성된 인터랙티브 리포트의 미리보기입니다. 
                일부 상호작용이 제한될 수 있으니, 전체 기능을 확인하려면 다운로드한 HTML 파일을 직접 열어보세요.
            </div>
            <iframe srcdoc="{html_content.replace('"', '&quot;')}"></iframe>
        </div>
    </div>
</body>
</html>
        """
        return preview_html


# 독립 실행을 위한 메인 함수
def main():
    """독립 실행용 메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="리서치 결과를 바탕으로 인터랙티브 리포트를 생성합니다.")
    parser.add_argument("research_file", type=str, help="리서치 결과 텍스트 파일의 경로")
    parser.add_argument("--output", "-o", type=str, default="interactive_report.html", 
                       help="출력 파일명 (기본값: interactive_report.html)")
    parser.add_argument("--api-key", type=str, help="Claude API 키")
    parser.add_argument("--package", "-p", action="store_true", help="ZIP 패키지로 생성")
    args = parser.parse_args()

    # API 키 설정
    api_key = args.api_key or os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        api_key = input("Claude API 키를 입력하세요: ").strip()

    try:
        # 리서치 파일 읽기
        with open(args.research_file, 'r', encoding='utf-8') as f:
            research_content = f.read()
        
        # 에이전트 생성 및 실행
        agent = ReporterAgent(api_key=api_key)
        
        # 임시 상태 생성
        temp_state = WorkflowState(research_result=research_content)
        
        # 리포트 생성
        import asyncio
        result_state = asyncio.run(agent.process(temp_state))
        
        # 결과 저장
        html_content = result_state.html_report
        filename = result_state.report_filename
        
        # 파일 저장
        agent.save_report(html_content, args.output)
        
        # 패키지 생성 (옵션)
        if args.package:
            agent.create_report_package(html_content, research_content)
        
        print(f"✅ 리포트가 성공적으로 생성되었습니다: {args.output}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
