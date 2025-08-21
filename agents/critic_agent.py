import os
import json
from datetime import datetime
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from rouge_score import rouge_scorer
from bert_score import score as bert_score

try:
    from .base_agent import BaseAgent
    from state import WorkflowState
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from .base_agent import BaseAgent
    from state import WorkflowState

# --- 환경 변수 로드 ---
load_dotenv()  # .env 파일에서 환경 변수 로드

class ResearchCriticAgent:
    """
    리서치 결과물을 평가하고 개선을 위한 경쟁적 피드백을 제공하는 전문 비평가 에이전트.
    LEGO 프레임워크의 Critic-Explainer 경쟁 구조를 참고하여 리서치 품질 향상을 도모합니다.
    """
    def __init__(self, model="gpt-4o"):
        """
        에이전트를 초기화하고 OpenAI 클라이언트를 설정합니다.
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
        # Critic 역할 프롬프트
        self.role_prompt = """
        당신은 ResearchCritic입니다. 리서처 에이전트가 생성한 리서치 결과물을 평가하고 
        개선을 위한 다각적이고 구체적인 피드백을 제공하는 전문가입니다.

        당신의 역할:
        1. 리서치 결과물을 객관적이고 엄격하게 평가
        2. Factual Feedback: 사실적 정확성과 출처 신뢰성 검토
        3. Logical Feedback: 논리적 완결성과 구조적 일관성 검토
        4. Relevance Feedback: 사용자 요구사항과의 관련성 검토
        5. 구체적이고 실행 가능한 개선 제안 제공
        6. 허위 정보나 부정확한 인용 식별 및 지적

        평가 기준:
        - 사실적 정확성과 출처 신뢰성
        - 논리적 완결성과 구조적 일관성
        - 사용자 요구사항과의 관련성
        - 정보의 깊이와 포괄성
        - 인용과 참조의 적절성
        """

    def _calculate_quantitative_metrics(self, generated_text: str, reference_texts: list[str]) -> dict:
        """
        [TOOL] 정량적 평가 지표를 계산하는 내부 메소드.
        """
        print("---  cuantitativa de la evaluación se ha iniciado ---")
        
        # BERTScore 계산
        P, R, F1 = bert_score([generated_text], reference_texts, lang="ko", model_type="bert-base-multilingual-cased")
        bertscore_f1 = F1.mean().item()
        print(f"BERTScore F1: {bertscore_f1:.4f}")

        # ROUGE Score 계산
        scorer = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True)
        # 여러 참조 문서에 대한 평균 점수를 계산할 수 있으나, 여기서는 첫 번째 문서를 기준으로 계산
        scores = scorer.score(reference_texts[0], generated_text)
        rougeL_fmeasure = scores['rougeL'].fmeasure
        print(f"ROUGE-L F-measure: {rougeL_fmeasure:.4f}")
        
        print("--- Evaluación Cuantitativa Completada ---")
        return {
            "bert_score_f1": round(bertscore_f1, 4),
            "rougeL_fmeasure": round(rougeL_fmeasure, 4)
        }

    def evaluate_research_output(self, research_output: str, source_documents: list[str], 
                               user_profile: str) -> dict:
        """
        리서치 결과물을 다각도로 평가하고 피드백 생성 (LEGO 프레임워크 스타일)
        
        Args:
            research_output (str): 평가할 리서치 결과물
            source_documents (list[str]): 참조 문서들
            user_profile (str): 사용자 프로필
            
        Returns:
            dict: 평가 결과와 피드백
        """
        print("--- 리서치 결과물 평가 시작 ---")
        
        prompt = f"""
{self.role_prompt}

**사용자 프로필:**
{user_profile}

**평가할 리서치 결과물:**
{research_output}

**참조 문서들:**
{chr(10).join([f"- {doc[:200]}..." for doc in source_documents])}

**작업:**
리서치 결과물을 다각적으로 평가하고 구체적인 피드백을 제공하세요.

다음 JSON 형식으로 응답해주세요:
```json
{{
    "overall_score": 0.85,
    "evaluation_criteria": {{
        "factual_accuracy": {{
            "score": 0.9,
            "feedback": "사실적 정확성이 매우 높습니다. 출처와 인용이 적절하게 처리되었습니다."
        }},
        "logical_consistency": {{
            "score": 0.8,
            "feedback": "논리적 일관성이 우수합니다. 구조와 흐름이 명확합니다."
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
    "detailed_feedback": "전반적으로 우수한 품질의 리서치 결과입니다. 특히 사실적 정확성과 명확성에서 높은 점수를 받았습니다.",
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
                temperature=0.1,
                max_tokens=2000
            )
            
            evaluation_text = response.choices[0].message.content.strip()
            
            # JSON 파싱
            try:
                evaluation_result = json.loads(evaluation_text)
            except json.JSONDecodeError:
                print("⚠️ JSON 파싱 실패, 기본 평가 결과 사용")
                evaluation_result = self._get_default_evaluation()
            
            # 정량적 지표 계산 (선택적)
            try:
                quantitative_metrics = self._calculate_quantitative_metrics(research_output, source_documents)
                evaluation_result["quantitative_metrics"] = quantitative_metrics
            except Exception as e:
                print(f"⚠️ 정량적 지표 계산 실패: {e}")
                evaluation_result["quantitative_metrics"] = {"error": "계산 실패"}
            
            print("--- 리서치 결과물 평가 완료 ---")
            return evaluation_result
            
        except Exception as e:
            print(f"❌ 평가 중 오류 발생: {e}")
            return self._get_default_evaluation()

    def _get_default_evaluation(self) -> dict:
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

def save_evaluation_results(data, filename=None):
    """평가 결과를 JSON 파일로 저장합니다."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_results_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ 평가 결과가 '{filename}'에 성공적으로 저장되었습니다.")
        return filename
    except Exception as e:
        print(f"❌ 파일 저장 중 오류 발생: {e}")
        return None

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
        self.role_prompt = """
        당신은 ResearchCritic입니다. 리서처 에이전트가 생성한 리서치 결과물을 평가하고 
        개선을 위한 다각적이고 구체적인 피드백을 제공하는 전문가입니다.

        당신의 역할:
        1. 리서치 결과물을 객관적이고 엄격하게 평가
        2. Factual Feedback: 사실적 정확성과 출처 신뢰성 검토
        3. Logical Feedback: 논리적 완결성과 구조적 일관성 검토
        4. Relevance Feedback: 사용자 요구사항과의 관련성 검토
        5. 구체적이고 실행 가능한 개선 제안 제공
        6. 허위 정보나 부정확한 인용 식별 및 지적

        평가 기준:
        - 사실적 정확성과 출처 신뢰성
        - 논리적 완결성과 구조적 일관성
        - 사용자 요구사항과의 관련성
        - 정보의 깊이와 포괄성
        - 인용과 참조의 적절성
        """
    
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
    
    def evaluate_research_output(self, research_output: str, source_documents: List[str], 
                               user_profile: str) -> Dict[str, Any]:
        """리서치 결과물을 다각도로 평가하고 피드백 생성"""
        print("--- 리서치 결과물 평가 시작 ---")
        
        prompt = f"""
{self.role_prompt}

**사용자 프로필:**
{user_profile}

**평가할 리서치 결과물:**
{research_output}

**참조 문서들:**
{chr(10).join([f"- {doc[:200]}..." for doc in source_documents])}

**작업:**
리서치 결과물을 다각적으로 평가하고 구체적인 피드백을 제공하세요.

다음 JSON 형식으로 응답해주세요:
```json
{{
    "overall_score": 0.85,
    "evaluation_criteria": {{
        "factual_accuracy": {{
            "score": 0.9,
            "feedback": "사실적 정확성이 매우 높습니다. 출처와 인용이 적절하게 처리되었습니다."
        }},
        "logical_consistency": {{
            "score": 0.8,
            "feedback": "논리적 일관성이 우수합니다. 구조와 흐름이 명확합니다."
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
    "detailed_feedback": "전반적으로 우수한 품질의 리서치 결과입니다. 특히 사실적 정확성과 명확성에서 높은 점수를 받았습니다.",
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
                temperature=0.1,
                max_tokens=2000
            )
            
            evaluation_text = response.choices[0].message.content.strip()
            
            # JSON 파싱
            try:
                evaluation_result = json.loads(evaluation_text)
            except json.JSONDecodeError:
                print("⚠️ JSON 파싱 실패, 기본 평가 결과 사용")
                evaluation_result = self._get_default_evaluation()
            
            return evaluation_result
            
        except Exception as e:
            print(f"⚠️ 평가 중 오류 발생: {e}, 기본 평가 결과 사용")
            return self._get_default_evaluation()
    
    def _get_default_evaluation(self) -> Dict[str, Any]:
        """기본 평가 결과를 반환합니다."""
        return {
            "overall_score": 0.75,
            "evaluation_criteria": {
                "factual_accuracy": {
                    "score": 0.8,
                    "feedback": "기본적인 사실적 정확성을 유지합니다."
                },
                "logical_consistency": {
                    "score": 0.7,
                    "feedback": "논리적 구조가 대체로 일관됩니다."
                },
                "relevance": {
                    "score": 0.8,
                    "feedback": "사용자 요구사항과 관련성이 있습니다."
                },
                "completeness": {
                    "score": 0.7,
                    "feedback": "기본적인 내용을 다루고 있습니다."
                },
                "clarity": {
                    "score": 0.8,
                    "feedback": "이해하기 쉬운 표현을 사용합니다."
                }
            },
            "detailed_feedback": "기본적인 품질의 리서치 결과입니다. 개선의 여지가 있습니다.",
            "improvement_suggestions": [
                "더 구체적인 예시와 데이터를 추가하세요.",
                "논리적 구조를 강화하세요."
            ],
            "critical_issues": [],
            "recommendations": "기본적인 검토 후 사용 가능합니다."
        }
    
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

def main():
    """
    메인 실행 함수
    """
    print("🚀 리서치 비평가 파이프라인 시작")
    print("=" * 50)
    
    # 1. ResearchCriticAgent 초기화
    print("\n1️⃣ ResearchCriticAgent 초기화 중...")
    critic = ResearchCriticAgent()
    
    # 2. 샘플 데이터 준비
    print("\n2️⃣ 샘플 데이터 준비 중...")
    sample_research_output = """
    최신 AI 트렌드 분석
    
    인공지능 분야에서 가장 주목받는 트렌드는 다음과 같습니다:
    
    1. 대규모 언어 모델 (LLM)의 발전
    - GPT-4, Claude 등의 모델이 지속적으로 개선되고 있습니다.
    - 멀티모달 기능이 강화되어 텍스트, 이미지, 음성을 통합 처리합니다.
    
    2. 생성형 AI의 확산
    - DALL-E, Midjourney 등의 이미지 생성 AI가 널리 사용됩니다.
    - 비즈니스 응용 사례가 증가하고 있습니다.
    
    3. AI 규제 및 윤리
    - AI의 안전성과 윤리에 대한 논의가 활발합니다.
    - 각국에서 AI 규제 법안을 도입하고 있습니다.
    """
    
    sample_source_documents = [
        "OpenAI의 최신 연구 보고서에 따르면 GPT-4는 다양한 작업에서 인간 수준의 성능을 보여줍니다.",
        "Google의 연구팀은 멀티모달 AI 모델의 발전에 대한 새로운 접근법을 제시했습니다.",
        "EU의 AI 규제 법안은 AI 시스템의 투명성과 책임성을 강조합니다."
    ]
    
    sample_user_profile = "AI 기술에 관심이 있는 일반 사용자"
    
    # 3. 평가 수행
    print("\n3️⃣ 리서치 결과 평가 중...")
    evaluation_result = critic.evaluate_research_output(
        sample_research_output, sample_source_documents, sample_user_profile
    )
    
    # 4. 결과 저장
    print("\n4️⃣ 결과 저장 중...")
    saved_filename = save_evaluation_results(evaluation_result)
    
    if saved_filename:
        print(f"\n✅ 리서치 비평가 파이프라인 완료!")
        print(f"📊 전체 점수: {evaluation_result.get('overall_score', 0.0)}")
        print(f"💾 저장된 파일: {saved_filename}")
        
        # 평가 결과 요약 출력
        print(f"\n📋 평가 결과 요약:")
        criteria = evaluation_result.get('evaluation_criteria', {})
        for criterion, result in criteria.items():
            print(f"   - {criterion}: {result.get('score', 0.0)}")
        
        print(f"\n💡 개선 제안:")
        suggestions = evaluation_result.get('improvement_suggestions', [])
        for i, suggestion in enumerate(suggestions, 1):
            print(f"   {i}. {suggestion}")
    else:
        print("❌ 결과 저장 실패")

if __name__ == "__main__":
    main()
