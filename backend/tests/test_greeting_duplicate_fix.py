"""Integration test for greeting node duplicate notification fix"""

from unittest.mock import patch

import pytest

from app.agents.nodes import ReceptionNodes
from app.models.conversation import ConversationState
from app.services.async_notification_manager import async_notification_manager


@pytest.mark.asyncio
async def test_greeting_node_duplicate_prevention():
    """Test that greeting_node doesn't send duplicate session start notifications"""

    # Create a fresh notification manager state for this test
    async_notification_manager._session_started.clear()
    async_notification_manager._session_threads.clear()

    # Mock the slack service to avoid actual API calls
    with patch.object(async_notification_manager.slack_service, 'send_initial_thread_message') as mock_slack:
        mock_slack.return_value = "test_thread_123"

        # Create nodes instance
        nodes = ReceptionNodes()

        # Create initial state
        session_id = "test_session_greeting"
        initial_state = ConversationState(
            messages=[],
            visitor_info=None,
            current_step="greeting",
            calendar_result=None,
            error_count=0,
            session_id=session_id
        )

        # First call to greeting_node - should send notification
        result1 = await nodes.greeting_node(initial_state)

        # Verify the result contains proper greeting
        assert result1["current_step"] == "collect_all_info"
        assert len(result1["messages"]) == 1
        assert "いらっしゃいませ" in result1["messages"][0].content

        # Verify session was marked as started
        assert async_notification_manager.is_session_started(session_id) is True
        assert async_notification_manager.get_session_thread(session_id) == "test_thread_123"

        # Verify slack service was called once
        assert mock_slack.call_count == 1

        # Second call to greeting_node with same session - should NOT send duplicate notification
        result2 = await nodes.greeting_node(initial_state)

        # Verify the result is still proper
        assert result2["current_step"] == "collect_all_info"
        assert len(result2["messages"]) == 1

        # Verify session is still marked as started
        assert async_notification_manager.is_session_started(session_id) is True

        # Most importantly: verify slack service was still called only once (no duplicate)
        assert mock_slack.call_count == 1

        # Cleanup for next tests
        async_notification_manager.clear_session_thread(session_id)


@pytest.mark.asyncio
async def test_greeting_node_different_sessions():
    """Test that different sessions can send their own notifications"""

    # Create a fresh notification manager state for this test
    async_notification_manager._session_started.clear()
    async_notification_manager._session_threads.clear()

    # Mock the slack service
    with patch.object(async_notification_manager.slack_service, 'send_initial_thread_message') as mock_slack:
        mock_slack.return_value = "test_thread_456"

        nodes = ReceptionNodes()

        # Create states for two different sessions
        session1_id = "test_session_1"
        session2_id = "test_session_2"

        state1 = ConversationState(
            messages=[],
            visitor_info=None,
            current_step="greeting",
            calendar_result=None,
            error_count=0,
            session_id=session1_id
        )

        state2 = ConversationState(
            messages=[],
            visitor_info=None,
            current_step="greeting",
            calendar_result=None,
            error_count=0,
            session_id=session2_id
        )

        # Call greeting_node for first session
        await nodes.greeting_node(state1)
        assert async_notification_manager.is_session_started(session1_id) is True
        assert mock_slack.call_count == 1

        # Call greeting_node for second session - should work independently
        await nodes.greeting_node(state2)
        assert async_notification_manager.is_session_started(session2_id) is True
        assert mock_slack.call_count == 2  # Should be called for both sessions

        # Call greeting_node for first session again - should not send duplicate
        await nodes.greeting_node(state1)
        assert async_notification_manager.is_session_started(session1_id) is True
        assert mock_slack.call_count == 2  # Should still be 2 (no duplicate for session1)

        # Cleanup
        async_notification_manager.clear_session_thread(session1_id)
        async_notification_manager.clear_session_thread(session2_id)


@pytest.mark.asyncio
async def test_greeting_node_after_session_clear():
    """Test that greeting_node works again after session is cleared"""

    # Create a fresh notification manager state for this test
    async_notification_manager._session_started.clear()
    async_notification_manager._session_threads.clear()

    # Mock the slack service
    with patch.object(async_notification_manager.slack_service, 'send_initial_thread_message') as mock_slack:
        mock_slack.return_value = "test_thread_789"

        nodes = ReceptionNodes()
        session_id = "test_session_clear"

        state = ConversationState(
            messages=[],
            visitor_info=None,
            current_step="greeting",
            calendar_result=None,
            error_count=0,
            session_id=session_id
        )

        # First call
        await nodes.greeting_node(state)
        assert async_notification_manager.is_session_started(session_id) is True
        assert mock_slack.call_count == 1

        # Clear session
        async_notification_manager.clear_session_thread(session_id)
        assert async_notification_manager.is_session_started(session_id) is False

        # Call again - should work since session was cleared
        await nodes.greeting_node(state)
        assert async_notification_manager.is_session_started(session_id) is True
        assert mock_slack.call_count == 2  # Should be called again

        # Cleanup
        async_notification_manager.clear_session_thread(session_id)
