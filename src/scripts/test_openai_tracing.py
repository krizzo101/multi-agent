#!/usr/bin/env python
"""
Test script for OpenTelemetry tracing with OpenAI API calls.

This script demonstrates how to use the AgentTracer utility to trace OpenAI API calls
and visualize them in Jaeger or via OTLP.
"""

import os
# Set environment variable for protobuf compatibility
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import sys
import argparse
import logging
import time
from typing import Dict, List, Any, Optional
import dataclasses
from openai.types.chat import ChatCompletionMessageParam

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import our tracing utility
from src.agents.utils.tracer import configure_tracing, AgentTracer

# Check if openai is installed
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI package not installed. Please install it with 'pip install openai'")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@dataclasses.dataclass
class TestConfig:
    """Configuration for test methods"""
    model: str = "o3-mini",
    temperature: float = 0.7,
    max_tokens: int = 1000,
    top_p: float = 1.0,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Test OpenTelemetry tracing with OpenAI")
    parser.add_argument(
        "--exporter", 
        choices=["console", "otlp", "jaeger"], 
        default="console",
        help="Exporter type to use"
    )
    parser.add_argument(
        "--endpoint", 
        type=str, 
        default=None,
        help="Endpoint for the exporter (e.g., localhost:4317 for OTLP)"
    )
    parser.add_argument(
        "--protocol", 
        choices=["grpc", "http", "thrift"], 
        default="http",
        help="Protocol to use for the exporter"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug logging"
    )
    return parser.parse_args()

@AgentTracer.trace_method()
def get_openai_completion(
    client: OpenAI,
    prompt: str,
    model: str = "o3-mini",
    temperature: float = 0.7,
    max_tokens: int = 1000
) -> str:
    """
    Get a completion from OpenAI.
    
    Args:
        client: OpenAI client
        prompt: The prompt to generate a completion for
        model: The model to use
        temperature: Temperature for response generation
        max_tokens: Maximum tokens to generate
        
    Returns:
        Generated completion text
    """
    messages = [{"role": "user", "content": prompt}]
    
    # Add span event for calling OpenAI
    from opentelemetry import trace
    current_span = trace.get_current_span()
    current_span.add_event("Calling OpenAI API", {
        "prompt": prompt,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens
    })
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        completion_text = response.choices[0].message.content
        token_usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        
        # Record token usage in span
        for key, value in token_usage.items():
            current_span.set_attribute(f"openai.usage.{key}", value)
            
        current_span.add_event("Received OpenAI response", {
            "tokens_used": token_usage["total_tokens"]
        })
        
        return completion_text
    
    except Exception as e:
        current_span.record_exception(e)
        current_span.set_status(trace.StatusCode.ERROR, str(e))
        logger.error(f"Error getting completion: {str(e)}")
        return f"Error: {str(e)}"

def main():
    """Main entry point"""
    args = parse_args()
    
    # Configure logging level
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger.setLevel(log_level)
    
    # Determine exporter protocol
    protocol = args.protocol
    if args.exporter == "otlp" and protocol == "thrift":
        protocol = "http"  # OTLP doesn't support thrift
    
    # Configure tracing
    if args.exporter == "jaeger":
        tracer = configure_tracing(
            service_name="openai-tracing-test",
            exporter_type="jaeger",
            endpoint=args.endpoint or "localhost:16686",
            jaeger_protocol=protocol
        )
    elif args.exporter == "otlp":
        tracer = configure_tracing(
            service_name="openai-tracing-test",
            exporter_type="otlp",
            endpoint=args.endpoint or "localhost:4318",
            otlp_protocol=protocol
        )
    else:  # Default to console
        tracer = configure_tracing(
            service_name="openai-tracing-test",
            exporter_type="console"
        )
    
    logger.info(f"Configured OpenTelemetry tracing with {args.exporter} exporter")
    
    # Check for OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return
    
    if not OPENAI_AVAILABLE:
        logger.error("OpenAI package not installed")
        return
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # List of prompts to try
    prompts = [
        "What is the capital of France?",
        "Explain quantum computing in simple terms",
        "Write a short poem about OpenTelemetry"
    ]
    
    # Process each prompt with tracing
    with tracer.start_as_current_span("process_multiple_prompts"):
        for i, prompt in enumerate(prompts):
            with tracer.start_as_current_span(f"process_prompt_{i}"):
                logger.info(f"Processing prompt: {prompt}")
                result = get_openai_completion(client, prompt)
                logger.info(f"Result: {result[:50]}...")
                
                # Add a small delay between requests
                if i < len(prompts) - 1:
                    time.sleep(1)
    
    logger.info("Tracing test complete")
    
    # Add a delay to ensure all spans are exported
    time.sleep(2)

if __name__ == "__main__":
    main() 