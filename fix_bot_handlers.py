#!/usr/bin/env python3
"""Fix bot handlers to use correct channel_name in callback_data"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing callback_data...")

# Find and replace the exact block
old_block = """                        if widgets:
                            msg_parts.append("<b>Социальные сети:</b>")
                            for w in widgets:
                                channel = w['channel_name'].capitalize()
                                widget_id = w['id']
                                msg_parts.append(f"• {channel}")
                                
                                buttons.append([
                                    InlineKeyboardButton(text=f"✏️ {channel}", callback_data=f"edit_widget_{widget_id}"),
                                    InlineKeyboardButton(text=f"🗑 {channel}", callback_data=f"delete_widget_{channel}")
                                ])"""

new_block = """                        if widgets:
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

if old_block in content:
    content = content.replace(old_block, new_block)
    print("✅ Fixed callback_data")
    
    with open('bot/handlers.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ File saved")
else:
    print("❌ Block not found - showing what we have:")
    # Show what's actually there
    import re
    match = re.search(r'if widgets:.*?for w in widgets:.*?callback_data=f"delete_widget_', content, re.DOTALL)
    if match:
        print(match.group(0)[:200])
