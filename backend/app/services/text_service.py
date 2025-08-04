from typing import Protocol

from openai import AsyncOpenAI

from ..config import settings


class MessageProcessor(Protocol):
    """Protocol for input/output processing - enables Step2 voice expansion"""

    async def process_input(self, input_data: str) -> str:
        """Process input and convert to text"""
        ...

    async def generate_output(self, text: str) -> str:
        """Generate output from text"""
        ...


class TextService:
    """Step1: Text processing service with extensible architecture for Step2"""

    def __init__(self) -> None:
        # Initialize OpenAI client with fallback for development
        if settings.openai_api_key and settings.openai_api_key.startswith('sk-'):
            self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            self.use_mock = False
            print(f"✅ TextService initialized with OpenAI API (key: {settings.openai_api_key[:10]}...)")
        else:
            self.openai_client = None
            self.use_mock = True
            print("⚠️ TextService initialized with mock mode (no valid OpenAI API key)")

    async def process_input(self, input_data: str) -> str:
        """Step1: Return input text as-is, cleaned"""
        return input_data.strip()

    async def generate_output(self, text: str, context: str = "") -> str:
        """Generate AI response using OpenAI GPT-4 or mock for development"""

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
7. 受付システムとして適切な質問や案内を行う"""

            if context:
                system_prompt += f"\n\n追加のコンテキスト: {context}"

            # Create conversation messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}  # Changed from "assistant" to "user"
            ]

            print(f"🤖 Sending to OpenAI: {text[:50]}...")

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # More cost-effective model
                messages=messages,
                max_tokens=200,  # Reduced for faster response
                temperature=0.7,
                timeout=15  # Add timeout
            )

            ai_response = response.choices[0].message.content or ""
            print(f"✅ OpenAI response: {ai_response[:50]}...")

            return ai_response

        except Exception as e:
            print(f"OpenAI API error: {e}")
            return "申し訳ございません。システムエラーが発生しました。もう一度お試しください。"

    async def _generate_mock_response(self, text: str, context: str = "") -> str:
        """Generate mock AI response for development mode"""
        import asyncio

        # Add small delay to simulate API call
        await asyncio.sleep(0.5)

        # Simple mock responses based on context
        if "名前" in text and "会社" in text:
            return """ありがとうございます。以下の内容で確認いたします：

お名前: [入力された名前]様
会社名: [入力された会社名]

この内容で間違いございませんか？
「はい」または「いいえ」でお答えください。"""

        elif "はい" in text or "yes" in text.lower():
            return """承知いたしました。ご来訪の目的をお聞かせください：

1. 予約のお客様
2. 営業のご訪問
3. 配達業者の方

該当する番号をお教えください。"""

        else:
            return """申し訳ございません。もう一度お聞かせください。

お名前と会社名を以下の形式で教えてください：
例: 山田太郎、株式会社テスト"""


# Step2 expansion point: AudioService(MessageProcessor) will be implemented here
