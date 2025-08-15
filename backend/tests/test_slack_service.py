from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from app.models.visitor import VisitorInfo
from app.services.slack_service import SlackService


class TestSlackService:
    """Test cases for SlackService"""

    @pytest.fixture
    def slack_service(self):
        """Create SlackService instance for testing"""
        return SlackService()

    def test_get_jst_timestamp_format(self, slack_service):
        """Test that JST timestamp returns correct format"""
        timestamp = slack_service._get_jst_timestamp()

        # Check format: YYYY-MM-DD HH:MM:SS
        assert len(timestamp) == 19
        assert timestamp[4] == '-'
        assert timestamp[7] == '-'
        assert timestamp[10] == ' '
        assert timestamp[13] == ':'
        assert timestamp[16] == ':'

    def test_get_jst_timestamp_timezone(self, slack_service):
        """Test that timestamp is in JST timezone"""
        # Mock current time to a known value in JST
        fixed_jst_time = datetime(2025, 8, 15, 18, 30, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        expected_jst_time = "2025-08-15 18:30:00"  # 18:30 JST

        with patch('app.services.slack_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_jst_time
            timestamp = slack_service._get_jst_timestamp()
            assert timestamp == expected_jst_time

    @pytest.mark.asyncio
    async def test_error_notification_uses_jst(self, slack_service):
        """Test that error notification uses JST timestamp"""
        with patch.object(slack_service, '_send_web_api_message', return_value={"ok": True}) as mock_send:
            with patch.object(slack_service, '_get_jst_timestamp', return_value="2025-08-15 18:30:00") as mock_jst:

                result = await slack_service.send_error_notification(
                    "Test error",
                    "test-session-id"
                )

                assert result is True
                mock_jst.assert_called_once()

                # Check that the JST timestamp was used in the message
                call_args = mock_send.call_args[0][0]
                error_time_field = call_args['blocks'][1]['fields'][1]['text']
                assert "2025-08-15 18:30:00" in error_time_field

    @pytest.mark.asyncio
    async def test_video_call_notification_uses_jst(self, slack_service):
        """Test that video call notification uses JST timestamp"""
        visitor_info: VisitorInfo = {
            'name': 'テスト太郎',
            'company': 'テスト株式会社'
        }

        with patch.object(slack_service, '_send_web_api_message', return_value={"ok": True}) as mock_send:
            with patch.object(slack_service, '_get_jst_timestamp', return_value="2025-08-15 18:30:00") as mock_jst:

                result = await slack_service.send_video_call_notification(
                    visitor_info,
                    "https://example.com/room",
                    "test-room"
                )

                assert result is True
                mock_jst.assert_called_once()

                # Check that the JST timestamp was used in the message
                call_args = mock_send.call_args[0][0]
                start_time_field = call_args['blocks'][1]['fields'][3]['text']
                assert "2025-08-15 18:30:00" in start_time_field

    @pytest.mark.asyncio
    async def test_visitor_notification_uses_jst(self, slack_service):
        """Test that visitor notification uses JST timestamp"""
        visitor_info: VisitorInfo = {
            'name': 'テスト太郎',
            'company': 'テスト株式会社',
            'visitor_type': 'appointment'
        }

        with patch.object(slack_service, '_send_web_api_message', return_value={"ok": True}) as mock_send:
            with patch.object(slack_service, '_get_jst_timestamp', return_value="2025-08-15 18:30:00") as mock_jst:

                result = await slack_service.send_visitor_notification(
                    visitor_info,
                    []
                )

                assert result is True
                mock_jst.assert_called_once()

                # Check that the JST timestamp was used in the message
                call_args = mock_send.call_args[0][0]
                response_time_field = call_args['blocks'][1]['fields'][3]['text']
                assert "2025-08-15 18:30:00" in response_time_field
