#!/usr/bin/env python3
"""Update DELETE endpoint to use widget_id"""

with open('backend/routers/sales_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Updating DELETE endpoint...")

# Find and replace DELETE endpoint
old_delete = '@router.delete("/companies/{company_id}/widgets/{channel_name}")'
new_delete = '@router.delete("/companies/{company_id}/widgets/{widget_id:int}")'

content = content.replace(old_delete, new_delete)

# Update function signature
old_sig = "async def delete_social_widget(\n    company_id: int,\n    channel_name: str,"
new_sig = "async def delete_social_widget(\n    company_id: int,\n    widget_id: int,"

content = content.replace(old_sig, new_sig)

# Update query
old_query = "SocialWidget.channel_name == channel_name"
new_query = "SocialWidget.id == widget_id"

content = content.replace(old_query, new_query)

print("✅ DELETE endpoint updated to use widget_id")

with open('backend/routers/sales_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

