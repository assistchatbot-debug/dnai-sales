#!/usr/bin/env python3
"""Add state parameter to process_manager_command"""

with open('bot/handlers.py', 'r') as f:
    content = f.read()

print("🔧 Fixing state parameter...")

# 1. Update function signature
content = content.replace(
    'async def process_manager_command(message: types.Message, text: str):',
    'async def process_manager_command(message: types.Message, text: str, state: FSMContext):'
)
print("✅ Updated function signature")

# 2. Update call in voice handler (around line 213)
content = content.replace(
    'await process_manager_command(message, transcribed_text)',
    'await process_manager_command(message, transcribed_text, state)'
)
print("✅ Updated voice handler call")

# 3. Update call in handle_text (around line 404)
content = content.replace(
    'await process_manager_command(message, message.text)',
    'await process_manager_command(message, message.text, state)'
)
print("✅ Updated handle_text call")

with open('bot/handlers.py', 'w') as f:
    f.write(content)

print("\n✅ All fixes applied!")
