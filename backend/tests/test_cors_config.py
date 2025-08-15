"""
Tests for CORS configuration in different environments
"""
import os
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCORSConfiguration:
    """Test CORS settings in different environments"""

    def test_development_cors_allows_all_origins(self):
        """Test that development environment allows all origins"""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'ALLOWED_ORIGINS': '',
            'OPENAI_API_KEY': 'test-key',
            'GOOGLE_SERVICE_ACCOUNT_KEY': '{"test": "key"}',
            'MEETING_ROOM_CALENDAR_IDS': 'test@test.com',
            'SLACK_BOT_TOKEN': 'xoxb-test-token',
            'SLACK_CHANNEL': '#test'
        }):
            # Reload config and app to pick up new environment
            from app.config import Settings
            settings = Settings()

            # Test cors_origins property
            assert settings.cors_origins == ["*"]
            assert not settings.cors_allow_credentials
            assert settings.environment == "development"

    def test_production_cors_with_specific_origins(self):
        """Test that production environment uses specific origins"""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'ALLOWED_ORIGINS': 'https://app.example.com,https://www.example.com',
            'OPENAI_API_KEY': 'test-key',
            'GOOGLE_SERVICE_ACCOUNT_KEY': '{"test": "key"}',
            'MEETING_ROOM_CALENDAR_IDS': 'test@test.com',
            'SLACK_BOT_TOKEN': 'xoxb-test-token',
            'SLACK_CHANNEL': '#test'
        }):
            from app.config import Settings
            settings = Settings()

            # Test cors_origins property
            expected_origins = ['https://app.example.com', 'https://www.example.com']
            assert settings.cors_origins == expected_origins
            assert settings.cors_allow_credentials
            assert settings.environment == "production"

    def test_production_cors_with_empty_origins(self):
        """Test that production with empty origins returns empty list"""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'ALLOWED_ORIGINS': '',
            'OPENAI_API_KEY': 'test-key',
            'GOOGLE_SERVICE_ACCOUNT_KEY': '{"test": "key"}',
            'MEETING_ROOM_CALENDAR_IDS': 'test@test.com',
            'SLACK_BOT_TOKEN': 'xoxb-test-token',
            'SLACK_CHANNEL': '#test'
        }):
            from app.config import Settings
            settings = Settings()

            # Test cors_origins property
            assert settings.cors_origins == []
            assert settings.cors_allow_credentials

    def test_cors_origins_parsing_with_spaces(self):
        """Test that origins with spaces are properly parsed"""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'ALLOWED_ORIGINS': ' https://app.example.com , https://www.example.com , https://api.example.com ',
            'OPENAI_API_KEY': 'test-key',
            'GOOGLE_SERVICE_ACCOUNT_KEY': '{"test": "key"}',
            'MEETING_ROOM_CALENDAR_IDS': 'test@test.com',
            'SLACK_BOT_TOKEN': 'xoxb-test-token',
            'SLACK_CHANNEL': '#test'
        }):
            from app.config import Settings
            settings = Settings()

            # Test that spaces are trimmed
            expected_origins = [
                'https://app.example.com',
                'https://www.example.com',
                'https://api.example.com'
            ]
            assert settings.cors_origins == expected_origins

    @pytest.mark.asyncio
    async def test_cors_headers_in_development(self):
        """Test actual CORS headers in development mode"""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'ALLOWED_ORIGINS': '',
            'OPENAI_API_KEY': 'test-key',
            'GOOGLE_SERVICE_ACCOUNT_KEY': '{"test": "key"}',
            'MEETING_ROOM_CALENDAR_IDS': 'test@test.com',
            'SLACK_BOT_TOKEN': 'xoxb-test-token',
            'SLACK_CHANNEL': '#test',
            'DEBUG': 'true'
        }, clear=True):
            # Need to reimport to get fresh settings
            import importlib

            import app.config
            importlib.reload(app.config)
            import app.main
            importlib.reload(app.main)

            from app.main import app
            client = TestClient(app)

            # Test OPTIONS request (preflight)
            response = client.options(
                "/api/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET"
                }
            )

            # In development, should allow any origin
            assert response.status_code == 200
            assert response.headers.get("access-control-allow-origin") == "*"
            assert "GET" in response.headers.get("access-control-allow-methods", "")

    @pytest.mark.asyncio
    async def test_cors_headers_in_production(self):
        """Test actual CORS headers in production mode"""
        allowed_origin = "https://app.example.com"
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'ALLOWED_ORIGINS': f'{allowed_origin},https://www.example.com',
            'OPENAI_API_KEY': 'test-key',
            'GOOGLE_SERVICE_ACCOUNT_KEY': '{"test": "key"}',
            'MEETING_ROOM_CALENDAR_IDS': 'test@test.com',
            'SLACK_BOT_TOKEN': 'xoxb-test-token',
            'SLACK_CHANNEL': '#test',
            'DEBUG': 'false'
        }, clear=True):
            # Need to reimport to get fresh settings
            import importlib

            import app.config
            importlib.reload(app.config)
            import app.main
            importlib.reload(app.main)

            from app.main import app
            client = TestClient(app)

            # Test OPTIONS request with allowed origin
            response = client.options(
                "/api/health",
                headers={
                    "Origin": allowed_origin,
                    "Access-Control-Request-Method": "GET"
                }
            )

            # Should allow the specific origin
            assert response.status_code == 200
            assert response.headers.get("access-control-allow-origin") == allowed_origin
            assert response.headers.get("access-control-allow-credentials") == "true"

            # Test with non-allowed origin
            response = client.options(
                "/api/health",
                headers={
                    "Origin": "https://evil.com",
                    "Access-Control-Request-Method": "GET"
                }
            )

            # Should not have CORS headers for non-allowed origin
            assert "access-control-allow-origin" not in response.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
