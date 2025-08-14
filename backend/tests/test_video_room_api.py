"""
Test cases for video room API endpoints
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.video_room import VideoRoomRequest


@pytest.fixture
def client():
    """Test client for API endpoints"""
    return TestClient(app)


@pytest.fixture
def sample_video_room_request():
    """Sample video room request data"""
    return {
        "visitor_name": "Test User",
        "visitor_company": "Test Corp",
        "purpose": "video_reception"
    }


@pytest.fixture
def mock_video_room_response():
    """Mock video room response data"""
    return {
        "room_name": "reception-12345678",
        "room_sid": "RMtest123",
        "access_token": "test_access_token",
        "room_url": "http://localhost:3000/video-call?room=reception-12345678",
        "created_at": "2023-01-01T12:00:00",
        "expires_at": "2023-01-01T13:00:00",
        "visitor_identity": "Test User_Test Corp",
        "max_participants": 2
    }


class TestVideoRoomAPI:
    """Test video room API endpoints"""

    @patch('app.api.video_room.twilio_service')
    @patch('app.api.video_room.slack_service')
    async def test_create_room_success(self, mock_slack, mock_twilio, client, sample_video_room_request, mock_video_room_response):
        """Test successful room creation"""
        # Mock Twilio service
        mock_twilio.create_room = AsyncMock(return_value=mock_video_room_response)
        
        # Mock Slack service
        mock_slack.send_video_call_notification = AsyncMock(return_value=True)
        
        # Make request
        response = client.post('/api/video/create-room', json=sample_video_room_request)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data['room_name'] == mock_video_room_response['room_name']
        assert data['access_token'] == mock_video_room_response['access_token']
        assert data['room_url'] == mock_video_room_response['room_url']
        
        # Verify service calls
        mock_twilio.create_room.assert_called_once_with(
            visitor_name="Test User",
            visitor_company="Test Corp"
        )
        mock_slack.send_video_call_notification.assert_called_once()

    async def test_create_room_missing_name(self, client):
        """Test room creation with missing visitor name"""
        request_data = {
            "visitor_company": "Test Corp",
            "purpose": "video_reception"
        }
        
        response = client.post('/api/video/create-room', json=request_data)
        
        # Should return validation error
        assert response.status_code == 422

    async def test_create_room_empty_name(self, client):
        """Test room creation with empty visitor name"""
        request_data = {
            "visitor_name": "",
            "visitor_company": "Test Corp",
            "purpose": "video_reception"
        }
        
        response = client.post('/api/video/create-room', json=request_data)
        
        # Should return validation error
        assert response.status_code == 422

    @patch('app.api.video_room.twilio_service')
    async def test_generate_staff_token_success(self, mock_twilio, client):
        """Test successful staff token generation"""
        # Mock Twilio service
        mock_token_response = {
            "access_token": "staff_test_token",
            "identity": "Staff_staff"
        }
        mock_twilio.generate_staff_token = AsyncMock(return_value=mock_token_response)
        
        request_data = {
            "room_name": "reception-12345678",
            "staff_name": "Staff"
        }
        
        response = client.post('/api/video/staff-token', json=request_data)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data['access_token'] == "staff_test_token"
        assert data['identity'] == "Staff_staff"
        
        # Verify service call
        mock_twilio.generate_staff_token.assert_called_once_with(
            room_name="reception-12345678",
            staff_name="Staff"
        )

    async def test_generate_staff_token_missing_room(self, client):
        """Test staff token generation with missing room name"""
        request_data = {
            "staff_name": "Staff"
        }
        
        response = client.post('/api/video/staff-token', json=request_data)
        
        # Should return validation error
        assert response.status_code == 422

    @patch('app.api.video_room.twilio_service')
    async def test_end_room_success(self, mock_twilio, client):
        """Test successful room ending"""
        # Mock Twilio service
        mock_twilio.end_room = AsyncMock(return_value=True)
        
        request_data = {
            "room_name": "reception-12345678"
        }
        
        response = client.post('/api/video/end-room', json=request_data)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['room_name'] == "reception-12345678"
        assert 'ended_at' in data
        
        # Verify service call
        mock_twilio.end_room.assert_called_once_with("reception-12345678")

    @patch('app.api.video_room.twilio_service')
    async def test_end_room_failure(self, mock_twilio, client):
        """Test room ending failure"""
        # Mock Twilio service failure
        mock_twilio.end_room = AsyncMock(return_value=False)
        
        request_data = {
            "room_name": "reception-12345678"
        }
        
        response = client.post('/api/video/end-room', json=request_data)
        
        # Should return error
        assert response.status_code == 500

    async def test_end_room_missing_name(self, client):
        """Test room ending with missing room name"""
        request_data = {}
        
        response = client.post('/api/video/end-room', json=request_data)
        
        # Should return validation error
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__])