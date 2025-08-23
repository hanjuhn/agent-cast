"""Critic Agent for evaluating research output and providing feedback."""

import os
import json
from datetime import datetime
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from rouge_score import rouge_scorer
from bert_score import score as bert_score

from ..base_agent import BaseAgent
from state.state import WorkflowState
from constants import OPENAI_CRITIC_PARAMS, OPENAI_CRITIC_FALLBACK_PARAMS, CHUNK_PROCESSING
from constants.prompts import RESEARCH_CRITIC_DETAILED_PROMPT

# --- 환경 변수 로드 ---
load_dotenv()

class CriticAgent(BaseAgent):
    """리서치 결과를 평가하고 품질을 검토하는 에이전트"""
    
    def __init__(self):
        super().__init__(
            name="critic",
            description="리서치 결과를 평가하고 품질을 검토하는 에이전트"
        )
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되어 있지 않습니다.")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4"
        
        # Critic 역할 프롬프트
        self.role_prompt = RESEARCH_CRITIC_DETAILED_PROMPT

    def _calculate_quantitative_metrics(self, generated_text: str, reference_texts: list[str]) -> dict:
        """정량적 평가 지표를 계산하는 내부 메소드."""
        print("--- 정량적 평가 시작 ---")
        
        try:
            # BERTScore 계산
            P, R, F1 = bert_score([generated_text], reference_texts, lang="ko", model_type="bert-base-multilingual-cased")
            bertscore_f1 = F1.mean().item()
            print(f"BERTScore F1: {bertscore_f1:.4f}")

            # ROUGE Score 계산
            scorer = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True)
            scores = scorer.score(reference_texts[0], generated_text)
            rougeL_fmeasure = scores['rougeL'].fmeasure
            print(f"ROUGE-L F-measure: {rougeL_fmeasure:.4f}")
            
            print("--- 정량적 평가 완료 ---")
            return {
                "bert_score_f1": round(bertscore_f1, 4),
                "rougeL_fmeasure": round(rougeL_fmeasure, 4)
            }
        except Exception as e:
            print(f"정량적 지표 계산 실패: {e}")
            return {"error": "계산 실패"}

    def _create_source_documents_from_state(self, state: WorkflowState) -> List[str]:
        """WorkflowState에서 소스 문서를 생성합니다."""
        source_documents = []
        
        # 검색 결과에서 소스 문서 생성
        search_results = getattr(state, 'search_results', [])
        for result in search_results:
            content = f"{result.get('title', '')} {result.get('content', '')}"
            if content.strip():
                source_documents.append(content)
        
        # 개인화 정보에서 소스 문서 생성
        personal_info = getattr(state, 'personal_info', {})
        if personal_info:
            for key, value in personal_info.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            content = " ".join([f"{k}: {v}" for k, v in item.items() if v])
                        else:
                            content = str(item)
                        
                        if content and len(content) > 10:
                            source_documents.append(content)
        
        # 연구 컨텍스트에서 소스 문서 생성
        research_context = getattr(state, 'research_context', {})
        if research_context:
            for key, value in research_context.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            content = " ".join([f"{k}: {v}" for k, v in item.items() if v])
                        else:
                            content = str(item)
                        
                        if content and len(content) > 10:
                            source_documents.append(content)
        
        # 기본 소스 문서가 없으면 기본값 제공
        if not source_documents:
            source_documents = [
                "AI 기술 동향에 대한 일반적인 정보와 연구 자료",
                "LLM 최적화 및 MoE 아키텍처 관련 기술 문서",
                "AI 연구 및 개발 프로젝트 관련 자료"
            ]
        
        return source_documents
    
    def _create_user_profile_from_state(self, state: WorkflowState) -> str:
        """WorkflowState에서 사용자 프로필을 생성합니다."""
        personal_info = getattr(state, 'personal_info', {})
        research_context = getattr(state, 'research_context', {})
        
        profile_parts = []
        
        # 연구 키워드
        research_keywords = personal_info.get('research_keywords', [])
        if research_keywords:
            profile_parts.append(f"연구 관심사: {', '.join(research_keywords)}")
        
        # 현재 프로젝트
        current_projects = research_context.get('current_projects', [])
        if current_projects:
            profile_parts.append(f"현재 프로젝트: {', '.join(current_projects)}")
        
        # 연구 방향
        research_direction = research_context.get('research_direction', '')
        if research_direction:
            profile_parts.append(f"연구 방향: {research_direction}")
        
        if profile_parts:
            return " | ".join(profile_parts)
        else:
            return "AI 기술에 관심이 있는 연구자"

    def _truncate_text(self, text: str, max_chars: int = 3000) -> str:
        """텍스트를 지정된 길이로 자르고 요약합니다."""
        if len(text) <= max_chars:
            return text
        
        # 첫 부분과 마지막 부분을 유지하고 중간을 요약
        first_part = text[:max_chars//3]
        last_part = text[-(max_chars//3):]
        middle_summary = f"...[중간 내용 요약: {len(text) - (max_chars//3)*2}자 생략]..."
        
        return first_part + middle_summary + last_part

    def evaluate_research_output(self, research_output: str, source_documents: List[str], 
                               user_profile: str) -> Dict[str, Any]:
        """리서치 결과물을 다각도로 평가하고 피드백 생성"""
        print("--- 리서치 결과물 평가 시작 ---")
        
        # 긴 텍스트를 요약하여 토큰 제한 방지
        truncated_research = self._truncate_text(research_output, CHUNK_PROCESSING["max_chars_for_critic_research"])
        truncated_profile = self._truncate_text(user_profile, CHUNK_PROCESSING["max_chars_for_critic_profile"])
        
        prompt = f"""
{self.role_prompt}

**사용자 프로필 (요약):**
{truncated_profile}

**평가할 리서치 결과물 (요약):**
{truncated_research}

**참조 문서 수:**
{len(source_documents)}개

**작업:**
리서치 결과물을 다각적으로 평가하고 구체적인 피드백을 제공하세요.

다음 JSON 형식으로 응답해주세요:
```json
{{
    "overall_score": 0.85,
    "evaluation_criteria": {{
        "factual_accuracy": {{
            "score": 0.9,
            "feedback": "사실적 정확성이 매우 높습니다."
        }},
        "logical_consistency": {{
            "score": 0.8,
            "feedback": "논리적 일관성이 우수합니다."
        }},
        "relevance": {{
            "score": 0.85,
            "feedback": "사용자 요구사항과 매우 관련성이 높습니다."
        }},
        "completeness": {{
            "score": 0.75,
            "feedback": "대부분의 내용을 다루지만, 일부 세부사항이 부족합니다."
        }},
        "clarity": {{
            "score": 0.9,
            "feedback": "명확하고 이해하기 쉬운 표현을 사용합니다."
        }}
    }},
    "detailed_feedback": "전반적으로 우수한 품질의 리서치 결과입니다.",
    "improvement_suggestions": [
        "완성도 향상을 위해 일부 세부사항을 추가하세요.",
        "논리적 일관성을 더욱 강화하세요."
    ],
    "critical_issues": [],
    "recommendations": "이 리서치 결과는 사용자에게 제공할 준비가 되었습니다."
}}
```

**중요:** JSON 형식으로만 응답해주세요. 다른 텍스트는 포함하지 마세요.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 전문적인 리서치 비평가입니다. 정확하고 객관적인 평가를 제공하세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=OPENAI_CRITIC_PARAMS["temperature"],
                max_tokens=OPENAI_CRITIC_PARAMS["max_tokens"]
            )
            
            evaluation_text = response.choices[0].message.content.strip()
            
            # 토큰 사용량 확인
            if hasattr(response, 'usage'):
                usage = response.usage
                print(f"토큰 사용량: 입력 {usage.prompt_tokens}, 출력 {usage.completion_tokens}, 총 {usage.total_tokens}")
            
            # 디버깅: GPT 응답 내용 확인
            print(f"GPT 응답 미리보기: {evaluation_text[:200]}...")
            
            try:
                evaluation_result = json.loads(evaluation_text)
                print("JSON 파싱 성공")
            except json.JSONDecodeError as e:
                print(f"JSON 파싱 실패: {e}")
                print(f"전체 응답: {evaluation_text}")
                
                try:
                    import re
                    
                    json_match = re.search(r'```json\s*(.*?)\s*```', evaluation_text, re.DOTALL)
                    if json_match:
                        json_content = json_match.group(1)
                        evaluation_result = json.loads(json_content)
                        print("JSON 블록에서 추출 성공")
                        return evaluation_result
                    
                    json_match = re.search(r'```\s*(.*?)\s*```', evaluation_text, re.DOTALL)
                    if json_match:
                        json_content = json_match.group(1)
                        try:
                            evaluation_result = json.loads(json_content)
                            print("코드 블록에서 JSON 추출 성공")
                            return evaluation_result
                        except:
                            pass
                    
                    json_match = re.search(r'\{.*\}', evaluation_text, re.DOTALL)
                    if json_match:
                        json_content = json_match.group(0)
                        try:
                            evaluation_result = json.loads(json_content)
                            print("JSON 객체 직접 추출 성공")
                            return evaluation_result
                        except:
                            pass
                    
                    print("GPT 응답을 구조화된 형태로 변환 시도...")
                    evaluation_result = self._parse_unstructured_response(evaluation_text)
                    if evaluation_result:
                        print("구조화된 응답 파싱 성공")
                        return evaluation_result
                    
                    print("모든 JSON 추출 방법 실패, 기본 평가 결과 사용")
                    evaluation_result = self._get_default_evaluation()
                    
                except Exception as extract_error:
                    print(f"JSON 추출 실패: {extract_error}, 기본 평가 결과 사용")
                    evaluation_result = self._get_default_evaluation()
            
            try:
                quantitative_metrics = self._calculate_quantitative_metrics(research_output, source_documents)
                evaluation_result["quantitative_metrics"] = quantitative_metrics
            except Exception as e:
                print(f"정량적 지표 계산 실패: {e}")
                evaluation_result["quantitative_metrics"] = {"error": "계산 실패"}
            
            print("--- 리서치 결과물 평가 완료 ---")
            return evaluation_result
            
        except Exception as e:
            print(f"평가 중 오류 발생: {e}")
            return self._get_default_evaluation()

    def _get_default_evaluation(self) -> Dict[str, Any]:
        """기본 평가 결과를 반환합니다."""
        return {
            "overall_score": 0.7,
            "evaluation_criteria": {
                "factual_accuracy": {
                    "score": 0.7,
                    "feedback": "평가를 수행할 수 없어 기본값을 사용합니다."
                },
                "logical_consistency": {
                    "score": 0.7,
                    "feedback": "평가를 수행할 수 없어 기본값을 사용합니다."
                },
                "relevance": {
                    "score": 0.7,
                    "feedback": "평가를 수행할 수 없어 기본값을 사용합니다."
                },
                "completeness": {
                    "score": 0.7,
                    "feedback": "평가를 수행할 수 없어 기본값을 사용합니다."
                },
                "clarity": {
                    "score": 0.7,
                    "feedback": "평가를 수행할 수 없어 기본값을 사용합니다."
                }
            },
            "detailed_feedback": "평가 중 오류가 발생하여 기본 피드백을 제공합니다.",
            "improvement_suggestions": ["평가를 다시 시도하세요."],
            "critical_issues": ["평가 시스템 오류"],
            "recommendations": "평가를 다시 수행하세요."
        }
    
    def _parse_unstructured_response(self, response_text: str) -> dict:
        """구조화되지 않은 GPT 응답을 파싱하여 평가 결과로 변환합니다."""
        try:
            import re
            
            # 점수 추출 (0.0 ~ 1.0 범위)
            score_match = re.search(r'(\d+\.?\d*)\s*점|score[:\s]*(\d+\.?\d*)|(\d+\.?\d*)', response_text, re.IGNORECASE)
            overall_score = 0.7  # 기본값
            if score_match:
                for group in score_match.groups():
                    if group:
                        try:
                            score = float(group)
                            if 0.0 <= score <= 1.0:
                                overall_score = score
                                break
                        except ValueError:
                            continue
            
            # 피드백 키워드 추출
            feedback_keywords = {
                "factual_accuracy": ["사실", "정확", "출처", "인용"],
                "logical_consistency": ["논리", "일관", "구조", "흐름"],
                "relevance": ["관련", "적절", "요구사항"],
                "completeness": ["완성", "포괄", "세부", "부족"],
                "clarity": ["명확", "이해", "표현", "가독"]
            }
            
            evaluation_criteria = {}
            for criterion, keywords in feedback_keywords.items():
                score = 0.7  # 기본값
                feedback = "평가를 수행할 수 없어 기본값을 사용합니다."
                
                # 키워드 기반 점수 조정
                for keyword in keywords:
                    if keyword in response_text:
                        score = min(0.9, score + 0.1)  # 키워드 발견 시 점수 상승
                        feedback = f"{keyword} 관련 내용이 포함되어 있습니다."
                        break
                
                evaluation_criteria[criterion] = {
                    "score": round(score, 2),
                    "feedback": feedback
                }
            
            # 개선 제안 추출
            improvement_suggestions = []
            if "개선" in response_text or "제안" in response_text or "suggestion" in response_text.lower():
                improvement_suggestions = ["평가 결과를 바탕으로 개선이 필요합니다."]
            else:
                improvement_suggestions = ["평가를 다시 시도하세요."]
            
            return {
                "overall_score": round(overall_score, 2),
                "evaluation_criteria": evaluation_criteria,
                "detailed_feedback": "구조화되지 않은 응답을 파싱하여 평가 결과를 생성했습니다.",
                "improvement_suggestions": improvement_suggestions,
                "critical_issues": [],
                "recommendations": "이 평가 결과는 파싱된 결과입니다."
            }
            
        except Exception as e:
            print(f"구조화된 응답 파싱 실패: {e}")
            return None

    async def process(self, state: WorkflowState) -> WorkflowState:
        """리서치 결과를 평가합니다."""
        self.log_execution("리서치 결과 평가 시작")
        
        try:
            # 상태에서 데이터 추출
            research_result = getattr(state, 'research_result', '')
            source_documents = self._create_source_documents_from_state(state)
            user_profile = self._create_user_profile_from_state(state)
            
            if not research_result:
                self.log_execution("평가할 리서치 결과가 없어 기본 평가를 수행합니다")
                research_result = "AI 기술 동향에 대한 기본 분석 보고서"
            
            # 평가 수행
            evaluation_results = self.evaluate_research_output(
                research_result, source_documents, user_profile
            )
            
            # 결과 저장
            output_filename = f"output/critic/evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs(os.path.dirname(output_filename), exist_ok=True)
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(evaluation_results, f, ensure_ascii=False, indent=2)
            
            # 워크플로우 상태 업데이트
            state_dict = {k: v for k, v in state.__dict__.items()}
            if 'evaluation_results' in state_dict:
                del state_dict['evaluation_results']
            if 'critic_feedback' in state_dict:
                del state_dict['critic_feedback']
            if 'quality_score' in state_dict:
                del state_dict['quality_score']
            
            new_state = WorkflowState(
                **state_dict,
                evaluation_results=evaluation_results,
                critic_feedback=evaluation_results.get('detailed_feedback', ''),
                quality_score=evaluation_results.get('overall_score', 0.0)
            )
            
            # 워크플로우 상태 업데이트
            new_state = self.update_workflow_status(new_state, "critic_completed")
            
            self.log_execution(f"리서치 결과 평가 완료: 점수 {evaluation_results.get('overall_score', 0.0)}")
            return new_state
            
        except Exception as e:
            self.log_execution(f"리서치 결과 평가 중 오류 발생: {str(e)}", "ERROR")
            raise
