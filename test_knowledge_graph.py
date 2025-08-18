"""Test script for Knowledge Graph and KG Search agents."""

import asyncio
import json
import logging
from typing import Dict, List, Any

from agents.knowledge_graph_agent import KnowledgeGraphAgent
from agents.kg_search_agent import KGSearchAgent
from state import WorkflowState

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_knowledge_graph_agent():
    """Test the Knowledge Graph Agent."""
    print("=== Testing Knowledge Graph Agent ===")
    
    # 샘플 크롤링 데이터 생성
    sample_documents = [
        {
            "id": "doc_1",
            "title": "OpenAI Releases GPT-4 Turbo",
            "content": "OpenAI has released GPT-4 Turbo, a more powerful version of their language model. The new model shows significant improvements in reasoning and coding capabilities. Researchers at OpenAI collaborated with Microsoft to develop this model.",
            "url": "https://openai.com/blog/gpt-4-turbo",
            "timestamp": "2024-01-15T10:00:00Z"
        },
        {
            "id": "doc_2", 
            "title": "Google Introduces Gemini Pro",
            "content": "Google has introduced Gemini Pro, their latest AI model. The model demonstrates advanced multimodal capabilities and is being used by researchers at Google DeepMind. This represents a significant advancement in AI technology.",
            "url": "https://ai.google.dev/gemini",
            "timestamp": "2024-01-16T14:30:00Z"
        },
        {
            "id": "doc_3",
            "title": "Anthropic's Claude 3 Research",
            "content": "Anthropic researchers have published new findings on Claude 3's capabilities. The research team, led by Dr. Sarah Chen, discovered novel approaches to AI safety and alignment. Their work has implications for the broader AI research community.",
            "url": "https://anthropic.com/research",
            "timestamp": "2024-01-17T09:15:00Z"
        }
    ]
    
    # 워크플로우 상태 생성
    state = WorkflowState()
    state.set("crawled_documents", sample_documents)
    
    # Knowledge Graph Agent 초기화 및 실행
    try:
        kg_agent = KnowledgeGraphAgent()
        await kg_agent.initialize()
        
        # 지식 그래프 구축
        result_state = await kg_agent.process(state)
        
        # 결과 확인
        knowledge_graph = result_state.get("knowledge_graph", {})
        document_store = result_state.get("document_store", {})
        
        print(f"✅ Knowledge Graph built successfully!")
        print(f"📊 Entities: {knowledge_graph.get('metadata', {}).get('entity_count', 0)}")
        print(f"🔗 Relationships: {knowledge_graph.get('metadata', {}).get('relationship_count', 0)}")
        print(f"📄 Documents: {len(document_store)}")
        
        # 엔티티 및 관계 출력
        entities = knowledge_graph.get("entities", {})
        relationships = knowledge_graph.get("relationships", [])
        
        print("\n📋 Entities found:")
        for entity_id, entity in list(entities.items())[:5]:  # 상위 5개만 출력
            print(f"  - {entity.get('name', 'Unknown')} ({entity.get('type', 'Unknown')})")
        
        print(f"\n🔗 Relationships found: {len(relationships)}")
        
        return result_state
        
    except Exception as e:
        logger.error(f"Error testing Knowledge Graph Agent: {e}")
        return None


async def test_kg_search_agent(state: WorkflowState):
    """Test the KG Search Agent."""
    print("\n=== Testing KG Search Agent ===")
    
    # 샘플 쿼리 작성자 출력 생성
    query_writer_output = {
        "queries": [
            {
                "query": "OpenAI GPT-4 Turbo capabilities",
                "type": "technology"
            },
            {
                "query": "Google Gemini Pro research",
                "type": "technology"
            },
            {
                "query": "AI safety research Anthropic",
                "type": "research"
            }
        ]
    }
    
    # 상태에 쿼리 추가
    state.set("query_writer_output", query_writer_output)
    
    # KG Search Agent 초기화 및 실행
    try:
        kg_search_agent = KGSearchAgent()
        await kg_search_agent.initialize()
        
        # 지식 그래프 검색
        result_state = await kg_search_agent.process(state)
        
        # 결과 확인
        search_results = result_state.get("kg_search_results", [])
        
        print(f"✅ KG Search completed successfully!")
        print(f"🔍 Search queries processed: {len(search_results)}")
        
        # 검색 결과 출력
        for i, search_result in enumerate(search_results, 1):
            query = search_result.get("query", "")
            results = search_result.get("results", [])
            print(f"\n📝 Query {i}: {query}")
            print(f"   Results found: {len(results)}")
            
            for j, result in enumerate(results[:3], 1):  # 상위 3개 결과만 출력
                title = result.get("title", "No title")
                score = result.get("score", 0.0)
                entities = result.get("entities", [])
                print(f"   {j}. {title} (Score: {score:.3f})")
                print(f"      Entities: {len(entities)} found")
        
        return result_state
        
    except Exception as e:
        logger.error(f"Error testing KG Search Agent: {e}")
        return None


async def test_advanced_features():
    """Test advanced features of the knowledge graph agents."""
    print("\n=== Testing Advanced Features ===")
    
    try:
        # Knowledge Graph Agent 생성
        kg_agent = KnowledgeGraphAgent()
        await kg_agent.initialize()
        
        # KG Search Agent 생성
        kg_search_agent = KGSearchAgent()
        await kg_search_agent.initialize()
        
        # 1. 엔티티별 검색 테스트
        print("\n🔍 Testing entity-based search...")
        entity_results = await kg_search_agent.search_by_entity("OpenAI", "organization")
        print(f"   Found {len(entity_results)} results for OpenAI")
        
        # 2. 트렌딩 토픽 테스트
        print("\n📈 Testing trending topics...")
        trending = await kg_search_agent.get_trending_topics("7d")
        print(f"   Found {len(trending)} trending topics")
        
        # 3. 검색 통계 테스트
        print("\n📊 Testing search statistics...")
        stats = kg_search_agent.get_search_statistics()
        print(f"   Search statistics: {stats}")
        
        # 4. 지식 그래프 통계 테스트
        print("\n📋 Testing knowledge graph statistics...")
        kg_stats = kg_agent.get_knowledge_graph_stats()
        print(f"   Knowledge graph stats: {kg_stats}")
        
    except Exception as e:
        logger.error(f"Error testing advanced features: {e}")


async def main():
    """Main test function."""
    print("🚀 Starting Knowledge Graph Agent Tests")
    print("=" * 50)
    
    # 1. Knowledge Graph Agent 테스트
    state = await test_knowledge_graph_agent()
    
    if state:
        # 2. KG Search Agent 테스트
        await test_kg_search_agent(state)
        
        # 3. 고급 기능 테스트
        await test_advanced_features()
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main()) 