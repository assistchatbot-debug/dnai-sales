#!/usr/bin/env python3
"""Add language parameter to voice transcription"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Adding language to voice handler...")

# Find voice handler and add language field
old_voice = """        # Prepare form data
        data = aiohttp.FormData()
        data.add_field('file', file_data, filename='voice.ogg', content_type='audio/ogg')
        data.add_field('session_id', session_id or 'voice_session') 
        data.add_field('user_id', user_id)
        data.add_field('username', username)"""

new_voice = """        # Prepare form data
        data_form = aiohttp.FormData()
        data_form.add_field('file', file_data, filename='voice.ogg', content_type='audio/ogg')
        data_form.add_field('session_id', session_id or 'voice_session') 
        data_form.add_field('user_id', user_id)
        data_form.add_field('username', username)
        
        # Get language from state (default to 'ru')
        state_data = await state.get_data()
        language = state_data.get('language', 'ru')
        data_form.add_field('language', language)"""

content = content.replace(old_voice, new_voice)

# Fix variable name conflict (data -> data_form)
content = content.replace(
    "async with session.post(f'{API_BASE_URL}/sales/{company_id}/voice', data=data)",
    "async with session.post(f'{API_BASE_URL}/sales/{company_id}/voice', data=data_form)"
)

print("✅ Added language parameter to voice handler")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

