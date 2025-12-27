#!/usr/bin/env python3
"""Add handlers for leads by period"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("🔧 Adding period handlers...")

# Find line with "Social media channels management" comment
insert_line = None
for i, line in enumerate(lines):
    if '# Social media channels management' in line:
        insert_line = i
        break

if insert_line is None:
    print("❌ Marker not found")
    exit(1)

# Create new handlers
new_handlers = '''    # Leads by period
    elif 'лиды за неделю' in text_lower:
        company_id = 1
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/sales/{company_id}/leads',params={'limit': 100},timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        leads = data.get('leads', [])
                        from datetime import datetime, timedelta
                        week_ago = datetime.now() - timedelta(days=7)
                        week_leads = [l for l in leads if datetime.fromisoformat(l['created_at'].replace('Z', '+00:00')) > week_ago]
                        msg = f"📊 <b>Лиды за неделю</b>\\n\\nВсего: {len(week_leads)}\\n\\n<b>Последние 10:</b>\\n"
                        for lead in week_leads[:10]:
                            name = lead.get('name', 'Не указано')
                            phone = lead.get('phone', 'Не указан')
                            source = lead.get('source_channel', 'web')
                            msg += f"• {name} ({phone}) - {source}\\n"
                        await message.answer(msg, parse_mode='HTML')
                    else:
                        await message.answer("⚠️ Не удалось получить лиды")
        except Exception as e:
            logging.error(f"Leads week error: {e}")
            await message.answer("❌ Ошибка получения лидов")
    elif 'лиды за месяц' in text_lower:
        company_id = 1
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API_BASE_URL}/sales/{company_id}/leads',params={'limit': 200},timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        leads = data.get('leads', [])
                        from datetime import datetime, timedelta
                        month_ago = datetime.now() - timedelta(days=30)
                        month_leads = [l for l in leads if datetime.fromisoformat(l['created_at'].replace('Z', '+00:00')) > month_ago]
                        from collections import Counter
                        sources = Counter(l.get('source_channel', 'web') for l in month_leads)
                        msg = f"📊 <b>Лиды за месяц</b>\\n\\nВсего: {len(month_leads)}\\n\\n<b>По источникам:</b>\\n"
                        for source, count in sources.most_common():
                            msg += f"• {source}: {count}\\n"
                        msg += "\\n<b>Последние 10:</b>\\n"
                        for lead in month_leads[:10]:
                            name = lead.get('name', 'Не указано')
                            phone = lead.get('phone', 'Не указан')
                            source = lead.get('source_channel', 'web')
                            msg += f"• {name} ({phone}) - {source}\\n"
                        await message.answer(msg, parse_mode='HTML')
                    else:
                        await message.answer("⚠️ Не удалось получить лиды")
        except Exception as e:
            logging.error(f"Leads month error: {e}")
            await message.answer("❌ Ошибка получения лидов")
    
'''

# Insert before the marker
lines.insert(insert_line, new_handlers)

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"✅ Inserted handlers before line {insert_line}")
