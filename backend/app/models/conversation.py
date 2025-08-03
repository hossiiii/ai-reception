import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage

from .visitor import VisitorInfo


class ConversationState(TypedDict):
    """LangGraph state for managing conversation flow"""
    messages: Annotated[list[BaseMessage], operator.add]
    visitor_info: VisitorInfo | None
    current_step: Literal[
        "greeting",
        "name_collection",
        "confirmation",
        "type_detection",
        "appointment_check",
        "guidance",
        "complete"
    ]
    calendar_result: dict | None
    error_count: int
    session_id: str  # Step2 voice session identification support
