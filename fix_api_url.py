#!/usr/bin/env python3
"""Fix widget API URL"""

with open('frontend/widget/standalone.html', 'r') as f:
    content = f.read()

print("🔧 Fixing API URL...")

# Fix widget config fetch URL
old_fetch = "const response = await fetch(`${API}/companies/${companyId}/widgets/${channelName}`);"
new_fetch = "const response = await fetch(`/sales/companies/${companyId}/widgets/${channelName}`);"

content = content.replace(old_fetch, new_fetch)
print("✅ Fixed widget API URL")

with open('frontend/widget/standalone.html', 'w') as f:
    f.write(content)

print("✅ Done!")
