"""
Tracer Utility for Agent Operations

This module provides a tracing system built on OpenTelemetry for agent operations,
allowing detailed monitoring of agent performance, request flow, and system behavior.
"""

import os
import time
import logging
import functools
import inspect
from typing import Dict, Any, Optional, Callable, List, Union, TypeVar, cast
from contextlib import contextmanager

# Set environment variable to use pure Python implementation if protobuf version issues
# This helps avoid compatibility issues with generated protobuf code
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# Note: If you encounter protobuf compatibility issues with Jaeger exporters,
# you may need to run:
# pip install "protobuf<=3.20.0" --force-reinstall
# OR simply avoid using Jaeger exporters and use the console or OTLP exporters instead

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Initialize logger
logger = logging.getLogger(__name__)

# Track which exporters are available
OTLP_GRPC_AVAILABLE = False
OTLP_HTTP_AVAILABLE = False
JAEGER_AVAILABLE = False  # Combined flag for any Jaeger exporter

# Import OTLP exporters
try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    OTLP_GRPC_AVAILABLE = True
except ImportError:
    logger.warning("OTLP gRPC exporter not available. Consider installing opentelemetry-exporter-otlp-proto-grpc")
    OTLPSpanExporter = None

try:
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HttpOTLPSpanExporter
    OTLP_HTTP_AVAILABLE = True
except ImportError:
    logger.warning("OTLP HTTP exporter not available. Consider installing opentelemetry-exporter-otlp-proto-http")
    HttpOTLPSpanExporter = None

# Try to import Jaeger exporters but gracefully handle any issues
# We'll try various import paths to support different OpenTelemetry versions
JaegerExporter = None
HttpJaegerExporter = None
ThriftJaegerExporter = None
GrpcJaegerExporter = None

# Wrap Jaeger imports in a try block to prevent any potential protobuf issues
try:
    # Try importing Jaeger HTTP exporter
    try:
        from opentelemetry.exporter.jaeger.proto.http import JaegerExporter as HttpJaegerExporter
    except ImportError:
        try:
            from opentelemetry.exporter.jaeger.proto.http.trace_exporter import JaegerExporter as HttpJaegerExporter
        except ImportError:
            HttpJaegerExporter = None
    
    # Try importing Jaeger Thrift exporter
    try:
        from opentelemetry.exporter.jaeger.thrift import JaegerExporter as ThriftJaegerExporter
    except ImportError:
        try:
            from opentelemetry.exporter.jaeger.thrift.trace_exporter import JaegerExporter as ThriftJaegerExporter
        except ImportError:
            ThriftJaegerExporter = None
    
    # Try importing Jaeger gRPC exporter
    try:
        from opentelemetry.exporter.jaeger.proto.grpc import JaegerExporter as GrpcJaegerExporter
    except ImportError:
        try:
            from opentelemetry.exporter.jaeger.proto.grpc.trace_exporter import JaegerExporter as GrpcJaegerExporter
        except ImportError:
            GrpcJaegerExporter = None
    
    # Set general Jaeger availability
    JAEGER_AVAILABLE = (HttpJaegerExporter is not None) or (ThriftJaegerExporter is not None) or (GrpcJaegerExporter is not None)
    
    if not JAEGER_AVAILABLE:
        logger.warning("No Jaeger exporters available. If needed, install one with: pip install opentelemetry-exporter-jaeger")
    
except Exception as e:
    logger.warning(f"Failed to import Jaeger exporters due to: {e}")
    logger.warning("Jaeger export will not be available. Use console or OTLP exporters instead.")
    JAEGER_AVAILABLE = False

# Type variable for generic function decorators
F = TypeVar('F', bound=Callable[..., Any])

class AgentTracer:
    """
    Tracer utility for monitoring and analyzing agent operations.
    
    This class provides a wrapper around OpenTelemetry tracing with convenience
    methods for agent-specific tracing needs.
    """
    
    def __init__(
        self, 
        service_name: str = "agent-system",
        enable_console_export: bool = False,
        enable_otlp_export: bool = False,
        otlp_endpoint: str = "localhost:4317",
        otlp_protocol: str = "grpc",  # "grpc" or "http"
        enable_jaeger_export: bool = False,
        jaeger_endpoint: str = "localhost:6831",
        jaeger_protocol: str = "thrift",  # "thrift", "grpc", or "http"
        sampling_ratio: float = 1.0,
        attributes: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the agent tracer.
        
        Args:
            service_name: Name of the service for trace identification
            enable_console_export: Whether to export traces to console
            enable_otlp_export: Whether to export traces to an OTLP endpoint
            otlp_endpoint: OTLP endpoint for trace export
            otlp_protocol: Protocol to use for OTLP export ("grpc" or "http")
            enable_jaeger_export: Whether to export traces to Jaeger
            jaeger_endpoint: Jaeger endpoint for trace export
            jaeger_protocol: Protocol to use for Jaeger export ("thrift", "grpc", or "http")
            sampling_ratio: Ratio of requests to sample (0.0-1.0)
            attributes: Additional resource attributes to include in all spans
        """
        self._service_name = service_name
        
        # Create resource with service information and additional attributes
        resource_attributes = {
            "service.name": service_name,
            "service.version": os.environ.get("SERVICE_VERSION", "0.1.0"),
            "deployment.environment": os.environ.get("DEPLOYMENT_ENV", "development")
        }
        
        if attributes:
            resource_attributes.update(attributes)
        
        resource = Resource.create(resource_attributes)
        
        # Configure trace provider with sampling
        sampler = TraceIdRatioBased(sampling_ratio)
        provider = TracerProvider(resource=resource, sampler=sampler)
        
        # Set up exporters
        if enable_console_export:
            console_exporter = ConsoleSpanExporter()
            console_processor = BatchSpanProcessor(console_exporter)
            provider.add_span_processor(console_processor)
            logger.info(f"Console trace export enabled for {service_name}")
        
        if enable_otlp_export:
            try:
                if otlp_protocol.lower() == "http":
                    # For HTTP protocol
                    if OTLP_HTTP_AVAILABLE and HttpOTLPSpanExporter:
                        # For HTTP, ensure we have the full URL including the path
                        if not otlp_endpoint.startswith("http"):
                            # Add http:// prefix if not present
                            if ":" in otlp_endpoint:
                                host, port = otlp_endpoint.split(":")
                                otlp_url = f"http://{host}:{port}/v1/traces"
                            else:
                                otlp_url = f"http://{otlp_endpoint}:4318/v1/traces"
                        else:
                            # URL already includes http:// or https://
                            if "/v1/traces" not in otlp_endpoint:
                                otlp_url = f"{otlp_endpoint}/v1/traces"
                            else:
                                otlp_url = otlp_endpoint
                            
                        otlp_exporter = HttpOTLPSpanExporter(endpoint=otlp_url)
                        logger.info(f"OTLP HTTP trace export enabled to {otlp_url}")
                        
                        otlp_processor = BatchSpanProcessor(otlp_exporter)
                        provider.add_span_processor(otlp_processor)
                    else:
                        logger.error("OTLP HTTP exporter not available. Please install opentelemetry-exporter-otlp-proto-http")
                else:
                    # Default to gRPC protocol if available
                    if OTLP_GRPC_AVAILABLE and OTLPSpanExporter:
                        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                        logger.info(f"OTLP gRPC trace export enabled to {otlp_endpoint}")
                        
                        otlp_processor = BatchSpanProcessor(otlp_exporter)
                        provider.add_span_processor(otlp_processor)
                    else:
                        logger.error("OTLP gRPC exporter not available. Please install opentelemetry-exporter-otlp-proto-grpc")
            except Exception as e:
                logger.error(f"Failed to initialize OTLP exporter: {e}")
        
        if enable_jaeger_export and JAEGER_AVAILABLE:
            try:
                jaeger_exporter = None
                
                if jaeger_protocol.lower() == "grpc" and GrpcJaegerExporter:
                    # For gRPC protocol
                    if ":" in jaeger_endpoint:
                        host, port_str = jaeger_endpoint.split(":")
                        jaeger_exporter = GrpcJaegerExporter(
                            collector_endpoint=f"http://{host}:{port_str}"
                        )
                    else:
                        jaeger_exporter = GrpcJaegerExporter(
                            collector_endpoint=f"http://{jaeger_endpoint}:14250"
                        )
                    logger.info(f"Jaeger gRPC trace export enabled to {jaeger_endpoint}")
                    
                elif jaeger_protocol.lower() == "http" and HttpJaegerExporter:
                    # For HTTP protocol
                    if ":" in jaeger_endpoint:
                        host, port_str = jaeger_endpoint.split(":")
                        jaeger_exporter = HttpJaegerExporter(
                            endpoint=f"http://{host}:{port_str}/api/traces"
                        )
                    else:
                        jaeger_exporter = HttpJaegerExporter(
                            endpoint=f"http://{jaeger_endpoint}:14268/api/traces"
                        )
                    logger.info(f"Jaeger HTTP trace export enabled to {jaeger_endpoint}")
                    
                elif jaeger_protocol.lower() == "thrift" and ThriftJaegerExporter:
                    # Default to thrift protocol
                    if ":" in jaeger_endpoint:
                        host, port_str = jaeger_endpoint.split(":")
                        port = int(port_str)
                        jaeger_exporter = ThriftJaegerExporter(
                            agent_host_name=host,
                            agent_port=port
                        )
                    else:
                        jaeger_exporter = ThriftJaegerExporter(
                            agent_host_name=jaeger_endpoint,
                            agent_port=6831
                        )
                    logger.info(f"Jaeger Thrift trace export enabled to {jaeger_endpoint}")
                
                # If we couldn't get the requested protocol, try fallbacks
                if jaeger_exporter is None:
                    logger.warning(f"Requested Jaeger protocol '{jaeger_protocol}' not available, trying fallbacks")
                    
                    if HttpJaegerExporter:
                        # HTTP is usually the most reliable
                        host = jaeger_endpoint.split(":")[0] if ":" in jaeger_endpoint else jaeger_endpoint
                        jaeger_exporter = HttpJaegerExporter(endpoint=f"http://{host}:14268/api/traces")
                        logger.info(f"Falling back to Jaeger HTTP exporter at http://{host}:14268/api/traces")
                    elif ThriftJaegerExporter:
                        # Then try thrift
                        host = jaeger_endpoint.split(":")[0] if ":" in jaeger_endpoint else jaeger_endpoint
                        jaeger_exporter = ThriftJaegerExporter(agent_host_name=host, agent_port=6831)
                        logger.info(f"Falling back to Jaeger Thrift exporter at {host}:6831")
                    elif GrpcJaegerExporter:
                        # Last try gRPC
                        host = jaeger_endpoint.split(":")[0] if ":" in jaeger_endpoint else jaeger_endpoint
                        jaeger_exporter = GrpcJaegerExporter(collector_endpoint=f"http://{host}:14250")
                        logger.info(f"Falling back to Jaeger gRPC exporter at http://{host}:14250")
                    else:
                        logger.error("No Jaeger exporters available. Please install at least one Jaeger exporter package.")
                
                # Add the processor if we found an exporter
                if jaeger_exporter is not None:
                    jaeger_processor = BatchSpanProcessor(jaeger_exporter)
                    provider.add_span_processor(jaeger_processor)
            except Exception as e:
                logger.error(f"Failed to initialize Jaeger exporter: {e}")
                logger.warning("Falling back to console export only. Install protobuf<=3.20.0 if you need Jaeger export.")
                
                # If Jaeger export fails and no other exporters are enabled, add console exporter as fallback
                if not enable_console_export and not enable_otlp_export:
                    logger.info("Adding console exporter as fallback")
                    console_exporter = ConsoleSpanExporter()
                    console_processor = BatchSpanProcessor(console_exporter)
                    provider.add_span_processor(console_processor)
        elif enable_jaeger_export and not JAEGER_AVAILABLE:
            logger.warning("Jaeger export requested but no Jaeger exporters are available.")
            logger.warning("Install opentelemetry-exporter-jaeger and try again.")
            
            # Add console exporter as fallback if no other exporters are enabled
            if not enable_console_export and not enable_otlp_export:
                logger.info("Adding console exporter as fallback")
                console_exporter = ConsoleSpanExporter()
                console_processor = BatchSpanProcessor(console_exporter)
                provider.add_span_processor(console_processor)
        
        # Set the global trace provider
        trace.set_tracer_provider(provider)
        
        # Create a tracer for the service
        self._tracer = trace.get_tracer(service_name)
        
        # Propagator for distributed tracing context
        self._propagator = TraceContextTextMapPropagator()
        
        logger.info(f"Agent tracer initialized for service: {service_name}")
    
    def get_current_span(self) -> trace.Span:
        """
        Get the current active span.
        
        Returns:
            The current span or a no-op span if none is active
        """
        return trace.get_current_span()
    
    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        kind: Optional[trace.SpanKind] = None
    ) -> trace.Span:
        """
        Start a new span as a context manager.
        
        Args:
            name: Name of the span
            attributes: Initial span attributes
            kind: Kind of span (client, server, internal, etc.)
            
        Yields:
            The created span
        """
        span = self._tracer.start_span(
            name=name,
            attributes=attributes,
            kind=kind or trace.SpanKind.INTERNAL
        )
        
        with trace.use_span(span, end_on_exit=True):
            yield span
    
    @contextmanager
    def start_as_current_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        kind: Optional[trace.SpanKind] = None,
        links: Optional[List[trace.Link]] = None
    ) -> trace.Span:
        """
        Start a new span as the current active span within a context manager.
        
        Args:
            name: Name of the span
            attributes: Initial span attributes
            kind: Kind of span (client, server, internal, etc.)
            links: Optional links to other spans
            
        Yields:
            The created span
        """
        with self._tracer.start_as_current_span(
            name=name,
            attributes=attributes,
            kind=kind or trace.SpanKind.INTERNAL,
            links=links
        ) as span:
            yield span
    
    def traced_function(
        self,
        name: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        kind: Optional[trace.SpanKind] = None
    ) -> Callable[[F], F]:
        """
        Decorator for tracing a function.
        
        Args:
            name: Optional name for the span (defaults to function name)
            attributes: Static attributes to add to the span
            kind: Kind of span (client, server, internal, etc.)
            
        Returns:
            Decorator function
        """
        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                # Get the function name if not provided
                span_name = name if name is not None else func.__qualname__
                
                # Get function info for additional context
                module = inspect.getmodule(func)
                module_name = module.__name__ if module else "unknown"
                
                # Base attributes
                span_attributes = {
                    "code.function": func.__name__,
                    "code.namespace": module_name
                }
                
                # Add custom attributes if provided
                if attributes:
                    span_attributes.update(attributes)
                
                with self._tracer.start_as_current_span(
                    name=span_name,
                    attributes=span_attributes,
                    kind=kind or trace.SpanKind.INTERNAL
                ) as span:
                    try:
                        # Record function arguments if not sensitive
                        if hasattr(func, "__traced_args__") and func.__traced_args__:
                            for param_name in func.__traced_args__:
                                if param_name in kwargs:
                                    span.set_attribute(f"arg.{param_name}", str(kwargs[param_name]))
                        
                        # Get the start time for performance tracking
                        start_time = time.time()
                        
                        # Execute the function
                        result = func(*args, **kwargs)
                        
                        # Record execution time
                        span.set_attribute("execution_time_ms", (time.time() - start_time) * 1000)
                        
                        return result
                    except Exception as e:
                        # Record the exception
                        span.record_exception(e)
                        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                        
                        # Re-raise the exception
                        raise
            
            return cast(F, wrapper)
        
        return decorator
    
    def trace_args(self, arg_names: List[str]) -> Callable[[F], F]:
        """
        Decorator to specify function arguments that should be traced.
        
        Args:
            arg_names: List of argument names to trace
            
        Returns:
            Decorator function
        """
        def decorator(func: F) -> F:
            func.__traced_args__ = arg_names  # type: ignore
            return func
        
        return decorator
    
    def add_event(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add an event to the current active span.
        
        Args:
            name: Name of the event
            attributes: Attributes to add to the event
        """
        current_span = trace.get_current_span()
        current_span.add_event(name=name, attributes=attributes)
    
    def set_attribute(
        self,
        key: str,
        value: Union[str, bool, int, float, List[str], List[bool], List[int], List[float]]
    ) -> None:
        """
        Set an attribute on the current active span.
        
        Args:
            key: Attribute key
            value: Attribute value
        """
        current_span = trace.get_current_span()
        current_span.set_attribute(key, value)
    
    def set_status(
        self,
        status_code: trace.StatusCode,
        description: Optional[str] = None
    ) -> None:
        """
        Set the status of the current active span.
        
        Args:
            status_code: Status code (OK, ERROR)
            description: Optional status description
        """
        current_span = trace.get_current_span()
        current_span.set_status(trace.Status(status_code, description))
    
    def record_exception(
        self,
        exception: Exception,
        attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record an exception in the current active span.
        
        Args:
            exception: Exception to record
            attributes: Additional attributes about the exception
        """
        current_span = trace.get_current_span()
        current_span.record_exception(exception, attributes)
    
    def create_span_link(
        self,
        context: Optional[trace.SpanContext] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> trace.Link:
        """
        Create a link to another span.
        
        Args:
            context: Context of the span to link to (defaults to current)
            attributes: Attributes to add to the link
            
        Returns:
            Link object
        """
        if context is None:
            context = trace.get_current_span().get_span_context()
        
        return trace.Link(context, attributes)
    
    def inject_context(self, carrier: Dict[str, str]) -> Dict[str, str]:
        """
        Inject trace context into a carrier dictionary.
        
        Args:
            carrier: Dictionary to inject context into
            
        Returns:
            Dictionary with injected trace context
        """
        self._propagator.inject(carrier)
        return carrier
    
    def extract_context(self, carrier: Dict[str, str]) -> trace.SpanContext:
        """
        Extract trace context from a carrier dictionary.
        
        Args:
            carrier: Dictionary containing trace context
            
        Returns:
            Extracted span context
        """
        context = self._propagator.extract(carrier)
        return context
    
    @contextmanager
    def profile_block(self, name: str) -> None:
        """
        Profile a block of code and record timing as a span.
        
        Args:
            name: Name for the profiling span
            
        Yields:
            None
        """
        with self.start_as_current_span(name) as span:
            start_time = time.time()
            try:
                yield
            finally:
                elapsed_ms = (time.time() - start_time) * 1000
                span.set_attribute("duration_ms", elapsed_ms)
    
    def trace_method(
        self,
        name: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        kind: Optional[trace.SpanKind] = None
    ) -> Callable[[F], F]:
        """
        Decorator for tracing a class method.
        
        Args:
            name: Optional name for the span (defaults to method name)
            attributes: Static attributes to add to the span
            kind: Kind of span (client, server, internal, etc.)
            
        Returns:
            Decorator function
        """
        def decorator(method: F) -> F:
            @functools.wraps(method)
            def wrapper(self_arg: Any, *args: Any, **kwargs: Any) -> Any:
                # Get the class and method info
                cls_name = self_arg.__class__.__name__
                method_name = method.__name__
                
                # Determine span name
                span_name = name if name is not None else f"{cls_name}.{method_name}"
                
                # Base attributes
                span_attributes = {
                    "code.function": method_name,
                    "code.namespace": cls_name
                }
                
                # Add custom attributes if provided
                if attributes:
                    span_attributes.update(attributes)
                
                with trace.get_tracer(cls_name).start_as_current_span(
                    name=span_name,
                    attributes=span_attributes,
                    kind=kind or trace.SpanKind.INTERNAL
                ) as span:
                    try:
                        # Record method arguments if not sensitive
                        if hasattr(method, "__traced_args__") and method.__traced_args__:
                            for param_name in method.__traced_args__:
                                if param_name in kwargs:
                                    span.set_attribute(f"arg.{param_name}", str(kwargs[param_name]))
                        
                        # Get the start time for performance tracking
                        start_time = time.time()
                        
                        # Execute the method
                        result = method(self_arg, *args, **kwargs)
                        
                        # Record execution time
                        span.set_attribute("execution_time_ms", (time.time() - start_time) * 1000)
                        
                        return result
                    except Exception as e:
                        # Record the exception
                        span.record_exception(e)
                        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                        
                        # Re-raise the exception
                        raise
            
            return cast(F, wrapper)
        
        return decorator


def configure_tracing(
    service_name: str,
    exporter_type: str = "console",
    endpoint: Optional[str] = None,
    sampling_ratio: float = 1.0,
    jaeger_protocol: str = "thrift",
    otlp_protocol: str = "grpc"
) -> AgentTracer:
    """
    Configure tracing for the application.
    
    Args:
        service_name: Name of the service
        exporter_type: Type of exporter (console, otlp, jaeger)
        endpoint: Exporter endpoint
        sampling_ratio: Sampling ratio (0.0-1.0)
        jaeger_protocol: Protocol to use for Jaeger export ("thrift", "grpc", or "http")
        otlp_protocol: Protocol to use for OTLP export ("grpc" or "http")
        
    Returns:
        Configured AgentTracer instance
    """
    # Default configuration
    config = {
        "service_name": service_name,
        "enable_console_export": False,
        "enable_otlp_export": False,
        "enable_jaeger_export": False,
        "sampling_ratio": sampling_ratio,
        "jaeger_protocol": jaeger_protocol,
        "otlp_protocol": otlp_protocol
    }
    
    # Configure based on exporter type
    if exporter_type == "console":
        config["enable_console_export"] = True
    elif exporter_type == "otlp":
        config["enable_otlp_export"] = True
        if endpoint:
            config["otlp_endpoint"] = endpoint
    elif exporter_type == "jaeger":
        if not JAEGER_AVAILABLE:
            logger.warning("Jaeger export requested but no Jaeger exporters available; falling back to console export")
            config["enable_console_export"] = True
        else:
            config["enable_jaeger_export"] = True
            if endpoint:
                config["jaeger_endpoint"] = endpoint
    else:
        logger.warning(f"Unknown exporter type: {exporter_type}, defaulting to console")
        config["enable_console_export"] = True
    
    # Create the tracer
    return AgentTracer(**config)


# Convenience functions for working with the current span
def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Add an event to the current span."""
    trace.get_current_span().add_event(name, attributes)

def set_span_attribute(key: str, value: Any) -> None:
    """Set an attribute on the current span."""
    trace.get_current_span().set_attribute(key, value)

def set_span_status(status_code: trace.StatusCode, description: Optional[str] = None) -> None:
    """Set the status of the current span."""
    trace.get_current_span().set_status(trace.Status(status_code, description))

def record_span_exception(exception: Exception, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Record an exception in the current span."""
    trace.get_current_span().record_exception(exception, attributes) 