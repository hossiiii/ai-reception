"""Simplified tests for BackgroundTaskManager"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.visitor import ConversationLog, VisitorInfo
from app.services.background_tasks import BackgroundTaskManager


class TestBackgroundTaskManagerSimple:
    """Simplified test cases for BackgroundTaskManager"""

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
        """Create BackgroundTaskManager instance for testing"""
        manager = BackgroundTaskManager()

        # Mock the SlackService to prevent actual API calls
        manager.slack_service = MagicMock()
        manager.slack_service.send_visitor_notification = AsyncMock(return_value=True)
        manager.slack_service.send_simple_message = AsyncMock(return_value=True)
        manager.slack_service.send_error_notification = AsyncMock(return_value=True)

        return manager

    @pytest.mark.asyncio
    async def test_send_slack_notification_async_success(self, sample_visitor_info, sample_conversation_logs):
        """Test successful async Slack notification"""
        task_manager = await self.create_test_manager()
        try:
            calendar_result = {"found": True, "roomName": "会議室A"}
            thread_ts = "1692096600.0"

            # Send notification asynchronously
            await task_manager.send_slack_notification_async(
                sample_visitor_info,
                sample_conversation_logs,
                calendar_result,
                thread_ts
            )

            # Give the background task time to complete
            await asyncio.sleep(0.2)

            # Verify SlackService was called
            task_manager.slack_service.send_visitor_notification.assert_called_once_with(
                sample_visitor_info,
                sample_conversation_logs,
                calendar_result,
                thread_ts
            )
        finally:
            await task_manager.cleanup()

    @pytest.mark.asyncio
    async def test_send_progress_notification_async_success(self, sample_visitor_info):
        """Test successful async progress notification"""
        task_manager = await self.create_test_manager()
        try:
            session_id = "test_session_123"
            stage = "collecting_info"
            additional_info = "追加情報"
            thread_ts = "1692096600.0"

            await task_manager.send_progress_notification_async(
                session_id, stage, sample_visitor_info, additional_info, thread_ts
            )

            # Give the background task time to complete
            await asyncio.sleep(0.2)

            # Verify SlackService was called
            task_manager.slack_service.send_simple_message.assert_called_once()
            call_args = task_manager.slack_service.send_simple_message.call_args

            message = call_args[0][0]
            passed_thread_ts = call_args[0][1]

            assert "📝 来客者情報を収集中" in message
            assert "テスト太郎様" in message
            assert "追加情報" in message
            assert session_id in message
            assert passed_thread_ts == thread_ts
        finally:
            await task_manager.cleanup()

    @pytest.mark.asyncio
    async def test_send_slack_notification_async_retry_mechanism(self, sample_visitor_info, sample_conversation_logs):
        """Test retry mechanism in async Slack notification"""
        task_manager = await self.create_test_manager()
        try:
            # Mock SlackService to fail twice, then succeed
            task_manager.slack_service.send_visitor_notification.side_effect = [
                False,  # First attempt fails
                False,  # Second attempt fails
                True    # Third attempt succeeds
            ]

            await task_manager.send_slack_notification_async(
                sample_visitor_info,
                sample_conversation_logs
            )

            # Give time for retries (with exponential backoff)
            await asyncio.sleep(4.0)

            # Should have been called 3 times
            assert task_manager.slack_service.send_visitor_notification.call_count == 3
        finally:
            await task_manager.cleanup()

    @pytest.mark.asyncio
    async def test_schedule_task_functionality(self):
        """Test generic task scheduling functionality"""
        task_manager = await self.create_test_manager()
        try:
            # Create a simple async coroutine for testing
            async def test_coro():
                await asyncio.sleep(0.1)
                return "completed"

            # Schedule the task
            task = task_manager.schedule_task(test_coro())

            # Task should be tracked
            assert task in task_manager._running_tasks

            # Wait for completion
            result = await task
            assert result == "completed"

            # Task should be removed from tracking after completion
            await asyncio.sleep(0.1)
            assert task not in task_manager._running_tasks
        finally:
            await task_manager.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_functionality(self):
        """Test cleanup functionality"""
        task_manager = await self.create_test_manager()

        # Create some tasks
        async def long_task():
            await asyncio.sleep(0.5)
            return "completed"

        # Schedule tasks
        for _ in range(3):
            task_manager.schedule_task(long_task())

        # Verify tasks are running
        assert len(task_manager._running_tasks) == 3

        # Cleanup should wait for all tasks to complete
        await task_manager.cleanup()

        # All tasks should be cleaned up
        assert len(task_manager._running_tasks) == 0

    @pytest.mark.asyncio
    async def test_stage_message_mapping(self):
        """Test progress notification stage message mapping"""
        task_manager = await self.create_test_manager()
        try:
            session_id = "test_session_stages"

            test_stages = [
                ("greeting", "👋 来客者への挨拶を開始"),
                ("collecting_info", "📝 来客者情報を収集中"),
                ("completing", "🏁 対応を完了"),
            ]

            for stage, expected_message in test_stages:
                # Reset mock for each test
                task_manager.slack_service.send_simple_message.reset_mock()

                await task_manager.send_progress_notification_async(session_id, stage)
                await asyncio.sleep(0.1)

                # Verify correct message was sent
                call_args = task_manager.slack_service.send_simple_message.call_args
                message = call_args[0][0]
                assert expected_message in message
        finally:
            await task_manager.cleanup()

    @pytest.mark.asyncio
    async def test_error_notification_fallback(self, sample_visitor_info, sample_conversation_logs):
        """Test error notification fallback when all retries fail"""
        task_manager = await self.create_test_manager()
        try:
            # Mock SlackService to always fail notifications
            task_manager.slack_service.send_visitor_notification.return_value = False

            await task_manager.send_slack_notification_async(
                sample_visitor_info,
                sample_conversation_logs
            )

            # Give time for all retries and error notification
            await asyncio.sleep(8.0)

            # Should have attempted error notification
            task_manager.slack_service.send_error_notification.assert_called_once()
        finally:
            await task_manager.cleanup()
