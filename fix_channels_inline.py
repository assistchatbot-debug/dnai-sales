#!/usr/bin/env python3
"""Add inline buttons to channels command"""

with open('bot/handlers.py', 'r') as f:
    lines = f.readlines()

print("🔧 Replacing 'каналы' command with inline buttons...")

# Find the line with 'каналы' command (line 318)
start_line = None
for i, line in enumerate(lines):
    if "'каналы' in text_lower or 'channels' in text_lower" in line:
        start_line = i - 2  # Include comment
        break

if start_line is None:
    print("❌ Command not found!")
    exit(1)

# Find end of this elif block (next elif or next major section)
end_line = start_line
for i in range(start_line + 1, len(lines)):
    if lines[i].strip().startswith('elif ') or lines[i].strip().startswith('# '):
        if 'меню' in lines[i] or 'Menu' in lines[i]:
            end_line = i
            break

new_command = '''    # Каналы
    elif 'каналы' in text_lower or 'channels' in text_lower:
        company_id = message.bot.company_id
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/sales/companies/{company_id}/widgets') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        widgets = data.get('widgets', [])
                        
                        msg_parts = ["📢 <b>Каналы распространения</b>\\n"]
                        msg_parts.append("📱 Telegram: ✅ Активен")
                        msg_parts.append("🌐 Widget: ✅ Работает\\n")
                        
                        # Build inline buttons
                        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                        buttons = []
                        
                        if widgets:
                            msg_parts.append("<b>Социальные сети:</b>")
                            for w in widgets:
                                channel = w['channel_name'].capitalize()
                                widget_id = w['id']
                                msg_parts.append(f"• {channel}")
                                
                                buttons.append([
                                    InlineKeyboardButton(text=f"✏️ {channel}", callback_data=f"edit_widget_{widget_id}"),
                                    InlineKeyboardButton(text=f"🗑 {channel}", callback_data=f"delete_widget_{widget_id}")
                                ])
                        else:
                            msg_parts.append("<i>Социальных каналов пока нет</i>")
                        
                        # Add create button
                        buttons.append([
                            InlineKeyboardButton(text="➕ Создать канал", callback_data=f"create_widget_{company_id}")
                        ])
                        
                        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                        await message.answer('\\n'.join(msg_parts), reply_markup=keyboard, parse_mode='HTML')
                    else:
                        await message.answer("⚠️ Не удалось получить список каналов")
        except Exception as e:
            logging.error(f"Channels command error: {e}")
            await message.answer(f"❌ Ошибка: {str(e)[:50]}")
    
'''

# Replace lines
lines[start_line:end_line] = [new_command]
print(f"✅ Replaced lines {start_line+1} - {end_line}")

# Add callback handlers at the end
callback_code = '''
# === Widget Management Callbacks ===

@router.callback_query(F.data.startswith("create_widget_"))
async def create_widget_callback(callback: types.CallbackQuery, state: FSMContext):
    """Create new widget"""
    if not is_manager(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    await state.set_state(ManagerFlow.entering_channel_name)
    await callback.message.answer(
        "📝 <b>Создание канала</b>\\n\\n"
        "Введите название (например: Instagram, Facebook, ВКонтакте):",
        parse_mode='HTML'
    )
    await callback.answer()

@router.callback_query(F.data.startswith("delete_widget_"))
async def delete_widget_callback(callback: types.CallbackQuery):
    """Delete widget"""
    if not is_manager(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    widget_id = callback.data.split("_")[-1]
    company_id = callback.bot.company_id
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{widget_id}'
            ) as resp:
                if resp.status == 200:
                    await callback.message.edit_text("✅ Канал удалён")
                else:
                    await callback.answer(f"❌ Ошибка {resp.status}", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ {str(e)[:30]}", show_alert=True)
    
    await callback.answer()
'''

if 'create_widget_' not in ''.join(lines):
    lines.append(callback_code)
    print("✅ Added callback handlers")

with open('bot/handlers.py', 'w') as f:
    f.writelines(lines)

print("\n✅ Done!")
