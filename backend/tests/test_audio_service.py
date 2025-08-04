"""
Comprehensive tests for AudioService (Step2 voice functionality)
Tests both real API integration and mock mode functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.services.audio_service import AudioService
from app.config import settings


class TestAudioService:
    """Test suite for AudioService"""
    
    @pytest.fixture
    def mock_audio_service(self):
        """Create AudioService in mock mode"""
        with patch.object(settings, 'openai_api_key', None):
            service = AudioService()
        return service
    
    @pytest.fixture
    def real_audio_service(self):
        """Create AudioService with API key (may use real or mocked OpenAI)"""
        with patch.object(settings, 'openai_api_key', 'sk-test123'):
            service = AudioService()
        return service
    
    @pytest.mark.asyncio
    async def test_audio_service_initialization_mock_mode(self):
        """Test AudioService initializes correctly in mock mode"""
        with patch.object(settings, 'openai_api_key', None):
            service = AudioService()
        
        assert service.use_mock is True
        assert service.openai_client is None
    
    @pytest.mark.asyncio
    async def test_audio_service_initialization_api_mode(self):
        """Test AudioService initializes correctly with API key"""
        with patch.object(settings, 'openai_api_key', 'sk-test123'):
            service = AudioService()
        
        assert service.use_mock is False
        assert service.openai_client is not None
    
    @pytest.mark.asyncio
    async def test_process_input_text_compatibility(self, mock_audio_service):
        """Test Step1 compatibility: process_input handles text"""
        test_text = "  こんにちは、山田太郎です  "
        result = await mock_audio_service.process_input(test_text)
        
        assert result == "こんにちは、山田太郎です"  # Stripped
    
    @pytest.mark.asyncio
    async def test_process_audio_input_mock_mode(self, mock_audio_service):
        """Test audio input processing in mock mode"""
        test_audio_data = b"fake_audio_data"
        
        result = await mock_audio_service.process_audio_input(test_audio_data)
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "テスト音声" in result  # Should contain mock response
    
    @pytest.mark.asyncio
    async def test_generate_output_mock_mode(self, mock_audio_service):
        """Test text response generation in mock mode"""
        test_text = "名前と会社名を教えてください"
        
        result = await mock_audio_service.generate_output(test_text)
        
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain appropriate mock response
        assert any(keyword in result for keyword in ["名前", "会社名", "お聞かせ"])
    
    @pytest.mark.asyncio
    async def test_generate_audio_output_mock_mode(self, mock_audio_service):
        """Test audio output generation in mock mode"""
        test_text = "こんにちは"
        
        result = await mock_audio_service.generate_audio_output(test_text)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert b"mock_audio_data" in result
    
    @pytest.mark.asyncio
    async def test_process_audio_input_with_openai_api(self, real_audio_service):
        """Test audio input processing with OpenAI API (mocked)"""
        test_audio_data = b"fake_audio_data_for_whisper"
        
        # Mock OpenAI Whisper API response
        mock_response = Mock()
        mock_response.text = "こんにちは、田中です"
        
        with patch.object(real_audio_service.openai_client.audio.transcriptions, 'create', 
                         new_callable=AsyncMock, return_value=mock_response):
            result = await real_audio_service.process_audio_input(test_audio_data)
        
        assert result == "こんにちは、田中です"
    
    @pytest.mark.asyncio
    async def test_generate_audio_output_with_openai_api(self, real_audio_service):
        """Test audio output generation with OpenAI API (mocked)"""
        test_text = "ありがとうございます"
        
        # Mock OpenAI TTS API response
        mock_response = Mock()
        mock_response.content = b"fake_tts_audio_data"
        
        with patch.object(real_audio_service.openai_client.audio.speech, 'create',
                         new_callable=AsyncMock, return_value=mock_response):
            result = await real_audio_service.generate_audio_output(test_text)
        
        assert result == b"fake_tts_audio_data"
    
    @pytest.mark.asyncio
    async def test_process_audio_input_error_handling(self, real_audio_service):
        """Test error handling in audio input processing"""
        test_audio_data = b"invalid_audio_data"
        
        # Mock OpenAI API to raise an exception
        with patch.object(real_audio_service.openai_client.audio.transcriptions, 'create',
                         new_callable=AsyncMock, side_effect=Exception("API Error")):
            result = await real_audio_service.process_audio_input(test_audio_data)
        
        assert "エラーが発生しました" in result
    
    @pytest.mark.asyncio
    async def test_generate_audio_output_error_handling(self, real_audio_service):
        """Test error handling in audio output generation"""
        test_text = "エラーテスト"
        
        # Mock OpenAI API to raise an exception
        with patch.object(real_audio_service.openai_client.audio.speech, 'create',
                         new_callable=AsyncMock, side_effect=Exception("TTS Error")):
            result = await real_audio_service.generate_audio_output(test_text)
        
        assert result == b""  # Should return empty bytes on error
    
    @pytest.mark.asyncio
    async def test_generate_output_with_context(self, mock_audio_service):
        """Test text generation with context"""
        test_text = "はい"
        test_context = "名前の確認中"
        
        result = await mock_audio_service.generate_output(test_text, test_context)
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_mock_response_patterns(self, mock_audio_service):
        """Test different mock response patterns"""
        # Test name and company input
        result1 = await mock_audio_service.generate_output("山田太郎、株式会社テストです")
        assert "確認" in result1
        
        # Test confirmation
        result2 = await mock_audio_service.generate_output("はい")
        assert any(keyword in result2 for keyword in ["目的", "番号"])
        
        # Test default case
        result3 = await mock_audio_service.generate_output("よくわからない")
        assert any(keyword in result3 for keyword in ["名前", "会社名"])
    
    @pytest.mark.asyncio
    async def test_concurrent_audio_processing(self, mock_audio_service):
        """Test concurrent audio processing"""
        audio_chunks = [b"chunk1", b"chunk2", b"chunk3"]
        
        # Process multiple audio chunks concurrently
        tasks = [
            mock_audio_service.process_audio_input(chunk) 
            for chunk in audio_chunks
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert all(isinstance(result, str) for result in results)
        assert all(len(result) > 0 for result in results)
    
    @pytest.mark.asyncio
    async def test_large_audio_data_handling(self, mock_audio_service):
        """Test handling of large audio data"""
        # Simulate large audio file (1MB)
        large_audio_data = b"x" * (1024 * 1024)
        
        result = await mock_audio_service.process_audio_input(large_audio_data)
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_empty_audio_data_handling(self, mock_audio_service):
        """Test handling of empty audio data"""
        empty_audio_data = b""
        
        result = await mock_audio_service.process_audio_input(empty_audio_data)
        
        assert isinstance(result, str)
        assert len(result) > 0  # Should still return a response
    
    @pytest.mark.asyncio
    async def test_japanese_text_processing(self, mock_audio_service):
        """Test Japanese text processing"""
        japanese_texts = [
            "こんにちは",
            "山田太郎です",
            "株式会社テスト",
            "予約の件でお伺いしました"
        ]
        
        for text in japanese_texts:
            result = await mock_audio_service.generate_output(text)
            assert isinstance(result, str)
            assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_audio_service_performance(self, mock_audio_service):
        """Test AudioService performance in mock mode"""
        import time
        
        start_time = time.time()
        
        # Process audio input
        await mock_audio_service.process_audio_input(b"test_audio")
        
        # Generate text response
        await mock_audio_service.generate_output("test text")
        
        # Generate audio response
        await mock_audio_service.generate_audio_output("test response")
        
        end_time = time.time()
        
        # Mock mode should be fast (under 3 seconds total)
        assert (end_time - start_time) < 3.0
    
    def test_message_processor_compatibility(self, mock_audio_service):
        """Test that AudioService maintains MessageProcessor interface compatibility"""
        # Check that AudioService has required methods
        assert hasattr(mock_audio_service, 'process_input')
        assert hasattr(mock_audio_service, 'generate_output')
        
        # Check new voice methods
        assert hasattr(mock_audio_service, 'process_audio_input')
        assert hasattr(mock_audio_service, 'generate_audio_output')
        
        # Check that methods are callable
        assert callable(mock_audio_service.process_input)
        assert callable(mock_audio_service.generate_output)
        assert callable(mock_audio_service.process_audio_input)
        assert callable(mock_audio_service.generate_audio_output)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])