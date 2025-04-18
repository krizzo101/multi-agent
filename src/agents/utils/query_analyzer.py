"""
Query Analyzer Utility

Provides utilities for analyzing user queries to extract structured information
such as intents, entities, knowledge domains, and complexity estimations.
"""

import logging
import re
import json
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class QueryAnalyzer:
    """Utility class for analyzing user queries."""
    
    # Common knowledge domains for categorization
    KNOWLEDGE_DOMAINS = [
        "science", "technology", "mathematics", "engineering", "medicine", "health",
        "biology", "chemistry", "physics", "computer science", "programming", "coding",
        "finance", "economics", "business", "marketing", "history", "art", "literature",
        "philosophy", "psychology", "sociology", "politics", "law", "education", 
        "language", "linguistics", "music", "entertainment", "sports", "travel",
        "cooking", "nutrition", "fitness", "environment", "geography", "astronomy",
        "statistics", "data science", "artificial intelligence", "machine learning",
        "web development", "mobile development", "cybersecurity", "blockchain",
        "cloud computing", "networking", "operating systems", "databases", "big data",
        "design", "agriculture", "architecture", "accounting", "human resources"
    ]
    
    # Complexity indicators with assigned weights
    COMPLEXITY_INDICATORS = {
        # Technical jargon
        r'\b(algorithm|implementation|architecture|framework|methodology)\b': 0.5,
        
        # Technical keywords by domain
        r'\b(neural network|machine learning|deep learning|reinforcement learning)\b': 0.6,
        r'\b(database|SQL|NoSQL|indexing|query optimization)\b': 0.5,
        r'\b(API|REST|GraphQL|microservices|distributed systems)\b': 0.5,
        r'\b(regression|classification|clustering|dimensionality reduction)\b': 0.6,
        
        # Indicates advanced or specialized topic
        r'\b(advanced|specialized|complex|intricate|sophisticated|detailed)\b': 0.4,
        
        # Comparative or evaluative words
        r'\b(compare|contrast|evaluate|assess|analyze|differentiate)\b': 0.3,
        
        # Multi-step or process-oriented request
        r'\b(steps to|process of|methodology for|approach to|strategy for)\b': 0.3,
        
        # Requirement for explanation
        r'\b(explain|elaborate|clarify|describe in detail)\b': 0.2,
        
        # Mathematical or scientific terms
        r'\b(equation|formula|theorem|calculus|statistical|quantum)\b': 0.5,
        
        # Question complexity indicators
        r'\b(why|how does|what causes|relationship between)\b': 0.2,
        
        # Simple question indicators (negative weights)
        r'^(what is|who is|when|where)\b': -0.3,
        r'^(can you|could you|will you|would you)\b': -0.2,
        
        # Simple tasks (negative weights)
        r'\b(list|show|tell me|give|find)\b': -0.1,
    }

    @staticmethod
    def extract_intent(query: str) -> str:
        """
        Extract the primary intent from the user query.
        
        Args:
            query: User query
            
        Returns:
            Primary intent
        """
        # Common intent patterns
        intent_patterns = [
            # Explanation intents
            (r'\b(explain|describe|clarify|define|elaborate on)\b', 'explain'),
            (r'\b(how does|how do|how can|how would)\b', 'explain how'),
            (r'\b(what is|what are|what does|what do)\b', 'explain what'),
            (r'\b(why is|why are|why does|why do)\b', 'explain why'),
            
            # Information seeking
            (r'\b(tell me about|information on|details about|learn about)\b', 'get information'),
            
            # Analysis intents
            (r'\b(analyze|examine|assess|evaluate|review)\b', 'analyze'),
            (r'\b(compare|contrast|differentiate|distinguish)\b', 'compare and contrast'),
            
            # Problem solving intents
            (r'\b(solve|fix|resolve|troubleshoot|debug)\b', 'solve problem'),
            (r'\b(how to|steps to|way to|method to)\b', 'find solution'),
            
            # Creation intents
            (r'\b(create|generate|make|produce|develop|build)\b', 'create'),
            (r'\b(design|draft|outline|sketch)\b', 'design'),
            (r'\b(write|compose|draft|author)\b', 'write'),
            (r'\b(code|program|implement|script)\b', 'code'),
            
            # Decision intents
            (r'\b(decide|choose|select|pick)\b', 'make decision'),
            (r'\b(should i|would it be|is it better)\b', 'get advice'),
            (r'\b(recommend|suggest|advise|propose)\b', 'get recommendation'),
            
            # Conversion/translation intents
            (r'\b(convert|translate|transform|change)\b', 'convert'),
            
            # Summary intents
            (r'\b(summarize|summarise|brief|overview|tldr)\b', 'summarize'),
        ]
        
        # Default intent
        default_intent = "general assistance"
        
        # Check for matches
        for pattern, intent in intent_patterns:
            if re.search(pattern, query.lower()):
                return intent
                
        return default_intent
    
    @staticmethod
    def estimate_complexity(query: str) -> Tuple[int, Dict[str, float]]:
        """
        Estimate the complexity of a query on a scale of 1-5.
        
        Args:
            query: User query
            
        Returns:
            Tuple of (complexity score, complexity indicators)
        """
        base_score = 2.0  # Start with a default complexity
        indicator_matches = {}
        
        # Apply complexity indicators
        for pattern, weight in QueryAnalyzer.COMPLEXITY_INDICATORS.items():
            if re.search(pattern, query.lower()):
                indicator_matches[pattern] = weight
                base_score += weight
        
        # Adjust based on query length (longer queries tend to be more complex)
        words = query.split()
        word_count = len(words)
        
        # Adjust score based on query length
        if word_count < 5:
            length_adjustment = -0.5
        elif word_count < 10:
            length_adjustment = 0
        elif word_count < 20:
            length_adjustment = 0.5
        else:
            length_adjustment = 1.0
            
        base_score += length_adjustment
        
        # Adjust based on sentence structure
        # More sentences often indicate more complex questions
        sentences = [s for s in re.split(r'[.!?]', query) if s.strip()]
        if len(sentences) >= 3:
            base_score += 0.5
            
        # Check for multiple questions in one query
        question_marks = query.count('?')
        if question_marks > 1:
            base_score += 0.5 * question_marks
            
        # Ensure score is within valid range (1-5)
        final_score = max(1, min(5, round(base_score)))
        
        return final_score, indicator_matches
            
    @staticmethod
    def extract_entities(query: str) -> List[str]:
        """
        Extract key entities from the query.
        
        Args:
            query: User query
            
        Returns:
            List of extracted entities
        """
        entities = []
        
        # Extract quoted phrases as specific entities
        quoted = re.findall(r'"([^"]*)"', query)
        entities.extend(quoted)
        
        # Extract potential noun phrases using simple patterns
        # This is a simplified approach - in production, consider using NLP libraries
        
        # Look for capitalized phrases (potential proper nouns)
        capitalized = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', query)
        entities.extend(capitalized)
        
        # Look for technical terms with specific patterns
        technical_terms = re.findall(r'\b([a-zA-Z]+(?:[_\-\.][a-zA-Z0-9]+)+)\b', query)
        entities.extend(technical_terms)
        
        # Remove duplicates and sort by length (longer entities first)
        unique_entities = list(set(entities))
        unique_entities.sort(key=len, reverse=True)
        
        return unique_entities
    
    @staticmethod
    def identify_domains(query: str) -> List[str]:
        """
        Identify knowledge domains relevant to the query.
        
        Args:
            query: User query
            
        Returns:
            List of relevant knowledge domains
        """
        query_lower = query.lower()
        matching_domains = []
        
        # Check for direct mentions of domains
        for domain in QueryAnalyzer.KNOWLEDGE_DOMAINS:
            if domain.lower() in query_lower:
                matching_domains.append(domain)
                
        return matching_domains
    
    @staticmethod
    def is_followup(query: str, conversation_history: List[Dict[str, Any]]) -> bool:
        """
        Determine if the query is a follow-up to a previous conversation.
        
        Args:
            query: User query
            conversation_history: Previous conversation turns
            
        Returns:
            True if query is likely a follow-up
        """
        if not conversation_history:
            return False
            
        # Check for explicit follow-up markers
        followup_markers = [
            r'\balso\b', r'\btoo\b', r'\banother\b', r'\bmore\b', 
            r'\bagain\b', r'\bfurther\b', r'\badditional\b',
            r'\binstead\b', r'\bhowever\b', r'\bbut\b', r'\band\b',
            r'^(so|then|therefore|thus|hence)', 
            r'^(what|how|why|when|where|who|which) (about|if|is|are|do|does)',
            r'^(can|could) (you|i|we|they|it)'
        ]
        
        for pattern in followup_markers:
            if re.search(pattern, query.lower()):
                return True
                
        # Check for very short queries (likely follow-ups)
        if len(query.split()) <= 3:
            return True
            
        # Check for pronouns referring to previous context
        pronoun_patterns = [
            r'\b(it|this|that|these|those|they|them|their|its)\b',
            r'\b(he|she|him|her|his)\b'
        ]
        
        for pattern in pronoun_patterns:
            if re.search(pattern, query.lower()):
                return True
                
        return False
    
    @staticmethod
    def analyze_query(query: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a user query.
        
        Args:
            query: User query
            conversation_history: Optional conversation history for context
            
        Returns:
            Dictionary with analysis results
        """
        try:
            if conversation_history is None:
                conversation_history = []
                
            # Extract primary intent
            primary_intent = QueryAnalyzer.extract_intent(query)
            
            # Estimate query complexity
            complexity, complexity_indicators = QueryAnalyzer.estimate_complexity(query)
            
            # Extract entities
            entities = QueryAnalyzer.extract_entities(query)
            
            # Identify knowledge domains
            domains = QueryAnalyzer.identify_domains(query)
            
            # Check if this is a follow-up question
            is_followup = QueryAnalyzer.is_followup(query, conversation_history)
            
            # Create structured analysis result
            analysis = {
                "query": query,
                "primary_intent": primary_intent,
                "complexity": complexity,
                "complexity_indicators": complexity_indicators,
                "entities": entities,
                "domains": domains,
                "is_followup": is_followup,
                "topics": []  # Placeholder for topic extraction (can be expanded later)
            }
            
            logger.info(f"Query analysis complete: intent={primary_intent}, complexity={complexity}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing query: {str(e)}")
            # Return basic analysis with default values on error
            return {
                "query": query,
                "primary_intent": "general assistance",
                "complexity": 2,
                "entities": [],
                "domains": [],
                "is_followup": False,
                "topics": []
            } 