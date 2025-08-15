# Slack Integration Migration Guide

## Overview

This document provides a comprehensive guide for migrating from Slack webhook-based integration to the new Web API-only implementation.

## What Changed

### Before (Webhook + Web API)
- **Primary**: Slack webhook URL for message delivery
- **Secondary**: Optional Slack bot token for threading support
- **Configuration**: `SLACK_WEBHOOK_URL` (required) + `SLACK_BOT_TOKEN` (optional)
- **Issues**: Unreliable threading, webhook limitations, complex fallback logic

### After (Web API Only)
- **Primary**: Slack Web API with bot token for all functionality
- **Configuration**: `SLACK_BOT_TOKEN` (required) + `SLACK_CHANNEL` (required)
- **Benefits**: Reliable threading, comprehensive error handling, simplified architecture

## Migration Steps

### 1. Update Environment Variables

#### Remove (no longer supported):
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

#### Add/Update (required):
```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_CHANNEL=#your-channel-name
```

### 2. Slack App Configuration

#### If you don't have a Slack app yet:

1. **Create a new Slack app**:
   - Go to https://api.slack.com/apps
   - Click "Create New App" → "From scratch"
   - Name your app (e.g., "AI Reception System")
   - Select your workspace

2. **Configure OAuth & Permissions**:
   - Go to "OAuth & Permissions" in the sidebar
   - Under "Scopes" → "Bot Token Scopes", add:
     - `chat:write` - Send messages to channels
     - `chat:write.public` - Send messages to channels without joining

3. **Install the app**:
   - Click "Install to Workspace"
   - Authorize the app
   - Copy the "Bot User OAuth Token" (starts with `xoxb-`)

#### If you already have a Slack app:

1. **Update permissions** (if needed):
   - Go to "OAuth & Permissions"
   - Ensure you have `chat:write` and `chat:write.public` scopes
   - Reinstall if you added new scopes

2. **Get your bot token**:
   - Copy the "Bot User OAuth Token" from OAuth & Permissions page

### 3. Channel Setup

1. **Invite the bot to your channel**:
   ```
   /invite @your-bot-name
   ```

2. **Verify channel name**:
   - Use the exact channel name (including #) in `SLACK_CHANNEL`
   - Examples: `#general`, `#ai-reception`, `#notifications`

### 4. Update Configuration Files

#### .env file:
```bash
# Remove this line:
# SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

# Add/update these lines:
SLACK_BOT_TOKEN=xoxb-your-actual-bot-token-here
SLACK_CHANNEL=#your-channel-name
```

#### docker-compose.yml (if using Docker):
```yaml
environment:
  # Remove this line:
  # - SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
  
  # Add/update these lines:
  - SLACK_BOT_TOKEN=xoxb-your-actual-bot-token-here
  - SLACK_CHANNEL=#your-channel-name
```

### 5. Test the Migration

Use the provided demo script to test your configuration:

```bash
cd backend
python slack_threading_demo.py
```

The script will:
- Validate your configuration
- Test basic connectivity
- Demonstrate threading functionality
- Show error handling

## Configuration Validation

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SLACK_BOT_TOKEN` | Bot User OAuth Token from Slack app | `xoxb-YOUR-BOT-TOKEN-HERE` |
| `SLACK_CHANNEL` | Target channel for notifications | `#ai-reception` |

### Validation Checklist

- [ ] `SLACK_BOT_TOKEN` starts with `xoxb-`
- [ ] `SLACK_CHANNEL` starts with `#`
- [ ] Bot is installed in your workspace
- [ ] Bot has `chat:write` and `chat:write.public` permissions
- [ ] Bot is invited to the target channel
- [ ] Test script runs successfully

## Error Handling

### Common Errors and Solutions

#### `invalid_auth`
**Problem**: Invalid bot token
**Solution**: 
- Verify `SLACK_BOT_TOKEN` is correct
- Ensure token starts with `xoxb-`
- Regenerate token if necessary

#### `channel_not_found`
**Problem**: Channel doesn't exist or bot can't see it
**Solution**:
- Verify channel name is correct (include #)
- Ensure channel exists
- Check if it's a private channel the bot can't access

#### `not_in_channel`
**Problem**: Bot is not a member of the channel
**Solution**:
- Invite bot to channel: `/invite @your-bot-name`
- Or use a public channel with `chat:write.public` permission

#### `missing_scope`
**Problem**: Bot lacks required permissions
**Solution**:
- Add `chat:write` scope in Slack app settings
- Reinstall the app to workspace
- Update bot token if needed

## Benefits of the New Implementation

### Reliability
- **Consistent threading**: All messages properly threaded
- **Better error handling**: Specific error messages and retry logic
- **No webhook limitations**: No dependency on webhook infrastructure

### Features
- **Rich formatting**: Full support for Slack blocks and attachments
- **Thread management**: Proper conversation threading per session
- **Error diagnostics**: Detailed error reporting and troubleshooting

### Maintenance
- **Simplified architecture**: Single API endpoint instead of webhook + API
- **Better monitoring**: Comprehensive logging and error tracking
- **Easier debugging**: Direct API responses instead of webhook callbacks

## Troubleshooting

### Configuration Issues

1. **Run the demo script**:
   ```bash
   python slack_threading_demo.py
   ```

2. **Check environment variables**:
   ```bash
   echo $SLACK_BOT_TOKEN
   echo $SLACK_CHANNEL
   ```

3. **Verify Slack app permissions**:
   - Go to your Slack app settings
   - Check OAuth & Permissions → Scopes
   - Ensure `chat:write` is present

### Testing Connectivity

Use the validation function in the demo script:
```python
from app.services.slack_service import SlackService
import asyncio

async def test():
    service = SlackService()
    response = await service._send_web_api_message({
        "channel": service.channel,
        "text": "Test message"
    })
    print(f"Response: {response}")

asyncio.run(test())
```

### Logs and Debugging

The system provides detailed logging for debugging:
- Configuration validation errors
- API call failures with specific error codes
- Retry attempts and backoff timing
- Thread management status

## Rollback Plan

If you need to rollback (not recommended):

1. **Restore webhook configuration**:
   ```bash
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
   SLACK_BOT_TOKEN=  # Can be empty
   ```

2. **Checkout previous version**:
   ```bash
   git checkout <previous-commit-hash>
   ```

**Note**: Webhook support has been completely removed in the new version. Rollback requires using an older version of the codebase.

## Support

### Getting Help

1. **Check the demo script output** for configuration validation
2. **Review Slack app settings** for permission issues
3. **Consult Slack API documentation**: https://api.slack.com/web
4. **Check application logs** for detailed error messages

### Common Resources

- [Slack API Documentation](https://api.slack.com/web)
- [Bot Token Guide](https://api.slack.com/authentication/token-types#bot)
- [OAuth Scopes Reference](https://api.slack.com/scopes)
- [Channel Management](https://api.slack.com/messaging/managing)

## Conclusion

The migration to Web API-only implementation provides a more reliable, maintainable, and feature-rich Slack integration. While it requires updating your configuration, the benefits significantly outweigh the migration effort.

Follow this guide step-by-step, use the provided demo script for validation, and refer to the troubleshooting section if you encounter any issues.