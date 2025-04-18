"""
Minimal test script for OpenTelemetry tracing.
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Import OpenTelemetry
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
    
    print("✅ OpenTelemetry imports successful")
    
    # Try creating a basic tracer
    resource = Resource.create({"service.name": "minimal-test"})
    provider = TracerProvider(resource=resource)
    
    # Add console exporter
    console_exporter = ConsoleSpanExporter()
    console_processor = BatchSpanProcessor(console_exporter)
    provider.add_span_processor(console_processor)
    
    # Set global tracer provider
    trace.set_tracer_provider(provider)
    
    # Create a tracer
    tracer = trace.get_tracer("minimal-test")
    
    print("✅ Basic tracer setup successful")
    
    # Create a span
    with tracer.start_as_current_span("test-span") as span:
        span.set_attribute("test.attribute", "test-value")
        span.add_event("test-event")
        print("✅ Span created successfully")
    
    print("All tests passed!")
    
except Exception as e:
    import traceback
    print(f"❌ Error: {str(e)}")
    traceback.print_exc() 