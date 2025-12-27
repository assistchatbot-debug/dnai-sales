with open('/var/www/bizdnai/widget-source/standalone.html', 'r') as f:
    content = f.read()

# 1. Добавить visitorId с localStorage (как в React виджете)
old_vars = "        let sessionId = null;"
new_vars = """        let sessionId = null;
        const visitorId = localStorage.getItem('bizdnaii_vid') || 'v_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('bizdnaii_vid', visitorId);"""

content = content.replace(old_vars, new_vars)

# 2. Заменить Date.now() на visitorId
content = content.replace("'standalone_' + Date.now()", "visitorId")

# 3. В resetChat создавать НОВЫЙ visitorId (как в React)
old_reset = "function resetChat() { sessionId = null; messages.innerHTML = ''; addMsg(greetings[langSelect.value] || greetings.ru, false); }"
new_reset = """function resetChat() { 
            const newId = 'v_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('bizdnaii_vid', newId);
            sessionId = null; 
            messages.innerHTML = ''; 
            addMsg(greetings[langSelect.value] || greetings.ru, false); 
        }"""

content = content.replace(old_reset, new_reset)

with open('/var/www/bizdnai/widget-source/standalone.html', 'w') as f:
    f.write(content)
with open('frontend/widget/standalone.html', 'w') as f:
    f.write(content)
    
print("✅ visitorId исправлен - теперь как в рабочем виджете")
