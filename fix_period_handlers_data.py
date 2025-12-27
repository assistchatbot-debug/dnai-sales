#!/usr/bin/env python3
"""Fix period handlers to read data from correct fields"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing data extraction in period handlers...")

# Fix week handler
old_week = """                        for lead in week_leads[:10]:
                            name=lead.get('name','Не указано')
                            phone=lead.get('phone','Не указан')
                            source=lead.get('source_channel','web')
                            msg+=f"• {name} ({phone}) - {source}\\n\""""

new_week = """                        for lead in week_leads[:10]:
                            contact=lead.get('contact_info',{})
                            name=contact.get('name','Не указано')
                            phone=contact.get('phone','Не указан')
                            source=lead.get('source','web')
                            msg+=f"• {name} ({phone}) - {source}\\n\""""

content = content.replace(old_week, new_week)

# Fix month handler
old_month_sources = """                        sources=Counter(l.get('source_channel','web') for l in month_leads)"""
new_month_sources = """                        sources=Counter(l.get('source','web') for l in month_leads)"""

content = content.replace(old_month_sources, new_month_sources)

old_month_leads = """                        for lead in month_leads[:10]:
                            name=lead.get('name','Не указано')
                            phone=lead.get('phone','Не указан')
                            source=lead.get('source_channel','web')
                            msg+=f"• {name} ({phone}) - {source}\\n\""""

new_month_leads = """                        for lead in month_leads[:10]:
                            contact=lead.get('contact_info',{})
                            name=contact.get('name','Не указано')
                            phone=contact.get('phone','Не указан')
                            source=lead.get('source','web')
                            msg+=f"• {name} ({phone}) - {source}\\n\""""

content = content.replace(old_month_leads, new_month_leads)

print("✅ Fixed data extraction")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

