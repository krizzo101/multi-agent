#!/usr/bin/env python3
"""
Example demonstrating the use of the tracing utility with agent operations.

This example shows how to:
1. Initialize the tracer
2. Trace function calls
3. Create custom spans
4. Add events and attributes to spans
5. Profile performance of code sections
6. Handle exceptions with proper error tracing

Run this example with:
    python examples/trace_agent_example.py

To view with OpenTelemetry:
    export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces
    python examples/trace_agent_example.py
"""

import os
import sys
import time
import random
import logging
from typing import Dict, Any, List

# Add the src directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import agent and tracer modules
from src.agents.utils.tracer import get_tracer, traced, span, profile
from src.agents.utils.metrics_collector import MetricsCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
tracer = get_tracer(service_name="agent-example")
metrics = MetricsCollector()

# Example Agent class
class ExampleAgent:
    """Simple agent class for demonstration purposes."""
    
    def __init__(self, agent_id: str, capabilities: List[str]):
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.response_time = random.uniform(0.1, 2.0)  # Simulated response time
    
    @traced(name="agent.process_query")
    def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a query and return a response."""
        context = context or {}
        
        # Add attributes to current span
        tracer.set_attribute("agent.id", self.agent_id)
        tracer.set_attribute("query.length", len(query))
        
        # Track request in metrics
        request_id = metrics.track_request(
            agent_id=self.agent_id,
            query=query,
            context=context
        )
        
        try:
            # Analyze query intent
            with span("analyze_intent") as intent_span:
                intent, entities = self._analyze_intent(query)
                tracer.set_attribute("query.intent", intent)
                
                # Add entities as an event
                tracer.add_event("entities_extracted", {
                    "count": len(entities),
                    "entities": entities
                })
            
            # Process the query based on intent
            response = self._generate_response(intent, entities, context)
            
            # Simulate different response times
            with profile("response_generation", threshold_ms=500):
                time.sleep(self.response_time)
            
            # Track successful response
            metrics.track_response(
                request_id=request_id,
                agent_id=self.agent_id,
                status="success",
                tokens_used=len(response["text"].split()),
                latency_ms=self.response_time * 1000
            )
            
            return response
            
        except Exception as e:
            # Record the exception
            tracer.record_exception(e)
            
            # Track error
            metrics.track_error(
                request_id=request_id,
                agent_id=self.agent_id,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            
            # Re-raise the exception
            raise
    
    def _analyze_intent(self, query: str) -> tuple:
        """Analyze the intent and entities in a query."""
        # Simulate intent analysis
        intents = {
            "what": "information_request",
            "how": "process_inquiry",
            "why": "explanation_request",
            "when": "time_inquiry",
            "where": "location_inquiry"
        }
        
        # Extract first word to determine intent
        first_word = query.strip().split()[0].lower() if query.strip() else ""
        intent = intents.get(first_word, "general_query")
        
        # Extract simple entities (just words longer than 4 chars)
        entities = [word for word in query.split() if len(word) > 4]
        
        return intent, entities
    
    def _generate_response(self, intent: str, entities: List[str], 
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a response based on intent and entities."""
        # Simple response generation logic
        response_templates = {
            "information_request": "Here's information about {entities}.",
            "process_inquiry": "The process for {entities} works as follows...",
            "explanation_request": "The reason for {entities} is...",
            "time_inquiry": "The timing for {entities} is typically...",
            "location_inquiry": "The location for {entities} is...",
            "general_query": "I understand you're asking about {entities}."
        }
        
        entity_text = ", ".join(entities) if entities else "your query"
        response_text = response_templates.get(intent, "I'm not sure how to respond.").format(
            entities=entity_text
        )
        
        # Simulated follow-up questions based on intent
        follow_ups = [
            f"Would you like to know more about {entity}?" for entity in entities[:2]
        ]
        
        # Generate the final response
        response = {
            "text": response_text,
            "intent": intent,
            "identified_entities": entities,
            "follow_up_questions": follow_ups,
            "confidence": random.uniform(0.7, 0.99)
        }
        
        # Simulate occasional slow operations
        if random.random() < 0.2:
            with profile("advanced_processing", threshold_ms=300):
                time.sleep(random.uniform(0.3, 0.8))
                response["enhanced_data"] = {"additional_insights": "Some valuable insights here"}
                
        return response


# Example Proxy class
class SimpleAgentProxy:
    """Simple proxy that routes to different agents based on capabilities."""
    
    def __init__(self):
        # Initialize some example agents
        self.agents = {
            "general": ExampleAgent("general", ["general_query", "information_request"]),
            "technical": ExampleAgent("technical", ["process_inquiry", "explanation_request"]),
            "assistant": ExampleAgent("assistant", ["time_inquiry", "location_inquiry"])
        }
    
    @traced(name="proxy.route_query")
    def route_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Route a query to the appropriate agent based on the query content."""
        context = context or {}
        
        # Select an agent
        with span("agent_selection"):
            agent_id = self._select_agent(query)
            tracer.set_attribute("selected_agent", agent_id)
        
        # Get the agent
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent '{agent_id}' not found")
        
        # Process the query with the selected agent
        with span("agent_processing"):
            return agent.process_query(query, context)
    
    def _select_agent(self, query: str) -> str:
        """Select the appropriate agent based on the query."""
        # Simple selection based on keywords
        technical_keywords = ["how", "process", "code", "build", "make", "create"]
        assistant_keywords = ["when", "where", "schedule", "time", "location"]
        
        query_lower = query.lower()
        
        for keyword in technical_keywords:
            if keyword in query_lower:
                return "technical"
                
        for keyword in assistant_keywords:
            if keyword in query_lower:
                return "assistant"
        
        # Default to general agent
        return "general"


def run_demo():
    """Run a demonstration of the agent system with tracing."""
    # Create the main operation span
    with span("agent_demo", attributes={"demo.type": "tracing_example"}):
        # Create a proxy
        proxy = SimpleAgentProxy()
        
        # Prepare some example queries
        queries = [
            "What is machine learning?",
            "How do I build a web application?",
            "Why does my code crash?",
            "When is the next meeting scheduled?",
            "Where is the documentation for this library?"
        ]
        
        # Process each query
        for i, query in enumerate(queries):
            logger.info(f"Processing query {i+1}: '{query}'")
            
            try:
                # Process the query with the proxy
                with span(f"process_query_{i}", attributes={"query.text": query}):
                    response = proxy.route_query(query, context={"session_id": f"demo-{i}"})
                    
                    # Log the response
                    logger.info(f"Response: {response['text']}")
                    
                    # Simulate user feedback (80% positive)
                    if random.random() < 0.8:
                        satisfaction = random.uniform(0.7, 1.0)
                        feedback = "helpful"
                    else:
                        satisfaction = random.uniform(0.3, 0.7)
                        feedback = "partially helpful"
                    
                    # Track feedback
                    metrics.track_user_feedback(
                        agent_id=response.get("agent_id", "unknown"),
                        request_id=f"demo-{i}",
                        rating=satisfaction,
                        feedback=feedback
                    )
                    
                    # Add slight delay between queries
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Error processing query '{query}': {e}")
        
        # Print metrics summary
        logger.info("=== Metrics Summary ===")
        system_metrics = metrics.get_system_metrics()
        logger.info(f"Total requests: {system_metrics['total_requests']}")
        logger.info(f"Avg response time: {system_metrics['average_response_time_ms']:.2f}ms")
        logger.info(f"Success rate: {system_metrics['success_rate']*100:.2f}%")
        
        # Print agent-specific metrics
        for agent_id in proxy.agents:
            agent_metrics = metrics.get_agent_metrics(agent_id)
            if agent_metrics["request_count"] > 0:
                logger.info(f"\nAgent '{agent_id}' metrics:")
                logger.info(f"  Requests: {agent_metrics['request_count']}")
                logger.info(f"  Avg response: {agent_metrics['average_response_time_ms']:.2f}ms")
                logger.info(f"  Success rate: {agent_metrics['success_rate']*100:.2f}%")


if __name__ == "__main__":
    # Run the demo
    try:
        run_demo()
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        sys.exit(1) 