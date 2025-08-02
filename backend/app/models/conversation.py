from typing import TypedDict, List, Optional, Annotated, Literal
from langchain_core.messages import BaseMessage
from .visitor import VisitorInfo
import operator


class ConversationState(TypedDict):
    """LangGraph state for managing conversation flow"""
    messages: Annotated[List[BaseMessage], operator.add]
    visitor_info: Optional[VisitorInfo]
    current_step: Literal[
        "greeting", 
        "name_collection", 
        "confirmation", 
        "type_detection", 
        "appointment_check", 
        "guidance", 
        "complete"
    ]
    calendar_result: Optional[dict]
    error_count: int
    session_id: str  # Step2 voice session identification support