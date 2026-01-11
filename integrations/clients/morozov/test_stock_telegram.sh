#!/bin/bash

# Получаем остатки из 1С
echo "Получаем остатки из 1С..."

STOCK=$(curl -s -u "odata.user:odata12345#" \
  "http://2.133.147.210:8081/company-Technology_support/odata/standard.odata/Catalog_%D0%9D%D0%BE%D0%BC%D0%B5%D0%BD%D0%BA%D0%BB%D0%B0%D1%82%D1%83%D1%80%D0%B0?\$top=10&\$filter=IsFolder eq false" | \
  python3 -c "
import xml.etree.ElementTree as ET
import sys

xml_data = sys.stdin.read()
root = ET.fromstring(xml_data)

ns = {
    'atom': 'http://www.w3.org/2005/Atom',
    'd': 'http://schemas.microsoft.com/ado/2007/08/dataservices',
    'm': 'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata'
}

result = '📦 *НОМЕНКЛАТУРА 1С (тест)*\n\n'
for entry in root.findall('.//atom:entry', ns):
    props = entry.find('.//m:properties', ns)
    if props is not None:
        name = props.find('d:Description', ns)
        code = props.find('d:Code', ns)
        if name is not None and name.text:
            result += f'• {name.text}\n'
print(result[:4000])
")

# Отправляем в Telegram
TELEGRAM_TOKEN="7585875409:AAFkToS4d4w2khPNVXIIYK3-_vHFCuhOhT0"
CHAT_ID="-4679037382"

curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
  -d "chat_id=${CHAT_ID}" \
  -d "text=${STOCK}" \
  -d "parse_mode=Markdown"

echo "✅ Отправлено в Telegram!"
