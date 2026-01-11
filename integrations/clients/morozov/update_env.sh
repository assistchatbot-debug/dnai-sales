#!/bin/bash

# Резервная копия
cp .env .env.backup

# Обновляем настройки 1С
python3 << 'PYEOF'
with open('.env', 'r') as f:
    content = f.read()

# Заменяем настройки 1С
replacements = {
    'ONEC_BASE_URL=http://2.133.147.210/company-TOO_HB': 'ONEC_BASE_URL=http://2.133.147.210:8081/company-Technology_support',
    'ONEC_PASSWORD=ПАРОЛЬ_ЗАВТРА': 'ONEC_PASSWORD=Администратор'
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open('.env', 'w') as f:
    f.write(content)

print("✅ .env обновлён!")
PYEOF
