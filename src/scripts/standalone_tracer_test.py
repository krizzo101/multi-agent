#!/usr/bin/env python
"""
Standalone OpenTelemetry tracer test with minimal dependencies.

This script tests the basic functionality of the OpenTelemetry tracing system
using only the Console exporter, which doesn't have external dependencies.
"""

import os
import time
import logging
import sys
from typing import Dict, Any, Optional
from contextlib import contextmanager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Set environment variable for protobuf compatibility
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

def main():
    """Test OpenTelemetry tracing with Console exporter."""
    print("Testing OpenTelemetry with Console exporter...")
    logger.info("Testing OpenTelemetry with Console exporter...")
    
    try:
        # Import OpenTelemetry packages
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        
        # Create a resource with service information
        resource = Resource.create(attributes={
            SERVICE_NAME: "standalone-tracer-test"
        })
        
        # Set up the tracer provider with console export
        provider = TracerProvider(resource=resource)
        console_exporter = ConsoleSpanExporter()
        console_processor = BatchSpanProcessor(console_exporter)
        provider.add_span_processor(console_processor)
        trace.set_tracer_provider(provider)
        
        # Create a tracer
        tracer = trace.get_tracer(__name__)
        
        # Create a MinimalTracer helper class
        class MinimalTracer:
            """A minimal tracer class with essential functionality."""
            
            def __init__(self, service_name: str = "minimal-tracer"):
                self._tracer = trace.get_tracer(service_name)
            
            @contextmanager
            def start_as_current_span(
                self, 
                name: str, 
                attributes: Optional[Dict[str, Any]] = None
            ):
                """Start a span as the current active span."""
                with self._tracer.start_as_current_span(
                    name=name, 
                    attributes=attributes
                ) as span:
                    yield span
            
            def set_attribute(self, key: str, value: Any) -> None:
                """Set an attribute on the current span."""
                trace.get_current_span().set_attribute(key, value)
            
            def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
                """Add an event to the current span."""
                trace.get_current_span().add_event(name, attributes=attributes)
        
        # Create an instance of our minimal tracer
        minimal_tracer = MinimalTracer(service_name="minimal-demo")
        
        # Test creating spans
        print("Creating test spans...")
        logger.info("Creating test spans...")
        
        # Create a parent span
        with minimal_tracer.start_as_current_span(
            "parent_operation", 
            attributes={"operation.type": "test"}
        ) as parent_span:
            logger.info("Executing parent operation")
            
            # Add some work simulation
            time.sleep(0.2)
            
            # Create a child span
            with minimal_tracer.start_as_current_span("child_operation") as child_span:
                logger.info("Executing child operation")
                minimal_tracer.set_attribute("child.attribute", "test_value")
                minimal_tracer.add_event("processing", {"step": "1", "status": "in_progress"})
                
                # Add some work simulation
                time.sleep(0.1)
                
                minimal_tracer.add_event("processing", {"step": "2", "status": "completed"})
            
            # Add more work to parent span
            time.sleep(0.1)
            parent_span.add_event("parent_operation_completed", {"success": True})
        
        # Wait for the BatchSpanProcessor to export
        time.sleep(1)
        
        print("✅ Successfully created and exported spans with Console exporter")
        logger.info("✅ Successfully created and exported spans with Console exporter")
        
    except Exception as e:
        print(f"❌ Error testing OpenTelemetry tracing: {e}")
        import traceback
        traceback.print_exc()
        logger.error(f"❌ Error testing OpenTelemetry tracing: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 