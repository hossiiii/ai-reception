"""Comprehensive tests for AsyncNotificationManager - Fixed Version"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.visitor import ConversationLog, VisitorInfo
from app.services.async_notification_manager import AsyncNotificationManager


class TestAsyncNotificationManagerFixed:
    """Test cases for AsyncNotificationManager with proper cleanup"""

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

    async def create_test_manager(self):
        """Create a test manager with mocked SlackService"""
        manager = AsyncNotificationManager()

        # Mock the SlackService to prevent actual API calls
        manager.slack_service = MagicMock()
        manager.slack_service.send_initial_thread_message = AsyncMock(return_value="test_thread_123")
        manager.slack_service.send_thread_message = AsyncMock(return_value=True)
        manager.slack_service.send_visitor_notification = AsyncMock(return_value=True)

        return manager

    @pytest.mark.asyncio
    async def test_processor_lifecycle(self):
        """Test processor start and stop lifecycle"""
        manager = await self.create_test_manager()
        try:
            # Initially processor should not be running
            assert manager._queue_processor_task is None

            # Start processor
            await manager.start_processor()
            assert manager._queue_processor_task is not None
            assert not manager._queue_processor_task.done()

            # Stop processor
            await manager.stop_processor()
            assert manager._queue_processor_task.done()
        finally:
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_session_start_notification_success(self):
        """Test successful session start notification"""
        manager = await self.create_test_manager()
        try:
            session_id = "test_session_123"

            # Start processor
            await manager.start_processor()

            # Send session start notification
            result = await manager.send_session_start_notification(session_id)

            assert result is True
            assert session_id in manager._session_threads
            assert manager._session_threads[session_id] == "test_thread_123"

            # Verify SlackService was called correctly
            manager.slack_service.send_initial_thread_message.assert_called_once()
        finally:
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_session_start_notification_failure(self):
        """Test session start notification failure handling"""
        manager = await self.create_test_manager()
        try:
            session_id = "test_session_456"

            # Mock SlackService to return None (failure)
            manager.slack_service.send_initial_thread_message.return_value = None

            result = await manager.send_session_start_notification(session_id)

            assert result is False
            assert session_id not in manager._session_threads
        finally:
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_progress_notification_queuing(self, sample_visitor_info):
        """Test progress notification queuing"""
        manager = await self.create_test_manager()
        try:
            session_id = "test_session_789"
            stage = "collecting_info"

            # Start processor
            await manager.start_processor()

            # Send progress notification
            result = await manager.send_progress_notification(
                session_id, stage, sample_visitor_info, "追加情報"
            )

            assert result is True
        finally:
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_notification_processing_with_thread(self, sample_visitor_info):
        """Test notification processing when thread exists"""
        manager = await self.create_test_manager()
        try:
            session_id = "test_session_404"

            # Start processor and create session
            await manager.start_processor()
            await manager.send_session_start_notification(session_id)

            # Send progress notification
            await manager.send_progress_notification(
                session_id, "greeting", sample_visitor_info
            )

            # Give processor time to handle the notification
            await asyncio.sleep(0.1)

            # Verify thread message was called
            manager.slack_service.send_thread_message.assert_called()
        finally:
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_notification_processing_without_thread(self, sample_visitor_info):
        """Test notification processing when no thread exists (should be skipped)"""
        manager = await self.create_test_manager()
        try:
            session_id = "test_session_505"

            # Start processor but don't create session thread
            await manager.start_processor()

            # Send progress notification for non-existent session
            await manager.send_progress_notification(
                session_id, "greeting", sample_visitor_info
            )

            # Give processor time to handle the notification
            await asyncio.sleep(0.1)

            # Verify thread message was not called due to missing thread
            manager.slack_service.send_thread_message.assert_not_called()
        finally:
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self):
        """Test handling multiple concurrent sessions"""
        manager = await self.create_test_manager()
        try:
            session_ids = ["session_1", "session_2", "session_3"]

            # Start processor
            await manager.start_processor()

            # Create multiple sessions concurrently
            tasks = [
                manager.send_session_start_notification(session_id)
                for session_id in session_ids
            ]
            results = await asyncio.gather(*tasks)

            # All sessions should be created successfully
            assert all(results)

            # All sessions should have threads
            for session_id in session_ids:
                assert session_id in manager._session_threads
        finally:
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_session_thread_management(self):
        """Test session thread management methods"""
        manager = await self.create_test_manager()
        try:
            session_id = "test_session_thread_mgmt"

            # Initially no thread
            assert manager.get_session_thread(session_id) is None

            # Create session
            await manager.send_session_start_notification(session_id)

            # Should have thread now
            thread_ts = manager.get_session_thread(session_id)
            assert thread_ts is not None
            assert thread_ts == "test_thread_123"

            # Clear thread
            manager.clear_session_thread(session_id)
            assert manager.get_session_thread(session_id) is None
        finally:
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_functionality(self):
        """Test cleanup functionality"""
        manager = await self.create_test_manager()
        session_id = "test_session_cleanup"

        # Start processor and create session
        await manager.start_processor()
        await manager.send_session_start_notification(session_id)

        # Verify initial state
        assert not manager._queue_processor_task.done()
        assert session_id in manager._session_threads

        # Cleanup
        await manager.cleanup()

        # Verify cleanup
        assert manager._queue_processor_task.done()
        assert len(manager._session_threads) == 0
        assert len(manager._running_tasks) == 0

    @pytest.mark.asyncio
    async def test_error_handling_in_notification_processing(self):
        """Test error handling in notification processing"""
        manager = await self.create_test_manager()
        try:
            session_id = "test_session_error"

            # Start processor and create session
            await manager.start_processor()
            await manager.send_session_start_notification(session_id)

            # Mock SlackService to raise an exception
            manager.slack_service.send_thread_message.side_effect = Exception("Test error")

            # Send notification - should not crash the processor
            await manager.send_progress_notification(session_id, "greeting")

            # Give processor time to handle the notification and error
            await asyncio.sleep(0.1)

            # Processor should still be running despite the error
            assert not manager._queue_processor_task.done()
        finally:
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_visitor_info_notification_queuing(self, sample_visitor_info, sample_conversation_logs):
        """Test visitor info notification queuing"""
        manager = await self.create_test_manager()
        try:
            session_id = "test_session_101"

            # Start processor
            await manager.start_processor()

            result = await manager.send_visitor_info_notification(
                session_id, sample_visitor_info, sample_conversation_logs
            )

            assert result is True
        finally:
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_completion_notification_queuing(self, sample_visitor_info, sample_conversation_logs):
        """Test completion notification queuing"""
        manager = await self.create_test_manager()
        try:
            session_id = "test_session_202"
            calendar_result = {"found": True, "roomName": "会議室A"}

            # Start processor
            await manager.start_processor()

            result = await manager.send_completion_notification(
                session_id, sample_visitor_info, sample_conversation_logs, calendar_result
            )

            assert result is True
        finally:
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_error_notification_queuing(self, sample_visitor_info):
        """Test error notification queuing"""
        manager = await self.create_test_manager()
        try:
            session_id = "test_session_303"
            error_message = "テストエラーメッセージ"

            # Start processor
            await manager.start_processor()

            result = await manager.send_error_notification(
                session_id, error_message, sample_visitor_info
            )

            assert result is True
        finally:
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_completion_notification_with_calendar_result(self, sample_visitor_info, sample_conversation_logs):
        """Test completion notification with calendar result"""
        manager = await self.create_test_manager()
        try:
            session_id = "test_session_completion"
            calendar_result = {"found": True, "roomName": "会議室A"}

            # Start processor and create session
            await manager.start_processor()
            await manager.send_session_start_notification(session_id)

            # Send completion notification
            await manager.send_completion_notification(
                session_id, sample_visitor_info, sample_conversation_logs, calendar_result
            )

            # Give processor time to handle notification
            await asyncio.sleep(0.1)

            # Verify visitor notification was called with thread_ts
            manager.slack_service.send_visitor_notification.assert_called()
            call_args = manager.slack_service.send_visitor_notification.call_args
            assert call_args[1]['thread_ts'] == "test_thread_123"
        finally:
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_non_blocking_behavior(self, sample_visitor_info):
        """Test that notifications don't block the caller"""
        manager = await self.create_test_manager()
        try:
            session_id = "test_session_nonblocking"

            # Start processor and create session
            await manager.start_processor()
            await manager.send_session_start_notification(session_id)

            # Mock SlackService to have a delay
            async def slow_send_thread_message(*args, **kwargs):
                await asyncio.sleep(0.1)
                return True

            manager.slack_service.send_thread_message.side_effect = slow_send_thread_message

            # Send multiple notifications and measure time
            import time
            start_time = time.time()

            # Send 5 notifications
            for i in range(5):
                await manager.send_progress_notification(
                    session_id, f"stage_{i}"
                )

            end_time = time.time()

            # Should complete quickly (much faster than 5 * 0.1 = 0.5 seconds)
            # because notifications are queued, not processed synchronously
            assert end_time - start_time < 0.1
        finally:
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_queue_overflow_handling(self):
        """Test behavior under high notification load"""
        manager = await self.create_test_manager()
        try:
            session_id = "test_session_overflow"

            # Start processor and create session
            await manager.start_processor()
            await manager.send_session_start_notification(session_id)

            # Send many notifications rapidly
            tasks = []
            for i in range(50):  # Reduced from 100 for faster test
                task = manager.send_progress_notification(
                    session_id, f"stage_{i}", additional_info=f"Message {i}"
                )
                tasks.append(task)

            # All notifications should be queued successfully
            results = await asyncio.gather(*tasks)
            assert all(results)
        finally:
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_notification_exception_handling(self):
        """Test notification queuing exception handling"""
        manager = await self.create_test_manager()
        try:
            session_id = "test_session_exception"

            # Test exception in progress notification
            with patch.object(manager._notification_queue, 'put', side_effect=Exception("Queue error")):
                result = await manager.send_progress_notification(session_id, "greeting")
                assert result is False

            # Test exception in visitor info notification
            with patch.object(manager._notification_queue, 'put', side_effect=Exception("Queue error")):
                result = await manager.send_visitor_info_notification(session_id, {})
                assert result is False
        finally:
            await manager.cleanup()
