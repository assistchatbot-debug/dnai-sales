#!/usr/bin/env python3
"""Update frontend to use widget_id from URL"""

with open('/var/www/bizdnai/widget-source/standalone.html', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Updating frontend to parse widget_id...")

# Update URL parsing
old_parsing = """        const pathParts = window.location.pathname.split('/');
        const companyId = pathParts[2];
        const channelName = pathParts[3];"""

new_parsing = """        const pathParts = window.location.pathname.split('/');
        const companyId = pathParts[2];
        const widgetId = pathParts[3];  // Now using widget ID instead of channel name"""

content = content.replace(old_parsing, new_parsing)
print("✅ Updated URL parsing to extract widget_id")

# Update loadWidgetConfig function
old_load = """        async function loadWidgetConfig() {
            if (channelName) {
                try {
                    const response = await fetch(`/sales/companies/${companyId}/widgets/${channelName}`);
                    if (response.status === 404) {
                        document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;flex-direction:column;"><h2>❌ Виджет не найден</h2><p>Этот виджет был деактивирован или удалён</p></div>';
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

new_load = """        let widgetData = null;  // Store widget data globally
        
        async function loadWidgetConfig() {
            if (widgetId) {
                try {
                    const response = await fetch(`/sales/companies/${companyId}/widgets/${widgetId}`);
                    if (response.status === 404) {
                        document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;flex-direction:column;"><h2>❌ Виджет не найден</h2><p>Этот виджет был деактивирован или удалён</p></div>';
                        return;
                    }
                    widgetData = await response.json();
                    if (widgetData.greeting_message) {
                        customGreeting = widgetData.greeting_message;
                        console.log('✅ Loaded widget', widgetId, 'for channel', widgetData.channel_name);
                    }
                } catch (e) {
                    console.log('No custom greeting, using default');
                }
            }
        }"""

content = content.replace(old_load, new_load)
print("✅ Updated loadWidgetConfig to use widget_id")

# Update source tracking to use channel_name from API response
old_source = """            source: channelName || 'web'"""
new_source = """            source: (widgetData && widgetData.channel_name) || 'web'"""

content = content.replace(old_source, new_source)
print("✅ Updated source tracking to use channel_name from API")

with open('/var/www/bizdnai/widget-source/standalone.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Frontend updated to use widget_id!")
