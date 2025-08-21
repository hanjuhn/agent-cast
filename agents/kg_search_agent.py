"""Knowledge Graph Search Agent for querying the knowledge graph."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base_agent import BaseAgent
from .knowledge_graph_agent import KnowledgeGraphAgent
from ..state import WorkflowState
from ..constants.agents import KG_SEARCH_AGENT_NAME
from ..constants.prompts import KG_SEARCH_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class KGSearchAgent(BaseAgent):
    """Knowledge Graph Search Agent for retrieving relevant information."""
    
    def __init__(self):
        super().__init__(KG_SEARCH_AGENT_NAME)
        self.knowledge_graph_agent: Optional[KnowledgeGraphAgent] = None
        self.search_results = []
        
    async def initialize(self) -> None:
        """Initialize the knowledge graph search agent."""
        try:
            self.knowledge_graph_agent = KnowledgeGraphAgent()
            await self.knowledge_graph_agent.initialize()
            logger.info("KG Search Agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize KG Search Agent: {e}")
            raise
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """Process query and search knowledge graph."""
        try:
            if not self.knowledge_graph_agent:
                await self.initialize()
            
            # Get query from query_writer output
            query_writer_output = state.get("query_writer_output", {})
            queries = query_writer_output.get("queries", [])
            
            if not queries:
                logger.warning("No queries found from query_writer")
                return state
            
            # Search knowledge graph for each query
            search_results = []
            for query in queries:
                query_text = query.get("query", "")
                query_type = query.get("type", "general")
                
                if query_text:
                    results = await self._search_knowledge_graph(query_text, query_type)
                    search_results.append({
                        "query": query_text,
                        "type": query_type,
                        "results": results,
                        "timestamp": datetime.now().isoformat()
                    })
            
            # Store search results in state
            state.set("kg_search_results", search_results)
            self.search_results = search_results
            
            logger.info(f"KG Search completed with {len(search_results)} query results")
            return state
            
        except Exception as e:
            logger.error(f"Error in KG Search Agent: {e}")
            return state
    
    async def _search_knowledge_graph(self, query: str, query_type: str = "general") -> List[Dict[str, Any]]:
        """Search knowledge graph using HippoRAG."""
        try:
            # Use knowledge graph agent to search
            results = await self.knowledge_graph_agent.search_knowledge_graph(
                query=query,
                top_k=10
            )
            
            # Process and enhance results based on query type
            enhanced_results = await self._enhance_search_results(results, query_type)
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Error searching knowledge graph: {e}")
            return []
    
    async def _enhance_search_results(self, results: List[Dict[str, Any]], query_type: str) -> List[Dict[str, Any]]:
        """Enhance search results with additional context and relationships."""
        enhanced_results = []
        
        for result in results:
            try:
                # Get basic result info
                enhanced_result = {
                    "content": result.get("content", ""),
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "score": result.get("score", 0.0),
                    "query_type": query_type,
                    "entities": [],
                    "relationships": [],
                    "related_concepts": []
                }
                
                # Extract entities from the result
                if hasattr(self.knowledge_graph_agent, 'knowledge_graph'):
                    entities = await self._extract_entities_from_content(result.get("content", ""))
                    enhanced_result["entities"] = entities
                    
                    # Get related entities for each found entity
                    for entity in entities:
                        entity_id = entity.get("id")
                        if entity_id:
                            related = await self.knowledge_graph_agent.get_related_entities(entity_id, max_depth=1)
                            enhanced_result["relationships"].extend(related)
                
                # Add related concepts based on query type
                enhanced_result["related_concepts"] = await self._get_related_concepts(query_type, result)
                
                enhanced_results.append(enhanced_result)
                
            except Exception as e:
                logger.error(f"Error enhancing search result: {e}")
                continue
        
        return enhanced_results
    
    async def _extract_entities_from_content(self, content: str) -> List[Dict[str, Any]]:
        """Extract entities from content using knowledge graph."""
        try:
            if not hasattr(self.knowledge_graph_agent, 'knowledge_graph'):
                return []
            
            knowledge_graph = self.knowledge_graph_agent.knowledge_graph
            entities = knowledge_graph.get("entities", {})
            
            # Simple entity matching (can be enhanced with NLP)
            found_entities = []
            for entity_id, entity in entities.items():
                entity_name = entity.get("name", "").lower()
                if entity_name and entity_name in content.lower():
                    found_entities.append(entity)
            
            return found_entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []
    
    async def _get_related_concepts(self, query_type: str, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get related concepts based on query type and result."""
        try:
            related_concepts = []
            
            # Define concept mappings based on query type
            concept_mappings = {
                "technology": ["AI", "Machine Learning", "Deep Learning", "Neural Networks"],
                "research": ["Papers", "Studies", "Experiments", "Methodologies"],
                "company": ["Organizations", "Startups", "Corporations", "Partnerships"],
                "person": ["Researchers", "Scientists", "Entrepreneurs", "Experts"]
            }
            
            # Get relevant concepts for the query type
            concepts = concept_mappings.get(query_type, [])
            
            # Search for these concepts in the knowledge graph
            for concept in concepts:
                if hasattr(self.knowledge_graph_agent, 'knowledge_graph'):
                    knowledge_graph = self.knowledge_graph_agent.knowledge_graph
                    entities = knowledge_graph.get("entities", {})
                    
                    for entity_id, entity in entities.items():
                        if concept.lower() in entity.get("type", "").lower():
                            related_concepts.append({
                                "concept": concept,
                                "entity": entity,
                                "relevance_score": 0.8
                            })
            
            return related_concepts
            
        except Exception as e:
            logger.error(f"Error getting related concepts: {e}")
            return []
    
    async def search_by_entity(self, entity_name: str, entity_type: str = None) -> List[Dict[str, Any]]:
        """Search knowledge graph by specific entity."""
        try:
            if not self.knowledge_graph_agent:
                await self.initialize()
            
            # Search for the entity in the knowledge graph
            if hasattr(self.knowledge_graph_agent, 'knowledge_graph'):
                knowledge_graph = self.knowledge_graph_agent.knowledge_graph
                entities = knowledge_graph.get("entities", {})
                
                # Find matching entities
                matching_entities = []
                for entity_id, entity in entities.items():
                    if entity.get("name", "").lower() == entity_name.lower():
                        if not entity_type or entity.get("type", "").lower() == entity_type.lower():
                            matching_entities.append(entity)
                
                # Get related information for each matching entity
                results = []
                for entity in matching_entities:
                    entity_id = entity.get("id")
                    if entity_id:
                        related = await self.knowledge_graph_agent.get_related_entities(entity_id, max_depth=2)
                        results.append({
                            "entity": entity,
                            "related_entities": related,
                            "search_timestamp": datetime.now().isoformat()
                        })
                
                return results
            
            return []
            
        except Exception as e:
            logger.error(f"Error searching by entity: {e}")
            return []
    
    async def get_trending_topics(self, time_window: str = "7d") -> List[Dict[str, Any]]:
        """Get trending topics from knowledge graph."""
        try:
            if not self.knowledge_graph_agent:
                await self.initialize()
            
            # This would typically analyze document timestamps and entity frequencies
            # For now, return top entities by frequency
            if hasattr(self.knowledge_graph_agent, 'knowledge_graph'):
                knowledge_graph = self.knowledge_graph_agent.knowledge_graph
                entities = knowledge_graph.get("entities", {})
                
                # Count entity mentions (simplified)
                entity_counts = {}
                for entity_id, entity in entities.items():
                    entity_name = entity.get("name", "")
                    entity_counts[entity_name] = entity_counts.get(entity_name, 0) + 1
                
                # Sort by frequency
                trending = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                
                return [
                    {
                        "topic": topic,
                        "frequency": count,
                        "entity_info": next((e for e in entities.values() if e.get("name") == topic), {})
                    }
                    for topic, count in trending
                ]
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting trending topics: {e}")
            return []
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get search statistics."""
        return {
            "total_searches": len(self.search_results),
            "successful_searches": len([r for r in self.search_results if r.get("results")]),
            "average_results_per_query": sum(len(r.get("results", [])) for r in self.search_results) / max(len(self.search_results), 1),
            "last_search_time": self.search_results[-1].get("timestamp") if self.search_results else None
        } 