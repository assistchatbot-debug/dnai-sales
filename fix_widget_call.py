#!/usr/bin/env python3
"""Add missing function call"""

with open('frontend/widget/standalone.html', 'r') as f:
    content = f.read()

print("🔧 Adding function call...")

# Find loadWidgetConfig function and add resetChat() + call
old_func = '''        async function loadWidgetConfig() {
            if (channelName) {
                try {
                    const response = await fetch(`${API}/companies/${companyId}/widgets/${channelName}`);
                    const data = await response.json();
                    if (data.greeting_message) {
                        customGreeting = data.greeting_message;
                        console.log('✅ Loaded custom greeting for', channelName);
                    }
                } catch (e) {
                    console.log('No custom greeting, using default');
                }
            }
            // Initialize chat AFTER loading greeting
        }'''

new_func = '''        async function loadWidgetConfig() {
            if (channelName) {
                try {
                    const response = await fetch(`${API}/companies/${companyId}/widgets/${channelName}`);
                    const data = await response.json();
                    if (data.greeting_message) {
                        customGreeting = data.greeting_message;
                        console.log('✅ Loaded custom greeting for', channelName);
                    }
                } catch (e) {
                    console.log('No custom greeting, using default');
                }
            }
            // Initialize chat AFTER loading greeting
            resetChat();
        }
        
        // Call the function
        loadWidgetConfig();'''

content = content.replace(old_func, new_func)
print("✅ Added resetChat() call and function invocation")

with open('frontend/widget/standalone.html', 'w') as f:
    f.write(content)

print("\n✅ Done!")
