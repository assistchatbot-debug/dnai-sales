with open('/var/www/bizdnai/widget-source/standalone.html', 'r') as f:
    content = f.read()

# Заменить одностроную версию resetChat
old_reset = "function resetChat() { sessionId = null; messages.innerHTML = ''; addMsg(customGreeting || defaultGreetings[langSelect.value] || defaultGreetings.ru, false); }"

new_reset = "function resetChat() { visitorId = 'v_' + Math.random().toString(36).substr(2, 9); localStorage.setItem('bizdnaii_vid', visitorId); sessionId = null; messages.innerHTML = ''; addMsg(customGreeting || defaultGreetings[langSelect.value] || defaultGreetings.ru, false); }"

content = content.replace(old_reset, new_reset)

with open('/var/www/bizdnai/widget-source/standalone.html', 'w') as f:
    f.write(content)
with open('frontend/widget/standalone.html', 'w') as f:
    f.write(content)
    
print("✅ resetChat обновлен!")
