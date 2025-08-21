"""HippoRAG Search Agent for retrieving documents from indexed knowledge graph."""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 로컬 HippoRAG 경로 추가
project_root = Path(__file__).parent.parent
hipporag_src_path = project_root / "HippoRAG" / "src"
sys.path.insert(0, str(hipporag_src_path))


class HippoRAGSearchAgent:
    """인덱싱된 HippoRAG 결과에서 문서를 검색하는 에이전트."""
    
    def __init__(self, save_dir: str = "outputs/hipporag_indexing"):
        self.name = "HippoRAGSearchAgent"
        self.description = "인덱싱된 HippoRAG 결과에서 문서를 검색하는 에이전트"
        
        # HippoRAG 설정
        self.save_dir = save_dir
        self.llm_model_name = "gpt-4o-mini"
        self.embedding_model_name = "text-embedding-3-small"
        self.hipporag_instance = None
        
    def load_hipporag_instance(self):
        """저장된 HippoRAG 인스턴스를 로드합니다."""
        if not os.path.exists(self.save_dir):
            return None
        
        try:
            from hipporag import HippoRAG
            
            hipporag = HippoRAG(
                save_dir=self.save_dir,
                llm_model_name=self.llm_model_name,
                embedding_model_name=self.embedding_model_name
            )
            
            if hasattr(hipporag, 'ready_to_retrieve') and not hipporag.ready_to_retrieve:
                hipporag.prepare_retrieval_objects()
            
            self.hipporag_instance = hipporag
            return hipporag
            
        except Exception as e:
            return None
    
    def search_documents(self, queries: List[str], num_to_retrieve: int = 5) -> List[Dict[str, Any]]:
        """쿼리로 문서를 검색합니다."""
        if not self.hipporag_instance:
            return []
        
        try:
            retrieval_results = self.hipporag_instance.retrieve(
                queries=queries,
                num_to_retrieve=num_to_retrieve
            )
            
            search_results = []
            for result in retrieval_results:
                query_result = {
                    "query": result.question,
                    "documents": [],
                    "scores": []
                }
                
                for j, (doc, score) in enumerate(zip(result.docs, result.doc_scores)):
                    query_result["documents"].append({
                        "rank": j + 1,
                        "content": doc,
                        "score": float(score)
                    })
                    query_result["scores"].append(float(score))
                
                search_results.append(query_result)
            
            return search_results
            
        except Exception as e:
            return []
    
    def search_single_query(self, query: str, num_to_retrieve: int = 5) -> Dict[str, Any]:
        """단일 쿼리로 문서를 검색합니다."""
        results = self.search_documents([query], num_to_retrieve)
        return results[0] if results else {"query": query, "documents": [], "scores": []}
    
    def get_graph_info(self) -> Dict[str, Any]:
        """그래프 정보를 반환합니다."""
        if not self.hipporag_instance:
            return {"error": "HippoRAG 인스턴스가 로드되지 않았습니다."}
        
        try:
            graph_info = self.hipporag_instance.get_graph_info()
            return graph_info
        except Exception as e:
            return {"error": f"그래프 정보 조회 실패: {e}"}
    
    def run(self, queries: List[str], num_to_retrieve: int = 5):
        """에이전트를 실행합니다."""
        if not self.hipporag_instance:
            if not self.load_hipporag_instance():
                return None
        
        search_results = self.search_documents(queries, num_to_retrieve)
        return search_results if search_results else None


def main():
    """메인 함수 - 독립 실행용
    - 쿼리 여러개 넣어도 됨. 
    - top-k 지정할 수 있음.
    """
    # 에이전트 생성
    agent = HippoRAGSearchAgent()
    
    # 테스트 쿼리
    test_queries = [
        "AI 최적화 방법과 MoE 아키텍처, Gemma 3에 대한 최신 연구 동향과 논문"
    ]
    
    # 에이전트 실행
    results = agent.run(test_queries, num_to_retrieve=5)
    
    if results:
        # JSON 파일로 저장
        output_file = "search_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # 결과 요약 출력
        for i, result in enumerate(results):
            print(f"쿼리 {i+1}: '{result['query']}' -> {len(result['documents'])}개 문서 검색됨")
            print(f"결과가 {output_file}에 저장되었습니다.")


if __name__ == "__main__":
    main()
