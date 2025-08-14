from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class VideoRoomRequest(BaseModel):
    """Request model for creating a video room"""
    visitor_name: str = Field(..., description="Name of the visitor", min_length=1, max_length=100)
    visitor_company: Optional[str] = Field(None, description="Company name of the visitor", max_length=200)
    purpose: str = Field(default="video_reception", description="Purpose of the video call")


class VideoRoomResponse(BaseModel):
    """Response model for video room creation"""
    room_name: str = Field(..., description="Unique room identifier")
    room_sid: str = Field(..., description="Twilio room SID")
    access_token: str = Field(..., description="JWT access token for visitor")
    room_url: str = Field(..., description="URL to join the video call")
    created_at: str = Field(..., description="Room creation timestamp (ISO format)")
    expires_at: str = Field(..., description="Token expiry timestamp (ISO format)")
    visitor_identity: str = Field(..., description="Unique visitor identity in the room")
    max_participants: int = Field(default=2, description="Maximum participants allowed")
    mock: Optional[bool] = Field(None, description="Whether this is a mock response for development")


class StaffTokenRequest(BaseModel):
    """Request model for generating staff access token"""
    room_name: str = Field(..., description="Name of the room to join", min_length=1)
    staff_name: str = Field(..., description="Name of the staff member", min_length=1, max_length=100)


class StaffTokenResponse(BaseModel):
    """Response model for staff token generation"""
    access_token: str = Field(..., description="JWT access token for staff member")
    identity: str = Field(..., description="Unique staff identity in the room")


class VideoRoomEndRequest(BaseModel):
    """Request model for ending a video room"""
    room_name: str = Field(..., description="Name of the room to end", min_length=1)


class VideoRoomNotification(BaseModel):
    """Model for Slack notification data"""
    room_name: str = Field(..., description="Room identifier")
    room_url: str = Field(..., description="URL to join the room")
    visitor_info: dict = Field(..., description="Visitor information")
    message: str = Field(..., description="Notification message")
    created_at: str = Field(..., description="Creation timestamp")