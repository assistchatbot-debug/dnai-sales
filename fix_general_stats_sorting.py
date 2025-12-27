#!/usr/bin/env python3
"""Fix sorting in general leads statistics"""

with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing general statistics sorting...")

# Find and replace the sorting logic
old_sorting = """                        for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
                            emoji_name = source_emojis.get(source, f'📍 {source.capitalize()}')
                            stats_text += f"{emoji_name}: {count}\\n\""""

new_sorting = """                        # Sort: named channels first, then widget IDs
                        def sort_key(item):
                            source = item[0]
                            if source.isdigit():
                                return (1, int(source))  # Widget IDs second
                            return (0, source.lower())  # Named channels first
                        
                        for source, count in sorted(by_source.items(), key=sort_key):
                            if source.isdigit():
                                emoji_name = f'📸 Instagram #{source}'
                            else:
                                emoji_name = source_emojis.get(source, f'📍 {source.capitalize()}')
                            stats_text += f"{emoji_name}: {count}\\n\""""

content = content.replace(old_sorting, new_sorting)
print("✅ Fixed general statistics sorting")

with open('bot/handlers.py', 'w', encoding='utf-8') as f:
    f.write(content)

