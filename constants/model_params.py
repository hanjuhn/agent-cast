"""Model parameters and configuration constants."""

# OpenAI GPT Model Parameters
OPENAI_DEFAULT_PARAMS = {
    "temperature": 0.1,
    "max_tokens": 1500,
    "timeout": 60
}

OPENAI_CRITIC_PARAMS = {
    "temperature": 0.1,
    "max_tokens": 1500
}

OPENAI_CRITIC_FALLBACK_PARAMS = {
    "temperature": 0.1,
    "max_tokens": 2000
}

OPENAI_SEARCHER_PARAMS = {
    "max_tokens": 800,
    "temperature": 0.1
}

OPENAI_SEARCHER_FALLBACK_PARAMS = {
    "max_tokens": 1000,
    "temperature": 0.3
}

OPENAI_SCRIPT_WRITER_PARAMS = {
    "max_tokens": 8000,
    "temperature": 0.7
}

OPENAI_SCRIPT_WRITER_FALLBACK_PARAMS = {
    "max_tokens": 4000,
    "temperature": 0.7
}

OPENAI_RESEARCHER_PARAMS = {
    "temperature": 0.3
}

OPENAI_PERSONALIZE_PARAMS = {
    "max_tokens": 100,
    "temperature": 0.3
}

# Anthropic Claude Model Parameters
ANTHROPIC_SCRIPT_WRITER_PARAMS = {
    "max_tokens": 4000,
    "temperature": 0.7
}

# Agent Timeout Settings (seconds)
AGENT_TIMEOUTS = {
    "base": 60,
    "orchestrator": 30,
    "personalize": 120,
    "query_writer": 60,
    "searcher": 300,
    "db_constructor": 300,
    "researcher": 180,
    "critic": 120,
    "script_writer": 240,
    "tts": 180,
    "knowledge_graph": 300,
    "kg_search": 120,
    "reporter": 120
}

# Data Processing Parameters
CHUNK_PROCESSING = {
    "default_chunk_size": 100,
    "max_chunk_size": 1000,
    "min_chunk_size": 10,
    "overlap_size": 20,
    "db_constructor_chunk_size": 100,
    "max_chars_for_kg": 2000,
    "max_chars_for_critic_research": 2000,
    "max_chars_for_critic_profile": 300
}

# Batch Processing Parameters
BATCH_PROCESSING = {
    "default_batch_size": 100,
    "max_batch_size": 1000,
    "min_batch_size": 1,
    "db_constructor_batch_size": 100
}

# Reporter Configuration
REPORTER_CONFIG = {
    "max_tokens": 4096,
    "temperature": 0.1,
    "timeout": 120,
    "improved_max_tokens": 8192
}

# Token Limits
TOKEN_LIMITS = {
    "gpt_4": 8192,
    "gpt_4_turbo": 128000,
    "gpt_3_5_turbo": 4096,
    "claude_3": 100000,
    "claude_3_haiku": 200000
}

# Default Model Settings
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-haiku-20240307",
    "embedding": "text-embedding-3-small",
    "tts": "tts-1"
}

# Summarizer Configuration
SUMMARIZER_CONFIG = {
    "default_max_length": 200,
    "default_min_length": 30,
    "max_input_length": 1024
}

# Web Crawling Configuration
WEB_CRAWLING_CONFIG = {
    "scroll_wait_time": 2,
    "page_load_wait": 3,
    "max_articles": 20,
    "days_back": 7
}

# File Processing Configuration
FILE_PROCESSING = {
    "encoding": "utf-8",
    "max_file_size_mb": 100,
    "backup_enabled": True
}
