#!/usr/bin/env python3
"""Remove uniqueness check from widget creation"""

with open('backend/routers/sales_agent.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("🔧 Removing uniqueness check...")

# Find and remove line 849
new_lines = []
for i, line in enumerate(lines, 1):
    if i == 849 and 'Widget.*exists' in line:
        print(f"✅ Removed line {i}: {line.strip()}")
        continue  # Skip this line
    new_lines.append(line)

with open('backend/routers/sales_agent.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ Uniqueness check removed!")
