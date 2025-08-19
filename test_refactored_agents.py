"""리팩토링된 에이전트들의 통합 테스트 스크립트."""

import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env 파일 로드 완료")
except ImportError:
    print("⚠️ python-dotenv가 설치되지 않음. pip install python-dotenv")
except Exception as e:
    print(f"⚠️ .env 파일 로드 실패: {e}")

# 환경변수 확인
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    print(f"✅ OPENAI_API_KEY 확인됨: {openai_key[:10]}...")
else:
    print("❌ OPENAI_API_KEY 환경변수 없음")

# 이제 절대 임포트 사용
from agents.personalize_agent import PersonalizeAgent
from agents.query_writer_agent import QueryWriterAgent
from state import WorkflowState


async def test_personalize_agent():
    """PersonalizeAgent 테스트."""
    print("=== PersonalizeAgent 테스트 시작 ===")
    
    # 에이전트 초기화
    agent = PersonalizeAgent()
    
    # 초기 상태 생성
    state = WorkflowState(
        user_query="AI 연구 동향에 대해 알려주세요",
        workflow_status={
            "current_step": "initialized",
            "completed_steps": 0,
            "total_steps": 8,
            "status": "running",
            "errors": [],
            "warnings": []
        }
    )
    
    try:
        # 에이전트 실행
        updated_state = await agent.process(state)
        
        print("✅ PersonalizeAgent 실행 성공")
        print(f"개인 정보: {updated_state.personal_info}")
        print(f"연구 컨텍스트: {updated_state.research_context}")
        print(f"현재 진행상황: {updated_state.current_progress}")
        
        return updated_state
        
    except Exception as e:
        print(f"❌ PersonalizeAgent 실행 실패: {e}")
        raise


async def test_query_writer_agent(personalize_state):
    """QueryWriterAgent 테스트."""
    print("\n=== QueryWriterAgent 테스트 시작 ===")
    
    # 에이전트 초기화
    agent = QueryWriterAgent()
    
    try:
        # 에이전트 실행
        updated_state = await agent.process(personalize_state)
        
        print("✅ QueryWriterAgent 실행 성공")
        print(f"RAG 쿼리: {updated_state.rag_query}")
        print(f"검색 범위: {updated_state.search_scope}")
        print(f"연구 우선순위: {updated_state.research_priorities}")
        
        return updated_state
        
    except Exception as e:
        print(f"❌ QueryWriterAgent 실행 실패: {e}")
        raise


async def test_full_pipeline():
    """전체 파이프라인 테스트."""
    print("=== 전체 파이프라인 테스트 시작 ===")
    
    # OpenAI API 키 확인
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("테스트는 계속 진행하지만, LLM 기능은 폴백 모드로 실행됩니다.")
    
    try:
        # 1단계: PersonalizeAgent 테스트
        personalize_state = await test_personalize_agent()
        
        # 2단계: QueryWriterAgent 테스트
        final_state = await test_query_writer_agent(personalize_state)
        
        print("\n=== 전체 파이프라인 테스트 완료 ===")
        print("✅ 모든 에이전트가 성공적으로 실행되었습니다!")
        
        # 최종 결과 요약
        print("\n=== 최종 결과 요약 ===")
        print(f"워크플로우 단계: {final_state.workflow_status['current_step']}")
        print(f"완료된 단계: {final_state.workflow_status['completed_steps']}")
        print(f"주요 검색 쿼리: {final_state.rag_query.get('primary_queries', [])[:2]}")
        print(f"연구 키워드: {final_state.personal_info.get('research_keywords', [])[:3]}")
        
    except Exception as e:
        print(f"\n❌ 파이프라인 테스트 실패: {e}")
        raise


if __name__ == "__main__":
    # 환경변수 설정 (선택사항)
    # os.environ["OPENAI_API_KEY"] = "your-api-key-here"
    
    # 테스트 실행
    asyncio.run(test_full_pipeline())
