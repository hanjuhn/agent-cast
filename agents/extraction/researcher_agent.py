"""Researcher Agent for generating concise article reports."""

import os
from datetime import datetime
from typing import List, Dict, Any
from openai import OpenAI

from ..base_agent import BaseAgent
from state.state import WorkflowState
from constants import OPENAI_RESEARCHER_PARAMS
from constants.prompts import AI_RESEARCH_EXPERT_PROMPT

class ResearcherAgent(BaseAgent):
    """AI 기술 동향을 분석하여 심층 보고서를 생성하는 에이전트"""
    
    def __init__(self):
        super().__init__(
            name="researcher",
            description="AI 기술 동향을 분석하여 심층 보고서를 생성하는 에이전트"
        )
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되어 있지 않습니다. .env 또는 환경 변수에 키를 등록하세요.")
            
        self.report_template = AI_RESEARCH_EXPERT_PROMPT

        try:
            self.client = OpenAI(api_key=api_key)
        except Exception as e:
            self.log_execution(f"OpenAI 클라이언트 초기화 실패: {str(e)}", "ERROR")
            raise
    
    def summarize_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """기사를 요약합니다."""
        try:
            title = article.get('title', '제목 없음')
            content = article.get('content', '내용 없음')
            source = article.get('source', '출처 없음')
            date = article.get('date', '날짜 없음')
            url = article.get('url', '')
            
            # 간단한 요약 (실제로는 LLM을 사용할 수 있음)
            summary = content[:200] + "..." if len(content) > 200 else content
            
            return {
                "title": title,
                "content": summary,
                "source": source,
                "date": date,
                "url": url
            }
        except Exception as e:
            self.log_execution(f"기사 요약 중 오류: {e}", "ERROR")
            return {
                "title": "요약 실패",
                "content": "내용을 요약할 수 없습니다.",
                "source": "알 수 없음",
                "date": "알 수 없음",
                "url": ""
            }
    
    def _generate_basic_report(self, personal_info: Dict[str, Any], research_context: Dict[str, Any]) -> str:
        """기본 정보를 기반으로 보고서를 생성합니다."""
        return f"""# AI 기술 동향 분석 보고서 (기본 정보 기반)

## 개요
사용자의 개인화된 연구 관심사와 현재 프로젝트를 기반으로 AI 기술 동향을 분석합니다.

## 연구 관심사
- {', '.join(personal_info.get('research_keywords', ['AI 기술']))}

## 현재 프로젝트
- {', '.join(research_context.get('current_projects', ['AI 연구']))}

## 기술 발전 방향
사용자의 연구 관심사와 프로젝트를 고려할 때, LLM 최적화와 MoE 아키텍처가 주요 기술 트렌드로 부상하고 있습니다.

## 결론
개인화된 연구 방향과 AI 기술 동향이 일치하여 효과적인 연구 진행이 가능할 것으로 전망됩니다.
"""

    def _generate_report_from_search_results(self, search_results: List[Dict[str, Any]]) -> str:
        """검색 결과를 기반으로 보고서를 생성합니다."""
        if not search_results:
            return self._generate_fallback_report()
        
        articles_content = []
        for i, result in enumerate(search_results, 1):
            title = result.get('title', '제목 없음')
            content = result.get('content', '내용 없음')
            source = result.get('source', '출처 없음')
            date = result.get('date', '날짜 없음')
            
            articles_content.append(f"""## {i}. {title}
- 출처: {source}
- 날짜: {date}
- 내용: {content[:200]}...""")
        
        return f"""# AI 기술 동향 분석 보고서

## 개요
최신 검색 결과를 기반으로 AI 기술 동향을 분석합니다.

## 주요 기술 동향
{chr(10).join(articles_content)}

## 결론
검색된 정보를 바탕으로 AI 기술의 현재 상태와 발전 방향을 파악할 수 있습니다.
"""

    def _generate_fallback_report(self) -> str:
        """폴백 보고서를 생성합니다."""
        return """# AI 기술 동향 분석 보고서 (폴백)

## 개요
기본적인 AI 기술 동향 정보를 제공합니다.

## 주요 기술 트렌드
1. **LLM 최적화**: 모델 효율성과 성능 향상
2. **MoE 아키텍처**: 전문가 모델의 효율적 활용
3. **Gemma 3**: 오픈소스 AI 모델의 발전
4. **메모리 구현**: AI 시스템의 장기 기억력 향상

## 결론
AI 기술은 지속적인 혁신을 통해 더욱 실용적이고 효율적인 방향으로 발전하고 있습니다.
"""

    async def process(self, state: WorkflowState) -> WorkflowState:
        """AI 기술 동향 분석 및 보고서 생성을 수행합니다."""
        self.log_execution("AI 기술 동향 분석 및 보고서 생성 시작")
        
        try:
            # 상태에서 데이터 추출
            search_results = getattr(state, 'search_results', [])
            personal_info = getattr(state, 'personal_info', {})
            research_context = getattr(state, 'research_context', {})
            
            if not search_results:
                self.log_execution("검색 결과가 없어 기본 정보로 보고서를 생성합니다")
                report_content = self._generate_basic_report(personal_info, research_context)
            else:
                self.log_execution(f"검색 결과 {len(search_results)}개를 기반으로 보고서를 생성합니다")
                report_content = self._generate_report_from_search_results(search_results)
            
            # 출력 파일 저장
            output_filename = f"output/research/research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            os.makedirs(os.path.dirname(output_filename), exist_ok=True)
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            # 상태 업데이트
            state_dict = {k: v for k, v in state.__dict__.items()}
            if 'research_results' in state_dict:
                del state_dict['research_results']
            if 'research_result' in state_dict:
                del state_dict['research_result']
            
            new_state = WorkflowState(
                **state_dict,
                research_results=[report_content],
                research_result=report_content
            )
            
            new_state = self.update_workflow_status(new_state, "research_completed")
            
            # 각 기사 요약
            print("[DEBUG] 기사 요약 시작...")
            summarized_articles = []
            for article in search_results:
                if isinstance(article, dict) and 'title' in article:
                    summarized = self.summarize_article(article)
                    summarized_articles.append(summarized)
                    self.log_execution(f"기사 요약 완료 (길이: {len(summarized['content'])}자)", "INFO")
            
            # 기사 정보를 마크다운 리스트로 변환
            articles_md = []
            for idx, article in enumerate(summarized_articles, 1):
                articles_md.append(f"## {idx}. {article['title']}\n- 날짜: {article['date']}\n- 출처: {article['source']}\n- URL: {article['url']}\n\n{article['content']}")
            articles_str = "\n\n".join(articles_md)
            print("[DEBUG] GPT-4 API 통합 보고서 생성 프롬프트 준비 완료")
            
            # 최종 보고서 생성
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """저는 AI 기술 전문 애널리스트로서, 제공된 기사들을 바탕으로 심층적이고 실행 가능한 기술 동향 분석 보고서를 작성합니다.

작성 원칙:

1. 상세한 서술 방식
- 각 개념과 기술에 대해 비전문가도 이해할 수 있도록 충분한 설명 제공
- 추상적인 표현을 피하고, 구체적인 수치와 예시를 통한 설명
- 실제 사용 사례와 구현 방식에 대한 상세한 설명 포함
- 각 섹션은 최소 2-3문단 이상의 충분한 내용으로 구성

2. 멀티미디어 콘텐츠 제작을 위한 요소
- 시각화할 수 있는 데이터와 통계 정보 강조
- 청취자의 흥미를 끌 수 있는 흥미로운 사례나 시나리오 포함
- 기술 발전의 타임라인이나 진화 과정을 스토리텔링 방식으로 설명
- 시청자/청취자와 공감대를 형성할 수 있는 실생활 적용 사례 포함

3. 분석의 깊이
기술적 측면:
- 핵심 알고리즘이나 방법론의 작동 원리
- 기존 기술과의 구체적인 성능 비교 수치
- 구현에 필요한 기술 스택과 리소스
- 실제 개발 과정에서의 문제점과 해결 방안

비즈니스 측면:
- 시장 규모와 성장률에 대한 구체적 수치
- 주요 기업들의 투자 현황과 전략
- 수익 모델과 비즈니스 케이스 분석
- 진입 장벽과 경쟁 구도 분석

사회적 측면:
- 일자리와 산업 구조 변화에 대한 구체적 예측
- 윤리적 이슈와 규제 관련 쟁점
- 교육과 인재 양성에 대한 시사점
- 환경과 지속가능성 관련 영향

4. 결론 작성 구조 (각 섹션별 충분한 분량 보장)
[거시적 결론] - 최소 3문단
- 현재와 향후 5년간의 기술 발전 로드맵
- 산업별 파급 효과와 적용 시나리오
- 사회경제적 변화와 대응 전략

[보고서 인사이트] - 최소 3문단
- 기술 발전의 핵심 동인과 촉진/저해 요인
- 산업별 기회 요인과 위협 요인 분석
- 성공적인 도입/활용을 위한 선결 과제

[향후 탐구 포인트] - 최소 5개 이상의 구체적 질문
- 기술 개발 관련 핵심 연구 질문
- 비즈니스 모델 관련 전략적 질문
- 규제와 정책 관련 이슈
- 사회적 영향과 대응 방안
- 잠재적 리스크와 완화 전략

5. 품질 기준
- 모든 주장에 대한 구체적인 근거와 출처 제시
- 정량적 데이터와 정성적 분석의 균형
- 실무자들이 참고할 수 있는 구체적 가이드라인 제시
- 팟캐스트나 비디오 콘텐츠로 전환 가능한 스토리텔링 구조"""
                    },
                    {
                        "role": "user",
                        "content": self.report_template.format(articles=articles_str)
                    }
                ],
                temperature=OPENAI_RESEARCHER_PARAMS["temperature"]
            )
            result = response.choices[0].message.content.strip()
            self.log_execution(f"통합 보고서 생성 완료 (길이: {len(result)}자)", "INFO")
            
            # 상태 업데이트
            state_dict = {k: v for k, v in state.__dict__.items()}
            if 'research_results' in state_dict:
                del state_dict['research_results']
            if 'research_result' in state_dict:
                del state_dict['research_result']
            
            new_state = WorkflowState(
                **state_dict,
                research_results=[result],
                research_result=result
            )
            
            new_state = self.update_workflow_status(new_state, "research_completed")
            return new_state
            
        except Exception as e:
            self.log_execution(f"처리 중 오류 발생: {str(e)}", "ERROR")
            raise



    def save_to_docs(self, report_text: str, title: str = "AI 기술 동향 심층 분석 보고서") -> Dict[str, Any]:
        """생성된 보고서를 Google Docs에 업로드합니다."""
        try:
            from mcp.docs_mcp import DocsMCP
            
            # DocsMCP 인스턴스 생성 및 업로드
            docs_mcp = DocsMCP()
            result = docs_mcp.upload_report(
                title=title,
                content=report_text
            )
            
            if not result['success']:
                raise Exception(f"Google Docs 업로드 실패: {result.get('error', '알 수 없는 오류')}")
            
            return result
            
        except Exception as e:
            self.log_execution(f"Google Docs 업로드 중 오류 발생: {str(e)}", "ERROR")
            raise

