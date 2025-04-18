#!/usr/bin/env python
"""
Test script to verify that OpenTelemetry imports and tracing are working properly.

This script tests:
1. Importing basic OpenTelemetry components
2. Setting up a console exporter
3. Creating traces with the console exporter
4. Optional: Testing OTLP exporters
"""

import os
import time
import logging
import sys
from typing import Optional, Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Set environment variable for protobuf compatibility
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

print("Starting OpenTelemetry import test...")

def test_import(module_name: str) -> bool:
    """Test importing a module and log the result."""
    try:
        __import__(module_name)
        print(f"✅ Successfully imported {module_name}")
        logger.info(f"✅ Successfully imported {module_name}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import {module_name}: {e}")
        logger.warning(f"❌ Failed to import {module_name}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error importing {module_name}: {e}")
        logger.warning(f"❌ Error importing {module_name}: {e}")
        return False

def main():
    """Run the OpenTelemetry import and tracing tests."""
    print("Testing OpenTelemetry imports...")
    logger.info("Testing OpenTelemetry imports...")
    
    # Test core OpenTelemetry imports
    core_imports = [
        "opentelemetry.sdk",
        "opentelemetry.trace",
        "opentelemetry.sdk.trace",
    ]
    
    core_success = all(test_import(module) for module in core_imports)
    if not core_success:
        print("❌ Core OpenTelemetry imports failed. Please check your installation.")
        logger.error("❌ Core OpenTelemetry imports failed. Please check your installation.")
        sys.exit(1)
    
    # Test exporter imports
    exporter_imports = [
        "opentelemetry.sdk.trace.export",
        "opentelemetry.exporter.otlp.proto.grpc.trace_exporter",
        "opentelemetry.exporter.otlp.proto.http.trace_exporter",
    ]
    
    for module in exporter_imports:
        test_import(module)
    
    # Skip Jaeger tests as they have compatibility issues with latest protobuf
    print("Skipping Jaeger exporter tests due to known protobuf compatibility issues")
    logger.info("Skipping Jaeger exporter tests due to known protobuf compatibility issues")
    
    # Test creating a basic tracer with console export
    try:
        print("Setting up basic tracer with console exporter...")
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        
        # Create and configure the tracer
        resource = Resource.create(attributes={
            SERVICE_NAME: "otel-import-test"
        })
        
        provider = TracerProvider(resource=resource)
        console_exporter = ConsoleSpanExporter()
        console_processor = BatchSpanProcessor(console_exporter)
        provider.add_span_processor(console_processor)
        trace.set_tracer_provider(provider)
        
        # Create a tracer
        tracer = trace.get_tracer(__name__)
        
        # Create test spans
        print("Creating test spans (output should appear below)...")
        logger.info("Creating test spans (output should appear below)...")
        with tracer.start_as_current_span("test_parent_span") as parent:
            parent.set_attribute("test.attribute", "test_value")
            time.sleep(0.1)  # Simulate some work
            
            with tracer.start_as_current_span("test_child_span") as child:
                child.set_attribute("child.attribute", 42)
                child.add_event("test_event", {"event.key": "event_value"})
                time.sleep(0.1)  # Simulate some work
        
        # Give time for the BatchSpanProcessor to export
        time.sleep(0.5)
        
        print("✅ Successfully created and exported spans with ConsoleSpanExporter")
        logger.info("✅ Successfully created and exported spans with ConsoleSpanExporter")
        
        # Test our local tracer utility if available
        try:
            print("Attempting to import local tracer utility...")
            # Add the parent directory to sys.path
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            print(f"Updated sys.path: {sys.path}")
            
            from src.agents.utils.tracer import configure_tracing
            
            # Test console exporter from our utility
            print("Testing local tracer utility with console exporter...")
            logger.info("Testing local tracer utility with console exporter...")
            tracer_util = configure_tracing(
                service_name="tracer-util-test",
                exporter_type="console"
            )
            
            with tracer_util.start_as_current_span("utility_test_span"):
                tracer_util.set_attribute("utility.test", "success")
                time.sleep(0.1)
            
            # Give time for the BatchSpanProcessor to export
            time.sleep(0.5)
            print("✅ Successfully used local tracer utility")
            logger.info("✅ Successfully used local tracer utility")
            
        except ImportError as e:
            print(f"⚠️ Could not test local tracer utility: {e}")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Directory contents: {os.listdir('.')}")
            print(f"src directory contents: {os.listdir('src') if os.path.exists('src') else 'src dir not found'}")
            if os.path.exists('src/agents'):
                print(f"agents directory contents: {os.listdir('src/agents')}")
            if os.path.exists('src/agents/utils'):
                print(f"utils directory contents: {os.listdir('src/agents/utils')}")
            logger.warning(f"⚠️ Could not test local tracer utility: {e}")
            
            # Try an alternative approach
            print("Trying alternative import approach...")
            try:
                from agents.utils.tracer import configure_tracing
                
                tracer_util = configure_tracing(
                    service_name="tracer-util-test",
                    exporter_type="console"
                )
                
                with tracer_util.start_as_current_span("utility_test_span_alt"):
                    tracer_util.set_attribute("utility.test", "success_alt")
                    time.sleep(0.1)
                
                print("✅ Successfully used local tracer utility (alternative approach)")
                logger.info("✅ Successfully used local tracer utility (alternative approach)")
            except ImportError as e2:
                print(f"⚠️ Alternative approach also failed: {e2}")
                logger.warning(f"⚠️ Alternative approach also failed: {e2}")
        
    except Exception as e:
        print(f"❌ Error testing tracer: {e}")
        import traceback
        traceback.print_exc()
        logger.error(f"❌ Error testing tracer: {e}")
        return
    
    print("✅ All basic OpenTelemetry tests passed!")
    logger.info("✅ All basic OpenTelemetry tests passed!")

if __name__ == "__main__":
    main() 