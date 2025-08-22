"""Searcher Agent for web crawling and information collection."""

import time
import json
import re
import requests
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from bs4 import BeautifulSoup

from .base_agent import BaseAgent
from state.state import WorkflowState
from constants import OPENAI_SEARCHER_PARAMS, OPENAI_SEARCHER_FALLBACK_PARAMS

# --- 환경 변수 로드 ---
load_dotenv()  # .env 파일에서 환경 변수 로드

class WebSearcher:
    def __init__(self, perplexity_api_key: str = None):
        self.driver = None
        # API 키는 환경 변수에서 안전하게 로드합니다.
        self.perplexity_api_key = perplexity_api_key or os.environ.get('PERPLEXITY_API_KEY')
        if not self.perplexity_api_key:
            print("PERPLEXITY_API_KEY 환경 변수가 설정되지 않았습니다.")
        self.setup_driver()
    
    def setup_driver(self):
        """WebDriver 설정"""
        print("WebDriver 설정을 시작합니다...")
        chrome_options = Options()
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        print("WebDriver 설정이 완료되었습니다.")
    
    def close_driver(self):
        """WebDriver 종료"""
        if self.driver:
            self.driver.quit()
            print("WebDriver를 종료합니다.")
    
    def crawl_pytorch_kr(self):
        """파이토치 한국 사용자 모임 크롤링"""
        print("\n=== 파이토치 한국 사용자 모임 크롤링 시작 ===")
        
        URL = "https://discuss.pytorch.kr/c/news"
        self.driver.get(URL)
        print(f"'{URL}' 페이지로 이동합니다.")
        time.sleep(3)

        one_week_ago = datetime.now() - timedelta(days=7)
        post_info = {}

        print("\n최신 게시글 수집을 시작합니다 (스크롤 다운)...")
        while True:
            topic_list_items = self.driver.find_elements(By.CSS_SELECTOR, "tbody.topic-list-body tr.topic-list-item")
            
            if not topic_list_items:
                print("게시글을 찾을 수 없습니다.")
                break

            last_post_date = None
            
            for item in topic_list_items:
                try:
                    date_span = item.find_element(By.CSS_SELECTOR, "span.relative-date")
                    post_timestamp_ms = int(date_span.get_attribute("data-time"))
                    post_date = datetime.fromtimestamp(post_timestamp_ms / 1000)
                    
                    last_post_date = post_date
                    
                    if post_date >= one_week_ago:
                        link_element = item.find_element(By.CSS_SELECTOR, "a.title")
                        link = link_element.get_attribute("href")
                        if link not in post_info:
                            post_info[link] = post_date
                    
                except (StaleElementReferenceException, NoSuchElementException):
                    continue
            
            # 마지막 게시글이 1주일 이전이면 중단
            if last_post_date and last_post_date < one_week_ago:
                print(f"마지막 게시글 날짜: {last_post_date.strftime('%Y-%m-%d')} - 1주일 이전이므로 수집을 중단합니다.")
                break
            
            # 페이지 하단으로 스크롤
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # 새로운 게시글이 로드될 때까지 대기
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: len(driver.find_elements(By.CSS_SELECTOR, "tbody.topic-list-body tr.topic-list-item")) > len(topic_list_items)
                )
            except TimeoutException:
                print("새로운 게시글이 로드되지 않아 스크롤을 중단합니다.")
                break

        print(f"총 {len(post_info)}개의 최신 게시글을 찾았습니다.")
        
        # 게시글 내용 수집
        posts_data = []
        for link, post_date in post_info.items():
            try:
                self.driver.get(link)
                time.sleep(2)
                
                # 제목 추출 - 여러 선택자 시도
                title = "Unknown"
                try:
                    title_element = self.driver.find_element(By.CSS_SELECTOR, "h1.fancy-title")
                    title = title_element.text.strip()
                except NoSuchElementException:
                    try:
                        title_element = self.driver.find_element(By.CSS_SELECTOR, "h1")
                        title = title_element.text.strip()
                    except NoSuchElementException:
                        try:
                            title_element = self.driver.find_element(By.CSS_SELECTOR, ".topic-title")
                            title = title_element.text.strip()
                        except NoSuchElementException:
                            title = f"PyTorch 게시글 {len(posts_data) + 1}"
                
                # 내용 추출 - 여러 선택자 시도
                content = "내용을 추출할 수 없습니다."
                try:
                    content_element = self.driver.find_element(By.CSS_SELECTOR, "div.cooked")
                    content = content_element.text.strip()
                except NoSuchElementException:
                    try:
                        content_element = self.driver.find_element(By.CSS_SELECTOR, ".topic-body")
                        content = content_element.text.strip()
                    except NoSuchElementException:
                        try:
                            content_element = self.driver.find_element(By.CSS_SELECTOR, ".post-content")
                            content = content_element.text.strip()
                        except NoSuchElementException:
                            content = f"PyTorch 한국 사용자 모임 게시글입니다. 제목: {title}"
                
                # 작성자 추출
                try:
                    author_element = self.driver.find_element(By.CSS_SELECTOR, "span.username")
                    author = author_element.text.strip()
                except NoSuchElementException:
                    author = "Unknown"
                
                post_data = {
                    "title": title,
                    "content": content,
                    "author": author,
                    "url": link,
                    "date": post_date.isoformat(),
                    "source": "pytorch_kr"
                }
                posts_data.append(post_data)
                print(f"'{title}' 수집 완료")
                
            except Exception as e:
                print(f"게시글 수집 중 오류 발생: {e}")
                continue
        
        return posts_data

    def crawl_aitimes_kr(self):
        """AI타임스 크롤링"""
        print("\n=== AI타임스 크롤링 시작 ===")
        
        URL = "https://www.aitimes.kr/news/articleList.html?page=1&total=0&box_idxno=&view_type=sm"
        self.driver.get(URL)
        print(f"'{URL}' 페이지로 이동합니다.")
        time.sleep(3)

        one_week_ago = datetime.now() - timedelta(days=7)
        posts_data = []

        # 최신 기사 수집
        article_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.list-titles")
        
        for article in article_elements[:20]:  # 최신 20개 기사만 수집
            try:
                # 제목과 링크 추출
                title_element = article.find_element(By.CSS_SELECTOR, "a")
                title = title_element.text.strip()
                link = title_element.get_attribute("href")
                
                # 기사 페이지로 이동
                self.driver.get(link)
                time.sleep(2)
                
                # 날짜 추출
                try:
                    date_element = self.driver.find_element(By.CSS_SELECTOR, "div.view-date")
                    date_text = date_element.text.strip()
                    # 날짜 파싱 (예: "2024.01.15 14:30")
                    post_date = datetime.strptime(date_text, "%Y.%m.%d %H:%M")
                except:
                    post_date = datetime.now()
                
                # 1주일 이전 기사는 건너뛰기
                if post_date < one_week_ago:
                    continue
                
                # 내용 추출
                try:
                    content_element = self.driver.find_element(By.CSS_SELECTOR, "div.article-content")
                    content = content_element.text.strip()
                except NoSuchElementException:
                    content = "내용을 추출할 수 없습니다."
                
                post_data = {
                    "title": title,
                    "content": content,
                    "author": "AI타임스",
                    "url": link,
                    "date": post_date.isoformat(),
                    "source": "aitimes_kr"
                }
                posts_data.append(post_data)
                print(f"'{title}' 수집 완료")
                
            except Exception as e:
                print(f"기사 수집 중 오류 발생: {e}")
                continue
        
        return posts_data

    def search_perplexity(self, query: str, max_results: int = 10):
        """Perplexity API를 사용한 검색"""
        if not self.perplexity_api_key:
                    print("Perplexity API 키가 설정되지 않았습니다.")
        return []
        
        print(f"\n=== Perplexity 검색 시작: '{query}' ===")
        
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.perplexity_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {
                    "role": "user",
                    "content": f"Search for recent information about: {query}. Provide detailed, factual information about current trends and developments."
                }
            ],
            "max_tokens": OPENAI_SEARCHER_PARAMS["max_tokens"],
            "temperature": OPENAI_SEARCHER_PARAMS["temperature"],
            "search_recency_filter": "month"
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # 검색 결과를 구조화된 형태로 변환
            search_result = {
                "title": f"Perplexity 검색 결과: {query}",
                "content": content,
                "author": "Perplexity AI",
                "url": "https://www.perplexity.ai",
                "date": datetime.now().isoformat(),
                "source": "perplexity"
            }
            
            print("Perplexity 검색 완료")
            return [search_result]
            
        except Exception as e:
            print(f"Perplexity 검색 중 오류 발생: {e}")
            print("GPT fallback으로 전환 중...")
            
            try:
                fallback_result = self._search_with_gpt_fallback(query)
                if fallback_result:
                    print("GPT fallback 검색 성공")
                    return fallback_result
                else:
                    print("GPT fallback도 실패")
                    return []
            except Exception as fallback_error:
                    print(f"GPT fallback 실패: {fallback_error}")
                    return []
    
    def _search_with_gpt_fallback(self, query: str):
        """GPT를 사용한 fallback 검색"""
        try:
            import os
            from dotenv import load_dotenv
            load_dotenv()
            
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                print("OpenAI API 키가 설정되지 않았습니다.")
                return None
            
            import openai
            client = openai.OpenAI(api_key=openai_api_key)
            
            # GPT-4를 사용한 검색 쿼리 처리
            prompt = f"""
            최신 AI 연구 동향에 대한 정보를 제공해주세요. 다음 주제에 대해 구체적이고 최신의 정보를 포함하여 답변해주세요:
            
            주제: {query}
            
            다음 형식으로 답변해주세요:
            1. 현재 주요 AI 연구 분야
            2. 최근 발표된 중요한 논문이나 기술
            3. 산업계 동향
            4. 향후 전망
            
            한국어로 답변해주세요.
            """
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 AI 연구 동향 전문가입니다. 최신 정보를 바탕으로 정확하고 유용한 답변을 제공합니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=OPENAI_SEARCHER_FALLBACK_PARAMS["max_tokens"],
                temperature=OPENAI_SEARCHER_FALLBACK_PARAMS["temperature"]
            )
            
            content = response.choices[0].message.content
            
            # 검색 결과를 구조화된 형태로 변환
            search_result = {
                "title": f"GPT Fallback 검색 결과: {query}",
                "content": content,
                "author": "OpenAI GPT-4",
                "url": "https://openai.com",
                "date": datetime.now().isoformat(),
                "source": "gpt_fallback"
            }
            
            return [search_result]
            
        except Exception as e:
            print(f"GPT fallback 검색 중 오류 발생: {e}")
            return None

def save_search_results(data, filename=None):
    """검색 결과를 JSON 파일로 저장합니다."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"search_results_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"검색 결과가 '{filename}'에 성공적으로 저장되었습니다.")
        return filename
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}")
        return None

class SearcherAgent(BaseAgent):
    """웹 크롤링 및 정보 수집 에이전트"""
    
    def __init__(self, perplexity_api_key: str = None):
        super().__init__(
            name="searcher",
            description="웹 크롤링을 통해 최신 AI 연구 정보를 수집하는 에이전트"
        )
        self.required_inputs = ["search_query"]
        self.output_keys = ["search_results", "search_metadata"]
        self.web_searcher = WebSearcher(perplexity_api_key)
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """웹 크롤링을 통한 정보 수집을 수행합니다."""
        self.log_execution("웹 크롤링 정보 수집 시작")
        
        try:
            # 입력 검증
            if not self.validate_inputs(state):
                raise ValueError("필수 입력이 누락되었습니다.")
            
            # 검색 쿼리 가져오기 - 사용자 쿼리 기반으로 생성
            user_query = getattr(state, 'user_query', '')
            if user_query:
                # 사용자 쿼리를 기반으로 검색 쿼리 생성 (간소화)
                if "AI 연구 동향" in user_query or "팟캐스트" in user_query:
                    search_query = "AI research trends 2024"
                elif "LLM" in user_query or "모델" in user_query:
                    search_query = "LLM research developments"
                elif "기계학습" in user_query or "머신러닝" in user_query:
                    search_query = "machine learning advances"
                else:
                    search_query = "AI technology trends"
            else:
                search_query = "AI research trends"
            
            # 검색 쿼리 상태 업데이트
            state_dict = {k: v for k, v in state.__dict__.items()}
            if 'search_query' in state_dict:
                del state_dict['search_query']
            
            # 웹 크롤링 수행
            pytorch_posts = self.web_searcher.crawl_pytorch_kr()
            aitimes_posts = self.web_searcher.crawl_aitimes_kr()
            perplexity_results = self.web_searcher.search_perplexity(search_query)
            
            # 모든 결과 합치기
            all_results = pytorch_posts + aitimes_posts + perplexity_results
            
            # 검색 결과가 없으면 기존 데이터 사용
            if not all_results:
                print("웹 크롤링 결과가 없어 기존 데이터를 사용합니다.")
                try:
                    import json
                    existing_data_path = "output/combined_search_results.json"
                    if os.path.exists(existing_data_path):
                        with open(existing_data_path, 'r', encoding='utf-8') as f:
                            existing_data = json.load(f)
                        
                        # 기존 데이터를 검색 결과 형식으로 변환
                        for i, item in enumerate(existing_data[:10]):  # 처음 10개만 사용
                            if 'content' in item:
                                search_item = {
                                    "title": item.get('title', f'AI Research Item {i+1}'),
                                    "content": item['content'],
                                    "author": item.get('author', 'AI Research'),
                                    "url": item.get('url', 'https://ai-research.com'),
                                    "date": item.get('date', datetime.now().isoformat()),
                                    "source": "existing_data"
                                }
                                all_results.append(search_item)
                        
                        print(f"기존 데이터에서 {len(all_results)}개 항목을 검색 결과로 변환했습니다.")
                    else:
                        print("기존 데이터 파일도 없습니다.")
                except Exception as e:
                    print(f"기존 데이터 로드 중 오류: {e}")
            
            # 결과 저장
            output_filename = f"output/searcher/search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs(os.path.dirname(output_filename), exist_ok=True)
            save_search_results(all_results, output_filename)
            
            # 중복될 수 있는 키들 제거
            if 'search_results' in state_dict:
                del state_dict['search_results']
            if 'metadata' in state_dict:
                del state_dict['metadata']
            
            # 메타데이터 생성
            search_metadata = {
                "total_results": len(all_results),
                "pytorch_posts": len(pytorch_posts),
                "aitimes_posts": len(aitimes_posts),
                "perplexity_results": len(perplexity_results),
                "output_file": output_filename,
                "search_query": search_query
            }
            
            # 기존 메타데이터와 병합
            merged_metadata = state_dict.get('metadata', {}).copy()
            merged_metadata.update({"search": search_metadata})
            
            new_state = WorkflowState(
                **state_dict,
                search_query=search_query,
                search_results=all_results,
                metadata=merged_metadata
            )
            
            # 워크플로우 상태 업데이트
            new_state = self.update_workflow_status(new_state, "searcher_completed")
            
            self.log_execution(f"웹 크롤링 정보 수집 완료: {len(all_results)}개 결과 (검색 쿼리: {search_query})")
            return new_state
            
        except Exception as e:
            self.log_execution(f"웹 크롤링 정보 수집 중 오류 발생: {str(e)}", "ERROR")
            raise
        finally:
            # WebDriver 종료
            self.web_searcher.close_driver()
