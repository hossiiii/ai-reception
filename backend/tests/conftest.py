"""Pytest configuration for LLM integration tests"""

import pytest


def pytest_addoption(parser):
    """カスタムpytestオプション"""
    parser.addoption(
        "--llm-report",
        action="store_true",
        default=False,
        help="Generate detailed LLM test report"
    )

@pytest.fixture(scope="session")
def llm_report_requested(request):
    """レポート生成の要求をチェック"""
    return request.config.getoption("--llm-report")
