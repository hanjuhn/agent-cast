"""HippoRAG Indexing Agent for creating knowledge graphs from crawled data."""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 로컬 HippoRAG 경로 추가
project_root = Path(__file__).parent.parent
hipporag_src_path = project_root / "HippoRAG" / "src"
sys.path.insert(0, str(hipporag_src_path))


class HippoRAGIndexingAgent:
    """크롤링 데이터를 HippoRAG로 인덱싱하여 지식 그래프를 생성하는 에이전트."""
    
    def __init__(self):
        self.name = "HippoRAGIndexingAgent"
        self.description = "크롤링 데이터를 HippoRAG로 인덱싱하여 지식 그래프를 생성하는 에이전트"
        
        # HippoRAG 설정
        self.save_dir = "outputs/hipporag_indexing"
        self.llm_model_name = "gpt-4o-mini"
        self.embedding_model_name = "text-embedding-3-small"
    
    def load_documents_from_file(self, file_path: str):
        """크롤링 결과에서 content만 추출하여 로드합니다."""
        print("=== 크롤링 결과 로드 ===")
        
        if not os.path.exists(file_path):
            print(f"❌ 파일이 없습니다: {file_path}")
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            search_results = json.load(f)
        
        # content 키만 추출
        documents = []
        for result in search_results:
            if 'content' in result:
                documents.append(result['content'])
        
        print(f"📁 {len(documents)}개 문서 로드됨 (크롤링 결과에서 content 추출)")
        
        for i, doc in enumerate(documents):
            print(f"  문서 {i+1}: {len(doc)} 문자")
        
        return documents
    
    def create_hipporag_index(self, documents):
        """HippoRAG 인덱스를 생성합니다."""
        print("=== HippoRAG 인덱싱 시작 ===")
        
        try:
            # 로컬 HippoRAG import
            print("🔍 로컬 HippoRAG import 시도...")
            from hipporag import HippoRAG
            print("✅ 로컬 HippoRAG import 성공!")
            
            # 저장 디렉토리 생성
            os.makedirs(self.save_dir, exist_ok=True)
            
            # HippoRAG 인스턴스 생성
            print(f"🔧 HippoRAG 설정:")
            print(f"  저장 디렉토리: {self.save_dir}")
            print(f"  LLM 모델: {self.llm_model_name}")
            print(f"  임베딩 모델: {self.embedding_model_name}")
            print(f"  문서 수: {len(documents)}")
            
            hipporag = HippoRAG(
                save_dir=self.save_dir,
                llm_model_name=self.llm_model_name,
                embedding_model_name=self.embedding_model_name
            )
            
            print("✅ HippoRAG 인스턴스 생성 성공!")
            
            # 인덱싱 실행
            print(f"📚 인덱싱 시작... ({len(documents)}개 문서)")
            hipporag.index(docs=documents)
            print("✅ 인덱싱 완료!")
            
            # 저장 디렉토리 확인
            if os.path.exists(self.save_dir):
                files = os.listdir(self.save_dir)
                print(f"📁 저장된 파일들: {files}")
                
                # 파일 크기 확인
                total_size = 0
                for file in files:
                    file_path = os.path.join(self.save_dir, file)
                    if os.path.isfile(file_path):
                        size = os.path.getsize(file_path)
                        total_size += size
                        print(f"  {file}: {size} bytes")
                
                print(f"📊 총 저장 크기: {total_size} bytes")
            
            # 그래프 정보 확인
            try:
                graph_info = hipporag.get_graph_info()
                print(f"📊 그래프 정보: {graph_info}")
            except Exception as e:
                print(f"⚠️  그래프 정보 조회 실패: {e}")
            
            return hipporag
            
        except ImportError as e:
            print(f"❌ 로컬 HippoRAG import 실패: {e}")
            print("💡 로컬 HippoRAG 폴더 구조를 확인해주세요.")
            return None
        except Exception as e:
            print(f"❌ HippoRAG 인덱싱 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run(self, crawled_data_path: str):
        """에이전트를 실행합니다."""
        print("🚀 HippoRAG Indexing Agent 시작")
        
        # 문서 로드
        documents = self.load_documents_from_file(crawled_data_path)
        
        if not documents:
            print("❌ 문서가 없어서 인덱싱을 건너뜁니다.")
            return None
        
        # HippoRAG 인덱싱 수행
        hipporag_instance = self.create_hipporag_index(documents)
        
        if hipporag_instance:
            print("🎉 HippoRAG 인덱싱 완료!")
            return hipporag_instance
        else:
            print("❌ HippoRAG 인덱싱 실패!")
            return None


def main():
    """메인 함수 - 독립 실행용"""
    print("🚀 HippoRAG Indexing Agent 독립 실행")
    
    # 에이전트 생성
    agent = HippoRAGIndexingAgent()
    
    # 크롤링 데이터 경로
    crawled_data_path = "crawled_data/filtered_data.json"
    
    # 에이전트 실행
    result = agent.run(crawled_data_path)
    
    if result:
        print("✅ 에이전트 실행 성공!")
    else:
        print("❌ 에이전트 실행 실패!")


if __name__ == "__main__":
    main() 