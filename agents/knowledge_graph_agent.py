"""Knowledge Graph Agent using HippoRAG for real-time document processing."""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

import hipporag
from hipporag import HippoRAG
from hipporag.retrievers import Retriever
from hipporag.retrievers.retriever import RetrieverConfig

from .base_agent import BaseAgent
from ..state import WorkflowState
from ..constants.agents import KNOWLEDGE_GRAPH_AGENT_NAME
from ..constants.prompts import KNOWLEDGE_GRAPH_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class KnowledgeGraphAgent(BaseAgent):
    """Real-time knowledge graph construction agent using HippoRAG."""
    
    def __init__(self):
        super().__init__(KNOWLEDGE_GRAPH_AGENT_NAME)
        self.hipporag: Optional[HippoRAG] = None
        self.retriever: Optional[Retriever] = None
        self.knowledge_graph = {}
        self.document_store = {}
        
    async def initialize(self) -> None:
        """Initialize HippoRAG and retriever."""
        try:
            # Initialize HippoRAG with configuration
            self.hipporag = HippoRAG(
                model_name="gritlm-7b",
                device="auto",
                max_length=4096,
                temperature=0.1
            )
            
            # Configure retriever
            retriever_config = RetrieverConfig(
                model_name="gritlm-7b",
                device="auto",
                max_length=4096,
                temperature=0.1,
                top_k=10,
                similarity_threshold=0.7
            )
            
            self.retriever = Retriever(retriever_config)
            logger.info("Knowledge Graph Agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Knowledge Graph Agent: {e}")
            raise
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """Process documents and build knowledge graph."""
        try:
            if not self.hipporag:
                await self.initialize()
            
            # Get crawled documents from state
            crawled_documents = state.get("crawled_documents", [])
            if not crawled_documents:
                logger.warning("No crawled documents found in state")
                return state
            
            # Process each document and build knowledge graph
            knowledge_graph = await self._build_knowledge_graph(crawled_documents)
            
            # Store in state
            state.set("knowledge_graph", knowledge_graph)
            state.set("document_store", self.document_store)
            
            logger.info(f"Knowledge graph built with {len(knowledge_graph)} entities")
            return state
            
        except Exception as e:
            logger.error(f"Error in Knowledge Graph Agent: {e}")
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
        
        # Prepare prompt for knowledge extraction
        prompt = f"""
        Extract entities and relationships from the following document:
        
        Title: {title}
        Content: {content}
        
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
            # Use HippoRAG to extract knowledge
            response = await self.hipporag.generate(prompt)
            
            # Parse response
            if response and hasattr(response, 'text'):
                result = json.loads(response.text)
                entities = result.get("entities", [])
                relationships = result.get("relationships", [])
                return entities, relationships
            
        except Exception as e:
            logger.error(f"Error extracting knowledge: {e}")
        
        return [], []
    
    async def search_knowledge_graph(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search knowledge graph using query."""
        try:
            if not self.retriever:
                await self.initialize()
            
            # Use retriever to search
            results = await self.retriever.retrieve(
                query=query,
                documents=list(self.document_store.values()),
                top_k=top_k
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching knowledge graph: {e}")
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