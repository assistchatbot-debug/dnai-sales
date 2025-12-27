#!/usr/bin/env python3
"""Fix delete URL to include /sales prefix"""

with open('bot/handlers.py', 'r') as f:
    content = f.read()

print("🔧 Fixing delete URL...")

# Fix URL to include /sales prefix
old_url = "f'{API_BASE_URL}/companies/{company_id}/widgets/{channel_name}'"
new_url = "f'{API_BASE_URL}/sales/companies/{company_id}/widgets/{channel_name}'"

content = content.replace(old_url, new_url)
print("✅ Fixed delete URL to include /sales prefix")

with open('bot/handlers.py', 'w') as f:
    f.write(content)

print("\n✅ Done!")
