#!/usr/bin/env python3
"""Fix delete widget callback to use channel_name instead of widget_id"""

with open('bot/handlers.py', 'r') as f:
    content = f.read()

print("🔧 Fixing delete widget callback...")

# Fix callback data to pass channel_name instead of widget_id
old_button = '''                                    InlineKeyboardButton(text=f"🗑 {channel}", callback_data=f"delete_widget_{widget_id}")'''

new_button = '''                                    InlineKeyboardButton(text=f"🗑 {channel}", callback_data=f"delete_widget_{channel}")'''

content = content.replace(old_button, new_button)

# Fix callback handler to use channel_name
old_handler = '''    widget_id = callback.data.split("_")[-1]
    company_id = callback.bot.company_id
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{widget_id}','''

new_handler = '''    channel_name = callback.data.split("_", 2)[-1]  # Get everything after "delete_widget_"
    company_id = callback.bot.company_id
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f'{API_BASE_URL}/companies/{company_id}/widgets/{channel_name}','''

content = content.replace(old_handler, new_handler)
print("✅ Fixed delete widget callback")

with open('bot/handlers.py', 'w') as f:
    f.write(content)

print("\n✅ Done! Restart bot:")
print("docker-compose restart bot")
