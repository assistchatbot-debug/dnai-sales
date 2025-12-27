#!/usr/bin/env python3
"""Fix leads statistics sorting and add period handlers"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing leads statistics...")

# Find the leads statistics display and fix sorting
old_stats_display = """                        for source, count in stats_by_source.items():
                            emoji = source_emojis.get(source, '📍')
                            source_name = source_names.get(source, source.capitalize())
                            msg_parts.append(f"{emoji} {source_name}: {count}")"""

new_stats_display = """                        # Sort: named channels first, then IDs
                        def sort_key(item):
                            source = item[0]
                            # Check if source is numeric (widget ID)
                            try:
                                int(source)
                                return (1, int(source))  # IDs second, sorted numerically
                            except:
                                return (0, source)  # Named channels first, alphabetically
                        
                        for source, count in sorted(stats_by_source.items(), key=sort_key):
                            emoji = source_emojis.get(source, '📍')
                            # For numeric sources, add Instagram emoji
                            if source.isdigit():
                                emoji = '📸'
                                source_name = f"Instagram #{source}"
                            else:
                                source_name = source_names.get(source, source.capitalize())
                            msg_parts.append(f"{emoji} {source_name}: {count}")"""

content = content.replace(old_stats_display, new_stats_display)
print("✅ Fixed statistics sorting")

# Add handlers for period-based leads
period_handlers = """
    # Leads by period
    elif 'лиды за неделю' in text_lower:
        company_id = 1
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{API_BASE_URL}/sales/{company_id}/leads',
                    params={'limit': 100},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        leads = data.get('leads', [])
                        
                        # Filter last 7 days
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
                async with session.get(
                    f'{API_BASE_URL}/sales/{company_id}/leads',
                    params={'limit': 200},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        leads = data.get('leads', [])
                        
                        # Filter last 30 days
                        from datetime import datetime, timedelta
                        month_ago = datetime.now() - timedelta(days=30)
                        month_leads = [l for l in leads if datetime.fromisoformat(l['created_at'].replace('Z', '+00:00')) > month_ago]
                        
                        # Group by source
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
"""

# Insert before channels management
marker = "    # Social media channels management"
content = content.replace(marker, period_handlers + "\n    # Social media channels management")
print("✅ Added period handlers")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Done!")
