#!/usr/bin/env python3
"""Add language code mapping for AI and Whisper"""

# Fix AI service
with open('backend/services/ai_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Adding language mapping to AI service...")

# Add mapping before the line with msg_with_lang
old_code = """        # Add current user message with lang parameter
        import json
        msg_with_lang = json.dumps({"message": user_query, "lang": language}, ensure_ascii=False)"""

new_code = """        # Add current user message with lang parameter
        import json
        # Map language codes (kz -> kk for Kazakh)
        lang_map = {'kz': 'kk', 'ky': 'ky', 'uz': 'uz', 'uk': 'uk', 'en': 'en', 'ru': 'ru'}
        mapped_lang = lang_map.get(language, 'ru')
        msg_with_lang = json.dumps({"message": user_query, "lang": mapped_lang}, ensure_ascii=False)"""

content = content.replace(old_code, new_code)
print("✅ Added language mapping to AI service")

with open('backend/services/ai_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Fix voice service
with open('backend/services/voice_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Adding language mapping to Voice service...")

old_voice = """    async def transcribe_audio(self, file_path: str, language: str = "ru") -> str:
        if not self.client: return "Voice Service not configured."
        try:
            with open(file_path, "rb") as audio_file:
                # Note: AsyncOpenAI audio.transcriptions.create is awaitable
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    language=language
                )"""

new_voice = """    async def transcribe_audio(self, file_path: str, language: str = "ru") -> str:
        if not self.client: return "Voice Service not configured."
        try:
            # Map language codes (kz -> kk for Kazakh)
            lang_map = {'kz': 'kk', 'ky': 'ky', 'uz': 'uz', 'uk': 'uk', 'en': 'en', 'ru': 'ru'}
            whisper_lang = lang_map.get(language, 'ru')
            
            with open(file_path, "rb") as audio_file:
                # Note: AsyncOpenAI audio.transcriptions.create is awaitable
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    language=whisper_lang
                )"""

content = content.replace(old_voice, new_voice)
print("✅ Added language mapping to Voice service")

with open('backend/services/voice_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Language mapping added to both services!")
