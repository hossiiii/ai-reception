#!/usr/bin/env python3
"""Debug script to test the API and validation logic"""

import asyncio
import sys
from pathlib import Path

import aiohttp

# Add the tests directory to the path
sys.path.append(str(Path(__file__).parent / "tests"))

from llm_test_runner import LLMTestRunner


async def test_single_scenario():
    """Test a single scenario to debug the validation"""

    # Test API directly first
    async with aiohttp.ClientSession() as session:
        # Start conversation
        async with session.post("http://localhost:8000/api/conversations/") as response:
            if response.status != 200:
                print(f"Failed to start conversation: {response.status}")
                return
            start_result = await response.json()
            print(f"Conversation started: {start_result}")

        session_id = start_result["session_id"]

        # Send test message
        test_message = "田中太郎です。ABC商事から14時の山田部長との会議で来ました。"
        async with session.post(
            f"http://localhost:8000/api/conversations/{session_id}/messages",
            json={"message": test_message}
        ) as response:
            if response.status != 200:
                print(f"Failed to send message: {response.status}")
                return
            message_result = await response.json()
            print(f"Message response: {message_result}")

    # Now test with the test runner
    print("\n--- Testing with LLMTestRunner ---")
    runner = LLMTestRunner("test_scenarios.yaml")

    # Test a single scenario
    results = await runner.run_test_suite(["APT-001"])

    if results:
        result = results[0]
        print(f"Test Result: {result}")
        print(f"Overall Success: {result.overall_success}")
        print(f"Extraction Scores: {result.extraction_scores}")
        print(f"Quality Scores: {result.quality_scores}")
        print(f"Issues: {result.issues}")
    else:
        print("No test results returned")

if __name__ == "__main__":
    asyncio.run(test_single_scenario())
