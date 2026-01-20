#!/usr/bin/env python3
"""Пометка накладных на удаление - XML формат"""
import httpx
from urllib.parse import quote
import time
import sys

ONEC_BASE_URL = "http://2.133.147.210:8081/company_Technology"
ONEC_USERNAME = "odata.user"
ONEC_PASSWORD = "@Technology26"
ODATA_URL = f"{ONEC_BASE_URL}/odata/standard.odata"
DOC_NAME = quote("Document_РеализацияТоваровУслуг")
DATE_FROM = "2026-01-05T00:00:00"

XML_BODY = '''<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
       xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
  <content type="application/xml">
    <m:properties>
      <d:DeletionMark>true</d:DeletionMark>
    </m:properties>
  </content>
</entry>'''

HEADERS = {
    "Content-Type": "application/atom+xml;type=entry",
    "Accept": "application/atom+xml"
}

def main():
    print("=" * 70)
    print("🗑️ ПОМЕТКА НАКЛАДНЫХ НА УДАЛЕНИЕ (XML формат)")
    print("=" * 70)
    
    with httpx.Client(auth=(ONEC_USERNAME, ONEC_PASSWORD), timeout=60) as client:
        
        print(f"🔍 Поиск НЕ помеченных накладных после 05.01.2026...")
        filter_str = f"substringof('Bitrix24', Комментарий) and Date ge datetime'{DATE_FROM}' and DeletionMark eq false"
        url = f"{ODATA_URL}/{DOC_NAME}?$filter={quote(filter_str)}&$select=Ref_Key,Number&$format=json"
        
        response = client.get(url)
        if response.status_code != 200:
            print(f"❌ Ошибка: {response.status_code}")
            return
        
        invoices = response.json().get("value", [])
        total = len(invoices)
        print(f"📋 Найдено: {total} накладных")
        
        if total == 0:
            print("✅ Все уже помечены!")
            return
        
        eta = total * 0.3 / 60
        print(f"⏱️ Ожидаемое время: ~{eta:.0f} минут\n")
        
        success = 0
        failed = 0
        start = time.time()
        
        for i, inv in enumerate(invoices, 1):
            ref_key = inv["Ref_Key"]
            patch_url = f"{ODATA_URL}/{DOC_NAME}(guid'{ref_key}')"
            
            try:
                resp = client.patch(patch_url, content=XML_BODY.encode('utf-8'), headers=HEADERS)
                if resp.status_code == 200:
                    success += 1
                else:
                    failed += 1
            except:
                failed += 1
            
            # Прогресс
            elapsed = time.time() - start
            speed = i / elapsed if elapsed > 0 else 1
            remaining = (total - i) / speed / 60
            pct = i * 100 // total
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            
            sys.stdout.write(f"\r   {bar} {pct:3d}% | {i}/{total} | ✅ {success} | ❌ {failed} | ~{remaining:.0f}м")
            sys.stdout.flush()
            
            time.sleep(0.2)
        
        print(f"\n\n{'='*70}")
        print(f"✅ ГОТОВО!")
        print(f"   Помечено: {success}")
        print(f"   Ошибок: {failed}")
        print(f"   Время: {(time.time()-start)/60:.1f} мин")
        print(f"{'='*70}")
        print("\n💡 Бухгалтер: 1С → Администрирование → Удаление помеченных объектов")

if __name__ == "__main__":
    main()
