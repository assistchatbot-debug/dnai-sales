#!/usr/bin/env python3
with open('/var/www/bizdnai/widget-source/standalone.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Simplify error message
old_msg = """document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;flex-direction:column;"><h2>❌ Виджет не найден</h2><p>Используйте новый URL формата: /w/company_id/widget_id</p></div>';"""

new_msg = """document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;"><h2>❌ Виджет не найден</h2></div>';"""

content = content.replace(old_msg, new_msg)

with open('/var/www/bizdnai/widget-source/standalone.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Сообщение упрощено")
