#!/usr/bin/env python3
"""Fix manager menu and add widget creation"""
import re

# Read handlers.py
with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing handlers.py...")

# 1. Remove FIRST cmd_start (lines 40-52)
# Find pattern: from line 40 to the closing parenthesis of reply_markup
pattern1 = r'@router\.message\(Command\(\'start\'\)\)\nasync def cmd_start\(message: types\.Message, state: FSMContext\):\n    await state\.set_state\(SalesFlow\.qualifying\)\n    company_id = getattr.*?reply_markup=get_start_keyboard\(\)\n    \)'

content = re.sub(pattern1, '', content, count=1, flags=re.DOTALL)
print("✅ Removed duplicate /start handler")

# 2. Add "создать канал" command after "каналы" (around line 330)
# Find the end of каналы command and insert before next elif
old_help = """    # Help
    elif 'помощь' in text_lower"""

new_create = """    # Create social widget
    elif 'создать канал' in text_lower or 'create channel' in text_lower:
        await state.set_state(ManagerFlow.entering_channel_name)
        await message.answer(
            "📝 <b>Создание канала</b>\\n\\n"
            "Введите название канала (например: Instagram, Facebook, ВКонтакте):",
            parse_mode='HTML'
        )
    
    # Help
    elif 'помощь' in text_lower"""

if "'создать канал' in text_lower" not in content:
    content = content.replace(old_help, new_create)
    print("✅ Added 'создать канал' command")

# 3. Add FSM handlers at the end of file
fsm_handlers = """

# === FSM Handlers for Social Widget Creation ===

@router.message(ManagerFlow.entering_channel_name)
async def process_channel_name(message: types.Message, state: FSMContext):
    \"\"\"Process channel name input\"\"\"
    if not is_manager(message.from_user.id, message.bot):
        await state.clear()
        return
    
    channel_name = message.text.strip()
    if not channel_name:
        await message.answer("❌ Название не может быть пустым. Попробуйте ещё раз:")
        return
    
    await state.update_data(channel_name=channel_name)
    await state.set_state(ManagerFlow.entering_greeting)
    
    await message.answer(
        f"✅ Канал: <b>{channel_name}</b>\\n\\n"
        "📝 Введите приветственное сообщение для этого канала\\n"
        "(или напишите 'skip' для стандартного):",
        parse_mode='HTML'
    )

@router.message(ManagerFlow.entering_greeting)
async def process_greeting(message: types.Message, state: FSMContext):
    \"\"\"Process greeting and create widget\"\"\"
    if not is_manager(message.from_user.id, message.bot):
        await state.clear()
        return
    
    greeting = message.text.strip()
    if greeting.lower() == 'skip':
        greeting = None
    
    data = await state.get_data()
    channel_name_raw = data.get('channel_name', '')
    company_id = message.bot.company_id
    
    await message.answer("⏳ Создаю канал...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{API_BASE_URL}/sales/companies/{company_id}/widgets',
                json={
                    'channel_name': channel_name_raw,
                    'greeting_message': greeting
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    url = result.get('url', '')
                    name = result.get('channel_name', '')
                    
                    await message.answer(
                        f"🎉 <b>Канал создан!</b>\\n\\n"
                        f"📱 Название: {channel_name_raw}\\n"
                        f"🔗 URL: {url}\\n"
                        f"💬 Приветствие: {greeting or 'стандартное'}\\n\\n"
                        f"Разместите эту ссылку в {channel_name_raw}!",
                        parse_mode='HTML'
                    )
                elif resp.status == 400:
                    error = await resp.json()
                    await message.answer(f"⚠️ {error.get('detail', 'Ошибка')}")
                else:
                    await message.answer(f"❌ Ошибка {resp.status}")
    except Exception as e:
        logging.error(f"Create widget error: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:50]}")
    finally:
        await state.clear()
"""

if "@router.message(ManagerFlow.entering_channel_name)" not in content:
    content += fsm_handlers
    print("✅ Added FSM handlers")

# 4. Fix hardcoded company_id in "каналы" command
content = content.replace(
    "company_id = 1  # For now, hardcoded",
    "company_id = message.bot.company_id"
)
print("✅ Fixed company_id")

# Write back
with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ All fixes applied!")
print("\nNext: docker-compose restart bot")
