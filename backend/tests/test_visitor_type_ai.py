"""Test AI visitor type determination with various scenarios"""
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.nodes import ReceptionNodes
from app.models.conversation import ConversationState
from app.models.visitor import VisitorInfo


@pytest.fixture
def reception_nodes():
    """Create ReceptionNodes instance for testing"""
    return ReceptionNodes()


class TestAIVisitorTypeDetermination:
    """Test AI-based visitor type determination"""

    @pytest.mark.asyncio
    async def test_delivery_type_detection(self, reception_nodes):
        """Test that delivery visitors are correctly classified"""
        test_cases = [
            ("配達で来ました", "ヤマト運輸", "delivery"),
            ("お荷物をお届けに参りました", "佐川急便", "delivery"),
            ("宅配便です", "日本郵便", "delivery"),
            ("荷物の配送です", "アマゾン", "delivery"),
            ("お届け物があります", "配送会社", "delivery"),
        ]

        for purpose, company, expected_type in test_cases:
            visitor_info = {
                "name": "配達員",
                "company": company,
                "purpose": purpose
            }

            # Test AI determination
            result = await reception_nodes._ai_determine_visitor_type(purpose, visitor_info)
            print(f"Purpose: '{purpose}', Company: '{company}' -> Type: {result} (expected: {expected_type})")
            assert result == expected_type, f"Failed for purpose: {purpose}, company: {company}"

    @pytest.mark.asyncio
    async def test_sales_type_detection(self, reception_nodes):
        """Test that sales visitors are correctly classified"""
        test_cases = [
            ("営業で伺いました", "営業会社", "sales"),
            ("新サービスのご紹介に", "IT企業", "sales"),
            ("商品のご案内で", "商社", "sales"),
            ("ご提案に伺いました", "コンサル会社", "sales"),
            ("セールスで来ました", "販売会社", "sales"),
        ]

        for purpose, company, expected_type in test_cases:
            visitor_info = {
                "name": "営業担当",
                "company": company,
                "purpose": purpose
            }

            # Test AI determination
            result = await reception_nodes._ai_determine_visitor_type(purpose, visitor_info)
            print(f"Purpose: '{purpose}', Company: '{company}' -> Type: {result} (expected: {expected_type})")
            assert result == expected_type, f"Failed for purpose: {purpose}, company: {company}"

    @pytest.mark.asyncio
    async def test_appointment_type_detection(self, reception_nodes):
        """Test that appointment visitors are correctly classified"""
        test_cases = [
            ("会議で来ました", "株式会社テスト", "appointment"),
            ("打ち合わせです", "取引先", "appointment"),
            ("お約束をいただいて", "パートナー企業", "appointment"),
            ("ミーティングで", "顧客企業", "appointment"),
            ("面談のため", "採用候補者", "appointment"),
        ]

        for purpose, company, expected_type in test_cases:
            visitor_info = {
                "name": "訪問者",
                "company": company,
                "purpose": purpose
            }

            # Test AI determination
            result = await reception_nodes._ai_determine_visitor_type(purpose, visitor_info)
            print(f"Purpose: '{purpose}', Company: '{company}' -> Type: {result} (expected: {expected_type})")
            assert result == expected_type, f"Failed for purpose: {purpose}, company: {company}"

    @pytest.mark.asyncio
    async def test_ambiguous_expression_detection(self, reception_nodes):
        """Test AI handling of ambiguous expressions"""
        test_cases = [
            ("ちょっとご挨拶に", "新規企業", "sales"),  # Likely sales
            ("お届け物です", "不明", "delivery"),  # Likely delivery
            ("約束の件で", "取引先", "appointment"),  # Likely appointment
        ]

        for purpose, company, expected_type in test_cases:
            visitor_info = {
                "name": "訪問者",
                "company": company,
                "purpose": purpose
            }

            # Test AI determination
            result = await reception_nodes._ai_determine_visitor_type(purpose, visitor_info)
            print(f"Ambiguous: '{purpose}', Company: '{company}' -> Type: {result} (expected: {expected_type})")
            # For ambiguous cases, we check if the result is reasonable
            assert result in ["appointment", "sales", "delivery"], f"Invalid type: {result}"

    @pytest.mark.asyncio
    async def test_confirm_info_node_with_delivery(self, reception_nodes):
        """Test full confirm_info_node flow with delivery visitor"""
        visitor_info: VisitorInfo = {
            "name": "配達員",
            "company": "ヤマト運輸",
            "purpose": "お荷物をお届けに参りました",
            "visitor_type": None,
            "confirmed": True,  # Already confirmed
            "correction_count": 0
        }

        # Mock the Slack service to prevent actual notifications
        mock_slack = AsyncMock()
        mock_slack.send_visitor_notification = AsyncMock(return_value=None)
        reception_nodes.slack_service = mock_slack

        # Include AI message before human response for proper context
        ai_confirm_msg = AIMessage(content="以下の情報で間違いございませんでしょうか？\n\n・会社名：ヤマト運輸\n・お名前：配達員\n・訪問目的：お荷物をお届けに参りました")
        human_response = HumanMessage(content="はい、正しいです")

        state: ConversationState = {
            "messages": [ai_confirm_msg, human_response],
            "visitor_info": visitor_info,
            "current_step": "confirmation_response",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-delivery"
        }

        # Execute confirm_info_node
        result = await reception_nodes.confirm_info_node(state)

        # Check that delivery type was correctly determined
        assert result["visitor_info"]["visitor_type"] == "delivery"

        # Check that it went to guidance without calendar check
        # (The node auto-executes guidance for delivery)
        assert result["current_step"] == "complete"

        # Verify Slack was called (auto-executed)
        mock_slack.send_visitor_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_info_node_with_sales(self, reception_nodes):
        """Test full confirm_info_node flow with sales visitor"""
        visitor_info: VisitorInfo = {
            "name": "営業担当",
            "company": "IT企業",
            "purpose": "新サービスのご紹介",
            "visitor_type": None,
            "confirmed": False,
            "correction_count": 0
        }

        # Mock the Slack service
        mock_slack = AsyncMock()
        mock_slack.send_visitor_notification = AsyncMock(return_value=None)
        reception_nodes.slack_service = mock_slack

        state: ConversationState = {
            "messages": [HumanMessage(content="はい、正しいです")],
            "visitor_info": visitor_info,
            "current_step": "confirmation_response",
            "calendar_result": None,
            "error_count": 0,
            "session_id": "test-sales"
        }

        # Execute confirm_info_node
        result = await reception_nodes.confirm_info_node(state)

        # Check that sales type was correctly determined
        assert result["visitor_info"]["visitor_type"] == "sales"

        # Check that it went to guidance without calendar check
        assert result["current_step"] == "complete"

        # Verify Slack was called
        mock_slack.send_visitor_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_pattern_matching(self, reception_nodes):
        """Test fallback pattern matching when AI fails"""
        # Test the fallback function directly
        test_cases = [
            ("配達です", "delivery"),
            ("営業で来ました", "sales"),
            ("会議があります", "appointment"),
            ("不明な目的", "appointment"),  # Default
        ]

        for purpose, expected_type in test_cases:
            result = reception_nodes._fallback_visitor_type_detection(purpose)
            assert result == expected_type, f"Fallback failed for: {purpose}"
