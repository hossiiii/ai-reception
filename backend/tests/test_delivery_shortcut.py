"""Test delivery shortcut flow with AI detection"""
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.nodes import ReceptionNodes
from app.models.conversation import ConversationState


@pytest.fixture
def reception_nodes():
    """Create ReceptionNodes instance for testing"""
    return ReceptionNodes()


class TestDeliveryShortcut:
    """Test delivery shortcut flow with AI detection"""

    @pytest.mark.asyncio
    async def test_ai_delivery_detection_positive_cases(self, reception_nodes):
        """Test AI correctly identifies delivery visitors"""
        test_cases = [
            ("ヤマトです", {"company": "ヤマト運輸", "purpose": ""}, True),
            ("佐川急便です", {"company": "佐川急便", "purpose": ""}, True),
            ("お荷物をお届けに参りました", {"company": "", "purpose": "配達"}, True),
            ("配達で来ました", {"company": "配送業者", "purpose": "配達"}, True),
            ("アマゾンの配送です", {"company": "Amazon", "purpose": "配送"}, True),
            ("宅配便です", {"company": "", "purpose": "宅配"}, True),
            ("日本郵便です、郵便物です", {"company": "日本郵便", "purpose": "郵便物配達"}, True),
        ]

        for input_text, extracted_info, expected in test_cases:
            result = await reception_nodes._ai_is_delivery_visitor(input_text, extracted_info)
            print(f"Input: '{input_text}' -> AI Detection: {result} (expected: {expected})")
            assert result == expected, f"Failed for input: {input_text}"

    @pytest.mark.asyncio
    async def test_ai_delivery_detection_negative_cases(self, reception_nodes):
        """Test AI correctly rejects non-delivery visitors"""
        test_cases = [
            ("営業で伺いました", {"company": "営業会社", "purpose": "営業"}, False),
            ("会議の件で来ました", {"company": "取引先", "purpose": "会議"}, False),
            ("新サービスのご提案で", {"company": "IT企業", "purpose": "提案"}, False),
            ("打ち合わせです", {"company": "", "purpose": "打ち合わせ"}, False),
            ("面接に来ました", {"company": "求職者", "purpose": "面接"}, False),
        ]

        for input_text, extracted_info, expected in test_cases:
            result = await reception_nodes._ai_is_delivery_visitor(input_text, extracted_info)
            print(f"Input: '{input_text}' -> AI Detection: {result} (expected: {expected})")
            assert result == expected, f"Failed for input: {input_text}"

    @pytest.mark.asyncio
    async def test_delivery_shortcut_full_flow_yamato(self, reception_nodes):
        """Test complete delivery shortcut flow for Yamato"""
        # Mock Slack service
        mock_slack = AsyncMock()
        mock_slack.send_visitor_notification = AsyncMock(return_value=None)
        reception_nodes.slack_service = mock_slack

        # Initial state after greeting
        state: ConversationState = {
            "messages": [HumanMessage(content="ヤマトです")],
            "visitor_info": {},
            "current_step": "collect_all_info",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-yamato"
        }

        # Execute collect_all_info_node (should trigger delivery shortcut)
        result = await reception_nodes.collect_all_info_node(state)

        # Verify delivery shortcut was triggered
        assert result["visitor_info"]["visitor_type"] == "delivery"
        assert result["visitor_info"]["confirmed"]
        assert result["current_step"] == "complete"

        # Verify company name is set appropriately
        assert "ヤマト" in result["visitor_info"]["company"] or result["visitor_info"]["company"] == "配送業者"

        # Verify Slack notification was sent
        mock_slack.send_visitor_notification.assert_called_once()

        # Check message content
        assert len(result["messages"]) > 0
        last_message = result["messages"][-1]
        assert isinstance(last_message, AIMessage)
        # Should contain delivery-related guidance
        message_content = last_message.content.lower()
        assert any(keyword in message_content for keyword in ["配達", "荷物", "お疲れ様", "ありがとう"])

    @pytest.mark.asyncio
    async def test_delivery_shortcut_full_flow_sagawa(self, reception_nodes):
        """Test complete delivery shortcut flow for Sagawa"""
        # Mock Slack service
        mock_slack = AsyncMock()
        mock_slack.send_visitor_notification = AsyncMock(return_value=None)
        reception_nodes.slack_service = mock_slack

        state: ConversationState = {
            "messages": [HumanMessage(content="佐川急便です、お荷物をお届けに参りました")],
            "visitor_info": {},
            "current_step": "collect_all_info",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-sagawa"
        }

        result = await reception_nodes.collect_all_info_node(state)

        # Verify delivery shortcut
        assert result["visitor_info"]["visitor_type"] == "delivery"
        assert result["current_step"] == "complete"

        # Verify Slack notification
        mock_slack.send_visitor_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_delivery_shortcut_amazon(self, reception_nodes):
        """Test delivery shortcut for Amazon delivery"""
        mock_slack = AsyncMock()
        mock_slack.send_visitor_notification = AsyncMock(return_value=None)
        reception_nodes.slack_service = mock_slack

        state: ConversationState = {
            "messages": [HumanMessage(content="Amazon delivery")],
            "visitor_info": {},
            "current_step": "collect_all_info",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-amazon"
        }

        result = await reception_nodes.collect_all_info_node(state)

        assert result["visitor_info"]["visitor_type"] == "delivery"
        assert result["current_step"] == "complete"
        mock_slack.send_visitor_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_delivery_goes_to_normal_flow(self, reception_nodes):
        """Test non-delivery visitors go through normal confirmation flow"""
        state: ConversationState = {
            "messages": [HumanMessage(content="山田太郎です、株式会社テストから会議で来ました")],
            "visitor_info": {},
            "current_step": "collect_all_info",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-normal"
        }

        result = await reception_nodes.collect_all_info_node(state)

        # Should go to normal confirmation flow, not shortcut
        assert result["current_step"] == "confirmation_response"
        assert result["visitor_info"].get("visitor_type") != "delivery"

        # Should generate confirmation message
        assert len(result["messages"]) > 0
        last_message = result["messages"][-1]
        assert isinstance(last_message, AIMessage)
        # Should ask for confirmation
        message_content = last_message.content
        assert any(keyword in message_content for keyword in ["確認", "間違い", "正しい"])

    @pytest.mark.asyncio
    async def test_ai_delivery_detection_error_handling(self, reception_nodes):
        """Test error handling in AI delivery detection"""
        # Mock TextService to raise an exception
        original_generate_output = reception_nodes.text_service.generate_output
        reception_nodes.text_service.generate_output = AsyncMock(side_effect=Exception("API Error"))

        try:
            result = await reception_nodes._ai_is_delivery_visitor("ヤマトです", {"company": "ヤマト運輸"})

            # Should return False on error (safe side)
            assert not result

        finally:
            # Restore original method
            reception_nodes.text_service.generate_output = original_generate_output

    @pytest.mark.asyncio
    async def test_delivery_shortcut_message_generation_fallback(self, reception_nodes):
        """Test fallback message when AI message generation fails"""
        # Mock Slack service
        mock_slack = AsyncMock()
        mock_slack.send_visitor_notification = AsyncMock(return_value=None)
        reception_nodes.slack_service = mock_slack

        # Mock TextService to fail for message generation but succeed for delivery detection
        original_generate_output = reception_nodes.text_service.generate_output

        async def mock_generate_output(task_type, context):
            if "配達業者の早期判定" in task_type:
                return "yes"
            elif "配達業者への直接案内" in task_type:
                raise Exception("Message generation failed")
            else:
                return await original_generate_output(task_type, context)

        reception_nodes.text_service.generate_output = AsyncMock(side_effect=mock_generate_output)

        try:
            state: ConversationState = {
                "messages": [HumanMessage(content="ヤマトです")],
                "visitor_info": {},
                "current_step": "collect_all_info",
                "calendar_result": None,
                "error_count": 0,
                "session_id": "test-fallback"
            }

            result = await reception_nodes.collect_all_info_node(state)

            # Should still work with fallback message
            assert result["visitor_info"]["visitor_type"] == "delivery"
            assert result["current_step"] == "complete"

            # Should have fallback delivery message
            assert len(result["messages"]) > 0
            last_message = result["messages"][-1]
            assert isinstance(last_message, AIMessage)
            message_content = last_message.content
            assert "配達" in message_content
            assert "ありがとう" in message_content

        finally:
            reception_nodes.text_service.generate_output = original_generate_output
