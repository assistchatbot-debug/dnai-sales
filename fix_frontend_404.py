#!/usr/bin/env python3
with open('/var/www/bizdnai/widget-source/standalone.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = """        async function loadWidgetConfig() {
            if (channelName) {
                try {
                    const response = await fetch(`/sales/companies/${companyId}/widgets/${channelName}`);
                    const data = await response.json();
                    if (data.greeting_message) {
                        customGreeting = data.greeting_message;
                        console.log('✅ Loaded custom greeting for', channelName);
                    }
                } catch (e) {
                    console.log('No custom greeting, using default');
                }
            }
        }"""

new_code = """        async function loadWidgetConfig() {
            if (channelName) {
                try {
                    const response = await fetch(`/sales/companies/${companyId}/widgets/${channelName}`);
                    if (response.status === 404) {
                        document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;"><h2>❌ Виджет не найден или деактивирован</h2></div>';
                        return;
                    }
                    const data = await response.json();
                    if (data.greeting_message) {
                        customGreeting = data.greeting_message;
                        console.log('✅ Loaded custom greeting for', channelName);
                    }
                } catch (e) {
                    console.log('No custom greeting, using default');
                }
            }
        }"""

content = content.replace(old_code, new_code)

with open('/var/www/bizdnai/widget-source/standalone.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Frontend обновлён - теперь показывает ошибку при 404")
