#!/usr/bin/env python3
"""Fix async loading of custom greeting"""

with open('frontend/widget/standalone.html', 'r') as f:
    content = f.read()

print("🔧 Fixing async greeting load...")

# Find and wrap widget load in async function with await
old_load = '''        // Load widget-specific greeting if channel_name is provided
        if (channelName) {
            fetch(`${API}/companies/${companyId}/widgets/${channelName}`)
                .then(r => r.json())
                .then(data => {
                    if (data.greeting_message) {
                        customGreeting = data.greeting_message;
                        console.log('✅ Loaded custom greeting for', channelName);
                    }
                })
                .catch(e => console.log('No custom greeting, using default'));
        }'''

new_load = '''        // Load widget-specific greeting and initialize
        async function loadWidgetConfig() {
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
        loadWidgetConfig();'''

content = content.replace(old_load, new_load)
print("✅ Made greeting load synchronous")

# Remove initial resetChat() call if it exists at the end of the script
# Find where resetChat() is called (usually at the end)
lines = content.split('\n')
new_lines = []
skip_reset = False

for i, line in enumerate(lines):
    # Skip standalone resetChat() calls that are not in function definition
    if 'resetChat();' in line and 'function resetChat()' not in line and 'loadWidgetConfig' not in line:
        # Check if this is the initial call (not inside a function)
        context = '\n'.join(lines[max(0, i-3):i+1])
        if 'async function' not in context and 'function ' not in context:
            print(f"✅ Removed standalone resetChat() at line {i+1}")
            continue
    new_lines.append(line)

content = '\n'.join(new_lines)

with open('frontend/widget/standalone.html', 'w') as f:
    f.write(content)

print("\n✅ Frontend fixed!")
