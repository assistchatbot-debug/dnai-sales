#!/usr/bin/env python3
"""Fix source sorting in all leads handlers"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing source sorting...")

# Add sorting function for sources
sorting_code = """
                        # Sort sources: named channels first, then widget IDs
                        def sort_sources(item):
                            source = item[0]
                            if source.isdigit():
                                return (1, int(source))  # Widget IDs second
                            return (0, source.lower())  # Named channels first
                        
"""

# Fix general leads statistics (line ~268)
old_general = """                        for source, count in stats_by_source.items():
                            emoji = source_emojis.get(source, '📍')
                            source_name = source_names.get(source, source.capitalize())
                            msg_parts.append(f"{emoji} {source_name}: {count}")"""

new_general = sorting_code + """                        for source, count in sorted(stats_by_source.items(), key=sort_sources):
                            emoji = source_emojis.get(source, '📍')
                            if source.isdigit():
                                emoji = '📸'
                                source_name = f"Instagram #{source}"
                            else:
                                source_name = source_names.get(source, source.capitalize())
                            msg_parts.append(f"{emoji} {source_name}: {count}")"""

content = content.replace(old_general, new_general)
print("✅ Fixed general leads sorting")

# Fix week leads
old_week = """                        msg=f"📊 <b>Лиды за неделю</b>\\n\\nВсего: {len(week_leads)}\\n\\n<b>По источникам:</b>\\n"
                        for source,count in sources.most_common():
                            msg+=f"• {source}: {count}\\n\""""

new_week = """                        msg=f"📊 <b>Лиды за неделю</b>\\n\\nВсего: {len(week_leads)}\\n\\n<b>По источникам:</b>\\n"
                        for source,count in sorted(sources.items(), key=lambda x: (1, int(x[0])) if x[0].isdigit() else (0, x[0].lower())):
                            if source.isdigit():
                                msg+=f"📸 Instagram #{source}: {count}\\n"
                            else:
                                msg+=f"• {source}: {count}\\n\""""

content = content.replace(old_week, new_week)
print("✅ Fixed week leads sorting")

# Fix month leads
old_month = """                        msg=f"📊 <b>Лиды за месяц</b>\\n\\nВсего: {len(month_leads)}\\n\\n<b>По источникам:</b>\\n"
                        for source,count in sources.most_common():
                            msg+=f"• {source}: {count}\\n\""""

new_month = """                        msg=f"📊 <b>Лиды за месяц</b>\\n\\nВсего: {len(month_leads)}\\n\\n<b>По источникам:</b>\\n"
                        for source,count in sorted(sources.items(), key=lambda x: (1, int(x[0])) if x[0].isdigit() else (0, x[0].lower())):
                            if source.isdigit():
                                msg+=f"📸 Instagram #{source}: {count}\\n"
                            else:
                                msg+=f"• {source}: {count}\\n\""""

content = content.replace(old_month, new_month)
print("✅ Fixed month leads sorting")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Сортировка исправлена во всех обработчиках!")
