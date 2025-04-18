#!/usr/bin/env python
"""
Test script for sending traces to Jaeger.

This script demonstrates how to configure and use different exporters to send trace data 
to Jaeger, including both OTLP HTTP and Jaeger's native protocols.
"""

import os
# Set environment variable for protobuf compatibility
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import sys
import time
import random
import logging
import argparse
from datetime import datetime
from typing import Optional, Dict, List, Any

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the required OpenTelemetry modules
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

# Import our tracing utility
from src.agents.utils.tracer import configure_tracing, AgentTracer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Test sending traces to Jaeger")
    parser.add_argument(
        "--exporter", 
        choices=["console", "otlp", "jaeger", "all"], 
        default="console",
        help="Exporter type to use"
    )
    parser.add_argument(
        "--jaeger-host",
        type=str,
        default="localhost",
        help="Jaeger host"
    )
    parser.add_argument(
        "--jaeger-port",
        type=int,
        default=16686,
        help="Jaeger UI port"
    )
    parser.add_argument(
        "--otlp-endpoint",
        type=str,
        default="localhost:4318",
        help="OTLP endpoint"
    )
    parser.add_argument(
        "--protocol",
        choices=["grpc", "http", "thrift"],
        default="http",
        help="Protocol to use for exporting"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Number of iterations for test spans"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    return parser.parse_args()

def create_random_work(tracer: AgentTracer, iteration: int, complexity: int) -> None:
    """
    Perform some random "work" with nested spans for testing.
    
    Args:
        tracer: The tracer to use
        iteration: Current iteration
        complexity: How complex the work should be (more spans)
    """
    with tracer.start_as_current_span(f"work_iteration_{iteration}") as parent_span:
        parent_span.set_attribute("iteration", iteration)
        parent_span.set_attribute("timestamp", datetime.now().isoformat())
        
        # Simulate some work
        time.sleep(random.uniform(0.05, 0.2))
        
        # Create child spans based on complexity
        for i in range(complexity):
            with tracer.start_as_current_span(f"sub_task_{i}") as child_span:
                child_span.set_attribute("sub_task_id", i)
                
                # Randomly add an event
                if random.random() > 0.5:
                    child_span.add_event("processing", {"progress": f"{random.randint(1, 100)}%"})
                
                # Simulate work in the subtask
                time.sleep(random.uniform(0.01, 0.1))
                
                # Randomly introduce deeper spans
                if random.random() > 0.7 and complexity > 1:
                    with tracer.start_as_current_span("detailed_operation") as op_span:
                        op_span.set_attribute("operation_type", "data_processing")
                        time.sleep(random.uniform(0.01, 0.05))
                
                # Randomly introduce errors
                if random.random() > 0.9:
                    try:
                        raise ValueError("Simulated error in processing")
                    except ValueError as e:
                        child_span.record_exception(e)
                        child_span.set_status(trace.StatusCode.ERROR, str(e))
                        logger.warning(f"Simulated error in sub_task_{i}")

def main():
    """Main entry point"""
    args = parse_args()
    
    # Configure logging level
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger.setLevel(log_level)
    
    service_name = "jaeger-test-app"
    tracers = []
    
    # Configure the tracers based on the exporter choice
    if args.exporter in ["console", "all"]:
        console_tracer = configure_tracing(
            service_name=f"{service_name}-console",
            exporter_type="console"
        )
        tracers.append(("Console", console_tracer))
    
    if args.exporter in ["otlp", "all"]:
        otlp_tracer = configure_tracing(
            service_name=f"{service_name}-otlp",
            exporter_type="otlp",
            endpoint=args.otlp_endpoint,
            otlp_protocol=args.protocol if args.protocol != "thrift" else "http"
        )
        tracers.append(("OTLP", otlp_tracer))
    
    if args.exporter in ["jaeger", "all"]:
        # For Jaeger direct export
        jaeger_endpoint = f"{args.jaeger_host}:{args.jaeger_port}"
        if args.protocol == "http":
            jaeger_port = 14268  # Default Jaeger HTTP collector port
            jaeger_endpoint = f"{args.jaeger_host}:{jaeger_port}"
        elif args.protocol == "grpc":
            jaeger_port = 14250  # Default Jaeger gRPC collector port
            jaeger_endpoint = f"{args.jaeger_host}:{jaeger_port}"
        else:  # thrift
            jaeger_port = 6831  # Default Jaeger thrift compact port
            jaeger_endpoint = f"{args.jaeger_host}:{jaeger_port}"
            
        jaeger_tracer = configure_tracing(
            service_name=f"{service_name}-jaeger",
            exporter_type="jaeger",
            endpoint=jaeger_endpoint,
            jaeger_protocol=args.protocol
        )
        tracers.append(("Jaeger", jaeger_tracer))
    
    # Validate that we have at least one tracer
    if not tracers:
        logger.error("No valid exporters configured")
        return
    
    # Log the configured exporters
    for name, _ in tracers:
        logger.info(f"Configured {name} exporter")
    
    # Run the test for each configured tracer
    for name, tracer in tracers:
        logger.info(f"Running test with {name} exporter")
        
        with tracer.start_as_current_span(f"test_run_{name}"):
            for i in range(args.iterations):
                # Complexity increases with iteration
                complexity = random.randint(1, 5)
                logger.info(f"Iteration {i+1}/{args.iterations} with complexity {complexity}")
                create_random_work(tracer, i, complexity)
                
                # Short delay between iterations
                if i < args.iterations - 1:
                    time.sleep(0.5)
        
        logger.info(f"Test with {name} exporter completed")
    
    # Add a delay to ensure all spans are exported
    logger.info("Waiting for spans to be exported...")
    time.sleep(5)
    logger.info("Test complete")

if __name__ == "__main__":
    main() 