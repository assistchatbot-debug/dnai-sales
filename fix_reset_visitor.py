with open('/var/www/bizdnai/widget-source/standalone.html', 'r') as f:
    content = f.read()

# 1. Изменить const на let чтобы можно было обновить
content = content.replace(
    "const visitorId =",
    "let visitorId ="
)

# 2. В resetChat обновить visitorId
old_reset = """function resetChat() { 
            const newId = 'v_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('bizdnaii_vid', newId);
            sessionId = null; 
            messages.innerHTML = ''; 
            addMsg(greetings[langSelect.value] || greetings.ru, false); 
        }"""

new_reset = """function resetChat() { 
            visitorId = 'v_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('bizdnaii_vid', visitorId);
            sessionId = null; 
            messages.innerHTML = ''; 
            addMsg(greetings[langSelect.value] || greetings.ru, false); 
        }"""

content = content.replace(old_reset, new_reset)

with open('/var/www/bizdnai/widget-source/standalone.html', 'w') as f:
    f.write(content)
with open('frontend/widget/standalone.html', 'w') as f:
    f.write(content)
    
print("✅ resetChat теперь создает НОВОГО лида")
