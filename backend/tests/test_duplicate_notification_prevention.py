"""Tests for duplicate Slack notification prevention"""

from unittest.mock import AsyncMock

import pytest

from app.services.async_notification_manager import AsyncNotificationManager


@pytest.fixture
def notification_manager():
    """Create a fresh notification manager instance for each test"""
    manager = AsyncNotificationManager()

    # Mock the slack service to avoid actual API calls
    manager.slack_service = AsyncMock()
    manager.slack_service.send_initial_thread_message = AsyncMock(return_value="test_thread_123")
    manager.slack_service.send_thread_message = AsyncMock(return_value=True)

    return manager


@pytest.mark.asyncio
async def test_duplicate_session_start_prevention(notification_manager):
    """Test that duplicate session start notifications are prevented"""
    session_id = "test_session_duplicate"

    # First call should succeed and create thread
    result1 = await notification_manager.send_session_start_notification(session_id, "First call")
    assert result1 is True
    assert notification_manager.is_session_started(session_id) is True
    assert notification_manager.get_session_thread(session_id) == "test_thread_123"

    # Verify slack service was called once
    notification_manager.slack_service.send_initial_thread_message.assert_called_once()

    # Second call should be skipped (returning True but not calling slack service again)
    result2 = await notification_manager.send_session_start_notification(session_id, "Second call")
    assert result2 is True
    assert notification_manager.is_session_started(session_id) is True
    assert notification_manager.get_session_thread(session_id) == "test_thread_123"

    # Verify slack service was still called only once (no additional calls)
    notification_manager.slack_service.send_initial_thread_message.assert_called_once()


@pytest.mark.asyncio
async def test_session_start_after_clear(notification_manager):
    """Test that session start works again after clearing session"""
    session_id = "test_session_clear"

    # First call
    result1 = await notification_manager.send_session_start_notification(session_id, "First call")
    assert result1 is True
    assert notification_manager.is_session_started(session_id) is True

    # Clear session
    notification_manager.clear_session_thread(session_id)
    assert notification_manager.is_session_started(session_id) is False
    assert notification_manager.get_session_thread(session_id) is None

    # Should be able to send notification again
    result2 = await notification_manager.send_session_start_notification(session_id, "After clear")
    assert result2 is True
    assert notification_manager.is_session_started(session_id) is True

    # Verify slack service was called twice (once for each start)
    assert notification_manager.slack_service.send_initial_thread_message.call_count == 2


@pytest.mark.asyncio
async def test_multiple_sessions_independent(notification_manager):
    """Test that different sessions work independently"""
    session1 = "test_session_1"
    session2 = "test_session_2"

    # Start both sessions
    result1 = await notification_manager.send_session_start_notification(session1, "Session 1")
    result2 = await notification_manager.send_session_start_notification(session2, "Session 2")

    assert result1 is True
    assert result2 is True
    assert notification_manager.is_session_started(session1) is True
    assert notification_manager.is_session_started(session2) is True

    # Try to start session1 again - should be prevented
    result3 = await notification_manager.send_session_start_notification(session1, "Session 1 again")
    assert result3 is True  # Returns True but doesn't send

    # Session2 should be unaffected
    assert notification_manager.is_session_started(session2) is True

    # Should have been called exactly twice (once per unique session)
    assert notification_manager.slack_service.send_initial_thread_message.call_count == 2


@pytest.mark.asyncio
async def test_cleanup_clears_all_sessions(notification_manager):
    """Test that cleanup clears all session tracking"""
    session1 = "test_session_cleanup_1"
    session2 = "test_session_cleanup_2"

    # Start both sessions
    await notification_manager.send_session_start_notification(session1, "Session 1")
    await notification_manager.send_session_start_notification(session2, "Session 2")

    assert notification_manager.is_session_started(session1) is True
    assert notification_manager.is_session_started(session2) is True

    # Cleanup
    await notification_manager.cleanup()

    # Both sessions should be cleared
    assert notification_manager.is_session_started(session1) is False
    assert notification_manager.is_session_started(session2) is False
    assert notification_manager.get_session_thread(session1) is None
    assert notification_manager.get_session_thread(session2) is None


@pytest.mark.asyncio
async def test_session_start_failure_doesnt_mark_as_started(notification_manager):
    """Test that failed session starts don't mark session as started"""
    session_id = "test_session_fail"

    # Mock slack service to return None (failure)
    notification_manager.slack_service.send_initial_thread_message = AsyncMock(return_value=None)

    # Call should fail
    result = await notification_manager.send_session_start_notification(session_id, "Failed call")
    assert result is False
    assert notification_manager.is_session_started(session_id) is False
    assert notification_manager.get_session_thread(session_id) is None

    # Next call should try again (not be prevented)
    notification_manager.slack_service.send_initial_thread_message = AsyncMock(return_value="test_thread_456")
    result2 = await notification_manager.send_session_start_notification(session_id, "Retry call")
    assert result2 is True
    assert notification_manager.is_session_started(session_id) is True
    assert notification_manager.get_session_thread(session_id) == "test_thread_456"
