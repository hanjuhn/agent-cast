"""Script Writer Agent for creating podcast scripts from research content."""

import os
import anthropic
import argparse
from datetime import datetime
from dotenv import load_dotenv

from .base_agent import BaseAgent
try:
    from state import WorkflowState
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from state import WorkflowState

# --- 환경 변수 로드 ---
load_dotenv()  # .env 파일에서 환경 변수 로드

def read_research_file(filepath):
    """지정된 경로의 리서치 텍스트 파일을 읽어 내용을 반환합니다."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"오류: 파일을 찾을 수 없습니다 - {filepath}")
        return None
    except Exception as e:
        print(f"오류: 파일을 읽는 중 문제가 발생했습니다 - {e}")
        return None

def generate_podcast_script(research_content, api_key):
    """리서치 내용을 바탕으로 팟캐스트 대본을 생성합니다."""
    
    try:
        # 먼저 Anthropic API 시도
        print("Anthropic API로 팟캐스트 대본을 생성하는 중...")
        client = anthropic.Anthropic(api_key=api_key)
        
        # 프롬프트 구성
        prompt = f"""## 지시문
        아래의 리서치 결과를 바탕으로 2명의 화자가 정보를 알기 쉽게 전달하는 팟캐스트의 대본을 작성해주세요.
        앞뒤의 설명 없이 **대본**만 작성하면 됩니다.

        ## 제약조건
        - 대본의 분량은 5,000자 이상 6,000자 이하입니다.
        - 리서치의 결과를 최대한 활용하여 대본을 작성해주세요. (요약하지 마세요.)
        - 화자1이 진행자, 화자2가 리서치 역할을 합니다.
        - 화자1이 질문하고 화두를 던지면, 화자2가 답변하며 인사이트를 공유합니다.
        - 적절하게 감탄사나 반응하는 리액션도 넣습니다.
        - 출력포맷의 인물은 Joe와 Jane이라 부르지만 실제 대본에서는 서로를 김민열, 배한준이라는 이름으로 부릅니다.
        - 시작할 때 소개하는 팟캐스트의 제목은 "비타민 트렌드"입니다.

        ## 대본 구조 요구사항
        1. **인트로 (1-2분)**: 팟캐스트 소개, 호스트 소개, 이번 주 주제 개요
        2. **본론 (5-7분)**: 
           - 각 트렌드별로 2-3분씩 상세히 다루기
           - 구체적인 사례나 예시 포함
           - 실무 적용 방안이나 시사점 포함
           - 호스트 간 자연스러운 대화와 반응
        3. **결론 (1-2분)**: 전체 요약, 핵심 인사이트, 다음 주 예고

        ## 호스트 캐릭터 설정
        - **김민열 (진행자)**: AI에 관심은 많지만 전문가는 아닌 일반인 관점, 궁금한 것을 잘 묻는 호기심 많은 성격
        - **배한준 (리서치)**: AI 분야 전문가, 깊이 있는 분석과 실무 경험을 바탕으로 한 인사이트 제공

        ## 리서치 결과
        {research_content}

        ## 출력 포맷
        Joe: ...
        Jane: ...
        Joe: ..."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        if response.content and len(response.content) > 0:
            return response.content[0].text
        else:
            print("오류: 대본 생성에 실패했습니다.")
            return None
            
    except Exception as e:
        print(f"Anthropic API 실패: {e}")
        
        # Anthropic API 실패 시 GPT로 폴백
        if "Overloaded" in str(e) or "529" in str(e):
            print("Anthropic API 과부하, GPT로 대체 시도...")
            try:
                from openai import OpenAI
                
                openai_api_key = os.environ.get('OPENAI_API_KEY')
                if not openai_api_key:
                    print("OPENAI_API_KEY가 설정되지 않음")
                    return None
                
                client = OpenAI(api_key=openai_api_key)
                
                gpt_prompt = f"""다음 리서치 결과를 바탕으로 자연스러운 대화형 팟캐스트 대본을 작성해주세요.

리서치 결과:
{research_content}

요구사항:
1. 진행자 김민열과 AI 전문가 배한준의 대화형으로 구성
2. 자연스럽고 이해하기 쉬운 설명
3. 구체적인 예시와 인사이트 포함
4. 5000-6000자 정도의 적당한 길이
5. 한국어로 작성
6. 팟캐스트 제목은 "비타민 트렌드"

대본을 작성해주세요:"""
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "당신은 AI 기술 동향에 정통한 팟캐스트 대본 작가입니다."},
                        {"role": "user", "content": gpt_prompt}
                    ],
                    max_tokens=4000,
                    temperature=0.7
                )
                
                podcast_script = response.choices[0].message.content.strip()
                print("GPT를 사용한 대본 생성 성공")
                return podcast_script
                
            except Exception as gpt_error:
                print(f"GPT 대본 생성도 실패: {gpt_error}")
                return None
        
        print(f"오류: 대본 생성 중 문제가 발생했습니다 - {e}")
        return None

def save_script_to_file(script_content, output_filename="podcast_script.txt"):
    """생성된 대본을 파일로 저장합니다."""
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(script_content)
        print(f"대본이 '{output_filename}' 파일로 저장되었습니다.")
        return True
    except Exception as e:
        print(f"오류: 파일 저장 중 문제가 발생했습니다 - {e}")
        return False

class ScriptWriterAgent(BaseAgent):
    """팟캐스트 대본 생성 에이전트"""
    
    def __init__(self, api_key: str = None):
        super().__init__(
            name="script_writer",
            description="리서치 결과를 바탕으로 팟캐스트 대본을 생성하는 에이전트"
        )
        self.required_inputs = ["research_result"]
        self.output_keys = ["podcast_script", "script_metadata"]
        self.api_key = api_key
    
    def _generate_with_gpt(self, state: WorkflowState) -> str:
        """OpenAI GPT를 사용하여 팟캐스트 대본을 생성합니다."""
        try:
            from openai import OpenAI
            
            research_result = getattr(state, 'research_result', '')
            personal_info = getattr(state, 'personal_info', {})
            
            # OpenAI API 키 확인
            openai_api_key = os.environ.get('OPENAI_API_KEY')
            if not openai_api_key:
                self.log_execution("OPENAI_API_KEY가 설정되지 않음", "ERROR")
                return None
            
            client = OpenAI(api_key=openai_api_key)
            
            # GPT 프롬프트 구성
            prompt = f"""다음 리서치 결과를 바탕으로 자연스러운 대화형 팟캐스트 대본을 작성해주세요.

리서치 결과:
{research_result}

개인 정보:
{personal_info}

요구사항:
1. 진행자 김민열과 AI 전문가 배한준의 대화형으로 구성
2. 자연스럽고 이해하기 쉬운 설명
3. 구체적인 예시와 인사이트 포함
4. 3000-5000자 정도의 적당한 길이
5. 한국어로 작성

대본을 작성해주세요:"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 AI 기술 동향에 정통한 팟캐스트 대본 작가입니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.7
            )
            
            podcast_script = response.choices[0].message.content.strip()
            self.log_execution("GPT를 사용한 대본 생성 성공", "INFO")
            return podcast_script
            
        except Exception as e:
            self.log_execution(f"GPT 대본 생성 실패: {e}", "ERROR")
            return None
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """리서치 결과를 바탕으로 팟캐스트 대본을 생성합니다."""
        self.log_execution("팟캐스트 대본 생성 시작")
        
        try:
            # 입력 검증
            if not self.validate_inputs(state):
                raise ValueError("필수 입력이 누락되었습니다.")
            
            # 리서치 결과 가져오기
            research_result = getattr(state, 'research_result', '')
            if not research_result:
                raise ValueError("대본 생성할 리서치 결과가 없습니다.")
            
            # API 키 확인
            if not self.api_key:
                self.api_key = os.environ.get("ANTHROPIC_API_KEY")
                if not self.api_key:
                    raise ValueError("Anthropic API 키가 필요합니다.")
            
            # 팟캐스트 대본 생성
            podcast_script = generate_podcast_script(research_result, self.api_key)
            
            if not podcast_script:
                raise ValueError("팟캐스트 대본 생성에 실패했습니다.")
            
            # 결과 저장
            output_filename = f"output/script_writer/podcast_script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            os.makedirs(os.path.dirname(output_filename), exist_ok=True)
            save_script_to_file(podcast_script, output_filename)
            
            # 워크플로우 상태 업데이트
            state_dict = {k: v for k, v in state.__dict__.items()}
            if 'podcast_script' in state_dict:
                del state_dict['podcast_script']
            if 'script_metadata' in state_dict:
                del state_dict['script_metadata']
            
            new_state = WorkflowState(
                **state_dict,
                podcast_script=podcast_script,
                script_metadata={
                    "script_length": len(podcast_script),
                    "output_file": output_filename,
                    "generated_at": datetime.now().isoformat()
                }
            )
            
            # 워크플로우 상태 업데이트
            new_state = self.update_workflow_status(new_state, "script_writer_completed")
            
            self.log_execution(f"팟캐스트 대본 생성 완료: {len(podcast_script)}자")
            return new_state
            
        except Exception as e:
            self.log_execution(f"팟캐스트 대본 생성 중 오류 발생: {str(e)}", "ERROR")
            
            # Anthropic API 과부하 시 GPT 사용
            if "Overloaded" in str(e) or "529" in str(e):
                self.log_execution("Anthropic API 과부하, GPT로 대체 시도", "WARNING")
                try:
                    podcast_script = self._generate_with_gpt(state)
                    if podcast_script:
                        # 결과 저장
                        output_filename = f"output/script_writer/podcast_script_gpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
                        save_script_to_file(podcast_script, output_filename)
                        
                        # 워크플로우 상태 업데이트
                        state_dict = {k: v for k, v in state.__dict__.items()}
                        if 'podcast_script' in state_dict:
                            del state_dict['podcast_script']
                        if 'script_metadata' in state_dict:
                            del state_dict['script_metadata']
                        
                        new_state = WorkflowState(
                            **state_dict,
                            podcast_script=podcast_script,
                            script_metadata={
                                "script_length": len(podcast_script),
                                "output_file": output_filename,
                                "generated_at": datetime.now().isoformat(),
                                "status": "gpt_fallback"
                            }
                        )
                        
                        new_state = self.update_workflow_status(new_state, "script_writer_completed")
                        self.log_execution(f"GPT 대본 생성 완료: {len(podcast_script)}자")
                        return new_state
                except Exception as gpt_error:
                    self.log_execution(f"GPT 생성도 실패: {gpt_error}", "ERROR")
            
            raise

def main():
    """
    메인 실행 함수
    """
    print("🚀 팟캐스트 대본 생성 파이프라인 시작")
    print("=" * 50)
    
    # 1. 명령행 인자 설정
    parser = argparse.ArgumentParser(description="리서치 결과를 바탕으로 팟캐스트 대본을 생성합니다.")
    parser.add_argument("research_file", type=str, help="리서치 결과 텍스트 파일의 경로")
    parser.add_argument("--output", "-o", type=str, default="podcast_script.txt", 
                       help="출력 파일명 (기본값: podcast_script.txt)")
    parser.add_argument("--api-key", type=str, help="Anthropic API 키")
    args = parser.parse_args()

    # 2. 리서치 파일 읽기
    print("\n1️⃣ 리서치 파일 읽기 중...")
    research_content = read_research_file(args.research_file)
    if not research_content:
        print("❌ 리서치 파일 읽기 실패로 프로그램을 종료합니다.")
        return

    # 3. API 키 설정
    print("\n2️⃣ API 키 설정 중...")
    api_key = args.api_key or os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
        return

    # 4. 팟캐스트 대본 생성
    print("\n3️⃣ 팟캐스트 대본 생성 중...")
    script_content = generate_podcast_script(research_content, api_key)
    if not script_content:
        print("❌ 대본 생성 실패로 프로그램을 종료합니다.")
        return

    # 5. 결과 저장
    print("\n4️⃣ 결과 저장 중...")
    if save_script_to_file(script_content, args.output):
        print(f"\n✅ 팟캐스트 대본 생성 파이프라인 완료!")
        print(f"📊 생성된 대본 길이: {len(script_content)}자")
        print(f"💾 저장된 파일: {args.output}")
        
        # 대본 미리보기 출력
        print(f"\n📋 대본 미리보기 (처음 500자):")
        print("-" * 50)
        print(script_content[:500] + "..." if len(script_content) > 500 else script_content)
        print("-" * 50)
    else:
        print("❌ 결과 저장 실패")

if __name__ == "__main__":
    main()
