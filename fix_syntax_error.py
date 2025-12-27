#!/usr/bin/env python3
"""Fix syntax error in Uzbek translation"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing syntax error...")

# Fix Uzbek translation with escaped apostrophe
content = content.replace(
    "'uz': '🧠 O'ylayapman...',",
    "'uz': '🧠 O\\'ylayapman...',"
)

content = content.replace(
    "'uz': '🗣 Siz aytdingiz:',",
    "'uz': '🗣 Siz aytdingiz:',"
)

print("✅ Fixed syntax error")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

