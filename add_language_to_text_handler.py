#!/usr/bin/env python3
"""Add language parameter to text message handler"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Adding language to text handler...")

# Find the text handler around line 669
old_json = """            async with session.post(f'{API_BASE_URL}/sales/{company_id}/chat', json={
                'message': message.text,
                'user_id': user_id,
                'username': username,
                'session_id': session_id,
                'source': 'telegram'
            })"""

new_json = """            # Get language from state
            state_data = await state.get_data()
            language = state_data.get('language', 'ru')
            
            async with session.post(f'{API_BASE_URL}/sales/{company_id}/chat', json={
                'message': message.text,
                'user_id': user_id,
                'username': username,
                'session_id': session_id,
                'source': 'telegram',
                'language': language
            })"""

content = content.replace(old_json, new_json)
print("✅ Added language to text handler")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

