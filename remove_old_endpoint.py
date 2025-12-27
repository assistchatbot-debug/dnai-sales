#!/usr/bin/env python3
"""Remove old channel_name endpoint to force ID-based URLs only"""

with open('backend/routers/sales_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Removing old channel_name endpoint...")

# Find and remove the old endpoint
import re
pattern = r'@router\.get\("/companies/\{company_id\}/widgets/\{channel_name\}"\).*?(?=@router\.|$)'
match = re.search(pattern, content, re.DOTALL)

if match:
    old_endpoint = match.group(0)
    # Only remove if it's the backward compatibility one (not the new ID one)
    if 'channel_name: str' in old_endpoint:
        content = content.replace(old_endpoint, '')
        print("✅ Removed old channel_name endpoint")
    else:
        print("⚠️ Endpoint already removed or pattern changed")
else:
    print("⚠️ Endpoint not found")

with open('backend/routers/sales_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

