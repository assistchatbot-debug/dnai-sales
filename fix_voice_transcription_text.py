#!/usr/bin/env python3
"""Fix 'You said:' text to be multilingual"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing voice transcription text...")

# Find and replace the "Вы сказали:" line
old_line = """                         await message.answer(f"🗣 Вы сказали: {transcribed_text}")"""

new_lines = """                         # Multilingual "You said:" prefix
                         you_said = {
                             'ru': '🗣 Вы сказали:',
                             'en': '🗣 You said:',
                             'kz': '🗣 Сіз айттыңыз:',
                             'ky': '🗣 Сиз айттыңыз:',
                             'uz': '🗣 Siz aytdingiz:',
                             'uk': '🗣 Ви сказали:'
                         }
                         await message.answer(f"{you_said.get(language, '🗣 Вы сказали:')} {transcribed_text}")"""

content = content.replace(old_line, new_lines)
print("✅ Fixed voice transcription text")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

