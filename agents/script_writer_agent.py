"""Script Writer Agent for creating podcast scripts from research content."""

import os
import anthropic
import argparse
from datetime import datetime
from dotenv import load_dotenv

from .base_agent import BaseAgent
from state.state import WorkflowState
from constants import OPENAI_SCRIPT_WRITER_PARAMS, ANTHROPIC_SCRIPT_WRITER_PARAMS, OPENAI_SCRIPT_WRITER_FALLBACK_PARAMS
from constants.prompts import PODCAST_SCRIPT_WRITER_DETAILED_PROMPT, SCRIPT_WRITER_SYSTEM_PROMPT

# --- 환경 변수 로드 ---
load_dotenv()  # .env 파일에서 환경 변수 로드

def read_research_file(file_path: str) -> str:
    """리서치 결과 파일을 읽습니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"파일 읽기 오류: {e}")
        return None

def generate_podcast_script(research_content: str, api_key: str) -> str:
    """리서치 결과를 바탕으로 팟캐스트 대본을 생성합니다."""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-5-sonnet",
            max_tokens=4000,
            temperature=0.7,
            messages=[
                {
                    "role": "user",
                    "content": PODCAST_SCRIPT_WRITER_DETAILED_PROMPT.format(research_content=research_content)
                }
            ]
        )
        return response.content[0].text
    except Exception as e:
        print(f"Anthropic API 대본 생성 실패: {e}")
        print("GPT fallback 시도 중...")
        
        # GPT fallback
        try:
            from openai import OpenAI
            
            openai_api_key = os.environ.get('OPENAI_API_KEY')
            if not openai_api_key:
                print("OPENAI_API_KEY가 설정되지 않음")
                return None
            
            client = OpenAI(api_key=openai_api_key)
            
            prompt = PODCAST_SCRIPT_WRITER_DETAILED_PROMPT.format(research_content=research_content)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SCRIPT_WRITER_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
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

def save_script_to_file(script_content: str, output_file: str) -> bool:
    """생성된 대본을 파일로 저장합니다."""
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(script_content)
        return True
    except Exception as e:
        print(f"파일 저장 오류: {e}")
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
            prompt = PODCAST_SCRIPT_WRITER_DETAILED_PROMPT.format(research_content=f"리서치 결과:\n{research_result}\n\n개인 정보:\n{personal_info}")
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SCRIPT_WRITER_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=OPENAI_SCRIPT_WRITER_FALLBACK_PARAMS["max_tokens"],
                temperature=OPENAI_SCRIPT_WRITER_FALLBACK_PARAMS["temperature"]
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
            
            # Anthropic API 실패 시 GPT 사용
            if "not_found_error" in str(e) or "Overloaded" in str(e) or "529" in str(e):
                self.log_execution("Anthropic API 실패, GPT로 대체 시도", "WARNING")
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
