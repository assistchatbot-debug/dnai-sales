#!/usr/bin/env python3
"""Fix delete endpoint and update get_widget_config to return all translations"""

with open('backend/routers/sales_agent.py', 'r') as f:
    content = f.read()

print("🔧 Fixing delete endpoint...")

# Find delete endpoint and ensure it uses @router.delete
old_delete = "@router.post('/companies/{company_id}/widgets/{channel_name}')"
new_delete = "@router.delete('/companies/{company_id}/widgets/{channel_name}')"

if old_delete in content:
    content = content.replace(old_delete, new_delete)
    print("✅ Fixed delete endpoint HTTP method")
else:
    print("⚠️ Delete endpoint already correct or not found")

# Update get_widget_config to return all translations
old_get_config = '''        return {
            'company_id': widget.company_id,
            'channel_name': widget.channel_name,
            'greeting_message': widget.greeting_message,
            'is_active': widget.is_active,
            'url': f'https://bizdnai.com/w/{company_id}/{channel_name}'
        }'''

new_get_config = '''        return {
            'company_id': widget.company_id,
            'channel_name': widget.channel_name,
            'greeting_message': widget.greeting_message,
            'greetings': {
                'ru': widget.greeting_ru or widget.greeting_message,
                'en': widget.greeting_en or widget.greeting_message,
                'kz': widget.greeting_kz or widget.greeting_message,
                'ky': widget.greeting_ky or widget.greeting_message,
                'uz': widget.greeting_uz or widget.greeting_message,
                'uk': widget.greeting_uk or widget.greeting_message
            },
            'is_active': widget.is_active,
            'url': f'https://bizdnai.com/w/{company_id}/{channel_name}'
        }'''

content = content.replace(old_get_config, new_get_config)
print("✅ Updated get_widget_config to return all translations")

with open('backend/routers/sales_agent.py', 'w') as f:
    f.write(content)

print("\n✅ Done! Restart backend:")
print("docker-compose restart backend")
