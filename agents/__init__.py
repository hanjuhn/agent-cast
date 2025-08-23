"""
Agent system for the Agent-Cast project.
Organized by functionality: personalization, search, generation, and extraction.
"""

from .base_agent import BaseAgent
from .orchestrator_agent import OrchestratorAgent

# Import from subdirectories
from .personalization import PersonalizeAgent
from .search import (
    SearcherAgent,
    KGSearchAgent,
    HippoRAGSearchAgent,
    HippoRAGIndexingAgent
)
from .generation import (
    ScriptWriterAgent,
    ReporterAgent,
    TTSAgent,
    QueryWriterAgent
)
from .extraction import (
    ResearcherAgent,
    CriticAgent,
    DBConstructorAgent,
    KnowledgeGraphAgent,
    SummarizerAgent
)

__all__ = [
    "BaseAgent",
    "OrchestratorAgent",
    "PersonalizeAgent",
    "SearcherAgent",
    "KGSearchAgent",
    "HippoRAGSearchAgent",
    "HippoRAGIndexingAgent",
    "ScriptWriterAgent",
    "ReporterAgent",
    "TTSAgent",
    "QueryWriterAgent",
    "ResearcherAgent",
    "CriticAgent",
    "DBConstructorAgent",
    "KnowledgeGraphAgent",
    "SummarizerAgent"
]
