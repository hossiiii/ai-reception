from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid
from ..agents.reception_graph import ReceptionGraphManager


class MessageRequest(BaseModel):
    """Request model for sending a message"""
    message: str


class ConversationStartResponse(BaseModel):
    """Response model for starting a conversation"""
    success: bool
    session_id: str
    message: str
    step: str
    visitor_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class MessageResponse(BaseModel):
    """Response model for message exchange"""
    success: bool
    session_id: str
    message: str
    step: str
    visitor_info: Optional[Dict[str, Any]] = None
    calendar_result: Optional[Dict[str, Any]] = None
    completed: bool = False
    error: Optional[str] = None


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history"""
    success: bool
    session_id: str
    messages: List[Dict[str, Any]] = []
    visitor_info: Optional[Dict[str, Any]] = None
    current_step: Optional[str] = None
    calendar_result: Optional[Dict[str, Any]] = None
    completed: bool = False
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    message: str


# Create router
router = APIRouter(prefix="/api/conversations", tags=["conversations"])

# Global graph manager instance
graph_manager = ReceptionGraphManager()


def get_graph_manager() -> ReceptionGraphManager:
    """Dependency to get graph manager instance"""
    return graph_manager


@router.post("/", response_model=ConversationStartResponse)
async def start_conversation(
    manager: ReceptionGraphManager = Depends(get_graph_manager)
) -> ConversationStartResponse:
    """Start a new conversation session
    
    Returns:
        ConversationStartResponse: Initial greeting and session info
    """
    try:
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Start conversation
        result = await manager.start_conversation(session_id)
        
        return ConversationStartResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start conversation: {str(e)}"
        )


@router.post("/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    session_id: str,
    request: MessageRequest,
    manager: ReceptionGraphManager = Depends(get_graph_manager)
) -> MessageResponse:
    """Send a message to an existing conversation
    
    Args:
        session_id: The conversation session ID
        request: Message request containing the message text
        
    Returns:
        MessageResponse: AI response and conversation state
    """
    try:
        # Validate session ID format
        try:
            uuid.UUID(session_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid session ID format"
            )
        
        # Validate message content
        if not request.message.strip():
            raise HTTPException(
                status_code=400,
                detail="Message cannot be empty"
            )
        
        # Send message to graph
        result = await manager.send_message(session_id, request.message.strip())
        
        if not result["success"]:
            if "Session not found" in result.get("error", ""):
                raise HTTPException(
                    status_code=404,
                    detail="Conversation session not found or expired"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=result.get("error", "Message processing failed")
                )
        
        return MessageResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    session_id: str,
    manager: ReceptionGraphManager = Depends(get_graph_manager)
) -> ConversationHistoryResponse:
    """Get conversation history for a session
    
    Args:
        session_id: The conversation session ID
        
    Returns:
        ConversationHistoryResponse: Complete conversation history
    """
    try:
        # Validate session ID format
        try:
            uuid.UUID(session_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid session ID format"
            )
        
        # Get conversation history
        result = await manager.get_conversation_history(session_id)
        
        if not result["success"]:
            if "Session not found" in result.get("error", ""):
                raise HTTPException(
                    status_code=404,
                    detail="Conversation session not found"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=result.get("error", "Failed to retrieve history")
                )
        
        return ConversationHistoryResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get conversation history: {str(e)}"
        )


@router.delete("/{session_id}")
async def end_conversation(
    session_id: str,
    manager: ReceptionGraphManager = Depends(get_graph_manager)
) -> Dict[str, str]:
    """End a conversation session and clean up resources
    
    Args:
        session_id: The conversation session ID
        
    Returns:
        Dict: Success message
    """
    try:
        # Validate session ID format
        try:
            uuid.UUID(session_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid session ID format"
            )
        
        # Note: LangGraph MemorySaver doesn't have explicit cleanup
        # In production, you might want to implement session timeout cleanup
        
        return {
            "message": f"Conversation {session_id} ended successfully",
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to end conversation: {str(e)}"
        )


@router.get("/", response_model=List[str])
async def list_active_sessions() -> List[str]:
    """List active conversation sessions
    
    Note: This is a placeholder. In production, you'd want to implement
    proper session tracking and cleanup.
    
    Returns:
        List[str]: List of active session IDs
    """
    # Placeholder implementation
    # In production, you'd track active sessions in a database or cache
    return []


# Health check endpoint
health_router = APIRouter(prefix="/api", tags=["health"])


@health_router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="Reception system API is running"
    )