"""Knowledge Graph Agent using HippoRAG for real-time document processing."""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

import sys
import os
# Add local HippoRAG to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'HippoRAG', 'src'))

# Delay HippoRAG import to avoid multiprocessing issues at module level
HIPPORAG_AVAILABLE = False
HippoRAG = None

def _import_hipporag():
    """Delayed import of HippoRAG to avoid multiprocessing issues."""
    global HIPPORAG_AVAILABLE, HippoRAG
    if HIPPORAG_AVAILABLE:
        return HippoRAG
    
    try:
        # Set multiprocessing start method to fork for macOS compatibility
        import multiprocessing
        if multiprocessing.get_start_method() != 'fork':
            try:
                multiprocessing.set_start_method('fork', force=True)
                print("Multiprocessing start method changed to 'fork'")
            except Exception as mp_error:
                print(f"Could not change multiprocessing method: {mp_error}")
        
        # Try to import HippoRAG
        from hipporag import HippoRAG as _HippoRAG
        HippoRAG = _HippoRAG
        HIPPORAG_AVAILABLE = True
        print("Local HippoRAG imported successfully")
        return HippoRAG
    except Exception as e:
        print(f"Failed to import local HippoRAG: {e}")
        print("Using mock implementation instead")
        return None

from ..base_agent import BaseAgent
from state.state import WorkflowState
from constants.agents import KNOWLEDGE_GRAPH_AGENT_NAME
from constants.prompts import KNOWLEDGE_GRAPH_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class KnowledgeGraphAgent(BaseAgent):
    """Real-time knowledge graph construction agent using HippoRAG."""
    
    def __init__(self):
        super().__init__(KNOWLEDGE_GRAPH_AGENT_NAME, "실시간 지식 그래프 구축을 위한 HippoRAG 에이전트")
        if HIPPORAG_AVAILABLE:
            self.hipporag: Optional[HippoRAG] = None
        else:
            self.hipporag = None
        self.retriever = None
        self.knowledge_graph = {}
        self.document_store = {}
        
    async def initialize(self) -> None:
        """Initialize HippoRAG and retriever."""
        try:
            # Try to import HippoRAG with delayed import
            hipporag_class = _import_hipporag()
            if hipporag_class is None:
                logger.warning("HippoRAG is not available, using mock implementation")
                self.hipporag = None
                self.retriever = None
                return
            
            # Initialize HippoRAG with local configuration
            logger.info("Initializing local HippoRAG...")
            self.hipporag = hipporag_class(
                llm_model_name="gpt-4o-mini",  # Use correct parameter name
                embedding_model_name="text-embedding-3-small",
                save_dir="output/hipporag_workflow"
            )
            
            logger.info("Knowledge Graph Agent initialized successfully with local HippoRAG")
            
        except Exception as e:
            logger.error(f"Failed to initialize Knowledge Graph Agent: {e}")
            logger.warning("Falling back to mock implementation")
            self.hipporag = None
            self.retriever = None
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """지식 그래프 구축을 수행합니다."""
        try:
            if not self.hipporag:
                logger.warning("HippoRAG is not available, using mock implementation")
                # Mock knowledge graph
                mock_kg = {
                    "entities": {},
                    "relationships": [],
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "document_count": 0,
                        "entity_count": 0,
                        "relationship_count": 0,
                        "status": "mock"
                    }
                }
                
                # Update state
                state_dict = {k: v for k, v in state.__dict__.items()}
                if 'knowledge_graph' in state_dict:
                    del state_dict['knowledge_graph']
                if 'document_store' in state_dict:
                    del state_dict['document_store']
                
                new_state = WorkflowState(
                    **state_dict,
                    knowledge_graph=mock_kg,
                    document_store={}
                )
                
                new_state = self.update_workflow_status(new_state, "knowledge_graph_completed")
                return new_state
            
            # Get crawled documents from state
            crawled_documents = getattr(state, 'search_results', [])
            if not crawled_documents:
                logger.warning("No crawled documents found in state, trying to use existing data")
                
                # Try to use existing combined_search_results.json if available
                try:
                    import json
                    import os
                    existing_data_path = "output/combined_search_results.json"
                    if os.path.exists(existing_data_path):
                        with open(existing_data_path, 'r', encoding='utf-8') as f:
                            existing_data = json.load(f)
                        
                        # Extract content from existing data
                        documents_for_kg = []
                        for item in existing_data[:10]:  # Use first 10 items for testing
                            if 'content' in item:
                                documents_for_kg.append({
                                    'title': item.get('title', 'Unknown'),
                                    'content': item['content'],
                                    'source': item.get('source', 'Unknown')
                                })
                        
                        if documents_for_kg:
                            logger.info(f"Using {len(documents_for_kg)} existing documents for knowledge graph")
                            crawled_documents = documents_for_kg
                        else:
                            logger.warning("No valid content found in existing data")
                    else:
                        logger.warning("No existing data file found")
                except Exception as e:
                    logger.error(f"Error loading existing data: {e}")
                
                if not crawled_documents:
                    # Return empty knowledge graph if still no documents
                    state_dict = {k: v for k, v in state.__dict__.items()}
                    if 'knowledge_graph' in state_dict:
                        del state_dict['knowledge_graph']
                    if 'document_store' in state_dict:
                        del state_dict['document_store']
                    
                    empty_kg = {
                        "entities": {},
                        "relationships": [],
                        "metadata": {
                            "created_at": datetime.now().isoformat(),
                            "document_count": 0,
                            "entity_count": 0,
                            "relationship_count": 0,
                            "status": "empty"
                        }
                    }
                    
                    new_state = WorkflowState(
                        **state_dict,
                        knowledge_graph=empty_kg,
                        document_store={}
                    )
                    
                    new_state = self.update_workflow_status(new_state, "knowledge_graph_completed")
                    return new_state
            
            # Process each document and build knowledge graph
            knowledge_graph = await self._build_knowledge_graph(crawled_documents)
            
            # Store in state
            state_dict = {k: v for k, v in state.__dict__.items()}
            if 'knowledge_graph' in state_dict:
                del state_dict['knowledge_graph']
            if 'document_store' in state_dict:
                del state_dict['document_store']
            
            new_state = WorkflowState(
                **state_dict,
                knowledge_graph=knowledge_graph,
                document_store=self.document_store
            )
            
            new_state = self.update_workflow_status(new_state, "knowledge_graph_completed")
            
            logger.info(f"Knowledge graph built with {len(knowledge_graph['entities'])} entities")
            return new_state
            
        except Exception as e:
            logger.error(f"Error in Knowledge Graph Agent: {e}")
            # Return state with error
            return state
    
    async def _build_knowledge_graph(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build knowledge graph from documents using HippoRAG."""
        knowledge_graph = {
            "entities": {},
            "relationships": [],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "document_count": len(documents),
                "entity_count": 0,
                "relationship_count": 0
            }
        }
        
        for doc in documents:
            try:
                # Extract entities and relationships using HippoRAG
                entities, relationships = await self._extract_knowledge(doc)
                
                # Add entities to knowledge graph
                for entity in entities:
                    entity_id = entity.get("id")
                    if entity_id:
                        if entity_id not in knowledge_graph["entities"]:
                            knowledge_graph["entities"][entity_id] = entity
                            knowledge_graph["metadata"]["entity_count"] += 1
                        else:
                            # Merge entity information
                            knowledge_graph["entities"][entity_id].update(entity)
                
                # Add relationships
                knowledge_graph["relationships"].extend(relationships)
                knowledge_graph["metadata"]["relationship_count"] += len(relationships)
                
                # Store document
                doc_id = doc.get("id", f"doc_{len(self.document_store)}")
                self.document_store[doc_id] = doc
                
            except Exception as e:
                logger.error(f"Error processing document: {e}")
                continue
        
        return knowledge_graph
    
    async def _extract_knowledge(self, document: Dict[str, Any]) -> tuple[List[Dict], List[Dict]]:
        """Extract entities and relationships from document using HippoRAG."""
        content = document.get("content", "")
        title = document.get("title", "")
        
        # 긴 문서를 요약하여 토큰 제한 방지
        def truncate_content(text: str, max_chars: int = 2000) -> str:
            """긴 텍스트를 지정된 길이로 자르고 요약합니다."""
            if len(text) <= max_chars:
                return text
            
            # 첫 부분과 마지막 부분을 유지하고 중간을 요약
            first_part = text[:max_chars//3]
            last_part = text[-(max_chars//3):]
            middle_summary = f"...[중간 내용 요약: {len(text) - (max_chars//3)*2}자 생략]..."
            
            return first_part + middle_summary + last_part
        
        # 문서 내용 요약
        truncated_content = truncate_content(content, 2000)
        truncated_title = truncate_content(title, 200)
        
        # Prepare prompt for knowledge extraction (요약된 내용 사용)
        prompt = f"""
        Extract entities and relationships from the following document:
        
        Title: {truncated_title}
        Content: {truncated_content}
        
        Please identify:
        1. Entities (people, organizations, technologies, concepts)
        2. Relationships between entities
        
        Return as JSON format:
        {{
            "entities": [
                {{
                    "id": "unique_id",
                    "name": "entity_name",
                    "type": "entity_type",
                    "description": "description",
                    "confidence": 0.9
                }}
            ],
            "relationships": [
                {{
                    "source": "source_entity_id",
                    "target": "target_entity_id",
                    "relation": "relationship_type",
                    "confidence": 0.9
                }}
            ]
        }}
        """
        
        try:
            # Use HippoRAG to index and extract knowledge
            # First, index the document content (요약된 내용 사용)
            doc_content = f"Title: {truncated_title}\nContent: {truncated_content}"
            
            # Index the document using HippoRAG
            self.hipporag.index(docs=[doc_content])
            
            # Extract entities using simple NLP approach since HippoRAG doesn't have direct entity extraction
            # For now, create basic entities from the document
            entities = []
            relationships = []
            
            # Create a document entity
            doc_entity = {
                "id": f"doc_{hash(title)}",
                "name": title,
                "type": "document",
                "description": content[:200] + "..." if len(content) > 200 else content,
                "confidence": 0.9
            }
            entities.append(doc_entity)
            
            # Extract key terms as entities (simplified approach)
            import re
            key_terms = re.findall(r'\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\b', content)
            for i, term in enumerate(key_terms[:5]):  # Limit to 5 key terms
                if len(term) > 2:  # Only meaningful terms
                    term_entity = {
                        "id": f"term_{hash(term)}",
                        "name": term,
                        "type": "concept",
                        "description": f"Key term from document: {title}",
                        "confidence": 0.8
                    }
                    entities.append(term_entity)
                    
                    # Create relationship between document and term
                    relationship = {
                        "source": doc_entity["id"],
                        "target": term_entity["id"],
                        "relation": "contains",
                        "confidence": 0.8
                    }
                    relationships.append(relationship)
            
            return entities, relationships
            
        except Exception as e:
            logger.error(f"Error extracting knowledge: {e}")
        
        return [], []
    
    async def search_knowledge_graph(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search knowledge graph using HippoRAG."""
        try:
            if not self.hipporag:
                logger.warning("HippoRAG not initialized, trying to initialize...")
                await self.initialize()
            
            if not self.hipporag:
                logger.error("HippoRAG still not available after initialization")
                return []
            
            # Use HippoRAG to search
            logger.info(f"Searching knowledge graph with query: '{query}'")
            
            # Convert query to list format for HippoRAG
            queries = [query]
            
            # Check if HippoRAG has indexed documents
            if not hasattr(self.hipporag, 'passage_embeddings') or self.hipporag.passage_embeddings is None or len(self.hipporag.passage_embeddings) == 0:
                logger.warning("No indexed documents found in HippoRAG. Skipping search.")
                return []
            
            # Search using HippoRAG
            search_results = self.hipporag.retrieve(
                queries=queries,
                num_to_retrieve=top_k
            )
            
            # Process and format results
            formatted_results = []
            for result in search_results:
                if hasattr(result, 'docs') and result.docs:
                    # Get the first document from each result
                    doc_content = result.docs[0] if result.docs else ""
                    
                    # Get score if available
                    score = 0.0
                    if hasattr(result, 'doc_scores') and result.doc_scores is not None:
                        if len(result.doc_scores) > 0:
                            score = float(result.doc_scores[0])
                    
                    formatted_result = {
                        "content": doc_content,
                        "title": f"Knowledge Graph Search: {query}",
                        "url": "knowledge_graph",
                        "score": score,
                        "query": query,
                        "source": "hipporag"
                    }
                    formatted_results.append(formatted_result)
            
            logger.info(f"Found {len(formatted_results)} results from knowledge graph search")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching knowledge graph: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def get_related_entities(self, entity_id: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """Get related entities from knowledge graph."""
        try:
            if "knowledge_graph" not in self.state:
                return []
            
            knowledge_graph = self.state["knowledge_graph"]
            entities = knowledge_graph.get("entities", {})
            relationships = knowledge_graph.get("relationships", [])
            
            related_entities = []
            visited = set()
            
            def find_related(entity_id: str, depth: int):
                if depth > max_depth or entity_id in visited:
                    return
                
                visited.add(entity_id)
                
                # Find relationships involving this entity
                for rel in relationships:
                    if rel["source"] == entity_id:
                        target_id = rel["target"]
                        if target_id in entities:
                            related_entities.append({
                                "entity": entities[target_id],
                                "relationship": rel,
                                "depth": depth
                            })
                            find_related(target_id, depth + 1)
                    elif rel["target"] == entity_id:
                        source_id = rel["source"]
                        if source_id in entities:
                            related_entities.append({
                                "entity": entities[source_id],
                                "relationship": rel,
                                "depth": depth
                            })
                            find_related(source_id, depth + 1)
            
            find_related(entity_id, 0)
            return related_entities
            
        except Exception as e:
            logger.error(f"Error getting related entities: {e}")
            return []
    
    async def update_knowledge_graph(self, new_documents: List[Dict[str, Any]]) -> None:
        """Update knowledge graph with new documents."""
        try:
            # Process new documents
            new_knowledge = await self._build_knowledge_graph(new_documents)
            
            # Merge with existing knowledge graph
            if hasattr(self, 'knowledge_graph'):
                # Merge entities
                for entity_id, entity in new_knowledge["entities"].items():
                    if entity_id in self.knowledge_graph["entities"]:
                        self.knowledge_graph["entities"][entity_id].update(entity)
                    else:
                        self.knowledge_graph["entities"][entity_id] = entity
                        self.knowledge_graph["metadata"]["entity_count"] += 1
                
                # Add new relationships
                self.knowledge_graph["relationships"].extend(new_knowledge["relationships"])
                self.knowledge_graph["metadata"]["relationship_count"] += len(new_knowledge["relationships"])
                
                # Update metadata
                self.knowledge_graph["metadata"]["document_count"] += len(new_documents)
                self.knowledge_graph["metadata"]["last_updated"] = datetime.now().isoformat()
            
            logger.info(f"Knowledge graph updated with {len(new_documents)} new documents")
            
        except Exception as e:
            logger.error(f"Error updating knowledge graph: {e}")
    
    def get_knowledge_graph_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        if not hasattr(self, 'knowledge_graph'):
            return {}
        
        return {
            "entity_count": len(self.knowledge_graph.get("entities", {})),
            "relationship_count": len(self.knowledge_graph.get("relationships", [])),
            "document_count": len(self.document_store),
            "metadata": self.knowledge_graph.get("metadata", {})
        } 