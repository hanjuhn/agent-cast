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
1. 보고서 구성
- 서론: 현재 AI 기술의 주요 트렌드와 발전 방향 제시
- 본론: 각 기술별 상세 분석과 의의, 기술적 특징과 혁신점 설명
- 결론: 기술 발전이 미치는 영향과 전망 정리

2. 작성 원칙
- 각 기술 간의 연관성과 시너지 효과 분석
- 기술적 깊이와 실용적 가치를 균형있게 다룸
- 구체적인 수치와 기술 스펙 포함
- 현업 적용 가능성과 한계점 명시

3. 형식
- 마크다운 형식으로 작성
- 주요 기술용어는 영문 병기
- 섹션별 명확한 소제목 사용"""

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
                        "content": """AI 기술 전문 애널리스트로서, 제공된 기사들을 바탕으로 심층적인 기술 동향 분석 보고서를 작성해주세요.

작성 원칙:
1. 서론에서는 현재 AI 기술의 발전 방향과 주요 트렌드를 제시하고, 왜 이러한 발전이 중요한지 설명합니다.
2. 본론에서는 각 기술을 다음 관점에서 분석합니다:
   - 기술적 혁신과 차별점
   - 실제 적용 사례와 성능 지표
   - 기존 기술과의 비교
   - 한계점과 향후 개선 방향
3. 결론에서는 전반적인 기술 발전 흐름을 종합하고, 산업과 사회에 미칠 영향을 전망합니다.

분석 관점:
- 기술 간 연결성과 시너지 효과
- 산업 적용 가능성과 실용적 가치
- 기술 발전의 의의와 시사점"""
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



if __name__ == "__main__":
    # 입력 파일과 출력 파일 경로 설정
    input_json = "output/search_results.json"
    output_dir = "output"
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
        report_text = agent.process(input_json)
        print(f"[DEBUG] 기사 분석 완료")
        print(f"[DEBUG] 결과 파일 저장 중...")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"[DEBUG] 완료!")
        print(f"\n보고서가 생성되었습니다: {output_file}")
    except Exception as e:
        print(f"[ERROR] 처리 중 오류 발생: {str(e)}")