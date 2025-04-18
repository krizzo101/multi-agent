from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import asyncio
import logging

from api.services.agent import AgentChat

# Create logger for this module
logger = logging.getLogger(__name__)

# Create router
agent_router = APIRouter(prefix="/agent", tags=["agent"])

# Request models
class ChatRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None

# Response models
class ChatResponse(BaseModel):
    response: str
    session_id: str

class ResetResponse(BaseModel):
    status: str
    message: str

class AgentStatusResponse(BaseModel):
    total_agents: int
    registered_agents: List[Dict[str, Any]]
    active_sessions: int

# Initialize agent chat globally
agent_chat = AgentChat()

@agent_router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint for agent chat interaction
    
    Args:
        request (ChatRequest): Contains the user query and optional session/user IDs
    
    Returns:
        ChatResponse: Agent's response to the query with session ID
    """
    try:
        # Get or generate session ID
        session_id = request.session_id or f"session_{len(agent_chat.proxy.sessions) + 1}"
        
        # Use the updated get_response method with session tracking
        response = await agent_chat.get_response(
            request.query,
            user_id=request.user_id or "anonymous",
            session_id=session_id
        )
        
        return ChatResponse(response=response, session_id=session_id)
    except Exception as e:
        # Log the error for debugging
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        
        # Handle any potential errors
        raise HTTPException(status_code=500, detail=str(e))

@agent_router.post("/reset", response_model=ResetResponse)
async def reset_chat_endpoint(session_id: Optional[str] = None):
    """
    Endpoint to reset the chat history for a specific session or all sessions
    
    Args:
        session_id: Optional session ID to reset (resets all if not provided)
    
    Returns:
        ResetResponse: Confirmation of chat history reset
    """
    try:
        # Call the reset_chat method with optional session_id
        agent_chat.reset_chat(session_id)
        
        message = f"Chat history for session {session_id} reset successfully" if session_id else "All chat sessions reset successfully"
        
        return ResetResponse(
            status="success", 
            message=message
        )
    except Exception as e:
        # Handle any potential errors
        raise HTTPException(status_code=500, detail=str(e))

@agent_router.get("/status", response_model=AgentStatusResponse)
async def agent_status_endpoint():
    """
    Endpoint to get agent system status information
    
    Returns:
        AgentStatusResponse: Information about registered agents and sessions
    """
    try:
        # Get status information
        status = await agent_chat.get_agent_status()
        return AgentStatusResponse(**status)
    except Exception as e:
        # Handle any potential errors
        raise HTTPException(status_code=500, detail=str(e))