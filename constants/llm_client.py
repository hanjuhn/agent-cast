"""LLM client utilities for OpenAI GPT-4 integration."""

import os
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI
from .ai_models import OPENAI_MODELS


class LLMClient:
    """OpenAI GPT-4 클라이언트 클래스."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        LLM 클라이언트를 초기화합니다.
        
        Args:
            api_key: OpenAI API 키 (없으면 환경변수에서 읽음)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or provide api_key parameter.")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.default_model = "gpt-4"  # GPT-4 사용
        self.max_retries = 3
        self.retry_delay = 1.0
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        GPT-4를 사용해 응답을 생성합니다.
        
        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트 (선택사항)
            model: 사용할 모델 (기본값: gpt-4)
            max_tokens: 최대 토큰 수
            temperature: 온도 설정
            **kwargs: 추가 OpenAI API 파라미터
            
        Returns:
            생성된 응답 텍스트
        """
        model = model or self.default_model
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # 재시도 로직
        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    print(f"LLM API 호출 실패 (시도 {attempt + 1}/{self.max_retries}): {e}")
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    raise e
    
    async def analyze_personalized_data(
        self,
        slack_data: Dict[str, Any],
        notion_data: Dict[str, Any],
        gmail_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        개인화된 데이터를 분석하여 사용자의 연구 컨텍스트를 추출합니다.
        
        Args:
            slack_data: Slack에서 수집된 데이터
            notion_data: Notion에서 수집된 데이터
            gmail_data: Gmail에서 수집된 데이터
            
        Returns:
            분석된 개인화 정보
        """
        system_prompt = """당신은 사용자의 개인화된 정보를 분석하는 AI 어시스턴트입니다.
Slack, Notion, Gmail 데이터를 종합하여 사용자의 연구 방향과 관심사를 파악하세요.

분석 결과를 다음 JSON 형식으로 반환하세요:
{
    "research_interests": ["관심 연구 분야 1", "관심 연구 분야 2"],
    "current_projects": ["진행 중인 프로젝트 1", "진행 중인 프로젝트 2"],
    "collaboration_opportunities": ["협력 기회 1", "협력 기회 2"],
    "upcoming_deadlines": [
        {"task": "할 일", "deadline": "마감일", "priority": "high/medium/low"}
    ],
    "research_keywords": ["키워드1", "키워드2"],
    "preferred_topics": ["선호 주제 1", "선호 주제 2"],
    "communication_patterns": {
        "active_channels": ["채널1", "채널2"],
        "frequent_collaborators": ["협력자1", "협력자2"],
        "communication_style": "설명"
    }
}

데이터가 없거나 연결 실패한 경우에는 해당 필드를 빈 배열이나 기본값으로 설정하세요."""

        user_prompt = f"""다음 데이터를 분석해주세요:

=== Slack 데이터 ===
{slack_data}

=== Notion 데이터 ===
{notion_data}

=== Gmail 데이터 ===
{gmail_data}

위 데이터를 종합하여 사용자의 연구 컨텍스트를 분석하고 JSON 형식으로 결과를 반환해주세요."""

        try:
            response = await self.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3  # 더 일관된 결과를 위해 낮은 온도 사용
            )
            
            # JSON 파싱 시도
            import json
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 텍스트에서 정보 추출
                return self._extract_info_from_text(response)
                
        except Exception as e:
            print(f"개인화 데이터 분석 실패: {e}")
            return self._get_default_analysis()
    
    async def generate_rag_queries(
        self,
        personalized_info: Dict[str, Any],
        user_query: str = ""
    ) -> Any:
        """
        개인화된 정보를 바탕으로 RAG 검색 쿼리를 생성합니다.
        
        Args:
            personalized_info: 개인화된 정보
            user_query: 사용자 쿼리 (선택사항)
            
        Returns:
            생성된 RAG 단일 문장 쿼리 (str)
        """
        system_prompt = """당신은 정보검색 전문가입니다.
개인화된 정보를 바탕으로, 사용자가 바로 검색에 사용할 수 있는 한국어 단일 문장 검색 쿼리를 만들어주세요.

요구사항:
- 문장 하나만 출력하세요. 앞뒤 여백 외 불필요한 텍스트/따옴표/코드블록/JSON을 넣지 마세요.
- 20~100자 사이의 간결한 문장으로 작성하세요.
- 핵심 주제, 시점(최신성), 문서유형(논문/리뷰 등)을 자연스럽게 포함하세요.
예: "동적 배칭을 활용한 대규모 언어모델 효율 학습 최신 논문과 리뷰"
"""

        user_prompt = f"""다음 정보를 바탕으로 단 하나의 한국어 검색 문장을 생성하세요:

[개인화된 정보]
{personalized_info}

[사용자 요청]
{user_query or "최신 AI 연구 동향에 대한 정보를 찾고 싶습니다."}
"""

        try:
            response = await self.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.5
            )
            # 단일 문장 추출
            single_query = self._extract_single_query(response, personalized_info, user_query)

            # 파일 저장
            await self._save_queries_to_file(single_query, personalized_info, user_query)

            return single_query
                
        except Exception as e:
            print(f"RAG 쿼리 생성 실패: {e}")
            fallback_query = self._get_default_single_query(personalized_info, user_query)

            # 폴백 쿼리도 저장
            await self._save_queries_to_file(fallback_query, personalized_info, user_query, is_fallback=True)

            return fallback_query
    
    def _extract_info_from_text(self, text: str) -> Dict[str, Any]:
        """텍스트에서 정보를 추출하여 기본 구조로 변환합니다."""
        # 간단한 키워드 추출 로직
        import re
        
        keywords = re.findall(r'\b(?:AI|머신러닝|딥러닝|최적화|데이터|연구|알고리즘|신경망)\b', text, re.IGNORECASE)
        
        return {
            "research_interests": keywords[:3] if keywords else ["AI", "머신러닝"],
            "current_projects": ["AI 연구 프로젝트"],
            "collaboration_opportunities": [],
            "upcoming_deadlines": [],
            "research_keywords": keywords[:5] if keywords else ["AI", "머신러닝", "최적화"],
            "preferred_topics": keywords[:3] if keywords else ["AI 연구"],
            "communication_patterns": {
                "active_channels": [],
                "frequent_collaborators": [],
                "communication_style": "협력적"
            }
        }
    
    def _extract_queries_from_text(self, text: str, personalized_info: Dict[str, Any]) -> Dict[str, Any]:
        """텍스트에서 쿼리를 추출하여 기본 구조로 변환합니다."""
        keywords = personalized_info.get("research_keywords", ["AI", "머신러닝"])
        
        return {
            "primary_queries": [f"{keyword} 최신 연구" for keyword in keywords[:3]],
            "secondary_queries": [f"{keyword} 응용 사례" for keyword in keywords[:2]],
            "keywords": keywords,
            "search_scope": {
                "time_range": "2023-2024",
                "sources": ["arxiv.org", "ieee.org"],
                "languages": ["en", "ko"],
                "document_types": ["research_paper", "conference_proceedings"]
            },
            "research_priorities": [
                {
                    "topic": keywords[0] if keywords else "AI 연구",
                    "priority": "high",
                    "rationale": "사용자의 주요 관심 분야"
                }
            ],
                        "expected_results": ["논문", "기술 동향"]
        }

    def _extract_single_query(self, text: str, personalized_info: Dict[str, Any], user_query: str) -> str:
        """응답 텍스트에서 단일 문장 쿼리를 추출합니다. JSON일 경우에도 첫 쿼리를 선택합니다."""
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                # 우선순위: explicit 'query' -> primary_queries[0] -> keywords 기반 생성
                query = data.get("query")
                if not query:
                    primary = data.get("primary_queries") or []
                    if isinstance(primary, list) and primary:
                        query = str(primary[0])
                if not query:
                    kws = data.get("keywords") or []
                    if isinstance(kws, list) and kws:
                        head = " ".join([str(k) for k in kws[:2]])
                        query = f"{head} 최신 연구 동향과 주요 논문"
                if query:
                    return query.strip()
        except Exception:
            pass

        # JSON이 아니거나 적합한 키가 없을 때: 응답에서 한 줄만 추출
        line = text.strip().splitlines()[0].strip().strip('"').strip("'")
        if line:
            return line

        # 최종 폴백
        return self._get_default_single_query(personalized_info, user_query)

    def _get_default_single_query(self, personalized_info: Dict[str, Any], user_query: str) -> str:
        """개인화 정보를 반영한 기본 단일 문장 쿼리 생성."""
        personal = personalized_info.get("personal_info", {}) if isinstance(personalized_info, dict) else {}
        context = personalized_info.get("research_context", {}) if isinstance(personalized_info, dict) else {}
        keywords = personal.get("research_keywords", [])
        interests = context.get("research_interests", [])
        base = (user_query or "최신 AI 연구 동향").strip()
        core = (interests[0] if interests else (keywords[0] if keywords else "AI")).strip()
        if core in base:
            topic = base
        else:
            topic = f"{core} {base}"
        return f"{topic} 관련 최신 논문과 리뷰"
    
    async def _save_queries_to_file(
        self, 
        queries: Dict[str, Any], 
        personalized_info: Dict[str, Any], 
        user_query: str, 
        is_fallback: bool = False
    ):
        """생성된 쿼리를 JSON 파일로 저장합니다."""
        try:
            # output/queries 디렉토리 생성
            output_dir = Path("output/queries")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 타임스탬프 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 파일명 생성
            prefix = "fallback_" if is_fallback else ""
            filename = f"{prefix}rag_queries_{timestamp}.json"
            
            # 저장할 데이터 구성
            save_data = {
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "user_query": user_query,
                    "is_fallback": is_fallback,
                    "generation_method": "fallback" if is_fallback else "llm_generated"
                },
                "personalized_info_summary": {
                    "research_keywords": personalized_info.get("personal_info", {}).get("research_keywords", []),
                    "research_interests": personalized_info.get("research_context", {}).get("research_interests", []),
                    "current_projects": personalized_info.get("research_context", {}).get("current_projects", [])
                },
                "generated_queries": queries
            }
            
            # 파일 저장
            file_path = output_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 RAG 쿼리 저장: {file_path}")
            
            # 최신 쿼리도 별도 저장 (덮어쓰기)
            latest_file = output_dir / "latest_rag_queries.json"
            with open(latest_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 최신 쿼리 저장: {latest_file}")
            
        except Exception as e:
            print(f"⚠️ 쿼리 저장 실패: {e}")

    def _get_default_analysis(self) -> Dict[str, Any]:
        """기본 분석 결과를 반환합니다."""
        return {
            "research_interests": ["AI", "머신러닝", "최적화"],
            "current_projects": ["AI 연구 프로젝트"],
            "collaboration_opportunities": [],
            "upcoming_deadlines": [],
            "research_keywords": ["AI", "머신러닝", "최적화", "데이터"],
            "preferred_topics": ["AI 연구", "머신러닝"],
            "communication_patterns": {
                "active_channels": [],
                "frequent_collaborators": [],
                "communication_style": "협력적"
            }
        }
    
    def _get_default_queries(self) -> Dict[str, Any]:
        """기본 쿼리를 반환합니다."""
        return {
            "primary_queries": ["AI 최신 연구 동향", "머신러닝 기법 발전"],
            "secondary_queries": ["AI 응용 사례", "데이터 최적화"],
            "keywords": ["AI", "머신러닝", "최적화"],
            "search_scope": {
                "time_range": "2023-2024",
                "sources": ["arxiv.org", "ieee.org"],
                "languages": ["en", "ko"],
                "document_types": ["research_paper"]
            },
            "research_priorities": [
                {
                    "topic": "AI 연구 동향",
                    "priority": "high",
                    "rationale": "일반적인 관심 주제"
                }
            ],
            "expected_results": ["논문", "기술 동향"]
        }


# 전역 클라이언트 인스턴스
_llm_client = None


def get_llm_client() -> LLMClient:
    """전역 LLM 클라이언트 인스턴스를 반환합니다."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
