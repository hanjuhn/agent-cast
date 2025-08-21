"""Researcher Agent for generating concise article reports."""

import json
import os
from datetime import datetime
from typing import Any, Dict, List
from openai import OpenAI
from dotenv import load_dotenv

class ResearcherAgent:
    """기사의 핵심 내용을 압축하여 보고서를 생성하는 에이전트."""
    
    # ...existing code...
    def __init__(self):
        load_dotenv()
        self.report_template = """
주어진 기사의 핵심 내용을 600~800자로 압축해주세요.

기사 제목: {title}
날짜: {date}
출처: {source}
내용: {content}

작성 지침:
- 불필요한 미사여구, 소개문, 배경설명은 생략
- 기사에서 다루는 모든 핵심 정보와 주요 논점을 포함
- 실제 데이터, 수치, 주요 인용문 등 구체적 정보 유지
- 명확하고 객관적인 문체 사용
- 문단 구분을 통해 가독성 확보
"""
        # OpenAI 클라이언트 초기화 (환경 변수에서 API 키 읽기)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되어 있지 않습니다. .env 또는 환경 변수에 키를 등록하세요.")
        try:
            self.client = OpenAI(api_key=api_key)
        except Exception as e:
            print(f"OpenAI 클라이언트 초기화 실패: {str(e)}")
    
    def process(self, json_path: str) -> str:
        """주어진 JSON 파일에서 모든 기사를 읽어서 보고서를 생성합니다."""
        try:
            print(f"\n[DEBUG] 파일 읽기 시작: {json_path}")
            # JSON 파일 읽기
            if not os.path.exists(json_path):
                raise ValueError(f"JSON 파일을 찾을 수 없습니다: {json_path}")
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"[DEBUG] 파일 읽기 완료. 기사 {len(data)}개 발견")
            
            # 모든 기사 선택 (날짜순)
            sorted_articles = sorted(data, key=lambda x: x.get('date', ''), reverse=True)
            print("[DEBUG] 기사 날짜순 정렬 완료")
            
            # 보고서 생성
            report_lines = []
            report_lines.append(f"{datetime.now().strftime('%Y년 %m월 %d일')} 기준 최신 AI/기술 기사 정리\n")
            
            for idx, article in enumerate(sorted_articles, 1):
                title = article.get('title', '제목 없음')
                date = article.get('date', '날짜 없음')
                source = article.get('source', '출처 없음')
                url = article.get('url', '')
                
                print(f"\n[DEBUG] {idx}/{len(sorted_articles)}번째 기사 분석 시작...")
                print(f"[DEBUG] 제목: {title}")
                print(f"[DEBUG] 날짜: {date}")
                print(f"[DEBUG] 출처: {source}")
                
                # 기사 헤더 추가
                report_lines.append(f"{idx}. {title}")
                report_lines.append(f"   날짜: {date}")
                report_lines.append(f"   출처: {source}")
                if url:
                    report_lines.append(f"   URL: {url}")
                
                # 내용 분석 및 추가
                print(f"[DEBUG] GPT-4 API 호출 중...")
                content = self._analyze_article_content(article)
                print(f"[DEBUG] 내용 압축 완료 (길이: {len(content)}자)")
                
                report_lines.append(f"\n   핵심 내용:")
                report_lines.append(f"   {content}")
                report_lines.append("")  # 기사 간 구분을 위한 빈 줄
                
                print(f"[DEBUG] {idx}번째 기사 처리 완료")
            
            return "\n".join(report_lines)
            
        except Exception as e:
            print(f"보고서 생성 중 오류 발생: {str(e)}")
            return {
                "title": "보고서 생성 실패",
                "error": str(e)
            }
    
    def _analyze_article_content(self, article: Dict[str, Any]) -> str:
        """기사의 핵심 내용을 600~800자로 압축합니다."""
        content = article.get('content', '')
        if not content:
            print("[DEBUG] 경고: 기사 내용이 비어있음")
            return "내용이 없습니다."
            
        title = article.get('title', '')
        date = article.get('date', '')
        source = article.get('source', '')
        print(f"[DEBUG] 원문 길이: {len(content)}자")
        
        try:
            # OpenAI API를 사용하여 내용 압축
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "기술 전문 에디터로서, 기사의 핵심 내용을 600~800자로 압축해주세요."
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
                temperature=0.3  # 일관성을 위해 낮은 temperature 사용
            )
            
            # 응답 텍스트를 줄바꿈으로 정리하여 반환
            result = response.choices[0].message.content.strip()
            # 들여쓰기를 위해 각 줄 앞에 공백 추가
            formatted_result = "\n   ".join(result.split("\n"))
            return formatted_result
        except Exception as e:
            return {
                "ki": f"분석 중 오류 발생: {str(e)}",
                "sho": "분석을 완료하지 못했습니다.",
                "ten": "분석을 완료하지 못했습니다.",
                "ketsu": "분석을 완료하지 못했습니다."
            }


if __name__ == "__main__":
    try:
        # 입력 파일과 출력 파일 경로 설정
        input_json = "output/combined_search_results copy.json"
        output_dir = "output"
        output_file = os.path.join(output_dir, "research_report.txt")
        
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
        report_text = agent.process(input_json)
        print(f"[DEBUG] 기사 분석 완료")
        
        print(f"[DEBUG] 결과 파일 저장 중...")
        # 결과를 텍스트 파일로 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print(f"[DEBUG] 완료!")
        print(f"\n보고서가 생성되었습니다: {output_file}")
        
    except Exception as e:
        print(f"[ERROR] 처리 중 오류 발생: {str(e)}")