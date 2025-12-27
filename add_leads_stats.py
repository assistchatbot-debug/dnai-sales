#!/usr/bin/env python3
"""Add source statistics to leads command"""

with open('bot/handlers.py', 'r') as f:
    content = f.read()

print("🔧 Adding source statistics...")

# Find and replace the leads display section
old_leads_block = '''                        if not leads:
                            await message.answer("📊 Лидов пока нет")
                            return
                        
                        leads_text = ["📊 <b>Последние лиды:</b>\\n"]
                        for i, lead in enumerate(leads[:5], 1):  # Show last 5'''

new_leads_block = '''                        if not leads:
                            await message.answer("📊 Лидов пока нет")
                            return
                        
                        # Count sources
                        from collections import Counter
                        source_counts = Counter(lead.get('source', 'unknown') for lead in leads)
                        
                        # Build stats
                        stats_text = "📊 <b>Статистика лидов</b>\\n"
                        stats_text += f"Всего: {len(leads)}\\n\\n"
                        
                        source_emojis = {
                            'telegram': '📱 Telegram',
                            'web': '🌐 Веб-сайт',
                            'instagram': '📸 Instagram',
                            'facebook': '📘 Facebook',
                            'vk': '🔵 ВКонтакте'
                        }
                        
                        for source, count in source_counts.most_common():
                            emoji_name = source_emojis.get(source, f'📍 {source.capitalize()}')
                            stats_text += f"{emoji_name}: {count}\\n"
                        
                        leads_text = [stats_text + "\\n<b>Последние 5 лидов:</b>\\n"]
                        for i, lead in enumerate(leads[:5], 1):  # Show last 5'''

content = content.replace(old_leads_block, new_leads_block)
print("✅ Added source statistics")

with open('bot/handlers.py', 'w') as f:
    f.write(content)

print("\n✅ Done!")
