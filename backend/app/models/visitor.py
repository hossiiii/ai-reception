from typing import TypedDict, Optional, Literal
from datetime import datetime

VisitorType = Literal["appointment", "sales", "delivery"]


class VisitorInfo(TypedDict):
    """Visitor information collected during conversation"""
    name: str
    company: str
    visitor_type: Optional[VisitorType]
    confirmed: bool
    correction_count: int


class ConversationLog(TypedDict):
    """Individual conversation message log"""
    timestamp: datetime
    speaker: Literal["visitor", "ai"]
    message: str