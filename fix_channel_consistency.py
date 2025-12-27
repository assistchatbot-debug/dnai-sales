#!/usr/bin/env python3
"""Fix channel name consistency - always use lowercase from DB"""

with open('bot/handlers.py', 'r') as f:
    content = f.read()

print("🔧 Fixing channel name consistency...")

# Fix button creation to use actual channel_name from DB (already lowercase)
old_button = '''                            # Add edit and delete buttons
                            widget_id = widget.get('id')
                            buttons.append([
                                InlineKeyboardButton(text=f"✏️ {channel}", callback_data=f"edit_widget_{widget_id}"),
                                InlineKeyboardButton(text=f"🗑 {channel}", callback_data=f"delete_widget_{channel}")'''

new_button = '''                            # Add edit and delete buttons
                            widget_id = widget.get('id')
                            channel_lower = widget.get('channel_name')  # Use actual DB name (lowercase)
                            buttons.append([
                                InlineKeyboardButton(text=f"✏️ {channel}", callback_data=f"edit_widget_{widget_id}"),
                                InlineKeyboardButton(text=f"🗑 {channel}", callback_data=f"delete_widget_{channel_lower}")'''

content = content.replace(old_button, new_button)

# Remove .lower() from callback since we now pass correct name
old_callback = '''    channel_name = callback.data.split("_", 2)[-1].lower()  # Get channel name in lowercase'''
new_callback = '''    channel_name = callback.data.split("_", 2)[-1]  # Get channel name from callback'''

content = content.replace(old_callback, new_callback)

print("✅ Fixed channel name consistency")

with open('bot/handlers.py', 'w') as f:
    f.write(content)

print("\n✅ Done! Restart bot:")
print("docker-compose restart bot")
