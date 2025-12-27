#!/usr/bin/env python3
"""Update bot to show widget ID and URL in list"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Updating widget list display...")

# Find the widget list display code
old_display = """                        if widgets:
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

new_display = """                        if widgets:
                            msg_parts.append("<b>Социальные сети:</b>")
                            for w in widgets:
                                channel_name = w['channel_name']
                                channel_display = channel_name.capitalize()
                                widget_id = w['id']
                                widget_url = w.get('url', f"https://bizdnai.com/w/{company_id}/{widget_id}")
                                
                                msg_parts.append(f"• {channel_display} (ID: {widget_id})")
                                msg_parts.append(f"  🔗 {widget_url}")
                                
                                buttons.append([
                                    InlineKeyboardButton(text=f"✏️ Edit #{widget_id}", callback_data=f"edit_widget_{widget_id}"),
                                    InlineKeyboardButton(text=f"🗑 Delete #{widget_id}", callback_data=f"delete_widget_{widget_id}")
                                ])"""

if old_display in content:
    content = content.replace(old_display, new_display)
    print("✅ Updated widget list display")
else:
    print("⚠️ Pattern not found, trying alternative...")
    # Try to find just the loop part
    import re
    pattern = r'for w in widgets:.*?callback_data=f"delete_widget_'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        print(f"Found at position {match.start()}")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

