## BizDNAi Integrations - Полная документация

# 🎯 Назначение
Универсальная мультиклиентская система интеграции CRM систем (Bitrix24, KOMMO) с 1С:Бухгалтерия через OData.

📊 Архитектура системы
┌─────────────────────────────────────────────────────────────┐
│                    BizDNAi Platform                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                │
│  │   Bitrix24   │────────▶│   Webhook    │                │
│  │     CRM      │         │   Endpoint   │                │
│  └──────────────┘         └──────┬───────┘                │
│                                   │                         │
│  ┌──────────────┐                │                         │
│  │   KOMMO      │────────────────┘                         │
│  │     CRM      │         FastAPI Server                   │
│  └──────────────┘         (port 8008)                      │
│                                   │                         │
│                          ┌────────▼────────┐               │
│                          │  Middleware     │               │
│                          │  Integration    │               │
│                          │  Logic          │               │
│                          └────────┬────────┘               │
│                                   │                         │
│                          ┌────────▼────────┐               │
│                          │   1С OData      │               │
│                          │   Client        │               │
│                          └────────┬────────┘               │
│                                   │                         │
└───────────────────────────────────┼─────────────────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │  1С:Бухгалтерия   │
                          │  OData Endpoint   │
                          └───────────────────┘

Telegram Bot (Polling) ──▶ Analytics Service ──▶ CRM API

📁 Структура проекта

/root/dnai-sales/
└── integrations/
    ├── shared/                         # Общие компоненты
    │   ├── analytics_service.py        # Аналитика продаж
    │   ├── README.md                   # Эта документация
    │   └── __init__.py
    │
    └── clients/                        # Клиентские интеграции
        ├── morozov/                    # Клиент 1: Bitrix24 ↔ 1С
        │   ├── .env                    # ❌ НЕ в Git!
        │   ├── docker-compose.yml
        │   ├── server.py               # FastAPI webhook
        │   ├── bitrix24_client.py      # Bitrix24 API
        │   ├── onec_client.py          # 1С OData
        │   ├── analytics_bot.py        # Telegram бот
        │   └── logs/
        │
        └── kommo/                      # Клиент 2 (будущий)

⚙️ Переменные окружения (.env)

Bitrix24

BITRIX24_WEBHOOK_URL=https://company.bitrix24.ru/rest/1/xxxxx/

Получение: Приложения → Вебхуки → Входящий вебхук

Использование: bitrix24_client.py - все API запросы

1С OData

ONEC_BASE_URL=http://2.133.147.210:8081/company_Technology

ONEC_USERNAME=odata.user

ONEC_PASSWORD=@Technology26

Формат: http://IP:PORT/база_данных

Использование: onec_client.py - накладные, остатки

PostgreSQL

DATABASE_URL=postgresql+asyncpg://user:pass@host/db

Использование: Хранение маппинга, логов

Telegram

TELEGRAM_BOT_TOKEN=7622964199:AAF_xxxxx

TELEGRAM_CHAT_ID=803934700

Получение: @BotFather и @userinfobot
Использование: Уведомления, аналитика

🚀 Быстрый старт нового клиента

Шаг 1: Создание структуры
cd /root/dnai-sales/integrations/clients
mkdir новый_клиент && cd новый_клиент

Шаг 2: Копирование шаблона
cp -r ../morozov/*.py ./
cp ../morozov/docker-compose.yml ./
cp ../morozov/Dockerfile ./
cp ../morozov/requirements.txt ./

Шаг 3: Создание .env
cat > .env << 'EOF'
BITRIX24_WEBHOOK_URL=https://новый-клиент.bitrix24.ru/rest/1/xxxxx/
ONEC_BASE_URL=http://1c-server:8080/база
ONEC_USERNAME=user
ONEC_PASSWORD=pass
DATABASE_URL=postgresql+asyncpg://новый:pass@localhost/новый_db
TELEGRAM_BOT_TOKEN=123:ABC
TELEGRAM_CHAT_ID=123456
EOF

Шаг 4: Обновление docker-compose.yml
Изменить:

container_name: новый_клиент_middleware
ports: - "8009:8009" (уникальный порт!)
command: uvicorn server:app --host 0.0.0.0 --port 8009
Шаг 5: Запуск
mkdir logs
docker-compose up -d --build
nohup python3 analytics_bot.py > logs/analytics_bot.log 2>&1 &
📱 Telegram бот аналитики
Меню
📈 Статус - Статус системы
💰 День - Продажи за сегодня
💰 Неделя - Продажи за 7 дней
💰 Месяц - Продажи за 30 дней
🏆 Товары недели - Топ-5 (7 дней)
🏆 Товары месяца - Топ-5 (30 дней)
Пример отчёта
💰 Продажи за месяц
📅 2025-12-12 — 2026-01-11
📊 Общая сумма: 2,807,520 ₸
📦 Сделок: 14
👥 Менеджеры:
1. Ольга — 1,935,482 ₸ (10 сд.)
2. Елена — 872,037 ₸ (4 сд.)
🔄 Процесс интеграции
Создание накладной в 1С
Bitrix24: Сделка → "Won"
    ↓
Webhook → /webhook/bitrix24/deal
    ↓
server.py: process_deal_to_1c()
    ↓
bitrix24_client: get_deal()
    ↓
onec_client: create_order()
    ↓
1С OData: POST Document_РеализацияТоваровУслуг
    ↓
Bitrix24: Комментарий "Накладная №37 создана"
    ↓
Telegram: Уведомление менеджеру
Синхронизация остатков
Cron (00:00)
    ↓
sync_service: get_stock_balances()
    ↓
bitrix24_client: update_product_quantity()
    ↓
Telegram: Отчёт синхронизации

🔌 KOMMO CRM Integration
Отличия от Bitrix24
Параметр	Bitrix24	KOMMO
Авторизация	Webhook	OAuth 2.0
API	{webhook}/{method}	https://{subdomain}.kommo.com/api/v4/
Сделки	crm.deal.*	/api/v4/leads
Лимиты	Нет	7 req/sec
Требования от клиента
Subdomain (например: mycompany)
Client ID
Client Secret
Refresh Token (через OAuth)
Процесс авторизации KOMMO

# Шаг 1: Получить код авторизации
https://www.amocrm.ru/oauth?client_id=ID&state=random&mode=post_message

# Шаг 2: Обменять на токены
curl -X POST https://mycompany.kommo.com/oauth2/access_token \
  -d "client_id=ID" \
  -d "client_secret=SECRET" \
  -d "grant_type=authorization_code" \
  -d "code=CODE" \
  -d "redirect_uri=https://example.com"

# Сохранить refresh_token в .env!
.env для KOMMO
KOMMO_SUBDOMAIN=mycompany
KOMMO_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
KOMMO_CLIENT_SECRET=xxxxxxxxxx
KOMMO_REFRESH_TOKEN=def502000xxxxx
kommo_client.py (структура)
class KommoClient:
    def __init__(self):
        self.base_url = f"https://{settings.kommo_subdomain}.kommo.com/api/v4"
        self.access_token = None
    
    async def _refresh_token(self):
        # POST /oauth2/access_token
        # grant_type=refresh_token
        pass
    
    async def get_lead(self, lead_id: int):
        return await self._call("GET", f"/leads/{lead_id}")
    
    async def get_won_leads(self, date_from, date_to):
        return await self._call("GET", "/leads", params={
            "filter[status_id]": 142,  # Успешно
            "filter[closed_at][from]": date_from
        })
Обработка лимитов KOMMO
async def _call(self, method, endpoint, **kwargs):
    response = await self.client.request(method, url, **kwargs)
    if response.status_code == 429:
        await asyncio.sleep(1)  # Retry через 1 сек
        return await self._call(method, endpoint, **kwargs)
    return response.json()

🗄️ База данных
Таблицы PostgreSQL
-- Логи синхронизации
CREATE TABLE bitrix_1c_sync_log (
    id SERIAL PRIMARY KEY,
    sync_type VARCHAR(50),
    status VARCHAR(20),
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
-- Снимки остатков
CREATE TABLE bitrix_1c_stock_snapshot (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(100),
    quantity DECIMAL(10,2),
    snapshot_date DATE
);
-- Маппинг товаров
CREATE TABLE bitrix_1c_product_mapping (
    id SERIAL PRIMARY KEY,
    bitrix24_product_id VARCHAR(100),
    onec_product_code VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
🛠 Troubleshooting
Docker не запускается
docker logs bitrix_1c_middleware
docker-compose down && docker-compose up -d --build
Telegram бот не отвечает
ps aux | grep analytics_bot
tail -50 logs/analytics_bot.log
pkill -f analytics_bot
nohup python3 analytics_bot.py > logs/analytics_bot.log 2>&1 &
1С недоступна
curl -u "user:pass" "http://1c:8080/base/odata/standard.odata/"
Автор: BizDNAi Development Team
Дата: 11 января 2026
Версия: 2.0

Integration Setup - BizDNAi System Architecture
🏗 System Components

1. SuperAdmin Bot
Location: /root/dnai-sales/bot/superadmin_bot.py
Process: Runs on HOST via nohup python3 superadmin_bot.py &
Logs: /tmp/superadmin.log
API: http://localhost:8005 (backend)

2. Backend API
Location: /root/dnai-sales/backend/
Process: Docker container bizdnaii_backend
Port: 8005:8000
Database: PostgreSQL on DigitalOcean

3. Client Middleware (e.g., Morozov)
Location: /root/dnai-sales/integrations/clients/morozov/
Process: Docker container bitrix_1c_middleware
Port: 8008
Purpose: Bitrix24 ↔ 1C integration

⚙️ Configuration Flow
OLD (DEPRECATED ❌)
Middleware reads .env → Hardcoded credentials

NEW (ACTIVE ✅)
SuperAdmin Bot → Backend API → PostgreSQL → Middleware loads from DB
🔌 Setup Integration for New Client
Step 1: Configure via SuperAdmin Bot
Telegram → SuperAdmin bot
🔌 Интеграции → Select company
⚙️ Настроить → Choose CRM type
Enter:
1C: URL, username, password
Bitrix24: webhook URL
OR KOMMO: subdomain, client_id, client_secret, refresh_token

✅ Settings saved to PostgreSQL
Step 2: Create Client Middleware

# Copy template
cp -r /root/dnai-sales/integrations/clients/morozov \
      /root/dnai-sales/integrations/clients/NEW_CLIENT
cd /root/dnai-sales/integrations/clients/NEW_CLIENT

# Update config.py - ONLY change company_id
vi config.py

# Change: self.company_id = 7  →  self.company_id = <NEW_ID>

# Create .env with ONLY DATABASE_URL
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST:PORT/DB?ssl=require
EOF

# Update docker-compose.yml
vi docker-compose.yml

# Change: container_name, ports

# Start
docker-compose up -d

# Verify
docker logs <container_name> | grep "Loaded from DB"

# Expected: "✅ Loaded from DB successfully!"
🗄 Database Schema
companies Table - Integration Fields
integration_enabled BOOLEAN DEFAULT FALSE
integration_type VARCHAR  -- 'bitrix24', 'kommo', 'amocrm'
-- 1C OData
onec_enabled BOOLEAN DEFAULT FALSE
onec_base_url VARCHAR
onec_username VARCHAR
onec_password VARCHAR
-- Bitrix24
bitrix24_webhook_url VARCHAR
-- KOMMO/AmoCRM
kommo_subdomain VARCHAR
kommo_client_id VARCHAR
kommo_client_secret VARCHAR
kommo_refresh_token TEXT
🚨 Critical Issues & Solutions
Issue 1: API returns integration_enabled: null
Problem: Backend didn't restart after models.py update
Solution:

docker-compose restart backend
Issue 2: Middleware uses empty fallback
Problem: /companies/all endpoint doesn't return integration fields
Solution: Check sales_agent.py includes integration fields in return dict

Issue 3: Settings not saved to DB
Problem: /company/upsert endpoint doesn't process integration fields
Solution: Add if 'integration_enabled' in data: blocks in upsert handler

Issue 4: Changes not in container
Problem: Docker cached old files
Solution:

docker-compose down
docker-compose build --no-cache
docker-compose up -d

✅ Verification Checklist

# 1. Database
psql -h <HOST> -U <USER> -d <DB> -c \
  "SELECT integration_enabled, integration_type FROM companies WHERE id=7;"

# Expected: t | bitrix24

# 2. API
curl http://localhost:8005/sales/companies/all | jq '.[] | select(.id==7)'

# Should return integration fields

# 3. Middleware logs
docker logs <container> | grep "Loaded from DB"

# Expected: "✅ Loaded from DB successfully!"
📝 Modified Files (Jan 11, 2026)
backend/models.py - Added 11 integration fields to Company model
backend/routers/sales_agent.py - Updated /company/upsert and /companies/all endpoints
bot/superadmin_bot.py - Added IntegrationFlow FSM states and handlers
integrations/clients/morozov/config.py - Loads from DB via API
🔄 Restart Commands

# Backend
cd /root/dnai-sales
docker-compose restart backend

# SuperAdmin Bot
pkill -f superadmin_bot
cd /root/dnai-sales/bot
nohup python3 superadmin_bot.py > /tmp/superadmin.log 2>&1 &

# Middleware (e.g., Morozov)
cd /root/dnai-sales/integrations/clients/morozov
docker-compose restart
Last Updated: January 11, 2026
Duration: 2 hours (40 min bot + 80 min migration)
Status: ✅ Production - All integrations from Database

# Widget → CRM Integration (Bitrix24)
Что делает
Автоматически отправляет лиды из виджетов (Instagram, Web и др.) в CRM клиента (Bitrix24).

Как работает
Поток данных
Виджет → Диалог с AI → Сбор контактов → Подтверждение пользователем → Отправка в Bitrix24
Что отправляется в Bitrix24
Контакт (crm.contact.add):

Имя
Телефон
Сделка (crm.deal.add):

Название: Лид с Widget #XX - Имя
Стадия: NEW
Комментарий: AI анализ диалога (температура, интересы, краткое содержание)
Привязка к контакту
Управление интеграцией
Для менеджера (в Telegram боте)
Кнопка 🔌 Интеграция CRM в главном меню
Показывает текущий статус (включена/выключена)
Inline кнопка для переключения ON/OFF
МУЛЬТИТЕНАНСИ: каждая компания управляет своей интеграцией отдельно
Для SuperAdmin
Команда ⚙️ Интеграции
Выбрать компанию
Настроить:
integration_type: bitrix24
bitrix24_webhook_url: webhook URL
integration_enabled: true/false
Настройка Bitrix24 Webhook
Формат URL:
https://COMPANY.bitrix24.kz/rest/USER_ID/WEBHOOK_KEY/
Как получить:
Bitrix24 → Приложения → Вебхуки → Входящий вебхук
Добавить права: crm.contact.add, crm.deal.add
Скопировать URL
Структура кода
Backend (backend/routers/sales_agent.py)
Функция отправки (строка ~61):

async def send_lead_to_bitrix24(lead_id: int, company_id: int, db: AsyncSession):
    # 1. Проверяет integration_enabled и integration_type
    # 2. Получает историю диалога
    # 3. Генерирует AI summary
    # 4. Создает контакт в Bitrix24
    # 5. Создает сделку с привязкой к контакту
Вызов (строка ~510):

# После background_send_notifications - ТОЛЬКО после подтверждения контактов
asyncio.create_task(send_lead_to_bitrix24(lead_id, company_id, db))
Bot (bot/handlers.py)
Кнопка в меню:

def get_manager_keyboard():
    # ...
    [KeyboardButton(text="🔌 Интеграция CRM")],
Handler (в process_manager_command):

elif 'интеграция' in text_lower or 'crm' in text_lower:
    # Показывает статус и inline кнопку toggle
Callback toggle:

@router.callback_query(F.data == "toggle_crm_integration")
async def toggle_crm_integration_callback(callback):
    # Переключает integration_enabled через API
Database (Company model)
# backend/models.py - Company table
integration_enabled: bool       # ON/OFF для CRM интеграции
integration_type: str           # 'bitrix24', 'kommo', etc.
bitrix24_webhook_url: str       # Webhook URL для Bitrix24
API Endpoints
Получить статус компаний:
GET /sales/companies/all
Response: [{id, integration_enabled, integration_type, bitrix24_webhook_url, ...}]

Обновить настройки:
POST /sales/company/upsert
{"id": company_id, "integration_enabled": true}
Тестирование
Включить интеграцию:

Через бот менеджера: кнопка 🔌 Интеграция CRM → Включить
Или через SuperAdmin: Интеграции → компания → включить
Создать тестовый лид:

https://bizdnai.com/w/{company_id}/{widget_id}
Проверить логи:

docker-compose logs backend | grep -E "Bitrix24|DEAL"
Проверить Bitrix24:

Раздел Сделки → новая сделка
Комментарий содержит AI анализ
Troubleshooting
Лид не приходит в Bitrix24
# Проверить настройки компании
curl -s http://localhost:8000/sales/companies/all | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data:
    if c.get('integration_enabled'):
        print(f\"Company {c['id']}: enabled={c['integration_enabled']}, type={c['integration_type']}, webhook={'YES' if c.get('bitrix24_webhook_url') else 'NO'}\")"
Ошибка "asyncio not defined"
grep "^import asyncio" backend/routers/sales_agent.py
# Если нет - добавить после import logging
Дубликаты лидов в Bitrix24
Вызов send_lead_to_bitrix24 должен быть ТОЛЬКО после background_send_notifications, не после get_or_create_lead.

Ошибка 429 (Rate limit)
AI summary генерируется слишком часто. Проверить что вызов идет только после подтверждения.

Важные моменты
Один лид = одна сделка - отправка только после подтверждения контактов
МУЛЬТИ режим - каждая компания настраивается отдельно
AI анализ - генерируется из истории диалога и добавляется в комментарий сделки
Контакт + Сделка - создаются оба объекта, связаны между собой
