"""Summarizer Agent for creating summaries of collected information."""

import json
import torch
import numpy as np
from tqdm import tqdm
from datetime import datetime

# Transformers 라이브러리 임포트
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

from .base_agent import BaseAgent
from state.state import WorkflowState
from constants import SUMMARIZER_CONFIG

# --- GPU 설정 ---
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"사용 디바이스: {DEVICE}")

class KoT5Summarizer:
    """
    KoT5 모델을 사용하여 텍스트를 요약하는 에이전트
    """
    
    def __init__(self, model_name="psyche/KoT5-summarization"):
        """
        KoT5 모델과 토크나이저를 초기화합니다.
        
        Args:
            model_name (str): 사용할 KoT5 모델명
        """
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """KoT5 모델과 토크나이저를 로드합니다."""
        print(f"KoT5 모델('{self.model_name}') 로드 중...")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name).to(DEVICE)
            print("KoT5 모델 로드 완료!")
        except Exception as e:
            print(f"모델 로드 실패: {e}")
            raise
    
    def summarize_text(self, text, max_length=SUMMARIZER_CONFIG["default_max_length"], min_length=SUMMARIZER_CONFIG["default_min_length"]):
        """
        텍스트를 요약합니다.
        
        Args:
            text (str): 요약할 텍스트
            max_length (int): 최대 요약 길이
            min_length (int): 최소 요약 길이
            
        Returns:
            str: 요약된 텍스트
        """
        try:
            # 텍스트 전처리 (너무 긴 텍스트는 잘라냄)
            if len(text) > 4000:
                text = text[:4000] + "..."
            
            # 토크나이징
            inputs = self.tokenizer(
                text, 
                return_tensors="pt", 
                max_length=SUMMARIZER_CONFIG["max_input_length"], 
                truncation=True
            ).to(DEVICE)
            
            # 요약 생성
            summary_ids = self.model.generate(
                inputs['input_ids'],
                max_length=max_length,
                min_length=min_length,
                num_beams=4,
                length_penalty=2.0,
                early_stopping=True
            )
            
            # 디코딩
            summary = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            return summary.strip()
            
        except Exception as e:
            print(f"요약 생성 중 오류 발생: {e}")
            return "요약 생성에 실패했습니다."

def load_search_results(filename="combined_search_results.json"):
    """
    검색 결과 JSON 파일을 로드합니다.
    
    Args:
        filename (str): 로드할 JSON 파일명
        
    Returns:
        list: 검색 결과 데이터
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"'{filename}' 파일에서 {len(data)}개의 샘플을 성공적으로 로드했습니다.")
        return data
    except FileNotFoundError:
        print(f"에러: '{filename}' 파일을 찾을 수 없습니다.")
        return None
    except json.JSONDecodeError:
        print(f"에러: '{filename}' 파일의 형식이 올바르지 않습니다.")
        return None

def save_summarized_results(data, filename=None):
    """
    요약이 추가된 결과를 JSON 파일로 저장합니다.
    
    Args:
        data (list): 요약이 추가된 데이터
        filename (str): 저장할 파일명 (None이면 자동 생성)
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"summarized_search_results_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"요약 결과가 '{filename}'에 성공적으로 저장되었습니다.")
        return filename
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}")
        return None

def process_search_results(data, summarizer):
    """
    검색 결과에 요약을 추가합니다.
    
    Args:
        data (list): 검색 결과 데이터
        summarizer (KoT5Summarizer): 요약 모델
        
    Returns:
        list: 요약이 추가된 데이터
    """
    print(f"총 {len(data)}개 샘플에 대한 요약 생성 시작")
    
    processed_data = []
    
    for i, sample in enumerate(tqdm(data, desc="요약 생성 중")):
        # 기존 데이터 복사
        processed_sample = sample.copy()
        
        # content가 있는 경우에만 요약 생성
        if 'content' in sample and sample['content'].strip():
            try:
                summary = summarizer.summarize_text(sample['content'])
                processed_sample['summary'] = summary
            except Exception as e:
                print(f"샘플 {i+1} 요약 실패: {e}")
                processed_sample['summary'] = "요약 생성에 실패했습니다."
        else:
            processed_sample['summary'] = "요약할 내용이 없습니다."
        
        processed_data.append(processed_sample)
    
    return processed_data

class SummarizerAgent(BaseAgent):
    """텍스트 요약 에이전트"""
    
    def __init__(self, model_name="psyche/KoT5-summarization"):
        super().__init__(
            name="summarizer",
            description="텍스트 요약 에이전트"
        )
        self.required_inputs = ["search_results"]
        self.output_keys = ["summarized_results", "summarization_metadata"]
        self.summarizer = KoT5Summarizer(model_name)
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """검색 결과에 요약을 추가합니다."""
        self.log_execution("텍스트 요약 시작")
        
        try:
            # 입력 검증
            if not self.validate_inputs(state):
                raise ValueError("필수 입력이 누락되었습니다.")
            
            # 검색 결과 가져오기
            search_results = getattr(state, 'search_results', [])
            if not search_results:
                raise ValueError("요약할 검색 결과가 없습니다.")
            
            # 요약 생성
            summarized_results = process_search_results(search_results, self.summarizer)
            
            # 결과 저장
            output_filename = f"AgentCast/output/summarizer/summarized_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            save_summarized_results(summarized_results, output_filename)
            
            # 워크플로우 상태 업데이트
            new_state = WorkflowState(
                **{k: v for k, v in state.__dict__.items()},
                summarized_results=summarized_results,
                summarization_metadata={
                    "total_items": len(summarized_results),
                    "successful_summaries": sum(1 for item in summarized_results if item.get('summary') != "요약 생성에 실패했습니다."),
                    "output_file": output_filename
                }
            )
            
            # 워크플로우 상태 업데이트
            new_state = self.update_workflow_status(new_state, "summarizer_completed")
            
            self.log_execution(f"텍스트 요약 완료: {len(summarized_results)}개 항목 처리")
            return new_state
            
        except Exception as e:
            self.log_execution(f"텍스트 요약 중 오류 발생: {str(e)}", "ERROR")
            raise
