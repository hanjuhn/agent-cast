"""Researcher Agent for analyzing articles and generating Kishotenketsu-structured reports."""

import json
import os
from datetime import datetime
from typing import Any, Dict, List
from openai import OpenAI

class ResearcherAgent:
    """기사를 분석하고 기승전결 구조의 보고서를 생성하는 에이전트."""
    
    def __init__(self):
        self.report_template = """
주어진 기사를 분석하여 기승전결(起承轉結) 구조로 보고서를 작성해주세요:

기사 제목: {title}
날짜: {date}
출처: {source}
내용: {content}

다음 구조로 작성해주세요:
- 기(起): 주제의 시작, 핵심 개념 소개
- 승(承): 주제의 전개, 세부 내용 설명
- 전(轉): 전환점, 다른 관점이나 도전 과제
- 結(結): 결론, 시사점과 전망

추가 지침:
- 전문적이고 객관적인 톤 유지
- 핵심 용어나 개념 설명 포함
- 실제 예시나 데이터 인용
- 미래 전망 및 시사점 제시
"""
        # OpenAI 클라이언트 초기화
        try:
            self.client = OpenAI()
        except Exception as e:
            print(f"OpenAI 클라이언트 초기화 실패: {str(e)}")
    
    def process(self, json_path: str) -> Dict[str, Any]:
        """주어진 JSON 파일에서 상위 5개 기사를 읽어서 기승전결 구조의 보고서를 생성합니다."""
        try:
            # JSON 파일 읽기
            if not os.path.exists(json_path):
                raise ValueError(f"JSON 파일을 찾을 수 없습니다: {json_path}")
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 상위 5개 기사 선택 (날짜순)
            top_articles = sorted(data, key=lambda x: x.get('date', ''), reverse=True)[:5]
            
            # 보고서 생성
            report = {
                "title": "상위 5개 기사 기승전결 분석 보고서",
                "generated_date": datetime.now().strftime("%Y-%m-%d"),
                "structure": "기승전결 (起承転結)",
                "articles": []
            }
            
            for idx, article in enumerate(top_articles, 1):
                article_report = {
                    "rank": idx,
                    "title": article.get('title', '제목 없음'),
                    "date": article.get('date', '날짜 없음'),
                    "source": article.get('source', '출처 없음'),
                    "kishotenketsu": self._analyze_article_kishotenketsu(article)
                }
                report["articles"].append(article_report)
            
            return report
            
        except Exception as e:
            print(f"보고서 생성 중 오류 발생: {str(e)}")
            return {
                "title": "보고서 생성 실패",
                "error": str(e)
            }
    
    def _analyze_article_kishotenketsu(self, article: Dict[str, Any]) -> Dict[str, str]:
        """기사를 기승전결 구조로 분석합니다."""
        content = article.get('content', '')
        if not content:
            return {
                "ki": "내용이 없습니다.",
                "sho": "내용이 없습니다.",
                "ten": "내용이 없습니다.",
                "ketsu": "내용이 없습니다."
            }
            
        title = article.get('title', '')
        date = article.get('date', '')
        source = article.get('source', '')
        
        try:
            # OpenAI API를 사용하여 기승전결 분석
            response = self.client.chat.completions.create(
                model="gpt-4",  # 또는 다른 적절한 모델
                messages=[
                    {
                        "role": "system",
                        "content": "전문 기술 분석가로서 기사를 기승전결 구조로 분석해주세요."
                    },
                    {
                        "role": "user",
                        "content": self.report_template.format(
                            title=title,
                            date=date,
                            source=source,
                            content=content
                        )
                    }
                ],
                temperature=0.7
            )
            
            # 응답을 구조화된 형식으로 변환
            result = response.choices[0].message.content
            
            # 여기서는 응답을 간단히 4개 섹션으로 나누어 반환합니다
            parts = result.split("\n\n")
            return {
                "ki": parts[0] if len(parts) > 0 else "분석 실패",
                "sho": parts[1] if len(parts) > 1 else "분석 실패",
                "ten": parts[2] if len(parts) > 2 else "분석 실패",
                "ketsu": parts[3] if len(parts) > 3 else "분석 실패"
            }
        except Exception as e:
            return {
                "ki": f"분석 중 오류 발생: {str(e)}",
                "sho": "분석을 완료하지 못했습니다.",
                "ten": "분석을 완료하지 못했습니다.",
                "ketsu": "분석을 완료하지 못했습니다."
            }


if __name__ == "__main__":
    # 입력 파일과 출력 파일 경로 설정
    input_json = "output/combined_search_results.json"
    output_dir = "output"
    output_file = os.path.join(output_dir, "research_report.json")
    
    # 출력 디렉토리가 없으면 생성
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 에이전트 생성 및 실행
    agent = ResearcherAgent()
    report = agent.process(input_json)
    
    # 결과를 파일로 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"보고서가 생성되었습니다: {output_file}")