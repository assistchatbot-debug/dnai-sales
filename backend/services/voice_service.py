import os
from openai import AsyncOpenAI

class VoiceService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            self.client = None
            print("Warning: OPENAI_API_KEY not set for VoiceService.")

    async def transcribe_audio(self, file_path: str, language: str = "ru") -> str:
        if not self.client: return "Voice Service not configured."
        try:
            with open(file_path, "rb") as audio_file:
                # Note: AsyncOpenAI audio.transcriptions.create is awaitable
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    language=language
                )
            return transcript.text
        except Exception as e:
            import traceback
            print(f"Transcription error: {e}")
            traceback.print_exc()
            return f"Error processing voice message: {str(e)}"

voice_service = VoiceService()
