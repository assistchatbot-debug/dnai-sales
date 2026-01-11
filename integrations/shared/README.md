##BizDNAi Integrations - Полная документация

#🎯 Назначение
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

