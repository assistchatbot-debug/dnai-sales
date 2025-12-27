#!/usr/bin/env python3
"""Update leads command to use stats API"""

with open('bot/handlers.py', 'r') as f:
    content = f.read()

print("🔧 Updating leads command...")

# Find the leads command and update to use stats API
old_stats_calc = '''                        # Count sources
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
                            stats_text += f"{emoji_name}: {count}\\n"'''

new_stats_fetch = '''                        # Get ALL leads statistics
                        async with session.get(
                            f'{API_BASE_URL}/sales/{company_id}/leads/stats',
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as stats_resp:
                            stats_data = await stats_resp.json() if stats_resp.status == 200 else {}
                        
                        total = stats_data.get('total', len(leads))
                        by_source = stats_data.get('by_source', {})
                        
                        # Build stats
                        stats_text = "📊 <b>Статистика лидов</b>\\n"
                        stats_text += f"Всего: {total} (все время)\\n\\n"
                        
                        source_emojis = {
                            'telegram': '📱 Telegram',
                            'web': '🌐 Веб-сайт',
                            'instagram': '📸 Instagram',
                            'facebook': '📘 Facebook',
                            'vk': '🔵 ВКонтакте'
                        }
                        
                        for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
                            emoji_name = source_emojis.get(source, f'📍 {source.capitalize()}')
                            stats_text += f"{emoji_name}: {count}\\n"'''

content = content.replace(old_stats_calc, new_stats_fetch)
print("✅ Updated to use stats API")

with open('bot/handlers.py', 'w') as f:
    f.write(content)

print("\n✅ Done!")
