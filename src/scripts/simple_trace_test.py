#!/usr/bin/env python3
"""
Simple OpenTelemetry Tracing Test

This script demonstrates basic functionality of the OpenTelemetry tracing system
with the console exporter only. It doesn't require any optional dependencies like
Jaeger or OTLP exporters, making it ideal for verifying the core functionality.
"""

import os
import sys
import time
import logging
import random
from typing import Dict, Any

# Set environment variable to use pure Python implementation to avoid protobuf issues
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("trace-test")

# Import OpenTelemetry core components
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace.status import StatusCode
except ImportError:
    logger.error("OpenTelemetry packages not found. Please install them with:")
    logger.error("pip install opentelemetry-api opentelemetry-sdk")
    sys.exit(1)

def create_attributes() -> Dict[str, Any]:
    """Create a set of random attributes for demonstration purposes."""
    return {
        "service.random_value": random.randint(1, 100),
        "operation.timestamp": time.time(),
        "custom.dimension": random.choice(["dimension1", "dimension2", "dimension3"])
    }

def main() -> None:
    """Run a simple trace test with console exporter."""
    logger.info("Starting simple OpenTelemetry trace test")
    
    # Create a resource with service information
    resource = Resource.create({
        "service.name": "trace-test-service",
        "service.version": "0.1.0",
        "deployment.environment": "test"
    })
    
    # Create a tracer provider
    tracer_provider = TracerProvider(resource=resource)
    
    # Create and register a console exporter
    console_exporter = ConsoleSpanExporter()
    span_processor = BatchSpanProcessor(console_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    # Set the global tracer provider
    trace.set_tracer_provider(tracer_provider)
    
    # Get a tracer
    tracer = trace.get_tracer("test-tracer")
    
    # Create a parent span
    logger.info("Creating main operation span")
    with tracer.start_as_current_span("main_operation") as main_span:
        # Set some attributes on the span
        main_span.set_attribute("operation.type", "test")
        main_span.set_attribute("operation.id", f"test-{random.randint(1000, 9999)}")
        
        # Add an event to the span
        main_span.add_event(
            name="operation.started",
            attributes={"timestamp": time.time()}
        )
        
        logger.info("Main operation in progress...")
        
        # Simulate some work
        time.sleep(0.5)
        
        # Create a child span
        logger.info("Creating sub-operation span")
        with tracer.start_as_current_span("sub_operation") as child_span:
            # Set attributes on child span
            child_span.set_attribute("sub_operation.type", "data_processing")
            
            for i in range(3):
                # Add some random attributes
                attributes = create_attributes()
                logger.info(f"Processing batch {i+1} with attributes: {attributes}")
                
                # Record the work as an event
                child_span.add_event(
                    name=f"batch.processed",
                    attributes={
                        "batch.id": i+1,
                        "batch.items": random.randint(10, 100),
                        "batch.processing_time_ms": random.randint(50, 200)
                    }
                )
                
                # Simulate processing time
                time.sleep(0.2)
            
            # Add success status to child span
            child_span.set_status(StatusCode.OK)
            logger.info("Sub-operation completed successfully")
        
        # Simulate more work in the parent span
        time.sleep(0.3)
        
        # Add a completion event to the main span
        main_span.add_event(
            name="operation.completed",
            attributes={
                "timestamp": time.time(),
                "result": "success"
            }
        )
        
        logger.info("Main operation completed")
    
    # Ensure all spans are exported
    span_processor.force_flush()
    logger.info("Test completed. Spans have been exported to the console.")

if __name__ == "__main__":
    main() 