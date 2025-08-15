"""Comprehensive tests for SlackService async methods and thread support (Web API only)"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models.visitor import ConversationLog, VisitorInfo
from app.services.slack_service import SlackService


class TestSlackServiceAsync:
    """Test cases for SlackService async functionality and thread support (Web API only)"""

    @pytest.fixture
    def slack_service(self):
        """Create SlackService instance for testing"""
        return SlackService()

    @pytest.fixture
    def sample_visitor_info(self) -> VisitorInfo:
        """Sample visitor information for testing"""
        return {
            'name': 'テスト太郎',
            'company': 'テスト株式会社',
            'purpose': '商品説明',
            'visitor_type': 'appointment'
        }

    @pytest.fixture
    def sample_conversation_logs(self) -> list[ConversationLog]:
        """Sample conversation logs for testing"""
        return [
            {
                'speaker': 'visitor',
                'message': 'こんにちは、テスト太郎と申します',
                'timestamp': datetime.now().isoformat()
            },
            {
                'speaker': 'ai',
                'message': 'こんにちは、テスト太郎様。いらっしゃいませ。',
                'timestamp': datetime.now().isoformat()
            }
        ]

    @pytest.mark.asyncio
    async def test_send_initial_thread_message_success(self, slack_service):
        """Test successful initial thread message creation with Web API"""
        title = "🔔 新しい来客セッションが開始されました"
        details = "セッションID: test_session_123\n開始時刻: 2025-08-15 15:30:00"

        # Mock successful Web API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "ts": "1692096600.123456"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            thread_ts = await slack_service.send_initial_thread_message(title, details)

        # Should return actual timestamp from Web API
        assert thread_ts == "1692096600.123456"

    @pytest.mark.asyncio
    async def test_send_initial_thread_message_failure(self, slack_service):
        """Test initial thread message failure handling"""
        title = "Test title"
        details = "Test details"

        # Mock failed Web API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": False, "error": "channel_not_found"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            thread_ts = await slack_service.send_initial_thread_message(title, details)

        assert thread_ts is None

    @pytest.mark.asyncio
    async def test_send_initial_thread_message_exception(self, slack_service):
        """Test initial thread message exception handling"""
        title = "Test title"
        details = "Test details"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.RequestError("Network error")
            )

            thread_ts = await slack_service.send_initial_thread_message(title, details)

        assert thread_ts is None

    @pytest.mark.asyncio
    async def test_send_thread_message_success(self, slack_service):
        """Test successful thread message sending"""
        message = "🔄 進捗更新: 来客者情報を収集中"
        thread_ts = "1692096600.0"

        # Mock successful Web API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "ts": "1692096601.123456"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await slack_service.send_thread_message(message, thread_ts)

        assert result is True

        # Verify the request was made with correct parameters
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        assert call_args[1]['json']['text'] == message
        assert call_args[1]['json']['thread_ts'] == thread_ts
        assert call_args[1]['json']['channel'] == slack_service.channel

    @pytest.mark.asyncio
    async def test_send_thread_message_failure(self, slack_service):
        """Test thread message failure handling"""
        message = "Test message"
        thread_ts = "1692096600.0"

        # Mock failed Web API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": False, "error": "invalid_thread_ts"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await slack_service.send_thread_message(message, thread_ts)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_simple_message_without_thread(self, slack_service):
        """Test simple message without thread"""
        message = "Simple test message"

        # Mock successful Web API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "ts": "1692096600.123456"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await slack_service.send_simple_message(message)

        assert result is True

        # Verify no thread_ts in request
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        assert 'thread_ts' not in call_args[1]['json']
        assert call_args[1]['json']['channel'] == slack_service.channel

    @pytest.mark.asyncio
    async def test_send_simple_message_with_thread(self, slack_service):
        """Test simple message with thread"""
        message = "Simple test message"
        thread_ts = "1692096600.0"

        # Mock successful Web API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "ts": "1692096601.123456"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await slack_service.send_simple_message(message, thread_ts)

        assert result is True

        # Verify thread_ts in request
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        assert call_args[1]['json']['thread_ts'] == thread_ts
        assert call_args[1]['json']['channel'] == slack_service.channel

    @pytest.mark.asyncio
    async def test_send_visitor_notification_with_thread(self, slack_service, sample_visitor_info, sample_conversation_logs):
        """Test visitor notification with thread support"""
        thread_ts = "1692096600.0"
        calendar_result = {"found": True, "roomName": "会議室A"}

        # Mock successful Web API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "ts": "1692096601.123456"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await slack_service.send_visitor_notification(
                sample_visitor_info,
                sample_conversation_logs,
                calendar_result,
                thread_ts
            )

        assert result is True

        # Verify thread_ts was included in the request
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        assert call_args[1]['json']['thread_ts'] == thread_ts
        assert call_args[1]['json']['channel'] == slack_service.channel

    @pytest.mark.asyncio
    async def test_send_visitor_notification_without_thread(self, slack_service, sample_visitor_info, sample_conversation_logs):
        """Test visitor notification without thread support"""
        # Mock successful Web API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "ts": "1692096600.123456"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await slack_service.send_visitor_notification(
                sample_visitor_info,
                sample_conversation_logs
            )

        assert result is True

        # Verify no thread_ts in request
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        assert 'thread_ts' not in call_args[1]['json']
        assert call_args[1]['json']['channel'] == slack_service.channel

    @pytest.mark.asyncio
    async def test_web_api_retry_mechanism(self, slack_service):
        """Test Web API retry mechanism with exponential backoff"""
        message = {"channel": "#test", "text": "Test message"}

        # Mock responses: fail twice, then succeed
        mock_responses = [
            MagicMock(status_code=500, text="Internal Server Error"),
            MagicMock(status_code=502, text="Bad Gateway"),
            MagicMock(status_code=200, json=lambda: {"ok": True, "ts": "1692096600.123456"})
        ]

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=mock_responses)

            result = await slack_service._send_web_api_message(message)

        assert result is not None
        assert result["ok"] is True

        # Should have made 3 attempts (2 failures + 1 success)
        assert mock_client.return_value.__aenter__.return_value.post.call_count == 3

    @pytest.mark.asyncio
    async def test_web_api_max_retries_exceeded(self, slack_service):
        """Test Web API behavior when max retries are exceeded"""
        message = {"channel": "#test", "text": "Test message"}

        # Mock all responses to fail
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await slack_service._send_web_api_message(message)

        assert result is None

        # Should have made 3 attempts (max retries)
        assert mock_client.return_value.__aenter__.return_value.post.call_count == 3

    @pytest.mark.asyncio
    async def test_web_api_network_exception_retry(self, slack_service):
        """Test Web API retry on network exceptions"""
        message = {"channel": "#test", "text": "Test message"}

        # Mock network errors then success
        side_effects = [
            httpx.RequestError("Network error"),
            httpx.TimeoutException("Timeout"),
            MagicMock(status_code=200, json=lambda: {"ok": True, "ts": "1692096600.123456"})
        ]

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=side_effects)

            result = await slack_service._send_web_api_message(message)

        assert result is not None
        assert result["ok"] is True
        assert mock_client.return_value.__aenter__.return_value.post.call_count == 3

    @pytest.mark.asyncio
    async def test_web_api_no_token_configured(self, slack_service):
        """Test Web API behavior when bot token is not configured"""
        # Mock missing bot token
        slack_service.bot_token = None

        message = {"channel": "#test", "text": "Test message"}
        result = await slack_service._send_web_api_message(message)

        assert result is None

    @pytest.mark.asyncio
    async def test_web_api_invalid_auth(self, slack_service):
        """Test Web API handling of invalid authentication"""
        message = {"channel": "#test", "text": "Test message"}

        # Mock invalid auth response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": False, "error": "invalid_auth"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await slack_service._send_web_api_message(message)

        assert result is None

    @pytest.mark.asyncio
    async def test_web_api_channel_not_found(self, slack_service):
        """Test Web API handling of channel not found error"""
        message = {"channel": "#nonexistent", "text": "Test message"}

        # Mock channel not found response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": False, "error": "channel_not_found"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await slack_service._send_web_api_message(message)

        assert result is None

    @pytest.mark.asyncio
    async def test_concurrent_web_api_calls(self, slack_service):
        """Test concurrent Web API calls handling"""
        messages = [
            {"channel": "#test", "text": f"Test message {i}"}
            for i in range(10)
        ]

        # Mock successful responses
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "ts": "1692096600.123456"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            # Send multiple Web API messages concurrently
            tasks = [
                slack_service._send_web_api_message(message)
                for message in messages
            ]

            results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(result and result.get("ok") for result in results)

        # Should have made 10 calls
        assert mock_client.return_value.__aenter__.return_value.post.call_count == 10

    @pytest.mark.asyncio
    async def test_timeout_configuration(self, slack_service):
        """Test timeout configuration in Web API calls"""
        message = {"channel": "#test", "text": "Test message"}

        # Verify default timeout
        assert slack_service.timeout == 10.0

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "ts": "1692096600.123456"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            await slack_service._send_web_api_message(message)

            # Verify timeout was passed to AsyncClient
            client_call_args = mock_client.call_args
            assert client_call_args[1]['timeout'] == 10.0

    @pytest.mark.asyncio
    async def test_visitor_type_info_mapping(self, slack_service):
        """Test visitor type information mapping"""
        # Test all visitor types
        test_cases = [
            ("appointment", {"name": "予約来客", "icon": "📅"}),
            ("sales", {"name": "営業訪問", "icon": "💼"}),
            ("delivery", {"name": "配達業者", "icon": "📦"}),
            (None, {"name": "不明", "icon": "❓"}),
            ("unknown_type", {"name": "不明", "icon": "❓"})
        ]

        for visitor_type, expected_info in test_cases:
            result = slack_service._get_visitor_type_info(visitor_type)
            assert result == expected_info

    @pytest.mark.asyncio
    async def test_visitor_message_blocks_structure(self, slack_service, sample_visitor_info, sample_conversation_logs):
        """Test visitor message blocks structure"""
        calendar_result = {"found": True, "roomName": "会議室A"}

        blocks = slack_service._create_visitor_message_blocks(
            sample_visitor_info,
            sample_conversation_logs,
            calendar_result
        )

        # Should have header, visitor info, calendar info, conversation, and actions
        assert len(blocks) >= 4

        # First block should be header
        assert blocks[0]["type"] == "header"
        assert "来客対応ログ" in blocks[0]["text"]["text"]

        # Should contain visitor info section
        visitor_section = next(
            (block for block in blocks if block["type"] == "section" and "fields" in block),
            None
        )
        assert visitor_section is not None

        # Should contain action buttons
        action_block = next(
            (block for block in blocks if block["type"] == "actions"),
            None
        )
        assert action_block is not None

    @pytest.mark.asyncio
    async def test_conversation_logs_filtering(self, slack_service, sample_visitor_info):
        """Test conversation logs duplicate filtering"""
        # Create logs with duplicates
        conversation_logs = [
            {
                'speaker': 'visitor',
                'message': 'こんにちは',
                'timestamp': datetime.now().isoformat()
            },
            {
                'speaker': 'visitor',
                'message': 'こんにちは',  # Duplicate
                'timestamp': datetime.now().isoformat()
            },
            {
                'speaker': 'ai',
                'message': 'いらっしゃいませ',
                'timestamp': datetime.now().isoformat()
            }
        ]

        blocks = slack_service._create_visitor_message_blocks(
            sample_visitor_info,
            conversation_logs
        )

        # Find conversation block
        conversation_block = next(
            (block for block in blocks
             if block["type"] == "section" and "text" in block and "会話履歴" in block["text"]["text"]),
            None
        )

        assert conversation_block is not None
        # Should indicate 2 messages (duplicate filtered out)
        assert "(2メッセージ)" in conversation_block["text"]["text"]

    @pytest.mark.asyncio
    async def test_error_notification_structure(self, slack_service, sample_visitor_info):
        """Test error notification message structure"""
        error_message = "テストエラーメッセージ"
        session_id = "test_session_123"

        # Mock successful Web API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "ts": "1692096600.123456"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await slack_service.send_error_notification(
                error_message, session_id, sample_visitor_info
            )

        assert result is True

        # Verify message structure
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        message_payload = call_args[1]['json']

        # Should have blocks with header, session info, error details, and visitor info
        blocks = message_payload['blocks']
        assert len(blocks) >= 3

        # Check header
        assert blocks[0]['type'] == 'header'
        assert '受付システムエラー' in blocks[0]['text']['text']

        # Check session and error info
        assert any(session_id in str(block) for block in blocks)
        assert any(error_message in str(block) for block in blocks)

        # Verify channel is set
        assert message_payload['channel'] == slack_service.channel

    @pytest.mark.asyncio
    async def test_video_call_notification_structure(self, slack_service, sample_visitor_info):
        """Test video call notification message structure"""
        room_url = "https://example.com/room/123"
        room_name = "テストルーム"

        # Mock successful Web API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "ts": "1692096600.123456"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await slack_service.send_video_call_notification(
                sample_visitor_info, room_url, room_name
            )

        assert result is True

        # Verify message structure
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        message_payload = call_args[1]['json']

        blocks = message_payload['blocks']

        # Should have header, fields, link, context, and actions
        assert len(blocks) >= 5

        # Check header
        assert blocks[0]['type'] == 'header'
        assert 'ビデオ通話受付' in blocks[0]['text']['text']

        # Check for room URL and action button
        assert any(room_url in str(block) for block in blocks)
        assert any(room_name in str(block) for block in blocks)

        # Check action button
        action_block = next(
            (block for block in blocks if block['type'] == 'actions'),
            None
        )
        assert action_block is not None
        assert action_block['elements'][0]['url'] == room_url

        # Verify channel is set
        assert message_payload['channel'] == slack_service.channel
