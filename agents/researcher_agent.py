"""Researcher Agent for generating concise article reports."""

import json
import os
from datetime import datetime
from typing import Any, Dict, List
from openai import OpenAI
from dotenv import load_dotenv

class ResearcherAgent:
    """기사의 핵심 내용을 압축하여 보고서를 생성하는 에이전트."""
    
    def __init__(self):
        """Initialize the ResearcherAgent with OpenAI client."""
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되어 있지 않습니다. .env 또는 환경 변수에 키를 등록하세요.")
            
        self.report_template = """# AI 기술 동향 심층 분석 보고서

{articles}

작성 지침:

1. 문서 스타일
- 서론과 결론은 반드시 단락형 서술식(줄글)으로 작성
- 본론은 말머리 구조(bullet points)와 단락형 서술식을 적절히 혼합하여 가독성 있게 구성
- 각 섹션은 명확한 소제목과 함께 시작

2. 보고서 구조
A. 서론 (줄글 형식)
- 현재 AI 기술의 주요 트렌드와 발전 방향 서술
- 이러한 발전이 가지는 의미와 중요성 설명
- 보고서의 분석 범위와 관점 제시

B. 본론
- 주요 기술 동향 분석 (말머리와 서술식 혼합)
- 기술 간 연관성과 시너지 효과 설명 (서술식 위주)
- 실용적 적용 사례와 한계점 분석 (말머리 구조 활용)
- 구체적 수치와 기술 스펙 포함

C. 결론 (줄글 형식으로 3개 파트)
[거시적 결론]
- 전반적인 기술 발전의 방향성과 의미
- 산업과 사회에 미치는 영향

[보고서 인사이트]
- 주요 발견 사항과 시사점
- 기술 발전이 제시하는 기회와 도전 과제

[향후 탐구 포인트]
- 추가 연구가 필요한 영역
- 주목해야 할 핵심 질문들
- 잠재적 리스크와 대응 방안

3. 형식
- 마크다운 형식 준수
- 주요 기술용어는 영문 병기
- 섹션별 명확한 소제목 사용
- 중요 내용은 적절한 강조 표시 활용"""

        try:
            self.client = OpenAI(api_key=api_key)
        except Exception as e:
            print(f"OpenAI 클라이언트 초기화 실패: {str(e)}")
            raise
    
    def summarize_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """개별 기사를 500자 내외로 요약"""
        try:
            content = article.get('content', '')
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "기술 전문 에디터로서, 아래 기사의 핵심 내용을 500자 내외로 요약해주세요."
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                temperature=0.3
            )
            summarized = response.choices[0].message.content.strip()
            return {
                'title': article.get('title', '제목 없음'),
                'date': article.get('date', '날짜 없음'),
                'source': article.get('source', '출처 없음'),
                'url': article.get('url', ''),
                'content': summarized
            }
        except Exception as e:
            print(f"[ERROR] 기사 요약 중 오류 발생: {str(e)}")
            raise

    def process(self, json_path: str) -> str:
        """Process articles from JSON file and generate a report."""
        try:
            print(f"\n[DEBUG] 파일 읽기 시작: {json_path}")
            if not os.path.exists(json_path):
                raise ValueError(f"JSON 파일을 찾을 수 없습니다: {json_path}")
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            documents = data[0].get('documents', []) if data else []
            print(f"[DEBUG] 파일 읽기 완료. 기사 {len(documents)}개 발견")
            
            # 각 기사 요약
            print("[DEBUG] 기사 요약 시작...")
            summarized_articles = []
            for article in documents:
                summarized = self.summarize_article(article)
                summarized_articles.append(summarized)
                print(f"[DEBUG] 기사 요약 완료 (길이: {len(summarized['content'])}자)")
            
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
                temperature=0.3
            )
            result = response.choices[0].message.content.strip()
            print(f"[DEBUG] 통합 보고서 생성 완료 (길이: {len(result)}자)")
            return result
            
        except Exception as e:
            print(f"[ERROR] 처리 중 오류 발생: {str(e)}")
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
            print(f"[ERROR] Google Docs 업로드 중 오류 발생: {str(e)}")
            raise

if __name__ == "__main__":
    # 입력 파일과 출력 파일 경로 설정
    input_json = "output/rag_data/search_results.json"
    output_dir = "output/docs_data"
    output_file = os.path.join(output_dir, "research_report.md")

    print(f"[DEBUG] 시작...")
    print(f"[DEBUG] 입력 파일: {input_json}")
    print(f"[DEBUG] 출력 파일: {output_file}")

    # 출력 디렉토리가 없으면 생성
    if not os.path.exists(output_dir):
        print(f"[DEBUG] 출력 디렉토리 생성: {output_dir}")
        os.makedirs(output_dir)

    print(f"[DEBUG] ResearcherAgent 초기화...")
    # 에이전트 생성 및 실행
    agent = ResearcherAgent()

    print(f"[DEBUG] 기사 분석 시작...")
    try:
        # 보고서 생성
        report_text = agent.process(input_json)
        print(f"[DEBUG] 기사 분석 완료")
        
        # 로컬 파일로 저장
        print(f"[DEBUG] 결과 파일 저장 중...")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"[DEBUG] 로컬 파일 저장 완료: {output_file}")
        
        # Google Docs에 업로드
        print(f"[DEBUG] Google Docs에 업로드 중...")
        current_date = datetime.now().strftime("%Y-%m-%d")
        docs_result = agent.save_to_docs(report_text, f"AI 기술 동향 심층 분석 보고서 ({current_date})")
        print(f"[DEBUG] Google Docs 업로드 완료")
        print(f"\n보고서가 생성되었습니다:")
        print(f"- 로컬 파일: {output_file}")
        print(f"- Google Docs: {docs_result['url']}")
        
    except Exception as e:
        print(f"[ERROR] 처리 중 오류 발생: {str(e)}")