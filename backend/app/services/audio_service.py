import asyncio
import io
from typing import Protocol

from openai import AsyncOpenAI

from ..config import settings
from .connection_pool import get_connection_pool
from .simple_audio_cache import get_audio_cache


class AudioProcessor(Protocol):
    """Audio processing protocol for Step2 voice functionality"""

    async def process_audio_input(self, audio_data: bytes) -> str:
        """Convert audio to text"""
        ...

    async def generate_audio_output(self, text: str) -> bytes:
        """Convert text to audio"""
        ...


class AudioService:
    """Step2: Audio processing service that extends Step1's MessageProcessor architecture"""

    def __init__(self):
        # Initialize audio cache
        self.audio_cache = get_audio_cache()
        
        # Use same settings pattern as Step1's TextService
        if settings.openai_api_key and settings.openai_api_key.startswith('sk-'):
            # Use individual OpenAI client with optimized timeout
            self.openai_client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                timeout=5.0  # Reduced timeout for better performance
            )
            self.use_mock = False
            print(f"✅ AudioService initialized with OpenAI API and cache")
        else:
            self.openai_client = None
            self.use_mock = True
            print("⚠️ AudioService initialized with mock mode (no valid OpenAI API key)")

    async def process_input(self, input_data: str) -> str:
        """Step1 compatibility: Process text input as-is"""
        return input_data.strip()

    async def process_audio_input(self, audio_data: bytes) -> str:
        """Step2: Convert audio data to text using OpenAI Whisper API"""
        if self.use_mock:
            # Add realistic delay to simulate API call
            await asyncio.sleep(0.8)
            return "こんにちは、テスト音声です。山田太郎、株式会社テストです。"

        try:
            # Create audio file for OpenAI Whisper API
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.webm"  # WebM format from frontend

            print(f"🎤 Processing audio input ({len(audio_data)} bytes)...")

            transcript = await self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ja",  # Japanese language specification
                temperature=0.0  # Deterministic transcription
            )

            transcribed_text = transcript.text
            print(f"✅ Audio transcribed: {transcribed_text[:50]}...")

            return transcribed_text

        except Exception as e:
            print(f"❌ Audio transcription error: {e}")
            return "申し訳ございません。音声が聞き取れませんでした。もう一度お話しください。"

    async def generate_output(self, text: str, context: str = "") -> str:
        """Step1 compatibility: Generate text response using same logic as TextService"""

        # Use mock response in development mode
        if self.use_mock:
            return await self._generate_mock_response(text, context)

        try:
            system_prompt = """あなたは丁寧で効率的な受付AIです。以下のルールに従って応答してください:

1. 常に敬語を使用し、丁寧に対応する
2. 来客者の名前と会社名を正確に確認する
3. 情報が不足している場合は、具体的に何が必要かを伝える
4. 来客者のタイプ（予約、営業、配達）を判断して適切に案内する
5. 応答は簡潔で分かりやすく、次にやるべきことを示す
6. 日本語で応答する
7. 受付システムとして適切な質問や案内を行う
8. 音声での対話を前提として、自然で聞き取りやすい応答を心がける"""

            if context:
                system_prompt += f"\n\n追加のコンテキスト: {context}"

            # Create conversation messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]

            print(f"🤖 Generating response for: {text[:50]}...")

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Same model as TextService
                messages=messages,
                max_tokens=200,
                temperature=0.7,
                timeout=5  # Reduced timeout from 15s to 5s for better performance
            )

            ai_response = response.choices[0].message.content or ""
            print(f"✅ Generated response: {ai_response[:50]}...")

            return ai_response

        except Exception as e:
            print(f"❌ Text generation error: {e}")
            return "申し訳ございません。システムエラーが発生しました。もう一度お試しください。"

    async def generate_audio_output(self, text: str, voice: str = "alloy") -> bytes:
        """Step2: Convert text to audio using OpenAI TTS API with caching"""
        
        # Check cache first
        cached_audio = self.audio_cache.get(text, voice)
        if cached_audio:
            return cached_audio
        
        if self.use_mock:
            # Add realistic delay to simulate API call
            await asyncio.sleep(0.6)
            # Return mock audio data (empty bytes with size indicator)
            mock_audio = b"mock_audio_data_" + text.encode('utf-8')[:20] + b"_end"
            self.audio_cache.set(text, mock_audio, voice)
            return mock_audio

        try:
            print(f"🔊 Generating audio for: {text[:50]}...")

            response = await self.openai_client.audio.speech.create(
                model="gpt-4o-mini-tts",  # Corrected TTS model name
                voice=voice,   # Clear, neutral voice suitable for Japanese
                input=text,
                response_format="wav"  # WAV format for broad compatibility
            )

            audio_data = response.content
            print(f"✅ Audio generated ({len(audio_data)} bytes)")
            
            # Store in cache
            self.audio_cache.set(text, audio_data, voice)

            return audio_data

        except Exception as e:
            print(f"❌ Audio generation error: {e}")
            return b""  # Return empty bytes on error

    async def _generate_mock_response(self, text: str, context: str = "") -> str:
        """Generate mock AI response for development mode (same as TextService)"""
        # Add small delay to simulate API call
        await asyncio.sleep(0.5)

        # Simple mock responses based on context
        if "名前" in text and "会社" in text:
            return """確認いたします。

お名前とご所属を、もう一度お聞かせください。"""

        elif "はい" in text or "yes" in text.lower():
            return """承知いたしました。

ご来訪の目的をお聞かせください。ご予約、営業、配達などご用件をお教えください。"""

        else:
            return """いらっしゃいませ。音声受付システムです。

会社名、お名前、ご用件をお聞かせください。"""


# Maintain Step1 compatibility by providing the same interface
MessageProcessorImpl = AudioService
