#!/usr/bin/env python3
"""Fix start_session call to include company_id"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing start_session call...")

# Fix the call on line 76
old_call = "    await start_session(message.from_user.id)"
new_call = "    await start_session(message.from_user.id, company_id=1)"

content = content.replace(old_call, new_call)
print("✅ Fixed start_session call")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

