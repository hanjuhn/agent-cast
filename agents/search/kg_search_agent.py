"""Knowledge Graph Search Agent for querying the knowledge graph."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..base_agent import BaseAgent
from ..extraction.knowledge_graph_agent import KnowledgeGraphAgent
from state.state import WorkflowState
from constants.agents import KG_SEARCH_AGENT_NAME
from constants.prompts import KG_SEARCH_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class KGSearchAgent(BaseAgent):
    """Knowledge Graph Search Agent for retrieving relevant information."""
    
    def __init__(self):
        super().__init__(KG_SEARCH_AGENT_NAME, "지식 그래프에서 정보를 검색하는 에이전트")
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
            logger.warning("Falling back to mock implementation")
            self.knowledge_graph_agent = None
    
    async def process(self, state: WorkflowState) -> WorkflowState:
        """지식 그래프 검색을 수행합니다."""
        try:
            if not self.knowledge_graph_agent:
                logger.warning("KnowledgeGraphAgent not available, using mock implementation")
                # Mock search results
                mock_results = [{
                    "query": "AI research trends",
                    "type": "general",
                    "status": "mock",
                    "message": "KnowledgeGraphAgent not initialized",
                    "content": "Mock search result for AI research trends",
                    "score": 0.0
                }]
                
                # Update state
                state_dict = {k: v for k, v in state.__dict__.items()}
                if 'kg_search_results' in state_dict:
                    del state_dict['kg_search_results']
                
                new_state = WorkflowState(
                    **state_dict,
                    kg_search_results=mock_results
                )
                
                new_state = self.update_workflow_status(new_state, "kg_search_completed")
                return new_state
            
            # Get search query from state
            search_query = getattr(state, 'search_query', 'AI research trends')
            if not search_query:
                search_query = 'AI research trends'
            
            # Get query type from state or use default
            query_type = getattr(state, 'query_type', 'general')
            
            # Search knowledge graph
            search_results = await self._search_knowledge_graph(search_query, query_type)
            
            # Add knowledge graph statistics
            kg_stats = {}
            if hasattr(self.knowledge_graph_agent, 'knowledge_graph'):
                kg_stats = self.knowledge_graph_agent.get_knowledge_graph_stats()
            
            # Enhance search results with knowledge graph insights
            enhanced_results = await self._enhance_search_results(search_results, query_type)
            
            # Update state
            state_dict = {k: v for k, v in state.__dict__.items()}
            if 'kg_search_results' in state_dict:
                del state_dict['kg_search_results']
            if 'kg_stats' in state_dict:
                del state_dict['kg_stats']
            
            new_state = WorkflowState(
                **state_dict,
                kg_search_results=enhanced_results,
                kg_stats=kg_stats
            )
            
            new_state = self.update_workflow_status(new_state, "kg_search_completed")
            
            logger.info(f"Knowledge graph search completed with {len(enhanced_results)} enhanced results")
            logger.info(f"Knowledge graph stats: {kg_stats}")
            return new_state
            
        except Exception as e:
            logger.error(f"Error in KG Search Agent: {e}")
            # Return state with error
            return state
    
    async def _search_knowledge_graph(self, query: str, query_type: str = "general") -> List[Dict[str, Any]]:
        """Search knowledge graph using HippoRAG."""
        try:
            if not self.knowledge_graph_agent:
                logger.warning("KnowledgeGraphAgent not available, returning mock results")
                return [{"query": query, "type": query_type, "status": "mock", "message": "KnowledgeGraphAgent not initialized"}]
            
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
            return [{"query": query, "type": query_type, "status": "error", "message": str(e)}]
    
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