#!/usr/bin/env python3
"""
Slack Web API Demo Script

This script demonstrates the Slack notification system using Web API only.
The webhook functionality has been completely removed and replaced with
Slack Web API for reliable threading support.

Key features:
1. Web API-only implementation with proper threading
2. Comprehensive error handling for common Slack API issues
3. Retry mechanism with exponential backoff
4. Better configuration validation

Run this script to test the Slack notification system.
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.async_notification_manager import AsyncNotificationManager
from app.services.slack_service import SlackService


async def demo_web_api_functionality():
    """Demo with Web API functionality"""
    print("\n🚀 WEB API DEMO")
    print("=" * 50)

    slack_service = SlackService()
    print(f"Bot token configured: {bool(slack_service.bot_token)}")
    print(f"Channel: {slack_service.channel}")

    # Test initial thread message
    print("\n📝 Testing initial thread message...")
    thread_ts = await slack_service.send_initial_thread_message(
        "🔔 New visitor session started",
        "Session ID: demo_session_123\nTime: 2025-01-15 10:30:00"
    )

    print(f"Thread TS returned: {thread_ts}")

    if thread_ts:
        print(f"✅ Thread created successfully: {thread_ts}")

        # Test thread message
        print("\n📨 Testing thread message...")
        success = await slack_service.send_thread_message(
            "👤 Visitor: John Doe from ACME Corp",
            thread_ts
        )
        print(f"Thread message success: {success}")

        # Test another thread message
        print("\n📨 Testing another thread message...")
        success = await slack_service.send_thread_message(
            "🔄 Progress: Collecting visitor information",
            thread_ts
        )
        print(f"Thread message success: {success}")

    else:
        print("❌ Failed to send initial message")
        print("Check your SLACK_BOT_TOKEN and SLACK_CHANNEL configuration")


async def demo_visitor_notification():
    """Demo visitor notification with rich formatting"""
    print("\n👤 VISITOR NOTIFICATION DEMO")
    print("=" * 50)

    slack_service = SlackService()

    # Sample visitor info
    visitor_info = {
        "name": "田中太郎",
        "company": "株式会社サンプル",
        "purpose": "製品デモの打ち合わせ",
        "visitor_type": "appointment"
    }

    # Sample conversation logs
    conversation_logs = [
        {
            "speaker": "visitor",
            "message": "こんにちは、田中と申します。10時からの打ち合わせでお伺いしました。",
            "timestamp": "2025-01-15T10:00:00"
        },
        {
            "speaker": "ai",
            "message": "田中様、いらっしゃいませ。お約束のお時間ですね。確認いたします。",
            "timestamp": "2025-01-15T10:00:30"
        },
        {
            "speaker": "visitor",
            "message": "はい、株式会社サンプルの田中です。新製品のデモをお願いしたく。",
            "timestamp": "2025-01-15T10:01:00"
        }
    ]

    # Sample calendar result
    calendar_result = {
        "found": True,
        "roomName": "会議室A"
    }

    print("\n📬 Sending rich visitor notification...")
    success = await slack_service.send_visitor_notification(
        visitor_info,
        conversation_logs,
        calendar_result
    )
    print(f"Visitor notification success: {success}")


async def demo_async_notification_manager():
    """Demo with AsyncNotificationManager"""
    print("\n🔄 ASYNC NOTIFICATION MANAGER DEMO")
    print("=" * 50)

    manager = AsyncNotificationManager()
    await manager.start_processor()

    try:
        session_id = "demo_session_456"

        # Test session start
        print(f"\n📱 Starting session: {session_id}")
        success = await manager.send_session_start_notification(session_id)
        print(f"Session start success: {success}")

        if success:
            # Test progress notification
            print("\n📊 Sending progress notification...")
            await manager.send_progress_notification(
                session_id,
                "collecting_info",
                visitor_info={"name": "佐藤花子", "company": "テクノロジー株式会社"}
            )

            # Wait a bit for processing
            await asyncio.sleep(1)

            # Test visitor info notification
            print("\n👤 Sending visitor info notification...")
            await manager.send_visitor_info_notification(
                session_id,
                {
                    "name": "佐藤花子",
                    "company": "テクノロジー株式会社",
                    "purpose": "新サービスの提案",
                    "visitor_type": "sales"
                },
                [
                    {"speaker": "visitor", "message": "こんにちは、新サービスのご提案にお伺いしました"},
                    {"speaker": "ai", "message": "佐藤様、お忙しい中ありがとうございます。"}
                ]
            )

            # Wait for processing
            await asyncio.sleep(1)

            # Test completion notification
            print("\n✅ Sending completion notification...")
            await manager.send_completion_notification(
                session_id,
                {
                    "name": "佐藤花子",
                    "company": "テクノロジー株式会社",
                    "purpose": "新サービスの提案",
                    "visitor_type": "sales"
                },
                [
                    {"speaker": "visitor", "message": "ありがとうございました"},
                    {"speaker": "ai", "message": "またのお越しをお待ちしております"}
                ],
                {"found": False}
            )

            # Wait for processing
            await asyncio.sleep(2)

            print(f"\n📋 Session thread info: {manager.get_session_thread(session_id)}")

    finally:
        await manager.cleanup()


async def demo_error_handling():
    """Demo error handling scenarios"""
    print("\n🚨 ERROR HANDLING DEMO")
    print("=" * 50)

    slack_service = SlackService()

    print("\n📧 Testing error notification...")
    success = await slack_service.send_error_notification(
        "テストエラー: データベース接続に失敗しました",
        "error_demo_session",
        {"name": "テストユーザー", "company": "テスト会社"}
    )
    print(f"Error notification success: {success}")


def show_configuration_guide():
    """Show configuration guide for Web API setup"""
    print("\n⚙️ CONFIGURATION GUIDE")
    print("=" * 50)

    print("""
New Web API-only configuration:
├── SLACK_BOT_TOKEN=xoxb-your-bot-token-here    # Required
└── SLACK_CHANNEL=#your-channel                 # Required

Previous webhook configuration is no longer supported:
❌ SLACK_WEBHOOK_URL (removed)

Setup Instructions:
1. Create or update your Slack app: https://api.slack.com/apps
2. Required OAuth scopes:
   • chat:write - Send messages to channels
   • chat:write.public - Send messages to channels without joining
3. Install app to your workspace
4. Copy Bot User OAuth Token (starts with xoxb-)
5. Set environment variables:
   • SLACK_BOT_TOKEN=xoxb-your-token-here
   • SLACK_CHANNEL=#your-channel-name
6. Invite the bot to your channel: /invite @your-bot-name

Benefits of Web API-only approach:
✅ Reliable threading support
✅ Better error handling
✅ Consistent message delivery
✅ Proper channel management
✅ No webhook URL management needed
    """)


async def validate_configuration():
    """Validate the current configuration"""
    print("\n🔍 CONFIGURATION VALIDATION")
    print("=" * 50)

    try:
        slack_service = SlackService()

        print(f"Bot token present: {bool(slack_service.bot_token)}")
        print(f"Channel configured: {slack_service.channel}")

        if not slack_service.bot_token:
            print("❌ SLACK_BOT_TOKEN is not configured")
            return False

        if not slack_service.channel:
            print("❌ SLACK_CHANNEL is not configured")
            return False

        # Test a simple message
        print("\n🧪 Testing basic connectivity...")
        test_message = {
            "channel": slack_service.channel,
            "text": "🔧 Configuration test from AI Reception System"
        }

        response = await slack_service._send_web_api_message(test_message)

        if response and response.get("ok"):
            print("✅ Configuration is valid and working")
            return True
        else:
            error = response.get("error", "Unknown error") if response else "No response"
            print(f"❌ Configuration test failed: {error}")

            if error == "invalid_auth":
                print("   → Check your SLACK_BOT_TOKEN")
            elif error == "channel_not_found":
                print(f"   → Channel '{slack_service.channel}' not found")
            elif error == "not_in_channel":
                print(f"   → Bot is not in channel '{slack_service.channel}'. Invite the bot first.")

            return False

    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False


async def main():
    """Main demo function"""
    print("🤖 SLACK WEB API DEMONSTRATION")
    print("=" * 60)

    print("""
This demo shows the new Web API-only Slack integration:

✅ Reliable threading support
✅ Comprehensive error handling
✅ Better configuration management
✅ No webhook dependency
    """)

    # Show configuration guide
    show_configuration_guide()

    # Validate configuration
    config_valid = await validate_configuration()

    if config_valid:
        # Demo Web API functionality
        await demo_web_api_functionality()

        # Demo visitor notification
        await demo_visitor_notification()

        # Demo async notification manager
        await demo_async_notification_manager()

        # Demo error handling
        await demo_error_handling()

        print("\n✅ DEMO COMPLETED SUCCESSFULLY")
    else:
        print("\n❌ DEMO SKIPPED DUE TO CONFIGURATION ISSUES")

    print("=" * 60)
    print("""
Migration Summary:
✅ Webhook support removed completely
✅ Web API-only implementation
✅ Improved threading reliability
✅ Better error handling and diagnostics
✅ Simplified configuration

Next Steps:
1. Update your .env file with SLACK_BOT_TOKEN
2. Remove SLACK_WEBHOOK_URL from configuration
3. Ensure bot is invited to your Slack channel
4. Test the integration with this demo script
    """)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        print("Check your configuration and try again")
