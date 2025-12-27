#!/usr/bin/env python3
with open('/var/www/bizdnai/widget-source/standalone.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Update to handle 405 same as 404
old_check = """                    if (response.status === 404) {
                        document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;flex-direction:column;"><h2>❌ Виджет не найден</h2><p>Этот виджет был деактивирован или удалён</p></div>';
                        return;
                    }"""

new_check = """                    if (response.status === 404 || response.status === 405) {
                        document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;flex-direction:column;"><h2>❌ Виджет не найден</h2><p>Используйте новый URL формата: /w/company_id/widget_id</p></div>';
                        return;
                    }"""

content = content.replace(old_check, new_check)

with open('/var/www/bizdnai/widget-source/standalone.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Frontend обновлён для обработки 405")
