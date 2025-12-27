#!/usr/bin/env python3
"""Fix FSM priority in handle_text"""

with open('bot/handlers.py', 'r') as f:
    content = f.read()

print("🔧 Fixing FSM priority...")

# Update handle_text to skip if user is in FSM state
old_handle = '''async def handle_text(message: types.Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    
    # Check if manager - handle commands
    if is_manager(message.from_user.id, message.bot):
        await process_manager_command(message, message.text, state)
        return'''

new_handle = '''async def handle_text(message: types.Message, state: FSMContext):
    if message.text.startswith('/'):
        return
    
    # Skip if user is in FSM state (let FSM handlers process it)
    current_state = await state.get_state()
    if current_state is not None:
        return
    
    # Check if manager - handle commands
    if is_manager(message.from_user.id, message.bot):
        await process_manager_command(message, message.text, state)
        return'''

content = content.replace(old_handle, new_handle)
print("✅ Added FSM state check to handle_text")

with open('bot/handlers.py', 'w') as f:
    f.write(content)

print("\n✅ Done!")
