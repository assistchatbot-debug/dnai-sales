#!/usr/bin/env python3
with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace w.get('url', ...) with direct generation
old = """                                widget_url = w.get('url', f"https://bizdnai.com/w/{company_id}/{widget_id}")"""
new = """                                widget_url = f"https://bizdnai.com/w/{company_id}/{widget_id}"  # Always use ID"""

content = content.replace(old, new)

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("✅ Bot fixed")
