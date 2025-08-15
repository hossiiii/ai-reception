import uuid
from datetime import datetime, timedelta
from typing import Any

from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VideoGrant
from twilio.rest import Client

from ..config import settings


class TwilioService:
    """Twilio Video service for video call room management"""

    def __init__(self):
        """Initialize Twilio client with credentials"""
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.api_key = settings.twilio_api_key
        self.api_secret = settings.twilio_api_secret

        # Initialize Twilio client only if credentials are provided
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            print("⚠️  Twilio credentials not configured. Video calls will be mocked.")

    async def create_room(self, visitor_name: str) -> dict[str, Any]:
        """
        Create a new video room for visitor reception

        Args:
            visitor_name: Name of the visitor

        Returns:
            Dictionary containing room details and access token
        """
        # Generate unique room name with prefix
        room_name = f"reception-{uuid.uuid4().hex[:8]}"

        # If in development mode without credentials, return mock data
        if not self.client:
            print(f"🔧 Development mode: Mocking room creation for {visitor_name}")
            return self._create_mock_room_response(room_name, visitor_name)

        try:
            print(f"🔄 Creating Twilio video room: {room_name}")

            # Try to create room with timeout parameters suitable for trial accounts
            # Trial accounts: 1-60 seconds, Production accounts: 1-3600 seconds
            room = None
            creation_method = None

            try:
                # Attempt 1: Create room with trial-compatible timeout values
                room = self.client.video.v1.rooms.create(
                    unique_name=room_name,
                    type='group',  # Group room for up to 50 participants
                    max_participants=2,  # Limit to 2 for reception use case
                    record_participants_on_connect=False,  # Disable recording for free trial
                    empty_room_timeout=60,  # 1 minute (compatible with trial accounts)
                    unused_room_timeout=60  # 1 minute (compatible with trial accounts)
                )
                creation_method = "with trial-compatible timeouts (60s)"

            except Exception as timeout_error:
                if "Timeout is out of range" in str(timeout_error):
                    print("⚠️  Trial timeout values failed, trying without timeout parameters...")

                    # Attempt 2: Create room without timeout parameters (uses Twilio defaults)
                    room = self.client.video.v1.rooms.create(
                        unique_name=room_name,
                        type='group',
                        max_participants=2,
                        record_participants_on_connect=False
                        # No timeout parameters - uses Twilio defaults
                    )
                    creation_method = "without timeout parameters (Twilio defaults)"
                else:
                    # Re-raise if it's not a timeout-related error
                    raise timeout_error

            if room:
                print(f"✅ Successfully created Twilio room {creation_method}: {room.sid}")
            else:
                raise Exception("Failed to create room with any configuration")

            # Generate access token for visitor
            identity = f"{visitor_name}_visitor"
            access_token = self._generate_access_token(identity, room_name)

            # Generate room URL for joining
            room_url = f"{settings.frontend_url}/video-call?room={room_name}"

            # Calculate expiry times
            created_at = datetime.now()
            expires_at = created_at + timedelta(hours=1)

            return {
                'room_name': room_name,
                'room_sid': room.sid,
                'access_token': access_token,
                'room_url': room_url,
                'created_at': created_at.isoformat(),
                'expires_at': expires_at.isoformat(),
                'visitor_identity': identity,
                'max_participants': 2
            }

        except ValueError as e:
            # JWT token generation error
            print(f"❌ Token generation error: {e}")
            raise Exception(f"Token generation failed: {str(e)}")
        except Exception as e:
            # Twilio API error
            error_message = str(e)
            print(f"❌ Failed to create Twilio room: {error_message}")

            # Provide specific error messages for common issues
            if "Type must be one of" in error_message:
                raise Exception("Invalid room type. Please check Twilio account permissions for room types.")
            elif "Invalid Access Token" in error_message or "authentication" in error_message.lower():
                raise Exception("Twilio authentication failed. Please verify TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.")
            elif "API Key" in error_message:
                raise Exception("API Key error. Ensure TWILIO_API_KEY and TWILIO_API_SECRET are set and the API Key is in US1 region.")
            else:
                # For development/testing, return mock response for unknown errors
                print("🔧 Falling back to mock response due to Twilio error")
                return self._create_mock_room_response(room_name, visitor_name)

    async def generate_staff_token(self, room_name: str, staff_name: str) -> dict[str, str]:
        """
        Generate access token for staff member to join existing room

        Args:
            room_name: Name of the existing room
            staff_name: Name of the staff member

        Returns:
            Dictionary containing access token

        Raises:
            Exception: If token generation fails
        """
        # Validate room name
        if not room_name or not room_name.strip():
            raise Exception("Room name cannot be empty")

        # Validate staff name
        if not staff_name or not staff_name.strip():
            raise Exception("Staff name cannot be empty")

        if not self.api_key or not self.api_secret:
            print("🔧 Development mode: Returning mock staff token")
            # Create mock JWT token for staff (similar to visitor token)
            mock_jwt_header = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            mock_jwt_payload = "eyJpc3MiOiJtb2NrIiwic3ViIjoic3RhZmYiLCJhdWQiOlsidmlkZW8iXSwiZXhwIjo5OTk5OTk5OTk5LCJpYXQiOjE2MDAwMDAwMDAsImp0aSI6Im1vY2tfc3RhZmZfand0X2lkIiwiZ3JhbnRzIjp7InZpZGVvIjp7InJvb20iOiJ0ZXN0LXJvb20tc3RhZmYifX19"
            mock_jwt_signature = "mock_staff_signature_for_development"
            mock_staff_token = f"{mock_jwt_header}.{mock_jwt_payload}.{mock_jwt_signature}"

            return {
                'access_token': mock_staff_token,
                'identity': f"{staff_name.strip()}_staff"
            }

        try:
            identity = f"{staff_name}_staff"
            access_token = self._generate_access_token(identity, room_name)

            return {
                'access_token': access_token,
                'identity': identity
            }
        except Exception as e:
            print(f"❌ Failed to generate staff token: {e}")
            raise Exception(f"Staff token generation failed: {str(e)}")

    async def end_room(self, room_name: str) -> bool:
        """
        End an active video room

        Args:
            room_name: Name of the room to end

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            print(f"🔧 Development mode: Mocking room end for {room_name}")
            return True

        try:
            # Update room status to completed
            self.client.video.v1.rooms(room_name).update(status='completed')
            print(f"Room {room_name} ended successfully")
            return True
        except Exception as e:
            print(f"Failed to end room {room_name}: {e}")
            return False

    def _generate_access_token(self, identity: str, room_name: str) -> str:
        """
        Generate JWT access token with Video grant

        Args:
            identity: Unique identifier for the participant
            room_name: Name of the room to grant access to

        Returns:
            JWT token string

        Raises:
            ValueError: If API key or secret is missing
        """
        # Validate required credentials
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret are required for token generation. Ensure TWILIO_API_KEY and TWILIO_API_SECRET are set.")

        if not self.account_sid:
            raise ValueError("Account SID is required for token generation. Ensure TWILIO_ACCOUNT_SID is set.")

        # Validate identity (must be non-empty and valid format)
        if not identity or not identity.strip():
            raise ValueError("Identity cannot be empty")

        # Sanitize identity to ensure it meets Twilio requirements
        sanitized_identity = identity.strip().replace(" ", "_")[:50]  # Max 50 chars, no spaces

        # Create access token with 1 hour TTL (max allowed is 24 hours)
        token = AccessToken(
            self.account_sid,
            self.api_key,
            self.api_secret,
            identity=sanitized_identity,
            ttl=3600  # 1 hour expiry (3600 seconds)
        )

        # Create Video grant for the specific room
        # The room parameter restricts access to only this room
        video_grant = VideoGrant(room=room_name)
        token.add_grant(video_grant)

        # Return JWT string
        try:
            jwt_token = token.to_jwt()
            print(f"✅ Generated JWT token for identity: {sanitized_identity}, room: {room_name}")
            return jwt_token
        except Exception as e:
            print(f"❌ Failed to generate JWT token: {e}")
            raise ValueError(f"JWT token generation failed: {str(e)}")

    def _create_mock_room_response(self, room_name: str, visitor_name: str) -> dict[str, Any]:
        """
        Create mock room response for development without Twilio credentials

        Args:
            room_name: Generated room name
            visitor_name: Name of the visitor

        Returns:
            Mock room response with proper JWT structure for development
        """
        created_at = datetime.now()
        expires_at = created_at + timedelta(hours=1)

        # Create a properly formatted mock JWT token that looks valid to frontend
        # This allows development testing without real Twilio credentials
        mock_jwt_header = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"  # {"alg":"HS256","typ":"JWT"}
        mock_jwt_payload = "eyJpc3MiOiJtb2NrIiwic3ViIjoidGVzdCIsImF1ZCI6WyJ2aWRlbyJdLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTYwMDAwMDAwMCwianRpIjoibW9ja19qd3RfaWQiLCJncmFudHMiOnsidmlkZW8iOnsicm9vbSI6InRlc3Qtcm9vbSJ9fX0"  # Mock payload with video grant
        mock_jwt_signature = "mock_signature_for_development_only"
        mock_access_token = f"{mock_jwt_header}.{mock_jwt_payload}.{mock_jwt_signature}"

        return {
            'room_name': room_name,
            'room_sid': f"mock_sid_{room_name}",
            'access_token': mock_access_token,
            'room_url': f"{settings.frontend_url}/video-call?room={room_name}",
            'created_at': created_at.isoformat(),
            'expires_at': expires_at.isoformat(),
            'visitor_identity': f"{visitor_name}_visitor",
            'max_participants': 2,
            'mock': True
        }
