import uuid
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.conversation import graph_manager
from app.main import app


class TestConversationAPI:
    """Test cases for Conversation API endpoints"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_session_id(self):
        return str(uuid.uuid4())

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/api/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "running" in data["message"]

    @patch.object(graph_manager, 'start_conversation')
    def test_start_conversation_success(self, mock_start, client):
        """Test successful conversation start"""
        mock_session_id = str(uuid.uuid4())
        mock_start.return_value = {
            "success": True,
            "session_id": mock_session_id,
            "message": "いらっしゃいませ！",
            "step": "name_collection",
            "visitor_info": None
        }

        response = client.post("/api/conversations")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["session_id"] == mock_session_id
        assert "いらっしゃいませ" in data["message"]
        assert data["step"] == "name_collection"

    @patch.object(graph_manager, 'start_conversation')
    def test_start_conversation_failure(self, mock_start, client):
        """Test conversation start failure"""
        mock_start.side_effect = Exception("System error")

        response = client.post("/api/conversations")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Failed to start conversation" in data["detail"]

    @patch.object(graph_manager, 'send_message')
    def test_send_message_success(self, mock_send, client, mock_session_id):
        """Test successful message sending"""
        mock_send.return_value = {
            "success": True,
            "session_id": mock_session_id,
            "message": "ありがとうございます。確認いたします。",
            "step": "confirmation",
            "visitor_info": {
                "name": "山田太郎",
                "company": "株式会社テスト",
                "confirmed": False
            },
            "completed": False
        }

        response = client.post(
            f"/api/conversations/{mock_session_id}/messages",
            json={"message": "山田太郎、株式会社テストです"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["step"] == "confirmation"
        assert data["visitor_info"]["name"] == "山田太郎"
        assert data["completed"] is False

    def test_send_message_invalid_session_id(self, client):
        """Test sending message with invalid session ID format"""
        response = client.post(
            "/api/conversations/invalid-uuid/messages",
            json={"message": "test message"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Invalid session ID format" in data["detail"]

    def test_send_message_empty_message(self, client, mock_session_id):
        """Test sending empty message"""
        response = client.post(
            f"/api/conversations/{mock_session_id}/messages",
            json={"message": ""}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Message cannot be empty" in data["detail"]

    @patch.object(graph_manager, 'send_message')
    def test_send_message_session_not_found(self, mock_send, client, mock_session_id):
        """Test sending message to non-existent session"""
        mock_send.return_value = {
            "success": False,
            "session_id": mock_session_id,
            "error": "Session not found"
        }

        response = client.post(
            f"/api/conversations/{mock_session_id}/messages",
            json={"message": "test message"}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Conversation session not found" in data["detail"]

    @patch.object(graph_manager, 'send_message')
    def test_send_message_system_error(self, mock_send, client, mock_session_id):
        """Test message sending with system error"""
        mock_send.return_value = {
            "success": False,
            "session_id": mock_session_id,
            "error": "System processing error"
        }

        response = client.post(
            f"/api/conversations/{mock_session_id}/messages",
            json={"message": "test message"}
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "System processing error" in data["detail"]

    @patch.object(graph_manager, 'get_conversation_history')
    def test_get_conversation_history_success(self, mock_history, client, mock_session_id):
        """Test successful conversation history retrieval"""
        mock_history.return_value = {
            "success": True,
            "session_id": mock_session_id,
            "messages": [
                {
                    "speaker": "ai",
                    "content": "いらっしゃいませ！",
                    "timestamp": "2024-01-01T10:00:00Z"
                },
                {
                    "speaker": "visitor",
                    "content": "山田太郎、株式会社テストです",
                    "timestamp": "2024-01-01T10:01:00Z"
                }
            ],
            "visitor_info": {
                "name": "山田太郎",
                "company": "株式会社テスト"
            },
            "current_step": "confirmation",
            "completed": False
        }

        response = client.get(f"/api/conversations/{mock_session_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["messages"]) == 2
        assert data["messages"][0]["speaker"] == "ai"
        assert data["visitor_info"]["name"] == "山田太郎"
        assert data["current_step"] == "confirmation"

    def test_get_conversation_history_invalid_session_id(self, client):
        """Test getting history with invalid session ID format"""
        response = client.get("/api/conversations/invalid-uuid")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Invalid session ID format" in data["detail"]

    @patch.object(graph_manager, 'get_conversation_history')
    def test_get_conversation_history_not_found(self, mock_history, client, mock_session_id):
        """Test getting history for non-existent session"""
        mock_history.return_value = {
            "success": False,
            "session_id": mock_session_id,
            "error": "Session not found"
        }

        response = client.get(f"/api/conversations/{mock_session_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Conversation session not found" in data["detail"]

    def test_end_conversation_success(self, client, mock_session_id):
        """Test successful conversation ending"""
        response = client.delete(f"/api/conversations/{mock_session_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == mock_session_id
        assert "ended successfully" in data["message"]

    def test_end_conversation_invalid_session_id(self, client):
        """Test ending conversation with invalid session ID format"""
        response = client.delete("/api/conversations/invalid-uuid")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Invalid session ID format" in data["detail"]

    def test_list_active_sessions(self, client):
        """Test listing active sessions (placeholder implementation)"""
        response = client.get("/api/conversations/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_conversation_flow_integration(self, client):
        """Test complete conversation flow integration"""
        with patch.object(graph_manager, 'start_conversation') as mock_start, \
             patch.object(graph_manager, 'send_message') as mock_send, \
             patch.object(graph_manager, 'get_conversation_history') as mock_history:

            session_id = str(uuid.uuid4())

            # Start conversation
            mock_start.return_value = {
                "success": True,
                "session_id": session_id,
                "message": "いらっしゃいませ！",
                "step": "name_collection"
            }

            start_response = client.post("/api/conversations")
            assert start_response.status_code == status.HTTP_200_OK
            start_data = start_response.json()
            session_id = start_data["session_id"]

            # Send message
            mock_send.return_value = {
                "success": True,
                "session_id": session_id,
                "message": "確認いたします",
                "step": "confirmation",
                "visitor_info": {
                    "name": "山田太郎",
                    "company": "株式会社テスト"
                },
                "completed": False
            }

            message_response = client.post(
                f"/api/conversations/{session_id}/messages",
                json={"message": "山田太郎、株式会社テストです"}
            )
            assert message_response.status_code == status.HTTP_200_OK
            message_data = message_response.json()
            assert message_data["step"] == "confirmation"

            # Get history
            mock_history.return_value = {
                "success": True,
                "session_id": session_id,
                "messages": [
                    {"speaker": "ai", "content": "いらっしゃいませ！"},
                    {"speaker": "visitor", "content": "山田太郎、株式会社テストです"},
                    {"speaker": "ai", "content": "確認いたします"}
                ],
                "current_step": "confirmation",
                "completed": False
            }

            history_response = client.get(f"/api/conversations/{session_id}")
            assert history_response.status_code == status.HTTP_200_OK
            history_data = history_response.json()
            assert len(history_data["messages"]) == 3

            # End conversation
            end_response = client.delete(f"/api/conversations/{session_id}")
            assert end_response.status_code == status.HTTP_200_OK


class TestConversationAPIValidation:
    """Test cases for API validation"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_send_message_missing_message_field(self, client):
        """Test sending request without message field"""
        session_id = str(uuid.uuid4())
        response = client.post(
            f"/api/conversations/{session_id}/messages",
            json={}
        )

        # Should return 422 for validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_send_message_invalid_json(self, client):
        """Test sending invalid JSON"""
        session_id = str(uuid.uuid4())
        response = client.post(
            f"/api/conversations/{session_id}/messages",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_send_message_long_message(self, client):
        """Test sending extremely long message"""
        session_id = str(uuid.uuid4())
        long_message = "あ" * 1000  # 1000 characters

        with patch.object(graph_manager, 'send_message') as mock_send:
            mock_send.return_value = {
                "success": True,
                "session_id": session_id,
                "message": "メッセージを受信しました",
                "step": "processing",
                "completed": False
            }

            response = client.post(
                f"/api/conversations/{session_id}/messages",
                json={"message": long_message}
            )

            # Should still process (no hard limit set in API)
            assert response.status_code == status.HTTP_200_OK

    def test_api_cors_headers(self, client):
        """Test that CORS headers are properly set"""
        response = client.options("/api/health")

        # Note: TestClient doesn't fully simulate CORS,
        # but we can test that the endpoint responds
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]


class TestAPIErrorHandling:
    """Test cases for API error handling"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @patch.object(graph_manager, 'start_conversation')
    def test_start_conversation_unexpected_error(self, mock_start, client):
        """Test handling of unexpected errors during conversation start"""
        mock_start.side_effect = RuntimeError("Unexpected system error")

        response = client.post("/api/conversations")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Failed to start conversation" in data["detail"]

    @patch.object(graph_manager, 'send_message')
    def test_send_message_timeout_error(self, mock_send, client):
        """Test handling of timeout errors"""
        session_id = str(uuid.uuid4())
        mock_send.side_effect = TimeoutError("Request timeout")

        response = client.post(
            f"/api/conversations/{session_id}/messages",
            json={"message": "test message"}
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Failed to process message" in data["detail"]

    def test_nonexistent_endpoint(self, client):
        """Test calling non-existent endpoint"""
        response = client.get("/api/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND
