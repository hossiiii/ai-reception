from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..models.video_room import (
    StaffTokenRequest,
    StaffTokenResponse,
    VideoRoomEndRequest,
    VideoRoomRequest,
    VideoRoomResponse,
)
from ..models.visitor import VisitorInfo
from ..services.slack_service import SlackService
from ..services.twilio_service import TwilioService

# Create router
router = APIRouter(prefix="/api/video", tags=["video-calls"])

# Global service instances
twilio_service = TwilioService()
slack_service = SlackService()


def get_twilio_service() -> TwilioService:
    """Dependency to get Twilio service instance"""
    return twilio_service


def get_slack_service() -> SlackService:
    """Dependency to get Slack service instance"""
    return slack_service


@router.post("/create-room", response_model=VideoRoomResponse)
async def create_video_room(
    request: VideoRoomRequest,
    twilio: TwilioService = Depends(get_twilio_service),
    slack: SlackService = Depends(get_slack_service)
) -> VideoRoomResponse:
    """
    Create a new video room for visitor reception

    Args:
        request: Video room creation request

    Returns:
        VideoRoomResponse: Room details and access token
    """
    try:
        # Create video room using Twilio service
        room_data = await twilio.create_room(
            visitor_name=request.visitor_name
        )

        # Prepare visitor info for Slack notification
        visitor_info: VisitorInfo = {
            'name': request.visitor_name,
            'company': 'N/A',
            'visitor_type': 'video_call',
            'purpose': request.purpose,
            'contact_method': 'video_call'
        }

        # Send Slack notification with video room URL
        slack_success = await slack.send_video_call_notification(
            visitor_info=visitor_info,
            room_url=room_data['room_url'],
            room_name=room_data['room_name']
        )

        if not slack_success:
            print(f"⚠️  Failed to send Slack notification for room {room_data['room_name']}")

        # Return structured response
        return VideoRoomResponse(**room_data)

    except Exception as e:
        print(f"Error creating video room: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create video room: {str(e)}"
        )


@router.post("/staff-token", response_model=StaffTokenResponse)
async def generate_staff_token(
    request: StaffTokenRequest,
    twilio: TwilioService = Depends(get_twilio_service)
) -> StaffTokenResponse:
    """
    Generate access token for staff member to join existing room

    Args:
        request: Staff token generation request

    Returns:
        StaffTokenResponse: Access token for staff member
    """
    try:
        # Validate request
        if not request.room_name.strip():
            raise HTTPException(
                status_code=400,
                detail="Room name cannot be empty"
            )

        if not request.staff_name.strip():
            raise HTTPException(
                status_code=400,
                detail="Staff name cannot be empty"
            )

        # Generate staff token
        token_data = await twilio.generate_staff_token(
            room_name=request.room_name,
            staff_name=request.staff_name
        )

        return StaffTokenResponse(**token_data)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating staff token: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate staff token: {str(e)}"
        )


@router.post("/end-room")
async def end_video_room(
    request: VideoRoomEndRequest,
    twilio: TwilioService = Depends(get_twilio_service)
) -> dict[str, Any]:
    """
    End an active video room

    Args:
        request: Room end request

    Returns:
        Dict containing success status
    """
    try:
        # Validate request
        if not request.room_name.strip():
            raise HTTPException(
                status_code=400,
                detail="Room name cannot be empty"
            )

        # End the room
        success = await twilio.end_room(request.room_name)

        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to end room {request.room_name}"
            )

        return {
            'success': True,
            'message': f'Room {request.room_name} ended successfully',
            'room_name': request.room_name,
            'ended_at': datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error ending video room: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to end room: {str(e)}"
        )
