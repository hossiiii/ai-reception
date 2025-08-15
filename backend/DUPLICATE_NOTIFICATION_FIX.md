# Duplicate Slack Notification Fix

## Issue Description

Users were experiencing duplicate Slack notifications during the initial greeting phase:

```
🔔 来客者が到着し、挨拶を開始しました
セッションID: 92c15e02-c202-40e9-8347-cae4deb95834
開始時刻: 2025-08-16 05:13:33

🔔 来客者が到着し、挨拶を開始しました
セッションID: 92c15e02-c202-40e9-8347-cae4deb95834
開始時刻: 2025-08-16 05:13:34
```

## Root Cause Analysis

The issue was in the `greeting_node` function in `/backend/app/agents/nodes.py`. The `send_session_start_notification` was being called every time the `greeting_node` executed, without checking if a notification had already been sent for that session.

The `greeting_node` was being called multiple times during the conversation flow:
1. Initial call from `start_conversation()` 
2. Potential additional calls during graph state management
3. WebSocket processing flow

## Solution Implementation

### 1. Added Session State Tracking

Modified `AsyncNotificationManager` to track which sessions have already had their start notification sent:

```python
class AsyncNotificationManager:
    def __init__(self):
        # ... existing code ...
        self._session_started: set[str] = set()  # Track sessions with start notification sent
```

### 2. Duplicate Prevention Logic

Updated `send_session_start_notification` to check for duplicates:

```python
async def send_session_start_notification(self, session_id: str, initial_message: str = "...") -> bool:
    # Check if session start notification already sent
    if session_id in self._session_started:
        self.logger.info(f"🔄 Session start notification already sent for {session_id}, skipping duplicate")
        return True  # Return True since notification was already sent successfully
    
    # ... existing notification logic ...
    
    if thread_ts:
        self._session_threads[session_id] = thread_ts
        self._session_started.add(session_id)  # Mark session as started
        return True
```

### 3. Cleanup Methods Updated

Updated cleanup methods to clear session tracking:

```python
def clear_session_thread(self, session_id: str):
    if session_id in self._session_threads:
        del self._session_threads[session_id]
    if session_id in self._session_started:
        self._session_started.remove(session_id)
```

### 4. Added Helper Methods

```python
def is_session_started(self, session_id: str) -> bool:
    """Check if session start notification has been sent"""
    return session_id in self._session_started
```

## Files Modified

1. `/backend/app/services/async_notification_manager.py`
   - Added `_session_started` tracking set
   - Modified `send_session_start_notification` with duplicate prevention
   - Updated cleanup methods
   - Added `is_session_started` helper method

## Testing

### Unit Tests Created

1. `/backend/tests/test_duplicate_notification_prevention.py`
   - Tests for duplicate prevention logic
   - Tests for session independence
   - Tests for cleanup functionality
   - Tests for failure scenarios

2. `/backend/tests/test_greeting_duplicate_fix.py`
   - Integration tests with `greeting_node`
   - Tests for multiple calls to same session
   - Tests for different sessions

3. `/backend/tests/test_end_to_end_duplicate_fix.py`
   - End-to-end simulation of user scenario
   - Tests for timing and race conditions
   - Exact reproduction of reported issue

### Test Results

All tests pass, confirming:
- ✅ Duplicate notifications are prevented
- ✅ Different sessions work independently
- ✅ Session clearing allows notifications again
- ✅ No regressions in existing functionality
- ✅ Race conditions are handled correctly

## Verification

Manual testing confirmed the fix works:

```bash
# Before fix: Multiple calls would result in multiple Slack notifications
# After fix: Multiple calls result in only ONE Slack notification

Session ID: 92c15e02-c202-40e9-8347-cae4deb95834
Calling send_session_start_notification 3 times...
  Slack call #1: 🔔 来客者が到着し、挨拶を開始しました...
Results: True, True, True
Total Slack calls: 1
✅ SUCCESS: Duplicate notifications prevented!
```

## Impact

- **User Experience**: No more duplicate Slack notifications
- **System Performance**: Reduced unnecessary Slack API calls
- **Reliability**: Consistent behavior regardless of internal call patterns
- **Maintainability**: Clear session state tracking with proper cleanup

## Backward Compatibility

The fix is fully backward compatible:
- Existing APIs remain unchanged
- Return values are consistent
- No breaking changes to public interfaces
- All existing tests continue to pass

## Future Considerations

The session tracking approach can be extended for other notification types if needed, providing a pattern for preventing other types of duplicate notifications in the system.