"""TTS Agent for converting podcast scripts to audio using TTS."""

import os
import google.generativeai as genai
from google.generativeai import types
import wave
from tqdm import tqdm
import argparse # 명령행 인자를 처리하기 위해 추가
from dotenv import load_dotenv
from datetime import datetime

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

def read_script_file(filepath):
    """지정된 경로의 텍스트 파일을 읽어 내용을 반환합니다."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"오류: 파일을 찾을 수 없습니다 - {filepath}")
        return None
    except Exception as e:
        print(f"오류: 파일을 읽는 중 문제가 발생했습니다 - {e}")
        return None

def split_script_into_chunks(script_text):
    """스크립트 텍스트를 API 제한에 맞는 청크로 분할합니다."""
    print("스크립트를 청크 단위로 나누는 중...")
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
        
    print(f"총 {len(final_chunks)}개의 청크로 분할되었습니다.")
    return final_chunks

def write_wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
   """오디오 데이터를 .wav 파일로 저장합니다."""
   with wave.open(filename, "wb") as wf:
      wf.setnchannels(channels)
      wf.setsampwidth(sample_width)
      wf.setframerate(rate)
      wf.writeframes(pcm)

def main():
    """메인 실행 함수"""
    # --- 1. 입력 파일 인자 설정 ---
    parser = argparse.ArgumentParser(description="텍스트 파일에서 스크립트를 읽어 TTS 오디오를 생성합니다.")
    parser.add_argument("input_file", type=str, help="입력 스크립트 텍스트 파일의 경로")
    args = parser.parse_args()

    # --- 2. 스크립트 파일 읽기 ---
    script = read_script_file(args.input_file)
    if not script:
        return # 파일 읽기 실패 시 종료

    # --- 3. API 키 설정 ---
    # API 키는 환경 변수에서 안전하게 로드합니다.
    API_KEY = os.environ.get('GOOGLE_API_KEY')
    if not API_KEY:
        print("❌ GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
        return
    os.environ['GOOGLE_API_KEY'] = API_KEY
    genai.configure(api_key=API_KEY)

    # --- 4. 스크립트 분할 ---
    final_chunks = split_script_into_chunks(script)
    
    # --- 5. 오디오 생성 ---
    audio_segments = []
    
    print("오디오 생성을 시작합니다...")
    for chunk in tqdm(final_chunks):
        prompt = f"""TTS the following conversation between Joe and Jane:
                {chunk}"""
        try:
            response = client.models.generate_content(
              model="gemini-2.5-flash-preview-tts",
              contents=prompt,
              config=types.GenerateContentConfig(
                  response_modalities=["AUDIO"],
                  speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=[
                          types.SpeakerVoiceConfig(
                              speaker='Joe',
                              voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Kore')
                              )
                          ),
                          types.SpeakerVoiceConfig(
                              speaker='Jane',
                              voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Puck')
                              )
                          ),
                        ]
                    )
                  )
              )
            )
            data = response.candidates[0].content.parts[0].inline_data.data
            audio_segments.append(data)
        except Exception as e:
            print(f"청크 처리 중 오류 발생: {e}")
            continue

    # --- 6. 오디오 병합 및 저장 ---
    if audio_segments:
        print("\n모든 오디오 조각을 합치는 중...")
        combined_audio_data = b''.join(audio_segments)
        output_filename = 'combined_output.wav'
        write_wave_file(output_filename, combined_audio_data)
        print(f"성공적으로 '{output_filename}' 파일로 저장되었습니다.")
    else:
        print("생성된 오디오가 없어 파일을 저장하지 않았습니다.")

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
            
            # API 키 확인
            if not self.api_key:
                self.api_key = os.environ.get("GOOGLE_API_KEY")
                if not self.api_key:
                    raise ValueError("Google API 키가 필요합니다.")
            
            # API 설정
            os.environ['GOOGLE_API_KEY'] = self.api_key
            genai.configure(api_key=self.api_key)
            
            # 스크립트 분할
            final_chunks = split_script_into_chunks(podcast_script)
            
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

if __name__ == "__main__":
    main()
