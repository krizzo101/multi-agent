"""
Simple test script for the tracer module.
"""
import os
import sys

# Make sure we can import from our local folders
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # Import directly from the tracer module
    from src.agents.utils.tracer import (
        AgentTracer, 
        configure_tracing, 
        add_span_event, 
        set_span_attribute
    )
    print("✅ Imports successful")
    
    # Try creating a tracer
    tracer = AgentTracer(
        service_name="test-service",
        enable_console_export=True
    )
    print("✅ AgentTracer created successfully")
    
    # Test configure_tracing function
    configured_tracer = configure_tracing(
        service_name="test-service",
        exporter_type="console",
        sampling_ratio=1.0
    )
    print("✅ configure_tracing successful")
    
    print("All tests passed!")
    
except Exception as e:
    import traceback
    print(f"❌ Error: {str(e)}")
    traceback.print_exc() 