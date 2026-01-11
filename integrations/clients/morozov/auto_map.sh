#!/bin/bash
echo "================================================================================"
echo "  АВТОМАТИЧЕСКОЕ СОПОСТАВЛЕНИЕ ВСЕХ ТОВАРОВ"
echo "================================================================================"

# Получаем ВСЕ товары с пагинацией
curl -s "https://hb-tech.bitrix24.kz/rest/34137/03i76p52if8jjq3a/crm.product.list" \
  -d 'select[]=ID&select[]=NAME&order[ID]=ASC&start=0' > b24_p1.json

curl -s "https://hb-tech.bitrix24.kz/rest/34137/03i76p52if8jjq3a/crm.product.list" \
  -d 'select[]=ID&select[]=NAME&order[ID]=ASC&start=50' > b24_p2.json

# Объединяем результаты
python3 << 'PYEOF'
import json
from difflib import SequenceMatcher
import re

# Загружаем страницы
with open('b24_p1.json') as f:
    p1 = json.load(f).get('result', [])
with open('b24_p2.json') as f:
    p2 = json.load(f).get('result', [])

b24 = p1 + p2
print(f"📦 Загружено {len(b24)} товаров из Bitrix24")

with open('1c_nomenclature.txt', 'r', encoding='utf-8') as f:
    onec = [line.strip() for line in f if line.strip()]
print(f"📋 Загружено {len(onec)} позиций из 1С\n")

def sim(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def code(name):
    for p in [r'RT[\s-]?(\d+)', r'BTH-[\d]+T', r'GS-[\d]+', r'\d{5,}']:
        m = re.search(p, name, re.I)
        if m: return m.group(0).upper().replace(' ', '')
    return '-'.join(name.split()[:3]).upper()[:20]

print('🔄 Сопоставление...\n')
matched = 0
with open('mapping.csv', 'w', encoding='utf-8') as f:
    f.write('bitrix24_id,bitrix24_name,onec_code,onec_name\n')
    for p in b24:
        best, score = None, 0
        for o in onec:
            s = sim(p['NAME'], o)
            if s > score: best, score = o, s
        if score >= 0.6:
            f.write(f'"{p["ID"]}","{p["NAME"]}","{code(best)}","{best}"\n')
            matched += 1
            print(f"{'✅' if score>0.8 else '⚠️'} {p['ID']:>4} {score:.0%} {p['NAME'][:50]}")
        else:
            print(f"❌ {p['ID']:>4} {score:.0%} {p['NAME'][:50]}")

print(f'\n✅ Сопоставлено: {matched}/{len(b24)}\n')
PYEOF

echo "💾 Загрузка в БД..."
tail -n +2 mapping.csv | while IFS=',' read -r id name code onec; do
    id=$(echo $id | tr -d '"'); code=$(echo $code | tr -d '"')
    name=$(echo $name | tr -d '"'); onec=$(echo $onec | tr -d '"')
    curl -s -X POST https://bizdnai.com/morozov/api/mapping/product \
      -H "Content-Type: application/json" \
      -d "{\"bitrix24_product_id\":\"$id\",\"bitrix24_product_name\":\"$name\",\"onec_product_code\":\"$code\",\"onec_product_name\":\"$onec\"}" \
      >/dev/null && echo "✅ $id → $code"
done

echo ""
echo "✅ ГОТОВО! Проверить: curl https://bizdnai.com/morozov/api/mapping/products"
