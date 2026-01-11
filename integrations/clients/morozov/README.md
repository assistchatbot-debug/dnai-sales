# 🔄 Интеграция 1С:Бухгалтерия (Казахстан) с Bitrix24

Middleware-сервис для автоматической интеграции системы учёта 1С:Бухгалтерия (редакция для Казахстана) с CRM Bitrix24.

---

## 📋 Описание проекта

Система обеспечивает двустороннюю автоматизацию бизнес-процессов:

- **Bitrix24 → 1С:** Автоматическое создание накладных при закрытии сделок
- **1С → Bitrix24:** Ежедневная синхронизация остатков товаров
- **ИИ-отчёты:** Генерация аналитических отчётов по продажам
- **Telegram-уведомления:** Мониторинг работы системы в реальном времени

---

## 🛠 Технологии

### Backend
- **Python 3.11** - Основной язык
- **FastAPI** - Async REST API framework
- **SQLAlchemy 2.0** - ORM для работы с БД
- **AsyncPG** - Асинхронный драйвер PostgreSQL
- **Pydantic** - Валидация данных
- **httpx** - Асинхронный HTTP клиент

### Инфраструктура
- **Docker** - Контейнеризация
- **Docker Compose** - Оркестрация
- **Nginx** - Reverse proxy + SSL termination
- **PostgreSQL** - База данных (managed database)
- **Let's Encrypt** - SSL сертификаты

### Интеграции
- **Bitrix24 REST API** - CRM система
- **1С HTTP-сервис** - Система учёта
- **OpenRouter API** - ИИ модели для отчётов
- **Telegram Bot API** - Уведомления

### Планировщик
- **APScheduler** - Cron-задачи для синхронизации

---

## 🏗 Архитектура

```
┌─────────────┐         HTTPS          ┌──────────────┐
│  Bitrix24   │ ───────────────────────>│   Nginx      │
│    CRM      │    Webhook Events       │ (SSL proxy)  │
└─────────────┘                         └──────┬───────┘
                                               │
                                        ┌──────▼───────┐
                                        │  Middleware  │
┌─────────────┐         HTTP           │   FastAPI    │
│  1С:Бухг    │ <──────────────────────┤   (Docker)   │
│  (Каз. КЗ)  │  Накладные/Остатки     └──────┬───────┘
└─────────────┘                               │
                                        ┌─────▼────────┐
┌─────────────┐         HTTPS          │  PostgreSQL  │
│  Telegram   │ <──────────────────────┤  (Managed)   │
│    Bot      │    Уведомления         └──────────────┘
└─────────────┘
```

---

## ✨ Основные возможности

### 1. Автоматизация создания накладных

- При закрытии сделки с платежом Kaspi в Bitrix24
- Автоматически создаётся накладная в 1С
- Передаются: клиент, товары, суммы, способ оплаты
- Номер накладной сохраняется в поле сделки

### 2. Синхронизация остатков

- Автоматически каждый день в 00:00 (настраивается)
- Получение остатков из 1С по всем складам
- Обновление количества в каталоге Bitrix24
- Сохранение истории изменений

### 3. ИИ-аналитика

- Генерация отчётов на естественном языке
- "Покажи продажи за неделю по менеджерам"
- "Сколько заказов с Kaspi за месяц?"
- Использование OpenRouter API (GPT/Claude)

### 4. Telegram-мониторинг

- Уведомления о создании накладных
- Алерты об ошибках синхронизации
- Статус работы middleware

---

## 📊 Текущий статус (05.01.2026)

| Компонент | Статус | Прогресс |
|-----------|--------|----------|
| Middleware API | ✅ Работает | 100% |
| HTTPS (SSL) | ✅ Настроено | 100% |
| Webhook Bitrix24 | ✅ Работает | 100% |
| Telegram уведомления | ✅ Работают | 100% |
| База данных | ✅ Готова | 100% |
| **Маппинг товаров** | ✅ Готов | **99% (79/80)** |
| **Подключение к 1С** | ✅ Работает | 100% |
| 1С OData | 🔄 Объекты не опубликованы | 50% |
| Синхронизация остатков | 🔄 Частично | 50% |

### 🔐 Учётные данные 1С
- **URL:** `http://***:8081/company-***`
- **Пользователь:** `api`
- **Пароль:** `api123`
- **OData:** `/odata/standard.odata/` (работает)
- **HTTP-сервис:** `/hs/dt/` (403 - нужны права)

---

## 🚀 Deployment

### Требования

- Ubuntu/Debian сервер
- Docker + Docker Compose
- Nginx с SSL
- PostgreSQL (managed или локальный)
- Доступ к серверу 1С

### Установка

1. **Клонирование и настройка:**
```bash
cd /root/dnai-sales/integrations/clients/morozov
cp .env.example .env
nano .env  # Заполнить параметры
```

2. **Инициализация БД:**
```bash
chmod +x init_db.sh
./init_db.sh
```

3. **Запуск:**
```bash
chmod +x deploy.sh
./deploy.sh
```

4. **Проверка:**
```bash
curl https://bizdnai.com/morozov/
```

---

## 📡 API Endpoints

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/` | GET | Health check |
| `/webhook/bitrix24/deal` | POST | Webhook от Bitrix24 |
| `/api/ai-report` | POST | Генерация ИИ отчёта |
| `/api/sync/stock` | POST | Запуск синхронизации |
| `/api/mapping/product` | POST | Создать маппинг товара |
| `/api/mapping/products` | GET | Список всех маппингов |

---

## 🗄 Структура базы данных

### Таблица: `bitrix_1c_product_mapping`
Связь товаров между системами

| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer | Primary key |
| bitrix24_product_id | String | ID товара в Bitrix24 |
| bitrix24_product_name | String | Название в Bitrix24 |
| onec_product_code | String | Код номенклатуры 1С |
| onec_product_name | String | Название в 1С |

### Таблица: `bitrix_1c_sync_log`
Журнал всех операций

| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer | Primary key |
| sync_type | String | Тип операции |
| direction | String | Направление (b24→1c / 1c→b24) |
| status | String | success/error |
| entity_id | String | ID сущности |
| request_data | Text | Данные запроса (JSON) |
| response_data | Text | Ответ (JSON) |
| error_message | Text | Текст ошибки |
| created_at | DateTime | Время создания |

### Таблица: `bitrix_1c_stock_snapshot`
История изменения остатков

| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer | Primary key |
| product_code | String | Код товара |
| product_name | String | Название |
| quantity | Integer | Количество |
| warehouse | String | Склад |
| snapshot_date | DateTime | Дата снимка |

---

## 🔧 Конфигурация (.env)

```env
# Bitrix24
BITRIX24_WEBHOOK_URL=https://domain.bitrix24.kz/rest/ID/TOKEN/
BITRIX24_DOMAIN=domain.bitrix24.kz

# 1С
ONEC_BASE_URL=http://1c-server/base-name
ONEC_USERNAME=Администратор
ONEC_PASSWORD=password
ONEC_HTTP_SERVICE_PATH=/hs/bitrix-integration

# Database
DATABASE_URL=postgresql://user:pass@host:25060/db?sslmode=require

# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENROUTER_MODEL=openai/gpt-oss-120b

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=987654321

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8008
LOG_LEVEL=INFO

# Sync Schedule
SYNC_SCHEDULE_HOUR=0
SYNC_SCHEDULE_MINUTE=0
```

---

## 📅 Roadmap

### ✅ Завершено (05.01.2026)
- [x] Middleware FastAPI сервис
- [x] Webhook integration с Bitrix24
- [x] HTTPS через Nginx
- [x] Telegram уведомления
- [x] База данных PostgreSQL
- [x] Docker контейнеризация
- [x] Автоматический маппинг товаров (79/80 = 99%)
- [x] **Подключение к 1С через OData** ✅
- [x] Публикация базы 1С через IIS
- [x] Создание документов в 1С из сделок Bitrix24(Kaspi)
### 🔄 В процессе
- [ ] Синхронизация остатков 1С → Bitrix24
- [ ] Создание документов в 1С из сделок Bitrix24

### 📋 Запланировано
- [ ] Web-интерфейс для управления маппингом
- [ ] Dashboard с метриками синхронизации
- [ ] Telegram bot с командами
- [ ] Автоматический маппинг по штрихкодам
- [ ] Поддержка множественных складов

---

## ⚙️ Настройка OData в 1С

### Шаг 1: Публикация OData в default.vrd
В файле `C:\inetpub\wwwroot\{база}\default.vrd` должно быть:
```xml
<standardOdata enable="true" reuseSessions="dontuse" sessionMaxAge="20" poolSize="10" poolTimeout="5"/>
```

### Шаг 2: Включение объектов в OData
В 1С:Предприятие выполните код (Функции для технического специалиста):
```1c
МассивСостава = Новый Массив;
МассивСостава.Добавить(Метаданные.Справочники.Контрагенты);
МассивСостава.Добавить(Метаданные.Справочники.Номенклатура);
МассивСостава.Добавить(Метаданные.Документы.РеализацияТоваровУслуг);
УстановитьСоставСтандартногоИнтерфейсаOData(МассивСостава);
```

### Шаг 3: Создание пользователя для OData
- Создайте пользователя `***` с паролем
- Добавьте роль "Полные права" или необходимые права на справочники

### Шаг 4: Тестирование
```bash
# Проверка метаданных
curl -u "***:password" \
  "http://IP:8081/base/odata/standard.odata/\$metadata"

# Получение контрагентов (URL encoding для кириллицы)
curl -u "***:password" \
  "http://IP:8081/base/odata/standard.odata/Catalog_%D0%9A%D0%BE%D0%BD%D1%82%D1%80%D0%B0%D0%B3%D0%B5%D0%BD%D1%82%D1%8B?\$top=3"
```

---

## 📞 Поддержка

- **Repository:** https://github.com/assistchatbot-debug/morozov
- **Production:** https://bizdnai.com/morozov/
- **Telegram:** @morozov_integration_bot

---

## 📄 Лицензия

Proprietary - H&B Technology
