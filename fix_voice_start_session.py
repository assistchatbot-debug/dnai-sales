#!/usr/bin/env python3
"""Fix start_session call in voice handler"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing start_session in voice handler...")

# Fix the call in voice handler (around line 168)
old_call = """    if not session_id:
        session_id = await start_session(message.from_user.id)
        if session_id:
            await state.update_data(session_id=session_id)"""

new_call = """    if not session_id:
        session_id = await start_session(message.from_user.id, company_id=1)
        if session_id:
            await state.update_data(session_id=session_id)"""

content = content.replace(old_call, new_call)
print("✅ Fixed start_session call in voice handler")

# Add multilingual status messages
old_status = '    status_msg = await message.answer("🎤 Думаю...")'
new_status = '''    # Get language for status message
    state_data = await state.get_data()
    language = state_data.get('language', 'ru')
    
    status_messages = {
        'ru': '🧠 Думаю...',
        'en': '🧠 Thinking...',
        'kz': '🧠 Ойланудамын...',
        'ky': '🧠 Ойлонуп жатам...',
        'uz': '🧠 O\'ylayapman...',
        'uk': '🧠 Думаю...'
    }
    
    status_msg = await message.answer(status_messages.get(language, '🧠 Думаю...'))'''

content = content.replace(old_status, new_status)
print("✅ Added multilingual status messages")

# Add multilingual transcription messages
old_transcribe = '                         await message.answer(f"🗣 Вы сказали: {transcribed_text}")'
new_transcribe = '''                         transcribe_prefix = {
                             'ru': '🗣 Вы сказали:',
                             'en': '🗣 You said:',
                             'kz': '🗣 Сіз айттыңыз:',
                             'ky': '🗣 Сиз айттыңыз:',
                             'uz': '🗣 Siz aytdingiz:',
                             'uk': '🗣 Ви сказали:'
                         }
                         await message.answer(f"{transcribe_prefix.get(language, '🗣 Вы сказали:')} {transcribed_text}")'''

content = content.replace(old_transcribe, new_transcribe)
print("✅ Added multilingual transcription messages")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Voice handler fixed!")
