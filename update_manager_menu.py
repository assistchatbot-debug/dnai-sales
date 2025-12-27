#!/usr/bin/env python3
"""Replace Widget button with Leads button in manager menu"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Updating manager menu...")

# Find and replace menu buttons
old_menu = """            keyboard = [
                [KeyboardButton(text="📢 Каналы")],
                [KeyboardButton(text="🌐 Виджет")],
                [KeyboardButton(text="📊 Лиды")],
                [KeyboardButton(text="🏠 Меню")]
            ]"""

new_menu = """            keyboard = [
                [KeyboardButton(text="📢 Каналы")],
                [KeyboardButton(text="📊 Лиды за неделю"), KeyboardButton(text="📊 Лиды за месяц")],
                [KeyboardButton(text="🏠 Меню")]
            ]"""

content = content.replace(old_menu, new_menu)
print("✅ Updated menu buttons")

# Remove old widget handler
import re
old_widget_handler = r"    # Widget management.*?await message\.answer\(\"❌ Ошибка обработки команды\"\)\s+"
content = re.sub(old_widget_handler, '', content, flags=re.DOTALL)
print("✅ Removed old widget handler")

# Add new leads handlers
new_handlers = """
    # Leads by period
    elif 'лиды за неделю' in text_lower or 'leads week' in text_lower:
        company_id = 1
        try:
            async with aiohttp.ClientSession() as session:
                # Get leads from last 7 days
                async with session.get(
                    f'{API_BASE_URL}/sales/{company_id}/leads',
                    params={'limit': 50},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        leads = data.get('leads', [])
                        
                        # Filter last 7 days
                        from datetime import datetime, timedelta
                        week_ago = datetime.now() - timedelta(days=7)
                        week_leads = [l for l in leads if datetime.fromisoformat(l['created_at'].replace('Z', '+00:00')) > week_ago]
                        
                        msg = f"📊 <b>Лиды за неделю</b>\\n\\nВсего: {len(week_leads)}\\n\\n"
                        
                        for lead in week_leads[:10]:
                            name = lead.get('name', 'Не указано')
                            phone = lead.get('phone', 'Не указан')
                            source = lead.get('source_channel', 'web')
                            status = lead.get('status', 'new')
                            msg += f"• {name} ({phone})\\n  Источник: {source}, Статус: {status}\\n\\n"
                        
                        await message.answer(msg, parse_mode='HTML')
                    else:
                        await message.answer("⚠️ Не удалось получить лиды")
        except Exception as e:
            logging.error(f"Leads week error: {e}")
            await message.answer("❌ Ошибка получения лидов")
    
    elif 'лиды за месяц' in text_lower or 'leads month' in text_lower:
        company_id = 1
        try:
            async with aiohttp.ClientSession() as session:
                # Get leads from last 30 days
                async with session.get(
                    f'{API_BASE_URL}/sales/{company_id}/leads',
                    params={'limit': 100},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        leads = data.get('leads', [])
                        
                        # Filter last 30 days
                        from datetime import datetime, timedelta
                        month_ago = datetime.now() - timedelta(days=30)
                        month_leads = [l for l in leads if datetime.fromisoformat(l['created_at'].replace('Z', '+00:00')) > month_ago]
                        
                        msg = f"📊 <b>Лиды за месяц</b>\\n\\nВсего: {len(month_leads)}\\n\\n"
                        
                        # Group by source
                        from collections import Counter
                        sources = Counter(l.get('source_channel', 'web') for l in month_leads)
                        
                        msg += "<b>По источникам:</b>\\n"
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
"""

# Find where to insert (after the existing лиды handler)
marker = "    # Social media channels management"
content = content.replace(marker, new_handlers + "\n    # Social media channels management")
print("✅ Added leads period handlers")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Manager menu updated!")
