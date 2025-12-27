with open('/var/www/bizdnai/widget-source/standalone.html', 'r') as f:
    content = f.read()

# Найти где парсится channelName и добавить как source
# В sendMsg добавить source: channelName

# 1. Найти sendMsg и добавить source
old_send = "body: JSON.stringify({ message: text, session_id: sessionId, user_id: visitorId, language: langMap[langSelect.value] || 'ru' })"

new_send = "body: JSON.stringify({ message: text, session_id: sessionId, user_id: visitorId, language: langMap[langSelect.value] || 'ru', source: channelName || 'web' })"

content = content.replace(old_send, new_send)

# 2. В voice тоже добавить source
old_voice = "formData.append('language', langMap[langSelect.value] || 'ru');"

new_voice = "formData.append('language', langMap[langSelect.value] || 'ru'); formData.append('source', channelName || 'web');"

content = content.replace(old_voice, new_voice)

with open('/var/www/bizdnai/widget-source/standalone.html', 'w') as f:
    f.write(content)
with open('frontend/widget/standalone.html', 'w') as f:
    f.write(content)
    
print("✅ Source tracking добавлен!")
