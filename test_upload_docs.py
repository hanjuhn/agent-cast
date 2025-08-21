#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Upload the research report to Google Docs."""

import os
from datetime import datetime
from mcp.docs_mcp import DocsMCP

def main():
    """메인 함수: 리서치 보고서를 Google Docs로 업로드합니다."""
    try:
        # 입력 파일 경로 설정
        input_file = "output/research_report.txt"
        
        print(f"[DEBUG] 시작...")
        print(f"[DEBUG] 입력 파일: {input_file}")
        
        # 파일 존재 확인
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"보고서 파일을 찾을 수 없습니다: {input_file}")
        
        # 보고서 내용 읽기
        print(f"[DEBUG] 보고서 파일 읽는 중...")
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Google Docs MCP 초기화 및 업로드
        print(f"[DEBUG] Google Docs MCP 초기화...")
        docs_mcp = DocsMCP()
        
        # 문서 제목 설정
        title = f"AI/기술 기사 정리 보고서 ({datetime.now().strftime('%Y-%m-%d')})"
        
        print(f"[DEBUG] 보고서 업로드 중...")
        result = docs_mcp.upload_report(
            title=title,
            content=content
        )
        
        if result['success']:
            print(f"\n보고서가 성공적으로 업로드되었습니다!")
            print(f"문서 링크: {result['url']}")
        else:
            print(f"\n업로드 실패: {result['error']}")
            
    except Exception as e:
        print(f"[ERROR] 처리 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    main()
