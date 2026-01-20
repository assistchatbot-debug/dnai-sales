#!/usr/bin/env python3
import os, shutil
from datetime import datetime
BASE_DIR = "/root/dnai-sales/integrations/clients/morozov"
FILES = {"onec_client": f"{BASE_DIR}/onec_client.py", "config": f"{BASE_DIR}/config.py", "server": f"{BASE_DIR}/server.py"}
def create_backups():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"📦 Создание бэкапов (timestamp: {timestamp})...")
    for name, path in FILES.items():
        shutil.copy2(path, f"{path}.backup_{timestamp}")
        print(f"   ✅ {name}")
    return timestamp
def patch_onec_client():
    print("\n📝 Патч onec_client.py...")
    with open(FILES["onec_client"], 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_function = '''
    async def find_invoice_by_deal_id(self, deal_id: str) -> Optional[str]:
        """Найти накладную по ID сделки в комментарии 1С"""
        try:
            from urllib.parse import quote
            search_text = f"Bitrix24 сделка {deal_id}:"
            filter_str = f"substringof('{search_text}', Комментарий)"
            url = f"{self.odata_url}/Document_%D0%A0%D0%B5%D0%B0%D0%BB%D0%B8%D0%B7%D0%B0%D1%86%D0%B8%D1%8F%D0%A2%D0%BE%D0%B2%D0%B0%D1%80%D0%BE%D0%B2%D0%A3%D1%81%D0%BB%D1%83%D0%B3?$filter={quote(filter_str)}&$select=Number&$top=1&$format=json"
            response = await self.client.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("value"):
                    invoice_number = data["value"][0].get("Number")
                    logger.info(f"✅ Найдена накладная {invoice_number} для сделки {deal_id}")
                    return invoice_number
            return None
        except Exception as e:
            logger.error(f"Ошибка поиска накладной: {e}")
            return None
'''
    insert_index = None
    for i, line in enumerate(lines):
        if 'self.client = httpx.AsyncClient' in line:
            insert_index = i + 1
            break
    if insert_index:
        lines.insert(insert_index, new_function)
        with open(FILES["onec_client"], 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"   ✅ Функция добавлена")
        return True
    print("   ❌ Точка вставки не найдена!")
    return False
def patch_config():
    print("\n📝 Патч config.py...")
    with open(FILES["config"], 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_method = '''
    def is_integration_enabled(self) -> bool:
        """Проверка integration_enabled в реальном времени из БД"""
        try:
            import httpx
            response = httpx.get(f'{self.api_base_url}/sales/companies/all', timeout=3.0)
            if response.status_code == 200:
                companies = response.json()
                company = next((c for c in companies if c['id'] == self.company_id), None)
                if company:
                    enabled = company.get('integration_enabled', False)
                    logger.debug(f"integration_enabled = {enabled}")
                    return enabled
        except Exception as e:
            logger.error(f"Ошибка проверки integration_enabled: {e}")
            return False
        return False
'''
    insert_index = None
    for i, line in enumerate(lines):
        if 'settings = Settings()' in line:
            insert_index = i
            break
    if insert_index:
        lines.insert(insert_index, new_method)
        with open(FILES["config"], 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"   ✅ Метод добавлен")
        return True
    print("   ❌ Точка вставки не найдена!")
    return False
def patch_server():
    print("\n📝 Патч server.py...")
    with open(FILES["server"], 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    checks = '''
        # ЗАЩИТА #1: Проверка integration_enabled
        if not settings.is_integration_enabled():
            logger.info(f"Integration disabled, skipping deal {deal_id}")
            return
        
        # ЗАЩИТА #2: Проверка дубликата
        existing_invoice = await onec.find_invoice_by_deal_id(deal_id)
        if existing_invoice:
            logger.info(f"✅ Invoice {existing_invoice} already exists for deal {deal_id}, skipping")
            return
'''
    insert_index = None
    for i, line in enumerate(lines):
        if 'logger.info(f"Processing deal {deal_id} for 1C")' in line:
            insert_index = i + 1
            break
    if insert_index:
        lines.insert(insert_index, checks)
        with open(FILES["server"], 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"   ✅ Проверки добавлены")
        return True
    print("   ❌ Точка вставки не найдена!")
    return False
def verify_syntax():
    print("\n🔍 Проверка синтаксиса...")
    import subprocess
    for name, path in FILES.items():
        result = subprocess.run(["python3", "-m", "py_compile", path], capture_output=True)
        if result.returncode == 0:
            print(f"   ✅ {name}")
        else:
            print(f"   ❌ {name}")
            return False
    return True
timestamp = create_backups()
if not (patch_onec_client() and patch_config() and patch_server() and verify_syntax()):
    print("\n❌ Ошибка! Откат...")
    for name, path in FILES.items():
        shutil.copy2(f"{path}.backup_{timestamp}", path)
    exit(1)
print("\n" + "="*60)
print("✅ ПАТЧИ ПРИМЕНЕНЫ УСПЕШНО!")
print("="*60)
print(f"\n📋 Бэкапы: *backup_{timestamp}")
