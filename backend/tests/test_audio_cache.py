"""Test suite for simple audio cache implementation"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.audio_service import AudioService
from app.services.simple_audio_cache import SimpleAudioCache


class TestSimpleAudioCache:
    """Test simple audio cache functionality"""

    def test_cache_initialization(self):
        """Test cache initialization"""
        cache = SimpleAudioCache(ttl_hours=1, max_size=50)
        assert cache._max_size == 50
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["cache_size"] == 0

    def test_cache_miss_and_set(self):
        """Test cache miss and setting value"""
        cache = SimpleAudioCache()

        # First access should be a miss
        result = cache.get("test text", "alloy")
        assert result is None

        # Set value
        test_audio = b"test_audio_data"
        cache.set("test text", test_audio, "alloy")

        # Now it should hit
        result = cache.get("test text", "alloy")
        assert result == test_audio

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0

    def test_cache_key_generation(self):
        """Test that different texts generate different keys"""
        cache = SimpleAudioCache()

        cache.set("text1", b"audio1")
        cache.set("text2", b"audio2")

        assert cache.get("text1") == b"audio1"
        assert cache.get("text2") == b"audio2"
        assert cache.get("text3") is None

    def test_cache_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = SimpleAudioCache(max_size=3)

        cache.set("text1", b"audio1")
        cache.set("text2", b"audio2")
        cache.set("text3", b"audio3")

        # Cache is now full
        assert cache.get_stats()["cache_size"] == 3

        # Adding a 4th item should evict the oldest (text1)
        cache.set("text4", b"audio4")

        assert cache.get("text1") is None  # Evicted
        assert cache.get("text2") == b"audio2"  # Still there
        assert cache.get("text3") == b"audio3"  # Still there
        assert cache.get("text4") == b"audio4"  # Newly added

    def test_cache_clear(self):
        """Test cache clearing"""
        cache = SimpleAudioCache()

        cache.set("text1", b"audio1")
        cache.set("text2", b"audio2")

        assert cache.get_stats()["cache_size"] == 2

        cache.clear()

        assert cache.get_stats()["cache_size"] == 0
        assert cache.get_stats()["hits"] == 0
        assert cache.get_stats()["misses"] == 0


class TestAudioServiceWithCache:
    """Test AudioService with caching functionality"""

    @pytest.fixture
    def audio_service(self):
        """Create AudioService instance for testing"""
        service = AudioService()
        # Clear cache before each test
        service.audio_cache.clear()
        return service

    @pytest.mark.asyncio
    async def test_audio_generation_with_cache(self, audio_service):
        """Test that audio generation uses cache effectively"""

        # Patch OpenAI client
        with patch.object(audio_service, 'openai_client') as mock_client:
            mock_response = MagicMock()
            mock_response.content = b"fake_audio_data"
            mock_client.audio.speech.create = AsyncMock(return_value=mock_response)
            audio_service.use_mock = False

            # First call - should hit OpenAI
            test_text = "いらっしゃいませ。音声受付システムです。"

            start_time = time.time()
            result1 = await audio_service.generate_audio_output(test_text)
            first_call_time = time.time() - start_time

            assert result1 == b"fake_audio_data"
            assert mock_client.audio.speech.create.call_count == 1

            # Second call - should use cache
            start_time = time.time()
            result2 = await audio_service.generate_audio_output(test_text)
            second_call_time = time.time() - start_time

            assert result2 == b"fake_audio_data"
            # Should NOT call OpenAI again
            assert mock_client.audio.speech.create.call_count == 1

            # Cache hit should be much faster
            assert second_call_time < first_call_time / 2

            # Check cache stats
            stats = audio_service.audio_cache.get_stats()
            assert stats["hits"] == 1
            assert stats["misses"] == 1
            assert stats["hit_rate"] == 50.0

    @pytest.mark.asyncio
    async def test_common_phrases_caching(self, audio_service):
        """Test that common phrases are cached effectively"""

        common_phrases = [
            "いらっしゃいませ。音声受付システムです。",
            "承知いたしました。",
            "ありがとうございます。",
            "申し訳ございません。",
            "少々お待ちください。",
            "処理中にエラーが発生しました。もう一度お試しください。"
        ]

        with patch.object(audio_service, 'openai_client') as mock_client:
            mock_response = MagicMock()
            mock_response.content = b"audio"
            mock_client.audio.speech.create = AsyncMock(return_value=mock_response)
            audio_service.use_mock = False

            # Generate audio for all phrases twice
            for phrase in common_phrases:
                await audio_service.generate_audio_output(phrase)
                await audio_service.generate_audio_output(phrase)

            # Each phrase should only call API once
            assert mock_client.audio.speech.create.call_count == len(common_phrases)

            # Check cache stats
            stats = audio_service.audio_cache.get_stats()
            assert stats["hits"] == len(common_phrases)  # Second calls all hit
            assert stats["misses"] == len(common_phrases)  # First calls all miss
            assert stats["hit_rate"] == 50.0

    @pytest.mark.asyncio
    async def test_mock_mode_caching(self, audio_service):
        """Test that caching works in mock mode too"""
        audio_service.use_mock = True

        test_text = "テスト音声"

        # First call
        result1 = await audio_service.generate_audio_output(test_text)
        assert b"mock_audio_data" in result1

        # Second call should be cached
        start_time = time.time()
        result2 = await audio_service.generate_audio_output(test_text)
        cache_time = time.time() - start_time

        assert result1 == result2
        # Cache hit should be instant (no mock delay)
        assert cache_time < 0.1

        stats = audio_service.audio_cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1


class TestCachePerformance:
    """Test performance improvements from caching"""

    @pytest.mark.asyncio
    async def test_sequential_requests_with_cache(self):
        """Test cache performance with sequential requests"""

        audio_service = AudioService()
        audio_service.audio_cache.clear()

        with patch.object(audio_service, 'openai_client') as mock_client:
            mock_response = MagicMock()
            mock_response.content = b"cached_audio"
            mock_client.audio.speech.create = AsyncMock(return_value=mock_response)
            audio_service.use_mock = False

            test_text = "順次テスト用音声"

            # Make 10 sequential requests for the same text
            for _ in range(10):
                result = await audio_service.generate_audio_output(test_text)
                assert result == b"cached_audio"

            # Only first request should call API
            assert mock_client.audio.speech.create.call_count == 1

            # Check cache effectiveness
            stats = audio_service.audio_cache.get_stats()
            assert stats["hits"] == 9  # 9 cache hits
            assert stats["misses"] == 1  # 1 cache miss (first call)
            assert stats["hit_rate"] == 90.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
