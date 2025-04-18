"""
Prompt Generator Utility

Provides utilities for generating specialized system prompts and
analyzing user queries to create optimized agent configurations.
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class PromptGenerator:
    """Utility class for generating specialized system prompts based on query analysis."""
    
    @staticmethod
    def extract_expertise_areas(entities: List[str], domains: List[str], 
                              topics: List[str]) -> List[str]:
        """
        Extract key expertise areas from analysis results.
        
        Args:
            entities: List of entities mentioned
            domains: List of knowledge domains
            topics: List of topics
            
        Returns:
            List of expertise areas
        """
        # Combine all sources of expertise areas
        combined = set(entities + domains + topics)
        
        # Filter out generic or low-value terms
        generic_terms = {
            'question', 'help', 'information', 'explanation', 'details',
            'problem', 'issue', 'topic', 'subject', 'matter', 'thing'
        }
        
        return [term for term in combined if term.lower() not in generic_terms]
    
    @staticmethod
    def determine_agent_type(intent: str, complexity: int) -> str:
        """
        Determine the type of agent needed based on intent and complexity.
        
        Args:
            intent: Primary intent of the query
            complexity: Estimated complexity (1-5)
            
        Returns:
            Agent type descriptor
        """
        # Map intents to agent types
        intent_map = {
            'explain': 'Educator',
            'teach': 'Educator',
            'learn': 'Educator',
            'understand': 'Educator',
            'summarize': 'Analyzer',
            'analyze': 'Analyzer',
            'evaluate': 'Analyzer',
            'review': 'Analyzer',
            'compare': 'Analyzer',
            'create': 'Creator',
            'generate': 'Creator',
            'design': 'Creator',
            'develop': 'Creator',
            'plan': 'Strategist',
            'strategize': 'Strategist',
            'solve': 'Problem Solver',
            'fix': 'Problem Solver',
            'troubleshoot': 'Problem Solver',
            'debug': 'Problem Solver',
            'decide': 'Decision Support',
            'choose': 'Decision Support',
            'recommend': 'Advisor'
        }
        
        # Extract the root intent from the full intent string
        root_intent = None
        for key in intent_map:
            if key in intent.lower():
                root_intent = key
                break
        
        agent_type = intent_map.get(root_intent, 'Specialist')
        
        # Adjust for complexity
        if complexity >= 4:
            prefixes = ['Senior ', 'Principal ', 'Lead ', 'Expert ', 'Master ']
            # Use complexity to index into prefixes (4->0, 5->1)
            prefix = prefixes[complexity - 4]
            agent_type = f"{prefix}{agent_type}"
        
        return agent_type
    
    @staticmethod
    def generate_system_prompt(analysis: Dict[str, Any]) -> str:
        """
        Generate a specialized system prompt based on query analysis.
        
        Args:
            analysis: Query analysis results
            
        Returns:
            Tailored system prompt
        """
        try:
            # Extract key information
            intent = analysis.get('primary_intent', 'general assistance')
            complexity = analysis.get('complexity', 3)
            expertise_areas = PromptGenerator.extract_expertise_areas(
                analysis.get('entities', []),
                analysis.get('domains', []),
                analysis.get('topics', [])
            )
            is_followup = analysis.get('is_followup', False)
            
            # Determine agent type
            agent_type = PromptGenerator.determine_agent_type(intent, complexity)
            
            # Build expertise descriptor
            expertise_str = ""
            if expertise_areas:
                # Format expertise areas as a list for better prompt structure
                if len(expertise_areas) == 1:
                    expertise_str = f" specializing in {expertise_areas[0]}"
                elif len(expertise_areas) == 2:
                    expertise_str = f" specializing in {expertise_areas[0]} and {expertise_areas[1]}"
                else:
                    formatted_areas = ", ".join(expertise_areas[:-1]) + f", and {expertise_areas[-1]}"
                    expertise_str = f" specializing in {formatted_areas}"
            
            # Generate the system prompt
            system_prompt = f"You are a {agent_type}{expertise_str}."
            
            # Add more details based on complexity
            if complexity >= 3:
                system_prompt += f"\n\nYour goal is to {intent} with precision and expertise."
                
                # Add guidance on communication style
                if 'explain' in intent.lower() or 'teach' in intent.lower():
                    system_prompt += "\n\nCommunicate complex ideas clearly, using analogies and examples where helpful."
                    
                elif 'analyze' in intent.lower() or 'evaluate' in intent.lower():
                    system_prompt += "\n\nProvide thorough analysis with attention to detail and logical reasoning."
                    
                elif 'create' in intent.lower() or 'generate' in intent.lower():
                    system_prompt += "\n\nBe innovative while remaining practical and focused on the user's needs."
                    
                elif 'solve' in intent.lower() or 'fix' in intent.lower():
                    system_prompt += "\n\nApproach problems methodically, explaining your reasoning at each step."
            
            # Add additional instructions for highest complexity
            if complexity >= 4:
                system_prompt += "\n\nLeverage your deep expertise to provide insights that might not be immediately obvious."
                
                if expertise_areas:
                    system_prompt += f"\n\nDraw on the latest understanding and best practices in {', '.join(expertise_areas)}."
            
            logger.info(f"Generated system prompt for {agent_type} with complexity {complexity}")
            return system_prompt
            
        except Exception as e:
            logger.error(f"Error generating system prompt: {str(e)}")
            return "You are a helpful assistant. Provide accurate and relevant information to the user's questions."
    
    @staticmethod
    def generate_prompt_preamble(query: str, analysis: Dict[str, Any]) -> str:
        """
        Generate a prompt preamble to better frame the user's query.
        
        Args:
            query: User's original query
            analysis: Query analysis results
            
        Returns:
            Prompt preamble text
        """
        try:
            intent = analysis.get('primary_intent', '').lower()
            complexity = analysis.get('complexity', 3)
            
            # Skip preamble for simple queries or followups
            if complexity < 3 or analysis.get('is_followup', False):
                return ""
                
            # Extract key information
            expertise_areas = PromptGenerator.extract_expertise_areas(
                analysis.get('entities', []),
                analysis.get('domains', []),
                analysis.get('topics', [])
            )
            
            # Format expertise context
            expertise_context = ""
            if expertise_areas:
                expertise_context = f"in the context of {', '.join(expertise_areas)}"
            
            # Generate appropriate preambles for different intents
            if any(term in intent for term in ['explain', 'teach', 'learn']):
                return f"I'll explain this {expertise_context} in a structured and clear way."
                
            elif any(term in intent for term in ['analyze', 'evaluate', 'assess']):
                return f"I'll analyze this {expertise_context} thoroughly, considering different perspectives."
                
            elif any(term in intent for term in ['create', 'generate', 'design']):
                return f"I'll create this {expertise_context} with attention to quality and your requirements."
                
            elif any(term in intent for term in ['solve', 'fix', 'trouble']):
                return f"I'll solve this problem {expertise_context} using a systematic approach."
                
            elif any(term in intent for term in ['compare', 'contrast']):
                return f"I'll compare these {expertise_context} highlighting key similarities and differences."
                
            elif any(term in intent for term in ['recommend', 'suggest']):
                return f"I'll provide recommendations {expertise_context} based on best practices."
                
            # Default preamble for other intents
            return f"I'll address your query {expertise_context} with the appropriate expertise and depth."
            
        except Exception as e:
            logger.error(f"Error generating prompt preamble: {str(e)}")
            return ""

    @staticmethod
    def adjust_temperature(intent: str, complexity: int) -> float:
        """
        Adjust temperature based on intent and complexity.
        
        Args:
            intent: Primary intent
            complexity: Complexity level (1-5)
            
        Returns:
            Appropriate temperature value (0.0-1.0)
        """
        # Base temperature mapping by intent type
        intent_temps = {
            # Factual/analytical intents (lower temperature)
            'explain': 0.3,
            'analyze': 0.2,
            'summarize': 0.2,
            'calculate': 0.1,
            'solve': 0.2,
            'troubleshoot': 0.2,
            'debug': 0.2,
            
            # Creative/generative intents (higher temperature)
            'create': 0.7,
            'generate': 0.7,
            'design': 0.6,
            'brainstorm': 0.8,
            'imagine': 0.8,
            
            # Decision/recommendation intents (moderate temperature)
            'recommend': 0.4,
            'suggest': 0.5,
            'advise': 0.4,
            'decide': 0.4
        }
        
        # Find matching intent
        temp = 0.5  # Default
        for key, value in intent_temps.items():
            if key in intent.lower():
                temp = value
                break
        
        # Adjust for complexity - higher complexity slightly increases temperature
        # to allow for more nuanced responses, except for very factual queries
        if 'explain' in intent.lower() or 'analyze' in intent.lower() or 'calculate' in intent.lower():
            # For factual queries, keep temperature low regardless of complexity
            temp = min(temp + 0.05 * (complexity - 3), 0.4)
        else:
            # For other queries, adjust based on complexity
            temp = temp + 0.05 * (complexity - 3)
            
        # Ensure temperature is within valid range
        return max(0.1, min(0.9, temp)) 