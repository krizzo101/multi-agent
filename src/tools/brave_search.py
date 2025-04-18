"""
Brave Search Integration Module

This module implements a tool that interfaces with Brave Search API via MCP (Machine Conversation Protocol).
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional, Union
from llama_index.core.tools import FunctionTool

logger = logging.getLogger(__name__)

class BraveSearchTool:
    """Tool for performing searches using the Brave Search API via MCP."""
    
    def __init__(self, api_key: Optional[str] = None, subscription_key: Optional[str] = None):
        """
        Initialize the Brave Search Tool.
        
        Args:
            api_key: Brave Search API key (will use BRAVE_SEARCH_API_KEY env var if not provided)
            subscription_key: Brave Search subscription key (will use BRAVE_SEARCH_SUBSCRIPTION_KEY env var if not provided)
        """
        self.api_key = api_key or os.environ.get('BRAVE_SEARCH_API_KEY')
        self.subscription_key = subscription_key or os.environ.get('BRAVE_SEARCH_SUBSCRIPTION_KEY')
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        
        if not self.api_key:
            logger.warning("No Brave Search API key found in environment variables or constructor")

    def search(self, query: str, count: int = 5, country: str = "US", 
               freshness: str = "week", 
               safe_search: str = "moderate") -> Dict[str, Any]:
        """
        Search the web using Brave Search.
        
        Args:
            query: The search query
            count: Number of results to return (max 20)
            country: Two-letter country code (e.g., "US", "GB", "DE")
            freshness: Filter for result freshness ("day", "week", "month")
            safe_search: Safe search setting ("off", "moderate", "strict")
            
        Returns:
            Dictionary with search results
        
        Raises:
            Exception: If the search fails
        """
        try:
            # Validate count parameter
            if count < 1 or count > 20:
                count = max(1, min(count, 20))  # Clamp between 1-20
                logger.warning(f"Count parameter adjusted to {count} (must be between 1-20)")
                
            # Validate safe_search parameter
            if safe_search not in ["off", "moderate", "strict"]:
                safe_search = "moderate"
                logger.warning(f"Invalid safe_search value, defaulting to 'moderate'")
                
            # Prepare headers
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Subscription-Token": self.subscription_key or "",
                "X-API-Key": self.api_key or ""
            }
            
            # Prepare parameters
            params = {
                "q": query,
                "count": count,
                "country": country,
                "safesearch": safe_search
            }
            
            # Add freshness parameter if provided and valid
            if freshness in ["day", "week", "month"]:
                params["freshness"] = freshness
                
            # Make the request
            response = requests.get(self.base_url, headers=headers, params=params)
            response.raise_for_status()  # Raise exception for 4XX/5XX status codes
            
            data = response.json()
            
            # Format the response in a more consumable structure
            results = []
            
            # Extract web pages
            if "web" in data and "results" in data["web"]:
                for result in data["web"]["results"][:count]:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "description": result.get("description", ""),
                        "published_date": result.get("published_date", "")
                    })
            
            # Return formatted results
            return {
                "results": results,
                "total_results": data.get("web", {}).get("totalResults", 0),
                "query": query
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Brave search request failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "results": []}
        
        except Exception as e:
            error_msg = f"Unexpected error in Brave search: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "results": []}

    def as_function_tool(self) -> FunctionTool:
        """
        Get the BraveSearchTool as a FunctionTool compatible with llama_index.
        
        Returns:
            A FunctionTool instance for this search tool
        """
        # Create the FunctionTool without an explicit schema
        # The schema will be auto-generated from the function signature
        return FunctionTool.from_defaults(
            name="brave_search",
            fn=self.search,
            description="Search the web using Brave Search. Useful for finding current information online."
        )
        
# Default instance for direct imports
brave_search_tool = BraveSearchTool().as_function_tool() 