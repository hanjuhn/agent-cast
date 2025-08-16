"""Critic Agent for reviewing and evaluating research results."""

from typing import Any, Dict, List
from ..constants import AGENT_NAMES, CRITIC_SYSTEM_PROMPT, QUALITY_THRESHOLDS
from .base_agent import BaseAgent, AgentResult
from ..state import WorkflowState


class CriticAgent(BaseAgent):
    """연구 결과의 품질을 평가하고 검토하는 에이전트."""
    
    def __init__(self):
        super().__init__(
            name=AGENT_NAMES["CRITIC"],
            description="연구 결과의 품질을 평가하고 검토하는 에이전트"
        )
        self.required_inputs = ["research_results"]
        self.output_keys = ["critic_feedback", "approval_status", "quality_score"]
        self.timeout = 60
        self.retry_attempts = 1
        self.priority = 5
        
        # 품질 평가 기준
        self.quality_criteria = {
            "factual_accuracy": 0.3,
            "source_verification": 0.25,
            "logical_consistency": 0.2,
            "data_freshness": 0.15,
            "completeness": 0.1
        }
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """연구 결과 품질 평가를 수행합니다."""
        self.log_execution("연구 결과 품질 평가 시작")
        
        try:
            # 입력 검증
            if not self.validate_inputs(state):
                raise ValueError("필수 입력이 누락되었습니다: research_results")
            
            # 연구 결과 분석
            research_results = state.research_results
            
            # 품질 점수 계산
            quality_score = self._calculate_quality_score(research_results)
            
            # 비평 피드백 생성
            critic_feedback = self._generate_critic_feedback(research_results, quality_score)
            
            # 승인 상태 결정
            approval_status = self._determine_approval_status(quality_score)
            
            # 결과 생성
            result = AgentResult(
                success=True,
                output={
                    "critic_feedback": critic_feedback,
                    "approval_status": approval_status,
                    "quality_score": quality_score
                },
                metadata={
                    "evaluation_method": "multi_criteria",
                    "threshold_used": QUALITY_THRESHOLDS["minimum_quality_score"],
                    "criteria_weights": self.quality_criteria
                }
            )
            
            # 상태 업데이트
            updated_state = self.update_workflow_status(state, "critique")
            updated_state.critic_feedback = critic_feedback
            updated_state.approval_status = approval_status
            updated_state.quality_score = quality_score
            
            self.log_execution(f"연구 결과 품질 평가 완료. 품질 점수: {quality_score:.2f}")
            return updated_state
            
        except Exception as e:
            self.log_execution(f"연구 결과 품질 평가 실패: {str(e)}", "ERROR")
            
            # 폴백 데이터 사용
            fallback_data = self._get_fallback_data()
            
            result = AgentResult(
                success=False,
                output=fallback_data,
                error_message=str(e)
            )
            
            # 폴백 데이터로 상태 업데이트
            updated_state = self.update_workflow_status(state, "critique")
            updated_state.critic_feedback = fallback_data["critic_feedback"]
            updated_state.approval_status = fallback_data["approval_status"]
            updated_state.quality_score = fallback_data["quality_score"]
            
            self.log_execution("폴백 데이터 사용으로 계속 진행")
            return updated_state
    
    def _calculate_quality_score(self, research_results: Dict[str, Any]) -> float:
        """연구 결과의 품질 점수를 계산합니다."""
        if "error" in research_results:
            return 0.0
        
        # 각 품질 기준별 점수 계산
        scores = {}
        
        # 1. 사실적 정확성 (Factual Accuracy)
        scores["factual_accuracy"] = self._evaluate_factual_accuracy(research_results)
        
        # 2. 출처 검증 (Source Verification)
        scores["source_verification"] = self._evaluate_source_verification(research_results)
        
        # 3. 논리적 일관성 (Logical Consistency)
        scores["logical_consistency"] = self._evaluate_logical_consistency(research_results)
        
        # 4. 데이터 최신성 (Data Freshness)
        scores["data_freshness"] = self._evaluate_data_freshness(research_results)
        
        # 5. 완성도 (Completeness)
        scores["completeness"] = self._evaluate_completeness(research_results)
        
        # 가중 평균으로 최종 품질 점수 계산
        final_score = sum(
            scores[criterion] * weight 
            for criterion, weight in self.quality_criteria.items()
        )
        
        return round(final_score, 3)
    
    def _evaluate_factual_accuracy(self, research_results: Dict[str, Any]) -> float:
        """사실적 정확성을 평가합니다."""
        summary = research_results.get("summary", {})
        
        # 고품질 결과의 비율
        high_relevance_count = summary.get("high_relevance_count", 0)
        total_results = summary.get("total_results", 1)
        
        if total_results == 0:
            return 0.0
        
        # 평균 유사도 점수
        avg_similarity = summary.get("average_similarity", 0.0)
        
        # 고품질 결과 비율과 평균 유사도의 가중 평균
        high_quality_ratio = high_relevance_count / total_results
        factual_accuracy = (high_quality_ratio * 0.7) + (avg_similarity * 0.3)
        
        return min(factual_accuracy, 1.0)
    
    def _evaluate_source_verification(self, research_results: Dict[str, Any]) -> float:
        """출처 검증을 평가합니다."""
        source_analysis = research_results.get("source_analysis", {})
        
        if not source_analysis:
            return 0.5  # 중간 점수
        
        # 신뢰할 수 있는 소스의 비율
        trusted_sources = ["arxiv.org", "ieee.org", "acm.org", "scholar.google.com"]
        trusted_count = 0
        total_sources = len(source_analysis)
        
        for source in source_analysis:
            if source in trusted_sources:
                trusted_count += 1
        
        trusted_ratio = trusted_count / total_sources if total_sources > 0 else 0
        
        # 소스 다양성 점수
        diversity_score = min(len(source_analysis) / 5, 1.0)  # 최대 5개 소스까지
        
        # 출처 검증 점수 계산
        source_verification = (trusted_ratio * 0.6) + (diversity_score * 0.4)
        
        return min(source_verification, 1.0)
    
    def _evaluate_logical_consistency(self, research_results: Dict[str, Any]) -> float:
        """논리적 일관성을 평가합니다."""
        trends = research_results.get("trends", [])
        keywords = research_results.get("keywords", [])
        
        # 트렌드 일관성
        trend_consistency = 0.0
        if trends:
            # 트렌드 간의 일관성 확인
            trend_descriptions = [trend.get("description", "") for trend in trends]
            consistency_score = self._calculate_text_consistency(trend_descriptions)
            trend_consistency = consistency_score * 0.6
        
        # 키워드 일관성
        keyword_consistency = 0.0
        if keywords:
            # 고품질 키워드의 비율
            high_relevance_keywords = [k for k in keywords if k.get("relevance") == "high"]
            keyword_consistency = len(high_relevance_keywords) / len(keywords) * 0.4
        
        logical_consistency = trend_consistency + keyword_consistency
        return min(logical_consistency, 1.0)
    
    def _evaluate_data_freshness(self, research_results: Dict[str, Any]) -> float:
        """데이터 최신성을 평가합니다."""
        summary = research_results.get("summary", {})
        
        # 최신 결과의 비율 (2024년)
        recent_results = summary.get("recent_results", 0)
        total_results = summary.get("total_results", 1)
        
        if total_results == 0:
            return 0.5
        
        # 최신성 점수 계산
        recency_ratio = recent_results / total_results
        
        # 2024년 데이터가 70% 이상이면 높은 점수
        if recency_ratio >= 0.7:
            return 1.0
        elif recency_ratio >= 0.5:
            return 0.8
        elif recency_ratio >= 0.3:
            return 0.6
        else:
            return 0.4
    
    def _evaluate_completeness(self, research_results: Dict[str, Any]) -> float:
        """완성도를 평가합니다."""
        summary = research_results.get("summary", {})
        source_analysis = research_results.get("source_analysis", {})
        trends = research_results.get("trends", [])
        recommendations = research_results.get("recommendations", [])
        
        # 필수 구성 요소 확인
        required_components = [
            summary.get("total_results", 0) > 0,
            len(source_analysis) > 0,
            len(trends) > 0,
            len(recommendations) > 0
        ]
        
        # 완성도 점수 계산
        completeness_score = sum(required_components) / len(required_components)
        
        # 결과 수량 보너스
        total_results = summary.get("total_results", 0)
        if total_results >= 10:
            completeness_score += 0.1
        elif total_results >= 5:
            completeness_score += 0.05
        
        return min(completeness_score, 1.0)
    
    def _calculate_text_consistency(self, texts: List[str]) -> float:
        """텍스트 간의 일관성을 계산합니다."""
        if len(texts) < 2:
            return 1.0
        
        # 간단한 키워드 기반 일관성 계산
        all_keywords = set()
        for text in texts:
            words = text.lower().split()
            keywords = [w for w in words if len(w) > 4]
            all_keywords.update(keywords)
        
        # 공통 키워드 비율
        common_keywords = 0
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                words1 = set(texts[i].lower().split())
                words2 = set(texts[j].lower().split())
                common = len(words1.intersection(words2))
                total = len(words1.union(words2))
                if total > 0:
                    common_keywords += common / total
        
        if len(texts) < 2:
            return 1.0
        
        consistency = common_keywords / (len(texts) * (len(texts) - 1) / 2)
        return min(consistency, 1.0)
    
    def _generate_critic_feedback(self, research_results: Dict[str, Any], quality_score: float) -> Dict[str, Any]:
        """비평 피드백을 생성합니다."""
        feedback = {
            "overall_assessment": self._get_overall_assessment(quality_score),
            "strengths": self._identify_strengths(research_results),
            "weaknesses": self._identify_weaknesses(research_results, quality_score),
            "improvement_suggestions": self._generate_improvement_suggestions(research_results, quality_score),
            "detailed_evaluation": {}
        }
        
        # 각 품질 기준별 상세 평가
        if "error" not in research_results:
            feedback["detailed_evaluation"] = {
                "factual_accuracy": {
                    "score": self._evaluate_factual_accuracy(research_results),
                    "comment": "사실적 정확성 평가"
                },
                "source_verification": {
                    "score": self._evaluate_source_verification(research_results),
                    "comment": "출처 검증 평가"
                },
                "logical_consistency": {
                    "score": self._evaluate_logical_consistency(research_results),
                    "comment": "논리적 일관성 평가"
                },
                "data_freshness": {
                    "score": self._evaluate_data_freshness(research_results),
                    "comment": "데이터 최신성 평가"
                },
                "completeness": {
                    "score": self._evaluate_completeness(research_results),
                    "comment": "완성도 평가"
                }
            }
        
        return feedback
    
    def _get_overall_assessment(self, quality_score: float) -> str:
        """전체 품질에 대한 평가를 반환합니다."""
        if quality_score >= 0.9:
            return "우수한 품질의 연구 결과입니다."
        elif quality_score >= 0.8:
            return "양호한 품질의 연구 결과입니다."
        elif quality_score >= 0.7:
            return "적절한 품질의 연구 결과입니다."
        elif quality_score >= 0.6:
            return "개선이 필요한 연구 결과입니다."
        else:
            return "상당한 개선이 필요한 연구 결과입니다."
    
    def _identify_strengths(self, research_results: Dict[str, Any]) -> List[str]:
        """연구 결과의 강점을 식별합니다."""
        strengths = []
        
        if "error" in research_results:
            return ["에러 상황에서도 기본 구조를 유지함"]
        
        summary = research_results.get("summary", {})
        source_analysis = research_results.get("source_analysis", {})
        
        # 결과 수량
        total_results = summary.get("total_results", 0)
        if total_results >= 10:
            strengths.append("충분한 수의 검색 결과 확보")
        
        # 고품질 결과
        high_relevance_count = summary.get("high_relevance_count", 0)
        if high_relevance_count >= 5:
            strengths.append("높은 관련성을 가진 결과 다수 포함")
        
        # 소스 다양성
        if len(source_analysis) >= 3:
            strengths.append("다양한 소스에서 정보 수집")
        
        # 트렌드 분석
        trends = research_results.get("trends", [])
        if len(trends) >= 2:
            strengths.append("트렌드 분석을 통한 인사이트 제공")
        
        return strengths
    
    def _identify_weaknesses(self, research_results: Dict[str, Any], quality_score: float) -> List[str]:
        """연구 결과의 약점을 식별합니다."""
        weaknesses = []
        
        if "error" in research_results:
            return ["데이터 처리 중 오류 발생", "검색 결과 부족"]
        
        summary = research_results.get("summary", {})
        source_analysis = research_results.get("source_analysis", {})
        
        # 결과 수량
        total_results = summary.get("total_results", 0)
        if total_results < 5:
            weaknesses.append("검색 결과 수가 부족함")
        
        # 고품질 결과
        high_relevance_count = summary.get("high_relevance_count", 0)
        if high_relevance_count < 3:
            weaknesses.append("높은 관련성을 가진 결과가 부족함")
        
        # 소스 다양성
        if len(source_analysis) < 2:
            weaknesses.append("소스 다양성이 부족함")
        
        # 품질 점수
        if quality_score < QUALITY_THRESHOLDS["minimum_quality_score"]:
            weaknesses.append("전체적인 품질이 기준치에 미달함")
        
        return weaknesses
    
    def _generate_improvement_suggestions(self, research_results: Dict[str, Any], quality_score: float) -> List[str]:
        """개선 제안을 생성합니다."""
        suggestions = []
        
        if "error" in research_results:
            return ["검색 쿼리를 수정하여 재시도하세요", "데이터 소스 연결을 확인하세요"]
        
        summary = research_results.get("summary", {})
        source_analysis = research_results.get("source_analysis", {})
        
        # 결과 수량 개선
        total_results = summary.get("total_results", 0)
        if total_results < 10:
            suggestions.append("검색 범위를 확장하여 더 많은 결과를 수집하세요")
        
        # 소스 다양성 개선
        if len(source_analysis) < 3:
            suggestions.append("더 다양한 소스에서 정보를 수집하세요")
        
        # 품질 개선
        if quality_score < QUALITY_THRESHOLDS["excellent_quality_score"]:
            suggestions.append("검색 쿼리를 더 구체적으로 만들어 관련성을 높이세요")
            suggestions.append("최신 정보를 우선적으로 포함하도록 검색 범위를 조정하세요")
        
        return suggestions
    
    def _determine_approval_status(self, quality_score: float) -> str:
        """승인 상태를 결정합니다."""
        if quality_score >= QUALITY_THRESHOLDS["minimum_quality_score"]:
            return "approved"
        else:
            return "rejected"
    
    def _get_fallback_data(self) -> Dict[str, Any]:
        """폴백 데이터를 반환합니다."""
        return {
            "critic_feedback": {
                "overall_assessment": "평가를 수행할 수 없습니다.",
                "strengths": [],
                "weaknesses": ["데이터 부족으로 인한 평가 불가"],
                "improvement_suggestions": ["데이터를 다시 수집하여 재시도하세요"],
                "detailed_evaluation": {}
            },
            "approval_status": "rejected",
            "quality_score": 0.0
        }
