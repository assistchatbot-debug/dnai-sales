#!/usr/bin/env python3
"""Fix both 'You said:' occurrences"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("🔧 Fixing 'Вы сказали:' on lines 218 and 266...")

# Multilingual dictionary
you_said_dict = """                        you_said_text = {
                            'ru': '🗣 Вы сказали:',
                            'en': '🗣 You said:',
                            'kz': '🗣 Сіз айттыңыз:',
                            'ky': '🗣 Сиз айттыңыз:',
                            'uz': '🗣 Siz aytdingiz:',
                            'uk': '🗣 Ви сказали:'
                        }
                        await message.answer(f"{you_said_text.get(language, '🗣 Вы сказали:')} {transcribed_text}")
"""

# Fix line 218 (index 217)
if 'Вы сказали' in lines[217]:
    lines[217] = you_said_dict
    print("✅ Fixed line 218")

# Fix line 266 (index 265)
if 'Вы сказали' in lines[265]:
    lines[265] = you_said_dict
    print("✅ Fixed line 266")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✅ Both occurrences fixed!")
