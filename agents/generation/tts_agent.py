"""TTS Agent for converting podcast scripts to audio using TTS."""

import os
from tqdm import tqdm
from datetime import datetime
from openai import OpenAI

from ..base_agent import BaseAgent
from state.state import WorkflowState
from constants.prompts import TTS_SYSTEM_PROMPT





class TTSAgent(BaseAgent):
    """팟캐스트 오디오 생성 에이전트"""
    
    def __init__(self, api_key: str = None):
        super().__init__(
            name="tts",
            description="팟캐스트 오디오 생성 에이전트"
        )
        self.required_inputs = ["podcast_script"]
        self.output_keys = ["audio_file", "audio_metadata"]
        self.api_key = api_key
    
    def _split_script_into_chunks(self, script_text: str) -> list:
        """스크립트 텍스트를 API 제한에 맞는 청크로 분할합니다."""
        self.log_execution("스크립트를 청크 단위로 나누는 중...")
        MAX_BYTES = 4500
        final_chunks = []
        current_chunk = ""
        dialogue_turns = script_text.strip().split('\n\n')

        for turn in tqdm(dialogue_turns):
            if len((current_chunk + turn).encode('utf-8')) > MAX_BYTES:
                if current_chunk:
                    final_chunks.append(current_chunk)
                current_chunk = turn
            else:
                if current_chunk:
                    current_chunk += "\n\n" + turn
                else:
                    current_chunk = turn
        
        if current_chunk:
            final_chunks.append(current_chunk)
            
        self.log_execution(f"총 {len(final_chunks)}개의 청크로 분할되었습니다.")
        return final_chunks
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """팟캐스트 대본을 오디오로 변환합니다."""
        self.log_execution("팟캐스트 오디오 생성 시작")
        
        try:
            # 입력 검증
            if not self.validate_inputs(state):
                raise ValueError("필수 입력이 누락되었습니다.")
            
            # 팟캐스트 대본 가져오기
            podcast_script = getattr(state, 'podcast_script', '')
            if not podcast_script:
                raise ValueError("변환할 팟캐스트 대본이 없습니다.")
            
            # 스크립트 분할
            final_chunks = self._split_script_into_chunks(podcast_script)
            
            # 오디오 생성 (OpenAI TTS 사용)
            audio_segments = []
            
            try:
                # OpenAI TTS API 사용
                from openai import OpenAI
                
                openai_api_key = os.environ.get('OPENAI_API_KEY')
                if not openai_api_key:
                    self.log_execution("OPENAI_API_KEY가 설정되지 않음, 텍스트 파일만 생성", "WARNING")
                    raise ValueError("OPENAI_API_KEY 없음")
                
                client = OpenAI(api_key=openai_api_key)
                
                for chunk in tqdm(final_chunks, desc="오디오 생성 중"):
                    try:
                        # OpenAI TTS API 호출
                        response = client.audio.speech.create(
                            model="tts-1",
                            voice="alloy",  # 또는 "echo", "fable", "onyx", "nova", "shimmer"
                            input=chunk
                        )
                        
                        # 오디오 데이터 추가
                        audio_segments.append(response.content)
                        
                    except Exception as e:
                        self.log_execution(f"청크 처리 중 오류 발생: {e}", "WARNING")
                        continue
                        
            except Exception as e:
                self.log_execution(f"OpenAI TTS API 실패: {e}", "WARNING")
                self.log_execution("TTS API 실패로 텍스트 파일만 생성", "INFO")
            
            # 오디오 병합 및 저장 (폴백 포함)
            if audio_segments:
                # 오디오 생성 성공
                combined_audio_data = b''.join(audio_segments)
                output_filename = f"output/tts/podcast_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                
                # 디렉토리 생성
                os.makedirs(os.path.dirname(output_filename), exist_ok=True)
                
                # MP3 파일로 저장
                with open(output_filename, 'wb') as f:
                    f.write(combined_audio_data)
                
                # 워크플로우 상태 업데이트
                state_dict = {k: v for k, v in state.__dict__.items()}
                if 'audio_file' in state_dict:
                    del state_dict['audio_file']
                if 'audio_metadata' in state_dict:
                    del state_dict['audio_metadata']
                
                new_state = WorkflowState(
                    **state_dict,
                    audio_file=output_filename,
                    audio_metadata={
                        "chunks_processed": len(final_chunks),
                        "audio_segments": len(audio_segments),
                        "output_file": output_filename,
                        "status": "success"
                    }
                )
                
                # 워크플로우 상태 업데이트
                new_state = self.update_workflow_status(new_state, "tts_completed")
                
                self.log_execution(f"팟캐스트 오디오 생성 완료: {output_filename}")
                return new_state
            else:
                # 오디오 생성 실패 시 텍스트 파일만 생성
                self.log_execution("오디오 생성 실패, 텍스트 파일만 생성", "WARNING")
                
                # 텍스트 파일로 저장
                text_output_filename = f"output/tts/podcast_script_for_tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(text_output_filename, 'w', encoding='utf-8') as f:
                    f.write(podcast_script)
                
                # 워크플로우 상태 업데이트
                state_dict = {k: v for k, v in state.__dict__.items()}
                if 'audio_file' in state_dict:
                    del state_dict['audio_file']
                if 'audio_metadata' in state_dict:
                    del state_dict['audio_metadata']
                
                new_state = WorkflowState(
                    **state_dict,
                    audio_file=text_output_filename,
                    audio_metadata={
                        "chunks_processed": len(final_chunks),
                        "audio_segments": 0,
                        "output_file": text_output_filename,
                        "status": "text_only",
                        "note": "TTS API 실패로 텍스트 파일만 생성됨"
                    }
                )
                
                # 워크플로우 상태 업데이트
                new_state = self.update_workflow_status(new_state, "tts_completed")
                
                self.log_execution(f"텍스트 파일 생성 완료: {text_output_filename}")
                return new_state
            
        except Exception as e:
            self.log_execution(f"팟캐스트 오디오 생성 중 오류 발생: {str(e)}", "ERROR")
            raise


