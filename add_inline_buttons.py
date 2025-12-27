#!/usr/bin/env python3
"""Add inline buttons for channel management"""

with open('bot/handlers.py', 'r') as f:
    content = f.read()

print("🔧 Adding inline buttons for channels...")

# Find and replace the 'каналы' command section
old_channels = '''    # Social media channels management
    elif 'каналы' in text_lower or 'channels' in text_lower or 'канал' in text_lower:
        company_id = message.bot.company_id
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get list of social widgets
                async with session.get(f'{API_BASE_URL}/sales/companies/{company_id}/widgets') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        widgets = data.get('widgets', [])
                        
                        # Build message
                        msg_parts = ["📢 <b>Каналы распространения</b>\\n"]
                        msg_parts.append("📱 Telegram: ✅ Активен")
                        msg_parts.append("🌐 Widget: ✅ Работает\\n")
                        
                        if widgets:
                            msg_parts.append("<b>Социальные сети:</b>")
                            for i, w in enumerate(widgets, 1):
                                channel = w['channel_name'].capitalize()
                                url = w['url']
                                msg_parts.append(f"{i}. {channel} - {url}")
                        else:
                            msg_parts.append("<i>Социальных каналов пока нет</i>")
                        
                        msg_parts.append("\\n💡 Создать новый: напишите <b>создать канал</b>")
                        
                        await message.answer('\\n'.join(msg_parts), parse_mode='HTML')
                    else:
                        await message.answer("⚠️ Не удалось получить список каналов")
        except Exception as e:
            logging.error(f"Channels command error: {e}")
            await message.answer(f"❌ Ошибка: {str(e)[:50]}")'''

new_channels = '''    # Social media channels management  
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
                                url = w['url']
                                widget_id = w['id']
                                msg_parts.append(f"• {channel}")
                                
                                # Add edit/delete buttons for each widget
                                buttons.append([
                                    InlineKeyboardButton(
                                        text=f"✏️ {channel}",
                                        callback_data=f"edit_widget_{widget_id}"
                                    ),
                                    InlineKeyboardButton(
                                        text=f"🗑 {channel}",
                                        callback_data=f"delete_widget_{widget_id}"
                                    )
                                ])
                        else:
                            msg_parts.append("<i>Социальных каналов пока нет</i>")
                        
                        # Add "Create" button
                        buttons.append([
                            InlineKeyboardButton(
                                text="➕ Создать канал",
                                callback_data=f"create_widget_{company_id}"
                            )
                        ])
                        
                        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                        await message.answer('\\n'.join(msg_parts), reply_markup=keyboard, parse_mode='HTML')
                    else:
                        await message.answer("⚠️ Не удалось получить список каналов")
        except Exception as e:
            logging.error(f"Channels command error: {e}")
            await message.answer(f"❌ Ошибка: {str(e)[:50]}")'''

content = content.replace(old_channels, new_channels)
print("✅ Updated 'каналы' command with inline buttons")

# Remove old "создать канал" text command - no longer needed
old_create = '''    # Create social widget
    elif 'создать канал' in text_lower or 'create channel' in text_lower:
        await state.set_state(ManagerFlow.entering_channel_name)
        await message.answer(
            "📝 <b>Создание канала</b>\\n\\n"
            "Введите название канала (например: Instagram, Facebook, ВКонтакте):",
            parse_mode='HTML'
        )
    
    '''

content = content.replace(old_create, '')
print("✅ Removed old text-based 'создать канал' command")

# Add callback handlers at the end
callback_handlers = '''

# === Inline Button Callbacks for Widget Management ===

@router.callback_query(F.data.startswith("create_widget_"))
async def create_widget_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle 'Create Widget' button"""
    if not is_manager(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    await state.set_state(ManagerFlow.entering_channel_name)
    await callback.message.answer(
        "📝 <b>Создание канала</b>\\n\\n"
        "Введите название канала (например: Instagram, Facebook, ВКонтакте):",
        parse_mode='HTML'
    )
    await callback.answer()

@router.callback_query(F.data.startswith("edit_widget_"))
async def edit_widget_callback(callback: types.CallbackQuery):
    """Handle 'Edit Widget' button"""
    if not is_manager(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    widget_id = callback.data.split("_")[-1]
    await callback.message.answer(
        f"✏️ Редактирование канала #{widget_id}\\n\\n"
        "🚧 В разработке...",
        parse_mode='HTML'
    )
    await callback.answer()

@router.callback_query(F.data.startswith("delete_widget_"))
async def delete_widget_callback(callback: types.CallbackQuery):
    """Handle 'Delete Widget' button"""
    if not is_manager(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    widget_id = callback.data.split("_")[-1]
    company_id = callback.bot.company_id
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{widget_id}',
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    await callback.message.answer("✅ Канал удалён")
                    # Refresh the list
                    await callback.message.delete()
                else:
                    await callback.message.answer(f"❌ Ошибка удаления (код {resp.status})")
    except Exception as e:
        logging.error(f"Delete widget error: {e}")
        await callback.message.answer(f"❌ Ошибка: {str(e)[:50]}")
    
    await callback.answer()
'''

if "@router.callback_query(F.data.startswith" not in content or "create_widget_" not in content:
    content += callback_handlers
    print("✅ Added callback handlers")

with open('bot/handlers.py', 'w') as f:
    f.write(content)

print("\n✅ All changes applied!")
