"""
Context Manager Utility

Provides utilities for managing conversation context, tracking relevant knowledge,
and maintaining conversation history state.
"""

import logging
import json
import time
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import deque

logger = logging.getLogger(__name__)

class ContextWindow:
    """Represents a sliding window of conversation context with memory management."""
    
    def __init__(self, max_turns: int = 10, max_tokens: int = 4000):
        """
        Initialize a context window.
        
        Args:
            max_turns: Maximum number of conversation turns to keep
            max_tokens: Approximate maximum tokens to maintain in the window
        """
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.turns = deque(maxlen=max_turns)
        self.current_tokens = 0
        self.metadata = {}
    
    def add_turn(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a new conversation turn to the context window.
        
        Args:
            role: The role of the speaker (user, assistant, system)
            content: The message content
            metadata: Optional metadata associated with this turn
        """
        # Estimate token count (roughly 4 chars per token as a heuristic)
        estimated_tokens = len(content) // 4
        
        turn = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "estimated_tokens": estimated_tokens,
            "metadata": metadata or {}
        }
        
        self.turns.append(turn)
        self.current_tokens += estimated_tokens
        
        # Trim if we exceed max tokens
        self._trim_to_token_limit()
    
    def _trim_to_token_limit(self) -> None:
        """Trim the context window to stay within token limits."""
        while self.turns and self.current_tokens > self.max_tokens:
            removed_turn = self.turns.popleft()  # Remove oldest turn
            self.current_tokens -= removed_turn["estimated_tokens"]
            logger.debug(f"Trimmed context window, removed {removed_turn['estimated_tokens']} tokens")
    
    def get_turns(self) -> List[Dict[str, Any]]:
        """Get all turns in the context window."""
        return list(self.turns)
    
    def get_formatted_context(self, include_roles: bool = True) -> str:
        """
        Get a formatted string representation of the context window.
        
        Args:
            include_roles: Whether to include role prefixes
            
        Returns:
            Formatted context string
        """
        formatted = []
        for turn in self.turns:
            if include_roles:
                formatted.append(f"{turn['role'].upper()}: {turn['content']}")
            else:
                formatted.append(turn['content'])
        
        return "\n\n".join(formatted)
    
    def clear(self) -> None:
        """Clear the context window."""
        self.turns.clear()
        self.current_tokens = 0
        self.metadata = {}
    
    def get_token_count(self) -> int:
        """Get the current estimated token count."""
        return self.current_tokens
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata for the context window."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from the context window."""
        return self.metadata.get(key, default)


class ConversationMemory:
    """Long-term memory for conversation context and knowledge."""
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize conversation memory.
        
        Args:
            max_size: Maximum number of memory entries to store
        """
        self.facts = {}  # Keyed by entity or concept
        self.preferences = {}  # User preferences
        self.interactions = deque(maxlen=max_size)  # Past interactions
        self.entity_mentions = {}  # Frequency of entity mentions
        self.topics = {}  # Topics discussed, with importance scores
    
    def add_fact(self, entity: str, fact: str, source: str = "conversation") -> None:
        """
        Add a fact about an entity to memory.
        
        Args:
            entity: The entity this fact relates to
            fact: The fact to store
            source: Source of this fact
        """
        if entity not in self.facts:
            self.facts[entity] = []
            
        self.facts[entity].append({
            "fact": fact,
            "source": source,
            "timestamp": time.time()
        })
        
        # Update entity mentions
        self.entity_mentions[entity] = self.entity_mentions.get(entity, 0) + 1
    
    def add_interaction(self, query: str, response: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an interaction to memory.
        
        Args:
            query: User query
            response: System response
            metadata: Additional metadata about the interaction
        """
        interaction = {
            "query": query,
            "response": response,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        
        self.interactions.append(interaction)
    
    def set_preference(self, category: str, preference: Any) -> None:
        """
        Set a user preference.
        
        Args:
            category: Preference category
            preference: Preference value
        """
        self.preferences[category] = {
            "value": preference,
            "timestamp": time.time()
        }
    
    def update_topic_importance(self, topic: str, importance_delta: float = 1.0) -> None:
        """
        Update the importance of a topic.
        
        Args:
            topic: The topic
            importance_delta: The change in importance score
        """
        current_importance = self.topics.get(topic, {"importance": 0.0, "last_mentioned": 0})
        self.topics[topic] = {
            "importance": current_importance["importance"] + importance_delta,
            "last_mentioned": time.time()
        }
    
    def get_facts_about(self, entity: str) -> List[Dict[str, Any]]:
        """
        Get facts about an entity.
        
        Args:
            entity: The entity to get facts about
            
        Returns:
            List of facts about the entity
        """
        return self.facts.get(entity, [])
    
    def get_most_important_topics(self, limit: int = 5) -> List[Tuple[str, float]]:
        """
        Get the most important topics discussed.
        
        Args:
            limit: Maximum number of topics to return
            
        Returns:
            List of (topic, importance) tuples
        """
        topics_list = list(self.topics.items())
        topics_list.sort(key=lambda x: x[1]["importance"], reverse=True)
        return [(topic, data["importance"]) for topic, data in topics_list[:limit]]
    
    def get_most_mentioned_entities(self, limit: int = 5) -> List[Tuple[str, int]]:
        """
        Get the most frequently mentioned entities.
        
        Args:
            limit: Maximum number of entities to return
            
        Returns:
            List of (entity, mention_count) tuples
        """
        entities_list = list(self.entity_mentions.items())
        entities_list.sort(key=lambda x: x[1], reverse=True)
        return entities_list[:limit]
    
    def get_recent_interactions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most recent interactions.
        
        Args:
            limit: Maximum number of interactions to return
            
        Returns:
            List of recent interactions
        """
        return list(self.interactions)[-limit:]
    
    def get_preference(self, category: str, default: Any = None) -> Any:
        """
        Get a user preference.
        
        Args:
            category: Preference category
            default: Default value if preference is not set
            
        Returns:
            Preference value
        """
        pref = self.preferences.get(category)
        return pref["value"] if pref else default


class ContextManager:
    """Manager for conversation context and knowledge tracking."""
    
    def __init__(self, session_id: str = "default"):
        """
        Initialize a context manager.
        
        Args:
            session_id: Unique identifier for this session
        """
        self.session_id = session_id
        self.active_window = ContextWindow()  # Active sliding window
        self.memory = ConversationMemory()  # Long-term memory
        self.active_entities = set()  # Currently active entities
        self.active_topics = set()  # Currently active topics
        self.metadata = {
            "start_time": time.time(),
            "turn_count": 0,
            "last_agent": None,
        }
    
    def add_user_message(self, message: str, analysis: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a user message to the context.
        
        Args:
            message: User message
            analysis: Optional analysis of the message
        """
        self.active_window.add_turn("user", message, metadata=analysis)
        self.metadata["turn_count"] += 1
        
        # Update active entities and topics if analysis is provided
        if analysis:
            if "entities" in analysis:
                self.active_entities.update(analysis["entities"])
                
                # Add entity-related facts to memory
                for entity in analysis["entities"]:
                    if entity not in self.memory.facts:
                        self.memory.add_fact(entity, f"User mentioned {entity}")
            
            if "domains" in analysis:
                self.active_topics.update(analysis["domains"])
                
                # Update topic importance
                for topic in analysis["domains"]:
                    self.memory.update_topic_importance(topic)
                    
            # Store preferences if detected
            if "preferences" in analysis:
                for category, value in analysis.get("preferences", {}).items():
                    self.memory.set_preference(category, value)
    
    def add_assistant_message(self, message: str, agent_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an assistant message to the context.
        
        Args:
            message: Assistant message
            agent_id: Identifier of the agent that generated the message
            metadata: Optional metadata about the message
        """
        if metadata is None:
            metadata = {}
            
        metadata["agent_id"] = agent_id
        
        self.active_window.add_turn("assistant", message, metadata=metadata)
        self.metadata["last_agent"] = agent_id
        
        # Add to interaction history in memory
        last_user_turn = next((turn for turn in reversed(self.active_window.get_turns()) 
                              if turn["role"] == "user"), None)
        
        if last_user_turn:
            self.memory.add_interaction(
                last_user_turn["content"], 
                message,
                metadata={"agent_id": agent_id}
            )
    
    def add_system_message(self, message: str) -> None:
        """
        Add a system message to the context.
        
        Args:
            message: System message
        """
        self.active_window.add_turn("system", message)
    
    def get_active_context(self) -> Dict[str, Any]:
        """
        Get the active context, including conversation window and relevant metadata.
        
        Returns:
            Dictionary with active context information
        """
        return {
            "conversation": self.active_window.get_turns(),
            "active_entities": list(self.active_entities),
            "active_topics": list(self.active_topics),
            "session_id": self.session_id,
            "turn_count": self.metadata["turn_count"],
            "last_agent": self.metadata["last_agent"],
        }
    
    def get_relevant_facts(self) -> List[str]:
        """
        Get facts relevant to the current conversation.
        
        Returns:
            List of relevant facts
        """
        relevant_facts = []
        
        # Get facts for active entities
        for entity in self.active_entities:
            entity_facts = self.memory.get_facts_about(entity)
            relevant_facts.extend([item["fact"] for item in entity_facts])
        
        return relevant_facts
    
    def get_formatted_history(self, include_system: bool = False, max_turns: Optional[int] = None) -> str:
        """
        Get formatted conversation history.
        
        Args:
            include_system: Whether to include system messages
            max_turns: Maximum number of turns to include
            
        Returns:
            Formatted conversation history
        """
        turns = self.active_window.get_turns()
        
        if not include_system:
            turns = [turn for turn in turns if turn["role"] != "system"]
            
        if max_turns is not None:
            turns = turns[-max_turns:]
            
        formatted = []
        for turn in turns:
            formatted.append(f"{turn['role'].upper()}: {turn['content']}")
            
        return "\n\n".join(formatted)
    
    def clear_active_window(self) -> None:
        """Clear the active conversation window but keep memory."""
        self.active_window.clear()
        
    def record_topic_completion(self, topic: str) -> None:
        """
        Record that a topic has been completed or resolved.
        
        Args:
            topic: The topic that has been completed
        """
        if topic in self.active_topics:
            self.active_topics.remove(topic)
            self.memory.update_topic_importance(topic, importance_delta=-0.5)
            
    def get_agent_performance(self, agent_id: str) -> Dict[str, Any]:
        """
        Get performance metrics for an agent.
        
        Args:
            agent_id: Identifier of the agent
            
        Returns:
            Dictionary with agent performance metrics
        """
        # Count interactions handled by this agent
        interactions = list(self.memory.interactions)
        agent_interactions = [
            interaction for interaction in interactions
            if interaction.get("metadata", {}).get("agent_id") == agent_id
        ]
        
        turns = self.active_window.get_turns()
        agent_turns = [
            turn for turn in turns
            if turn["role"] == "assistant" and turn.get("metadata", {}).get("agent_id") == agent_id
        ]
        
        return {
            "total_interactions": len(agent_interactions),
            "total_turns": len(agent_turns),
            "last_used": agent_turns[-1]["timestamp"] if agent_turns else None
        } 