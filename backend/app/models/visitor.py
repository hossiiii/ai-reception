from datetime import datetime
from typing import Literal, TypedDict

VisitorType = Literal["appointment", "sales", "delivery"]


class VisitorInfo(TypedDict):
    """Visitor information collected during conversation"""
    name: str
    company: str
    visitor_type: VisitorType | None
    confirmed: bool
    correction_count: int


class ConversationLog(TypedDict):
    """Individual conversation message log"""
    timestamp: datetime
    speaker: Literal["visitor", "ai"]
    message: str
