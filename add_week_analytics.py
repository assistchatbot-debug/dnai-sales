#!/usr/bin/env python3
"""Add channel analytics to week leads handler"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Adding channel analytics to week leads...")

# Find and replace week handler
old_week = """                        week_leads=[l for l in leads if datetime.fromisoformat(l['created_at'].replace('Z','+00:00'))>week_ago]
                        msg=f"📊 <b>Лиды за неделю</b>\\n\\nВсего: {len(week_leads)}\\n\\n<b>Последние 10:</b>\\n\""""

new_week = """                        week_leads=[l for l in leads if datetime.fromisoformat(l['created_at'].replace('Z','+00:00'))>week_ago]
                        from collections import Counter
                        sources=Counter(l.get('source','web') for l in week_leads)
                        msg=f"📊 <b>Лиды за неделю</b>\\n\\nВсего: {len(week_leads)}\\n\\n<b>По источникам:</b>\\n"
                        for source,count in sources.most_common():
                            msg+=f"• {source}: {count}\\n"
                        msg+="\\n<b>Последние 10:</b>\\n\""""

content = content.replace(old_week, new_week)
print("✅ Added channel analytics to week leads")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

