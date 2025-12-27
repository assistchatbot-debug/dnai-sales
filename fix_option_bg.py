#!/usr/bin/env python3
"""Add CSS for option background"""

with open('/var/www/bizdnai/widget-source/standalone.html', 'r') as f:
    content = f.read()

print("🔧 Adding option styles...")

# Find the style section and add option CSS
old_style_end = "        .sticky-logo { position: sticky; top: 20px; z-index: 50; background: rgba(99, 102, 241, 0.8); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }"

new_style_end = """        .sticky-logo { position: sticky; top: 20px; z-index: 50; background: rgba(99, 102, 241, 0.8); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }
        select option { background-color: #1f2937; color: white; }
        select option:hover { background-color: #374151; }"""

content = content.replace(old_style_end, new_style_end)
print("✅ Added option background styles")

with open('/var/www/bizdnai/widget-source/standalone.html', 'w') as f:
    f.write(content)

# Также обновить исходник
with open('frontend/widget/standalone.html', 'w') as f:
    f.write(content)

print("✅ Обновлены оба файла")
