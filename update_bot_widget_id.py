#!/usr/bin/env python3
"""Update bot to use widget_id in URLs and delete operations"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Updating bot handlers...")

# Update widget list to show ID and use it in callback_data
old_list = """                        if widgets:
                            msg_parts.append("<b>Социальные сети:</b>")
                            for w in widgets:
                                channel_name = w['channel_name']  # Original from DB (lowercase)
                                channel_display = channel_name.capitalize()  # For display only
                                widget_id = w['id']
                                msg_parts.append(f"• {channel_display}")
                                
                                buttons.append([
                                    InlineKeyboardButton(text=f"✏️ {channel_display}", callback_data=f"edit_widget_{widget_id}"),
                                    InlineKeyboardButton(text=f"🗑 {channel_display}", callback_data=f"delete_widget_{channel_name}")
                                ])"""

new_list = """                        if widgets:
                            msg_parts.append("<b>Социальные сети:</b>")
                            for w in widgets:
                                channel_name = w['channel_name']
                                channel_display = channel_name.capitalize()
                                widget_id = w['id']
                                widget_url = w.get('url', f"https://bizdnai.com/w/{company_id}/{widget_id}")
                                
                                # Show channel name and ID
                                msg_parts.append(f"• {channel_display} (ID: {widget_id})")
                                msg_parts.append(f"  {widget_url}")
                                
                                buttons.append([
                                    InlineKeyboardButton(text=f"✏️ Edit #{widget_id}", callback_data=f"edit_widget_{widget_id}"),
                                    InlineKeyboardButton(text=f"🗑 Delete #{widget_id}", callback_data=f"delete_widget_{widget_id}")
                                ])"""

content = content.replace(old_list, new_list)
print("✅ Updated widget list to show ID and URL")

# Update delete callback to use widget_id
old_delete_callback = """@router.callback_query(F.data.startswith("delete_widget_"))
async def delete_widget_callback(callback: types.CallbackQuery):
    """Handle 'Delete Widget' button"""
    if not is_manager(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    channel_name = callback.data.split("_", 2)[-1]  # Get channel name from callback
    company_id = callback.bot.company_id
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{channel_name}',"""

new_delete_callback = """@router.callback_query(F.data.startswith("delete_widget_"))
async def delete_widget_callback(callback: types.CallbackQuery):
    """Handle 'Delete Widget' button"""
    if not is_manager(callback.from_user.id, callback.bot):
        await callback.answer("❌ Недостаточно прав", show_alert=True)
        return
    
    widget_id = int(callback.data.split("_")[-1])  # Get widget ID from callback
    company_id = callback.bot.company_id
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{widget_id}',"""

content = content.replace(old_delete_callback, new_delete_callback)
print("✅ Updated delete callback to use widget_id")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Bot updated to use widget_id!")
