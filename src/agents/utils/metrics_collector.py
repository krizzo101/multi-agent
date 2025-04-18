"""
Metrics Collector for Agent Operations

This module provides a metrics collection and analysis system for agent operations,
tracking request/response patterns, latency, token usage, error rates, and user feedback.
"""

import time
import threading
import uuid
from typing import Dict, Any, List, Optional
from collections import defaultdict
import statistics
import logging

logger = logging.getLogger(__name__)

class MetricsCollector:
    """
    Collects and analyzes performance metrics for agent operations.
    
    This class maintains performance statistics for individual agents and the
    overall system, supporting real-time monitoring and analysis.
    """
    
    def __init__(self):
        """Initialize the metrics collector with empty data stores."""
        # Thread safety for metrics collection
        self._lock = threading.RLock()
        
        # Request tracking
        self._requests = {}
        self._responses = {}
        self._errors = {}
        self._feedback = {}
        
        # Agent-specific metrics
        self._agent_metrics = defaultdict(lambda: {
            "request_count": 0,
            "successful_responses": 0,
            "error_count": 0,
            "response_times_ms": [],
            "token_usage": [],
            "user_ratings": [],
            "start_time": time.time()
        })
        
        # System-wide metrics
        self._system_metrics = {
            "total_requests": 0,
            "successful_responses": 0,
            "error_count": 0,
            "response_times_ms": [],
            "token_usage": [],
            "user_ratings": [],
            "start_time": time.time()
        }
    
    def track_request(self, agent_id: str, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Track a new request to an agent.
        
        Args:
            agent_id: The ID of the agent handling the request
            query: The user query text
            context: Optional context data for the request
            
        Returns:
            request_id: A unique identifier for the request
        """
        request_id = str(uuid.uuid4())
        timestamp = time.time()
        
        request_data = {
            "agent_id": agent_id,
            "query": query,
            "context": context or {},
            "timestamp": timestamp,
            "request_id": request_id
        }
        
        with self._lock:
            self._requests[request_id] = request_data
            self._agent_metrics[agent_id]["request_count"] += 1
            self._system_metrics["total_requests"] += 1
        
        return request_id
    
    def track_response(self, request_id: str, agent_id: str, status: str, 
                      latency_ms: float, tokens_used: int) -> None:
        """
        Track a response from an agent.
        
        Args:
            request_id: The ID of the original request
            agent_id: The ID of the agent that generated the response
            status: Response status (success, partial, failure)
            latency_ms: Response time in milliseconds
            tokens_used: Number of tokens used in the response
        """
        timestamp = time.time()
        
        response_data = {
            "request_id": request_id,
            "agent_id": agent_id,
            "status": status,
            "latency_ms": latency_ms,
            "tokens_used": tokens_used,
            "timestamp": timestamp
        }
        
        with self._lock:
            self._responses[request_id] = response_data
            
            # Update agent metrics
            if status == "success":
                self._agent_metrics[agent_id]["successful_responses"] += 1
                self._system_metrics["successful_responses"] += 1
            
            self._agent_metrics[agent_id]["response_times_ms"].append(latency_ms)
            self._agent_metrics[agent_id]["token_usage"].append(tokens_used)
            
            # Update system metrics
            self._system_metrics["response_times_ms"].append(latency_ms)
            self._system_metrics["token_usage"].append(tokens_used)
    
    def track_error(self, request_id: str, agent_id: str, 
                   error_type: str, error_message: str) -> None:
        """
        Track an error that occurred during processing.
        
        Args:
            request_id: The ID of the original request
            agent_id: The ID of the agent that encountered the error
            error_type: Type of error (e.g., "ValidationError")
            error_message: Error message details
        """
        timestamp = time.time()
        
        error_data = {
            "request_id": request_id,
            "agent_id": agent_id,
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": timestamp
        }
        
        with self._lock:
            self._errors[request_id] = error_data
            
            # Update metrics
            self._agent_metrics[agent_id]["error_count"] += 1
            self._system_metrics["error_count"] += 1
    
    def track_user_feedback(self, agent_id: str, request_id: str, 
                           rating: float, feedback: Optional[str] = None) -> None:
        """
        Track user feedback on a response.
        
        Args:
            agent_id: The ID of the agent that generated the response
            request_id: The ID of the original request
            rating: User rating (0.0 to 1.0)
            feedback: Optional textual feedback
        """
        timestamp = time.time()
        
        feedback_data = {
            "request_id": request_id,
            "agent_id": agent_id,
            "rating": rating,
            "feedback": feedback,
            "timestamp": timestamp
        }
        
        with self._lock:
            self._feedback[request_id] = feedback_data
            
            # Update metrics
            self._agent_metrics[agent_id]["user_ratings"].append(rating)
            self._system_metrics["user_ratings"].append(rating)
    
    def get_request_history(self, agent_id: Optional[str] = None, 
                           limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent request history, optionally filtered by agent.
        
        Args:
            agent_id: Optional agent ID to filter by
            limit: Maximum number of requests to return
            
        Returns:
            List of request data dictionaries
        """
        with self._lock:
            if agent_id:
                filtered_requests = [
                    req for req in self._requests.values() 
                    if req["agent_id"] == agent_id
                ]
            else:
                filtered_requests = list(self._requests.values())
            
            # Sort by timestamp (newest first) and limit
            sorted_requests = sorted(
                filtered_requests, 
                key=lambda r: r["timestamp"], 
                reverse=True
            )[:limit]
            
            return sorted_requests
    
    def get_agent_metrics(self, agent_id: str) -> Dict[str, Any]:
        """
        Get performance metrics for a specific agent.
        
        Args:
            agent_id: ID of the agent to get metrics for
            
        Returns:
            Dictionary of agent performance metrics
        """
        with self._lock:
            metrics = self._agent_metrics[agent_id].copy()
            
            # Calculate derived metrics
            request_count = metrics["request_count"]
            if request_count > 0:
                metrics["success_rate"] = (
                    metrics["successful_responses"] / request_count 
                    if request_count > 0 else 0
                )
                metrics["error_rate"] = (
                    metrics["error_count"] / request_count 
                    if request_count > 0 else 0
                )
            else:
                metrics["success_rate"] = 0
                metrics["error_rate"] = 0
            
            # Calculate statistics if we have data
            if metrics["response_times_ms"]:
                metrics["average_response_time_ms"] = statistics.mean(
                    metrics["response_times_ms"]
                )
                metrics["median_response_time_ms"] = statistics.median(
                    metrics["response_times_ms"]
                )
                if len(metrics["response_times_ms"]) > 1:
                    metrics["stddev_response_time_ms"] = statistics.stdev(
                        metrics["response_times_ms"]
                    )
                else:
                    metrics["stddev_response_time_ms"] = 0
            else:
                metrics["average_response_time_ms"] = 0
                metrics["median_response_time_ms"] = 0
                metrics["stddev_response_time_ms"] = 0
            
            if metrics["token_usage"]:
                metrics["average_token_usage"] = statistics.mean(
                    metrics["token_usage"]
                )
                metrics["total_tokens"] = sum(metrics["token_usage"])
            else:
                metrics["average_token_usage"] = 0
                metrics["total_tokens"] = 0
            
            if metrics["user_ratings"]:
                metrics["average_rating"] = statistics.mean(
                    metrics["user_ratings"]
                )
            else:
                metrics["average_rating"] = 0
            
            # Calculate uptime
            metrics["uptime_seconds"] = time.time() - metrics["start_time"]
            
            return metrics
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get system-wide performance metrics.
        
        Returns:
            Dictionary of system performance metrics
        """
        with self._lock:
            metrics = self._system_metrics.copy()
            
            # Calculate derived metrics
            request_count = metrics["total_requests"]
            if request_count > 0:
                metrics["success_rate"] = (
                    metrics["successful_responses"] / request_count 
                    if request_count > 0 else 0
                )
                metrics["error_rate"] = (
                    metrics["error_count"] / request_count 
                    if request_count > 0 else 0
                )
            else:
                metrics["success_rate"] = 0
                metrics["error_rate"] = 0
            
            # Calculate statistics if we have data
            if metrics["response_times_ms"]:
                metrics["average_response_time_ms"] = statistics.mean(
                    metrics["response_times_ms"]
                )
                metrics["median_response_time_ms"] = statistics.median(
                    metrics["response_times_ms"]
                )
                if len(metrics["response_times_ms"]) > 1:
                    metrics["stddev_response_time_ms"] = statistics.stdev(
                        metrics["response_times_ms"]
                    )
                else:
                    metrics["stddev_response_time_ms"] = 0
            else:
                metrics["average_response_time_ms"] = 0
                metrics["median_response_time_ms"] = 0
                metrics["stddev_response_time_ms"] = 0
            
            if metrics["token_usage"]:
                metrics["average_token_usage"] = statistics.mean(
                    metrics["token_usage"]
                )
                metrics["total_tokens"] = sum(metrics["token_usage"])
            else:
                metrics["average_token_usage"] = 0
                metrics["total_tokens"] = 0
            
            if metrics["user_ratings"]:
                metrics["average_rating"] = statistics.mean(
                    metrics["user_ratings"]
                )
            else:
                metrics["average_rating"] = 0
            
            # Calculate uptime
            metrics["uptime_seconds"] = time.time() - metrics["start_time"]
            
            return metrics
    
    def get_error_distribution(self, agent_id: Optional[str] = None) -> Dict[str, int]:
        """
        Get distribution of errors by type.
        
        Args:
            agent_id: Optional agent ID to filter by
            
        Returns:
            Dictionary mapping error types to counts
        """
        with self._lock:
            if agent_id:
                filtered_errors = [
                    err for err in self._errors.values() 
                    if err["agent_id"] == agent_id
                ]
            else:
                filtered_errors = list(self._errors.values())
            
            error_counts = defaultdict(int)
            for error in filtered_errors:
                error_counts[error["error_type"]] += 1
            
            return dict(error_counts)
    
    def reset_metrics(self, agent_id: Optional[str] = None) -> None:
        """
        Reset metrics, optionally for a specific agent only.
        
        Args:
            agent_id: Optional agent ID to reset metrics for
        """
        with self._lock:
            if agent_id:
                self._agent_metrics[agent_id] = {
                    "request_count": 0,
                    "successful_responses": 0,
                    "error_count": 0,
                    "response_times_ms": [],
                    "token_usage": [],
                    "user_ratings": [],
                    "start_time": time.time()
                }
            else:
                # Reset all agent metrics
                for agent_id in self._agent_metrics:
                    self._agent_metrics[agent_id] = {
                        "request_count": 0,
                        "successful_responses": 0,
                        "error_count": 0,
                        "response_times_ms": [],
                        "token_usage": [],
                        "user_ratings": [],
                        "start_time": time.time()
                    }
                
                # Reset system metrics
                self._system_metrics = {
                    "total_requests": 0,
                    "successful_responses": 0,
                    "error_count": 0,
                    "response_times_ms": [],
                    "token_usage": [],
                    "user_ratings": [],
                    "start_time": time.time()
                }
                
                # Clear data stores
                self._requests = {}
                self._responses = {}
                self._errors = {}
                self._feedback = {}
    
    def export_metrics(self) -> Dict[str, Any]:
        """
        Export all metrics data in a format suitable for external analysis.
        
        Returns:
            Dictionary containing all metrics data
        """
        with self._lock:
            export_data = {
                "system_metrics": self.get_system_metrics(),
                "agent_metrics": {
                    agent_id: self.get_agent_metrics(agent_id)
                    for agent_id in self._agent_metrics
                },
                "requests": self._requests,
                "responses": self._responses,
                "errors": self._errors,
                "feedback": self._feedback
            }
            
            return export_data 