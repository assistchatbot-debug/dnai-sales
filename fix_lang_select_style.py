#!/usr/bin/env python3
"""Fix language selector styling"""

with open('frontend/widget/standalone.html', 'r') as f:
    content = f.read()

print("🔧 Fixing language selector...")

# Find and update select styles
old_select = '<select id="langSelect" class="bg-white/10 text-white px-2 py-1 rounded border border-white/20">'
new_select = '<select id="langSelect" class="bg-gray-800 text-white px-2 py-1 rounded border border-white/20">'

content = content.replace(old_select, new_select)
print("✅ Fixed select background color")

with open('frontend/widget/standalone.html', 'w') as f:
    f.write(content)
