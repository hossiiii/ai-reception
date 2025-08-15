"""End-to-end test simulating the duplicate notification issue and fix"""

from unittest.mock import patch

import pytest

from app.agents.reception_graph import ReceptionGraphManager
from app.services.async_notification_manager import async_notification_manager


@pytest.mark.asyncio
async def test_end_to_end_duplicate_prevention():
    """
    Test that simulates the exact scenario from the user report:
    Starting a conversation should result in only ONE session start notification,
    even if the greeting_node gets called multiple times during the flow.
    """

    # Clear any existing state
    async_notification_manager._session_started.clear()
    async_notification_manager._session_threads.clear()

    # Mock the slack service to track calls
    with patch.object(async_notification_manager.slack_service, 'send_initial_thread_message') as mock_initial:
        with patch.object(async_notification_manager.slack_service, 'send_thread_message') as mock_thread:
            mock_initial.return_value = "test_thread_duplicate_fix"
            mock_thread.return_value = True

            # Create graph manager
            graph_manager = ReceptionGraphManager()

            # Simulate the exact scenario: starting a conversation
            session_id = "92c15e02-c202-40e9-8347-cae4deb95834"  # Same as user report

            # First: Start conversation (this calls greeting_node)
            result = await graph_manager.start_conversation(session_id)

            # Verify conversation started successfully
            assert result["success"] is True
            assert result["session_id"] == session_id
            assert "いらっしゃいませ" in result["message"]

            # Verify only ONE session start notification was sent
            assert mock_initial.call_count == 1

            # Verify the notification content matches expected format
            call_args = mock_initial.call_args
            assert "来客者が到着し、挨拶を開始しました" in call_args[0][0]
            assert session_id in call_args[0][1]

            # Simulate potential additional calls to greeting_node that might happen
            # during graph processing or WebSocket handling
            from app.agents.nodes import ReceptionNodes
            from app.models.conversation import ConversationState

            nodes = ReceptionNodes()
            test_state = ConversationState(
                messages=[],
                visitor_info=None,
                current_step="greeting",
                calendar_result=None,
                error_count=0,
                session_id=session_id
            )

            # Call greeting_node multiple times (simulating the issue scenario)
            await nodes.greeting_node(test_state)
            await nodes.greeting_node(test_state)
            await nodes.greeting_node(test_state)

            # CRITICAL: Even after multiple calls, still only ONE session start notification
            assert mock_initial.call_count == 1

            # Verify session tracking state
            assert async_notification_manager.is_session_started(session_id) is True
            assert async_notification_manager.get_session_thread(session_id) == "test_thread_duplicate_fix"

            # Clean up
            async_notification_manager.clear_session_thread(session_id)


@pytest.mark.asyncio
async def test_timing_scenario_multiple_rapid_calls():
    """
    Test rapid successive calls (like the 1-second difference in user report)
    to ensure no race conditions or timing issues cause duplicates.
    """

    # Clear state
    async_notification_manager._session_started.clear()
    async_notification_manager._session_threads.clear()

    with patch.object(async_notification_manager.slack_service, 'send_initial_thread_message') as mock_initial:
        mock_initial.return_value = "test_thread_timing"

        import asyncio

        from app.agents.nodes import ReceptionNodes
        from app.models.conversation import ConversationState

        nodes = ReceptionNodes()
        session_id = "timing_test_session"

        state = ConversationState(
            messages=[],
            visitor_info=None,
            current_step="greeting",
            calendar_result=None,
            error_count=0,
            session_id=session_id
        )

        # Simulate rapid calls within 1 second (like the user reported timestamps)
        tasks = []
        for _i in range(5):  # Multiple rapid calls
            tasks.append(nodes.greeting_node(state))

        # Execute all calls concurrently
        results = await asyncio.gather(*tasks)

        # All calls should succeed
        for result in results:
            assert result["current_step"] == "collect_all_info"
            assert len(result["messages"]) == 1

        # But only ONE Slack notification should have been sent
        assert mock_initial.call_count == 1

        # Clean up
        async_notification_manager.clear_session_thread(session_id)


@pytest.mark.asyncio
async def test_user_reported_scenario_exact_reproduction():
    """
    Test that exactly reproduces the user's reported scenario with timestamps
    """

    # Clear state
    async_notification_manager._session_started.clear()
    async_notification_manager._session_threads.clear()

    # Track all calls to see what would have been sent
    sent_notifications = []

    def track_notification(title, details):
        # Extract timestamp-like info to simulate the user's scenario
        sent_notifications.append({
            "title": title,
            "details": details,
            "timestamp": len(sent_notifications) + 1  # Simulate seconds
        })
        return f"test_thread_{len(sent_notifications)}"

    with patch.object(async_notification_manager.slack_service, 'send_initial_thread_message', side_effect=track_notification):

        session_id = "92c15e02-c202-40e9-8347-cae4deb95834"  # Exact session from user report

        # Create graph manager and start conversation
        graph_manager = ReceptionGraphManager()

        # This would have previously caused the duplicate notifications
        await graph_manager.start_conversation(session_id)

        # Simulate any additional processing that might trigger greeting_node again
        from app.agents.nodes import ReceptionNodes
        from app.models.conversation import ConversationState

        nodes = ReceptionNodes()
        state = ConversationState(
            messages=[],
            visitor_info=None,
            current_step="greeting",
            calendar_result=None,
            error_count=0,
            session_id=session_id
        )

        # Additional calls that might happen in the WebSocket flow
        await nodes.greeting_node(state)

        # VERIFICATION: Only one notification should be sent
        assert len(sent_notifications) == 1

        # Verify the notification content matches what user saw
        notification = sent_notifications[0]
        assert "来客者が到着し、挨拶を開始しました" in notification["title"]
        assert session_id in notification["details"]
        assert "開始時刻:" in notification["details"]

        print(f"✅ Fix verified: Only {len(sent_notifications)} notification sent instead of 2")
        print(f"   Notification: {notification['title']}")
        print(f"   Session ID: {session_id}")

        # Clean up
        async_notification_manager.clear_session_thread(session_id)
