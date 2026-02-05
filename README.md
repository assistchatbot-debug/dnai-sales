# 🤖 BizDNAi Sales Agent
**Intelligent AI-powered sales assistant for Telegram with voice recognition and multi-language support.**

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-blue.svg)](https://docs.aiogram.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)

## 🔗 WhatsApp Business Setup Integration (NEW)

**Status:** Phase 1 ✅ | Phase 2 🔄 (2026-02-05)

New feature: Allow customers to connect WhatsApp Business accounts via a **web form** without terminal setup.

### Quick Start
- **Live URL:** https://bizdnai.com/whatsapp-setup/
- **Tech Spec:** See [WHATSAPP-INTEGRATION-TECH-SPEC.md](/.openclaw/workspace/WHATSAPP-INTEGRATION-TECH-SPEC.md)
- **Phase 1 Status:** QR code generation ✅ | Real WhatsApp linking (Phase 2) 🔄

### User Flow
```
1. Customer opens: https://bizdnai.com/whatsapp-setup/
2. Select language (RU/EN/KK/KY/UZ)
3. Solve CAPTCHA (math puzzle)
4. Enter WhatsApp number
5. Confirm company info
6. Scan QR code with WhatsApp Business
7. [Phase 2] System detects → shows success ✅
```

### Backend Changes (Phase 1)
**New endpoint:** `/sales/api/whatsapp/*`

```python
# File: backend/routers/whatsapp.py (NEW)
POST   /sales/api/whatsapp/lookup                  # Verify phone in DB
POST   /sales/api/whatsapp/pairing/create          # Generate QR code
GET    /sales/api/whatsapp/pairing/status          # Check status (polling)
POST   /sales/api/whatsapp/pairing/webhook         # OpenClaw callback [Phase 2]
```

**Database:** New table `whatsapp_pairings`
```sql
id (UUID) | company_id (FK) | phone | qr_code | status | linked_at | expires_at
```

**Trigger:** Auto-updates `companies.whatsapp` when status='linked'

### Frontend (Phase 1)
**New app:** `frontend/whatsapp-setup/`
- React 18 + Vite
- Tailwind CSS (dark theme, purple gradients)
- 6-page flow (Language → CAPTCHA → Phone → Confirm → QR → Success)
- Deployed to: `/var/www/bizdnai/whatsapp-setup/` (Nginx)
- Polling: checks pairing status every 2 seconds

### Deployment

```bash
# Build frontend
cd frontend/whatsapp-setup
npm install
npm run build
# Output: ../../www/whatsapp-setup/

# Deploy to Nginx
cp -r www/whatsapp-setup/* /var/www/bizdnai/whatsapp-setup/

# Rebuild backend Docker
docker-compose build --no-cache backend
docker-compose up -d backend
```

### Testing

```bash
# Test QR generation
curl -X POST http://127.0.0.1:8005/sales/api/whatsapp/pairing/create \
  -H "Content-Type: application/json" \
  -d '{"company_id": 1, "phone": "+77073333481"}'

# Response: { pairing_id, qr_code (base64), expires_at, expires_in }
```

### Phase 2: Real WhatsApp Linking
Requires integration with OpenClaw Baileys client:
1. Listen for `authenticated` event in OpenClaw
2. Call webhook: `POST /sales/api/whatsapp/pairing/webhook`
3. Update status to `'linked'` in database
4. Send Telegram notification to manager

See [WHATSAPP-INTEGRATION-TECH-SPEC.md](/.openclaw/workspace/WHATSAPP-INTEGRATION-TECH-SPEC.md) for details.

---
## 🚀 Features
- ✅ **AI-Powered Conversations** - GPT-based product recommendations
- 🎤 **Voice Recognition** - OpenAI Whisper for speech-to-text
- 🌍 **Multi-Language Support** - Russian, English, Kazakh, Kyrgyz, Uzbek, Ukrainian
- 📊 **Lead Management** - Automatic lead tracking and interaction logging
- 🔄 **Async Architecture** - High-performance async/await with SQLAlchemy
- 🐳 **Docker Deployment** - One-command deployment with Docker Compose
- 💳 **Tier Pricing System** - 4 subscription tiers (Free, Basic, Pro, Enterprise) + 4 AI agent packages
- 📧 **Email Notifications** - Automated pricing emails and lead reports via SMTP
- 🎯 **A/B Testing** - Multiple widgets per channel with unique IDs for analytics
- 🏢 **Multi-Tenancy** - Support for multiple companies with separate bots and managers
## 🏗️ Architecture
┌─────────────────┐ ┌─────────────────┐ │ Telegram Bot │ │ Web Widget │ │ (@DNAiSoft) │ │ (bizdnai.com) │ └────────┬────────┘ └────────┬────────┘ │ │ │ ┌─────────────────┴────────┐ │ │ │ └────────►│ FastAPI Backend │ │ (Port 8000) │ └──────────┬───────────────┘ │ ┌────────────────────┼────────────────────┐ │ │ │ ▼ ▼ ▼ ┌─────────┐ ┌─────────────┐ ┌──────────┐ │ OpenAI │ │ PostgreSQL │ │ Email │ │ Whisper │ │ Database │ │ SMTP │ │ (STT) │ │ (AsyncPG) │ │ Service │ └─────────┘ └─────────────┘ └──────────┘ │ │ ▼ ▼ ┌─────────────┐ ┌──────────────┐ │ OpenRouter │ │ Telegram │ │ GPT │ │ API │ └─────────────┘ └──────────────┘

<img width="410" height="544" alt="image" src="https://github.com/user-attachments/assets/eb36a4a5-51dd-4229-afdd-8c58ad10d93d" />

## 📦 Tech Stack
### Backend
- **FastAPI** - Modern async web framework
- **SQLAlchemy 2.0** - Async ORM with PostgreSQL
- **AsyncPG** - High-performance PostgreSQL driver
- **Pydantic** - Data validation
- **SlowAPI** - Rate limiting

### Bot
- **Aiogram 3.x** - Async Telegram Bot framework
- **OpenAI API** - Whisper for voice transcription
- **OpenRouter** - GPT model access

### Database
- **PostgreSQL 15** - Primary database
- **DigitalOcean Managed DB** - Production hosting

### AI Services
- **OpenRouter GPT** - Conversational AI
- **OpenAI Whisper** - Speech-to-text

### DevOps
- **Docker & Docker Compose** - Containerization
- **Nginx** - Reverse proxy (optional)

## 🗄️ Database Schema

### Core Tables
**companies** - Main company configuration

```sql
id, name, subdomain, settings, default_language, created_at,
tier (VARCHAR), tier_expiry (TIMESTAMP), ai_package (VARCHAR),
leads_used_this_month (INTEGER), leads_reset_date (TIMESTAMP)
leads - Customer leads with Telegram integration

sql
id, company_id, telegram_user_id (BigInt), contact_info, status, 
sales_agent_session_id, product_match_score, selection_criteria
interactions - Conversation history

sql
id, company_id, lead_id, type (text/voice), content, outcome, created_at
user_preferences - User language settings

sql
id, telegram_user_id (BigInt), language_code, created_at
ui_texts - Multi-language UI translations

sql
id, company_id, key, language_code, text, created_at
tier_settings - Subscription tier configuration (NEW)

sql
tier (VARCHAR PRIMARY KEY), name_ru, price_usd, leads_limit,
web_widgets_limit, social_widgets_limit, features_ru (TEXT[]),
is_active, updated_at
ai_agent_packages - AI setup packages (NEW)

sql
package (VARCHAR PRIMARY KEY), name_ru, price_usd, 
features_ru (TEXT[]), is_active, updated_at

💳 Tier Pricing System (NEW)
Subscription Tiers (Monthly)
Tier	Price	Leads/month	Web Widgets	Social Widgets

🆓 FREE	$0	20	1	0

💼 BASIC	$19	100	1	2

🚀 PRO	$39	200	1	5

🏢 ENTERPRISE	$99	1000	3	10
AI Agent Packages (One-time payment)
Package	Price	Features

🎯 Basic	$0	Standard greeting, basic qualification, contact collection

📊 Standard	$99	Personalization, extended qualification, FAQ training

⚡ Advanced	$199	Knowledge base, smart qualification, dialog scripts

🎨 Custom	$399	Full customization, CRM integration, 24/7 support

Pricing API Endpoints (NEW)

Method	Endpoint	Description

GET	/sales/tiers	List all subscription tiers
GET	/sales/ai-packages	List AI agent packages
GET	/sales/pricing.html	Dynamic pricing page (RU/EN language toggle)
GET	/sales/{id}/tier-usage	Company's tier and usage statistics
POST	/sales/{id}/send-pricing-email	Send pricing info to company email
PATCH	/sales/tiers/{tier}	Update tier settings (SuperAdmin only)
PATCH	/sales/ai-packages/{pkg}	Update AI package (SuperAdmin only)

🔧 Environment Variables
Create a .env file with the following variables:

bash
# Telegram
BOT_TOKEN=your_telegram_bot_token
MANAGER_CHAT_ID=123456789               # Manager ID for reports
SUPER_ADMIN_CHAT_ID=987654321           # SuperAdmin ID for managing all companies

# API Keys
OPENROUTER_API_KEY=your_openrouter_key
OPENAI_API_KEY=your_openai_key          # For voice transcription

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/dbname

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=user@example.com
SMTP_PASSWORD=password
EMAIL_TO=manager@example.com

🚀 Quick Start
bash

# 1. Clone
git clone [https://github.com/assistchatbot-debug/dnai-sales.git](https://github.com/assistchatbot-debug/dnai-sales.git)
cd dnai-sales

# 2. Configure
cp .env.example .env

# Edit .env with your credentials

# 3. Deploy
docker-compose up -d --build

# 4. Check logs
docker-compose logs -f bot backend
Architecture Details

┌─────────────────────────────────────────────────────────────────┐
│                        NGINX (порт 80/443)                      │
│                         bizdnai.com                             │
├─────────────────────────────────────────────────────────────────┤
│                               │                                 │
│               ┌───────────────┴───────────────┐                 │
│               ▼                               ▼                 │
│    ┌─────────────────────┐        ┌─────────────────────┐       │
│    │   Web Widget (JS)   │        │   Telegram Bot      │       │
│    │   frontend/widget   │        │   bot/              │       │
│    └─────────┬───────────┘        └─────────┬───────────┘       │
│              │                              │                   │
│              │ /sales/* API                 │ source: telegram  │
│              ▼                              ▼                   │
│    ┌──────────────────────────────────────────────────┐         │
│    │              bizdnaii_backend (8005)             │         │
│    │              backend/routers/sales_agent.py      │         │
│    │                                                  │         │
│    │  Endpoints:                                      │         │
│    │  - POST /sales/{company_id}/chat                 │         │
│    │  - POST /sales/{company_id}/voice                │         │
│    │  - GET  /sales/{company_id}/leads                │         │
│    │  - GET  /sales/{company_id}/leads/count          │         │
│    │  - GET  /sales/{company_id}/widget-enabled       │         │
│    │  - POST /sales/{company_id}/widget-enabled       │         │
│    │  - GET  /sales/health/db                         │         │
│    │  - GET  /sales/companies/list                    │         │
│    │  - GET  /sales/tiers                             │         │
│    │  - GET  /sales/pricing.html                      │         │
│    └──────────────────────────────────────────────────┘         │
│                         │                                       │
│                         ▼                                       │
│               ┌─────────────────────┐                           │
│               │   PostgreSQL (DB)   │                           │
│               │     port 5432       │                           │
│               └─────────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘

Ports
Port	Service	Description
80/443	NGINX	External proxy, SSL termination
8005	bizdnaii_backend	Main API for widget and bot
8000	bizdna-new-api-1	Old API (not used for voice)
5432	PostgreSQL	Database
User Roles
MANAGER_CHAT_ID
Company manager receiving lead notifications.

Commands (text in bot):

status
 - Check systems (API, DB, AI, widget)
leads
 - Last 5 leads with source, date, temperature
lead count for day/week/month
widget 1 / widget 0 - Enable/disable widget
help - Command list
SUPER_ADMIN_CHAT_ID
Super administrator for multi-tenancy.

Commands:

bots - List of all connected companies/bots
All manager commands
Multi-Tenancy
The system supports multiple companies (Company ID). Each company has:

Own widget
Own Telegram bot
Own leads and settings
SuperAdmin (SUPER_ADMIN_CHAT_ID) can view and manage all companies.

📱 Multilingual Lead Detection Logic (6 Languages)
Overview
BizDNAi widget now supports intelligent lead detection across 6 languages: Russian, English, Kazakh, Kyrgyz, Uzbek, and Ukrainian. The system uses AI-powered analysis to extract contact information and detect user confirmation in any language.

🎯 Supported Languages
🇷🇺 Russian (ru) - Русский
🇺🇸 English (en) - English
🇰🇿 Kazakh (kz) - Қазақша
🇰🇬 Kyrgyz (kg) - Кыргызча
🇺🇿 Uzbek (uz) - O'zbekcha
🇺🇦 Ukrainian (ua) - Українська
1️⃣ Name Extraction Logic
Method: AI-Powered Extraction
Location: 
backend/routers/sales_agent.py
 (lines 290-336)

How it works:

Trigger: Only when lead doesn't have a name saved yet
Context: Analyzes last 10 messages from conversation
AI Prompt:
"Из этого диалога извлеки имя клиента. 
Ответь ТОЛЬКО именем, без ничего лишнего. 
Если имя не найдено, ответь: НЕТ"
Validation:
Response must not be "НЕТ"
Length between 2-30 characters
Capitalized automatically
Storage: Saved to lead.contact_info['name']
Example:

User: "Меня зовут Сакен" → AI extracts: "Сакен" ✅
User: "My name is John" → AI extracts: "John" ✅
User: "Атым Айдар" → AI extracts: "Айдар" ✅
Languages supported: All 6 (AI understands context in any language)

2️⃣ Phone Number Detection
Method: Regex Pattern Matching
Location: 
backend/routers/sales_agent.py
 (line 338)

Function: 
extract_phone_number(text)

Regex Pattern:

python
r'\+?\d[\d\s\-\(\)]{7,}'
Detects:

✅ +77012345678
✅ 8 (701) 234-56-78
✅ 7012345678
✅ +1 (555) 123-4567
✅ Any format with 7+ digits
Storage:

First detected phone saved to lead.contact_info['phone']
Won't overwrite existing phone number
Language-agnostic: Works regardless of conversation language
3️⃣ Confirmation Detection (NEW - 25.12.2024)
Method: AI-Powered Sentiment Analysis
Location: 
backend/routers/sales_agent.py
 (lines 338-358)

⚠️ Previous Problem

Old logic used hardcoded keyword matching:

python
# ❌ OLD - Only worked for specific words
confirm_words = ['да', 'yes', 'ок']
is_confirmed = any(w in message for w in confirm_words)
Issues:

❌ Didn't work for "Дұрыс" (Kazakh)
❌ Missed "Туура" (Kyrgyz)
❌ Failed on "To'g'ri" (Uzbek)
❌ Couldn't handle variations like "конечно", "exactly", "ага"
✅ New Solution: AI Confirmation Detection

How it works:

AI Prompt (in Russian, but analyzes ANY language):
python
f"""Пользователь ответил: "{user_message}"
Это положительное подтверждение (да, согласен, верно, ok и т.д.) или отрицание?
Ответь ОДНИМ словом: ДА или НЕТ"""
AI Response: "ДА" or "НЕТ"
Detection:
python
is_confirmed = 'да' in ai_response.lower() or 'yes' in ai_response.lower()
Fallback: If AI fails, uses simple keywords:
python
simple_confirms = ['да', 'yes', 'ок', 'ok', '+', '👍']
Examples that NOW work:

✅ "Да" (Russian) → AI: "ДА"
✅ "Yes" (English) → AI: "ДА"
✅ "Дұрыс" (Kazakh) → AI: "ДА"
✅ "Туура" (Kyrgyz) → AI: "ДА"
✅ "To'g'ri" (Uzbek) → AI: "ДА"
✅ "Вірно" (Ukrainian) → AI: "ДА"
✅ "Конечно" (Russian variation) → AI: "ДА"
✅ "Exactly" (English variation) → AI: "ДА"
✅ "Ооба" (Kyrgyz variation) → AI: "ДА"
✅ "👍" (emoji) → AI: "ДА"
❌ "Нет" → AI: "НЕТ"
❌ "No" → AI: "НЕТ"
❌ "Жоқ" (Kazakh "no") → AI: "НЕТ"
Logging:

🤖 AI confirmation check: "Дұрыс" → ДА → True
4️⃣ Confirmation Question Detection
Method: Multilingual Keyword + Pattern Matching
Location: 
backend/routers/sales_agent.py
 (lines 360-374)

Checks if bot asked for confirmation in last 3 messages:

Method 1: Multilingual Keywords

python
confirm_keywords = [
    'верно', 'правильно', 'подтвердите',  # Russian
    'correct', 'confirm',                  # English
    'дұрыс', 'рас',                       # Kazakh
    'туура',                              # Kyrgyz
    'to\'g\'ri',                          # Uzbek
    'вірно'                               # Ukrainian
]
Method 2: Phone Pattern Detection

python
# If bot message contains phone number = confirmation message
has_phone_pattern = bool(re.search(r'\+?\d[\d\s()-]{7,}', bot_text))
Logic:

python
if (has_keyword OR has_phone_pattern):
    has_confirm_q = True
Examples of detected bot messages:

✅ "Ваше имя: Сакен\nВаш телефон: 7075456987\nВсё верно?" (Russian)
✅ "Your name: John\nYour phone: +1234567890\nIs this correct?" (English)
✅ "Сіздің атыңыз: Айдар\nТелефон: 77012345678\nДұрыс па?" (Kazakh)
5️⃣ Complete Notification Flow
Trigger Conditions (ALL must be TRUE):

python
if (saved_phone AND is_confirmed AND has_confirm_q AND lead.status != 'confirmed'):
    # Send notification to manager
Breakdown:

✅ saved_phone - Phone number extracted and saved
✅ is_confirmed - AI detected positive confirmation
✅ has_confirm_q - Bot asked confirmation question
✅ lead.status != 'confirmed' - Not already sent
Result:

Lead marked as confirmed
Telegram notification sent to manager
Email notification sent (if configured)
📊 Performance & Accuracy
Feature	Accuracy	Speed	Notes
Name Extraction	~95%	200-500ms	Depends on AI model
Phone Detection	~99%	<1ms	Regex-based
Confirmation Detection	~98%	200-400ms	AI-powered
🔧 Configuration
AI Service
File: backend/services/ai_service.py

Uses OpenRouter API with:

model: "anthropic/claude-3-haiku:beta"
Fallback Behavior

If AI service fails:

Name extraction: Skip (won't block conversation)
Confirmation: Use simple keyword matching
🚀 Benefits
Truly Multilingual: No hardcoded language-specific logic
Handles Variations: Works with slang, abbreviations, emojis
Context-Aware: AI understands intent, not just keywords
Maintainable: No need to update keyword lists for new languages
Scalable: Easy to add more languages without code changes
📝 Example Full Flow
Conversation (Kazakh):

User: Сәлем
Bot: Сәлеметсіз бе! Біз BizDNAi...
User: Маркетинг
Bot: Тамаша! Атыңызды жазыңыз.
User: Сакен
Bot: Рақмет, Сакен! Телефон нөміріңізді жазыңыз.
User: 7075456987
Bot: Сіздің атыңыз: Сакен
     Сіздің телефон нөміріңіз: 7075456987
     Дұрыс па?
User: Дұрыс
Backend Processing:

✅ Name extracted: "Сакен"
✅ Phone detected: "7075456987"
✅ Bot asked confirmation (phone pattern detected)
🤖 AI confirmation check: "Дұрыс" → ДА → True
✅ All conditions met → Notification sent!
🎉 Result

Manager receives Telegram notification:

🔥 НОВЫЙ ЛИД!
👤 Имя: Сакен
📱 Телефон: 7075456987
💼 Область: Маркетинг
🌡 Температура: 🔥 горячий
📝 Диалог: [...]
Works for ALL 6 languages without code changes!

🔐 SuperAdmin Bot (EN)
@BizDNAi_SuperAdmin_bot - centralized company management and multitenancy.

Features
🏢 Company Management
Create/Edit companies through 9-step process:
Company Name
TIN/BIN (Tax ID)
Phone Number
WhatsApp Number
Email (for reports)
Description
Logo (image upload)
Bot Token (Telegram bot token)
Manager Chat ID (Telegram manager chat ID for notifications)
View company list with indicators:
🤖 - Bot configured
❌ - Bot not configured
📈 System Monitoring
Real-time system status:
Backend: Online/Offline
Database: Online/Offline
Voice Input: Online
Active Bots: number of configured bots
💳 Tier Management (NEW)
View all tiers and AI packages with current prices and limits
Edit prices: Click 💰 button → enter new price
Edit lead limits: Click 👥 button → enter new limit
Edit AI package prices: Click 🤖 button → enter new price
Changes apply immediately to pricing page and database
Multitenancy
Each company receives:

Own Telegram bot (via bot_token)
Separate manager (via manager_chat_id)
Personal email notifications (via company email)
Isolated lead data
Usage
Start: Send /start to @BizDNAi_SuperAdmin_bot
Create Company:
Press "🏢 Companies"
Select "➕ Create company"
Complete 9 steps
Edit:
"🏢 Companies" → "✏️ Edit company"
Enter company ID
Update fields (. = keep unchanged)
Check Status: Press "📈 Status"
Manage Tiers (NEW): Press "💳 Tiers" → use inline buttons to edit
Technical Details
Auto-loading: Main bot loads all active companies from DB on startup
Dynamic Management: Changes apply after main bot restart
Security: Access only for authorized SuperAdmin (via SUPER_ADMIN_CHAT_ID)
Fallback: Uses .env values when DB data is missing
🌐 BizDNAi Widget
Overview
Preact-based chat widget with voice support for lead collection.

Features
💬 Text chat with AI assistant
🎤 Push-to-talk voice recording (hold to record)
🌐 Multilingual support (RU/EN synced with main site)
📱 Mobile responsive design
🔔 Tooltip notification with pulse animation
🔄 Reset button for new lead testing
Configuration
Widget Position:

jsx
style={{ right: '40px' }}           // Toggle button position
style={{ marginRight: '-30px' }}    // Dialog window offset
API Endpoints:

POST /sales/{company_id}/chat   - Text messages
POST /sales/{company_id}/voice  - Voice messages
Language Detection:
Widget reads language from:

localStorage.getItem('bizdnaii_widget_lang')
Event listener: bizdnaii-language-change
Data Sent to Backend:

Text chat:

json
{
  "message": "user text",
  "session_id": "web-session", 
  "user_id": "v_xxxxx",
  "language": "en"
}
Voice:

FormData: file, session_id, user_id, language
Build & Deploy
bash
# Build widget
docker-compose build --no-cache widget
# Extract to host
docker run --rm -v /var/www/bizdnai/widget-source:/out \
  dnai-sales-widget cp /usr/share/nginx/html/bizdnaii-widget.js /out/
# Embed on site
<script src="[https://bizdnai.com/widget-source/bizdnaii-widget.js"></script](https://bizdnai.com/widget-source/bizdnaii-widget.js"></script)>
Version History
v4.0: Pointer events for push-to-talk, reset creates new lead
v3.x: Language support, tooltip, pulse animation adjustments
🎯 Widget ID-Based URLs Refactoring
Objective
Refactor widget system from channel_name-based URLs to widget_id-based URLs to enable multiple widgets per channel for A/B testing.

What Was Implemented
1. Database Schema
✅ Translation fields added to 
social_widgets
 table:

greeting_ru, greeting_en, greeting_kz, greeting_ky, greeting_uz, greeting_uk
Existing greeting_message copied to greeting_ru for backward compatibility
2. Backend API Changes
New ID-Based Endpoints:

✅ GET /companies/{company_id}/widgets/{widget_id:int} - Get widget by ID

Returns:

json
{
  "id": 2,
  "company_id": 1,
  "channel_name": "instagram",
  "greeting_message": "Здравствуйте!!!...",
  "greetings": {
    "ru": "Здравствуйте!!!...",
    "en": null,
    "kz": null,
    ...
  }
}
✅ DELETE /companies/{company_id}/widgets/{widget_id:int} - Delete widget by ID

Widget Creation:

✅ Removed uniqueness constraint on 
channel_name
Multiple widgets can now have same 
channel_name
Each gets unique ID
URL format: https://bizdnai.com/w/{company_id}/{widget_id}
3. Frontend Updates
URL Parsing: Changed from:

javascript
const channelName = pathParts[3];  // /w/1/instagram
To:

javascript
const widgetId = pathParts[3];  // /w/1/2
API Integration:

javascript
// Fetch widget data by ID
const response = await fetch(`/sales/companies/${companyId}/widgets/${widgetId}`);
// Use channel_name from response for source tracking
source: widgetData.channel_name || 'web'
Error Handling:

404/405 responses show "Виджет не найден"
Old channel_name URLs blocked
4. Telegram Bot Updates
Widget List Display:

Социальные сети:
- Instagram (ID: 2)
  🔗 [https://bizdnai.com/w/1/2](https://bizdnai.com/w/1/2)
- Instagram (ID: 3)
  🔗 [https://bizdnai.com/w/1/3](https://bizdnai.com/w/1/3)
Delete Operation:

Callback data uses widget_id
API call: DELETE /sales/companies/{company_id}/widgets/{widget_id}
Testing Results
✅ Multiple Widgets Per Channel

Created 3 Instagram widgets:

Widget ID=2: Active, URL /w/1/2
Widget ID=3: Active, URL /w/1/3
Widget ID=4: Active, URL /w/1/4
✅ Widget Operations

Create: Multiple widgets with same channel_name ✅
List: Shows all active widgets with IDs and URLs ✅
Delete: Removes widget by ID, URL becomes inaccessible ✅
✅ URL Behavior

New URLs (/w/1/2, /w/1/3) work correctly ✅
Old URLs (/w/1/instagram) blocked with 405 error ✅
Deleted widget URLs show "Виджет не найден" ✅
Migration Impact
Backward Compatibility:

Old channel_name endpoint removed
Existing widgets updated with ID-based URLs in database
No data loss during migration
Breaking Changes:

Old URL format /w/{company_id}/{channel_name} no longer works
All widgets must use ID-based URLs
Benefits Achieved
A/B Testing Support: Create unlimited widgets per channel with different greetings
Unique Identification: Each widget has permanent unique ID
Scalability: No naming conflicts or uniqueness constraints
Analytics: Track performance per widget ID, not just channel
📁 Project Structure
dnai-sales/
├── backend/
│   ├── routers/
│   │   ├── companies.py      # Company management
│   │   ├── sales_agent.py    # AI chat, voice, tiers, pricing
│   │   └── widget.py         # Web widget
│   ├── services/
│   │   ├── ai_service.py     # GPT integration
│   │   ├── voice_service.py  # Whisper STT
│   │   └── email_service.py  # SMTP notifications
│   ├── database.py           # Async DB session
│   ├── models.py             # SQLAlchemy models
│   ├── main.py               # FastAPI app
│   └── requirements.txt
├── bot/
│   ├── handlers.py           # Manager bot handlers
│   ├── superadmin_bot.py     # SuperAdmin bot
│   ├── keyboards.py          # UI keyboards
│   ├── states.py             # FSM states
│   ├── config.py             # Bot config
│   ├── main.py               # Bot entry point
│   └── requirements.txt
├── frontend/
│   └── widget/               # Web chat widget (Preact)
├── docker-compose.yml
├── .env.example
└── README.md
🔌 API Endpoints
Sales Agent
Method	Endpoint	Description
POST	/sales/{company_id}/chat	Text chat
POST	/sales/{company_id}/voice	Voice message processing
POST	/sales/{company_id}/configure	Agent configuration
Companies
Method	Endpoint	Description
POST	/companies/	Create company
GET	/companies/{company_id}	Get company details
Monitoring
Method	Endpoint	Description
GET	/	Health check
GET	/logs	Application logs
🌍 Supported Languages
Flag	Language	Code
🇬🇧	English	en
🇷🇺	Русский	ru
🇰🇿	Қазақша	kk
🇰🇬	Кыргызча	ky
🇺🇿	O'zbekcha	uz
🇺🇦	Українська	uk
🐛 Troubleshooting
Bot not responding:

bash
docker-compose logs bot
docker-compose restart bot
Database connection errors:

bash
# Check DATABASE_URL in .env
# Ensure SSL is enabled for managed databases
DATABASE_URL=postgresql+asyncpg://...?ssl=require
Async/await errors:

bash
# Ensure all DB operations use async/await
# Use db.flush() instead of db.refresh() to avoid greenlet errors
📊 Performance
Rate Limiting: 100 req/min for chat, 10 req/min for voice
Connection Pooling: 20 connections, 10 overflow
Async Processing: Non-blocking I/O for all operations
🔐 Security
✅ Rate limiting on all endpoints
✅ Environment-based secrets
✅ SSL/TLS for database connections
✅ Input validation with Pydantic
📝 License
MIT License - see LICENSE file for details

🤝 Contributing
Fork the repository
Create a feature branch
Commit your changes
Push to the branch
Open a Pull Request
© 2025 BizDNAi

## 📲 QR Codes for Social Widgets

Manager bot can generate QR codes for standalone widget URLs:

1. Open **📢 Каналы** menu
2. Click **📲 QR код #{id}** button
3. Get 250x250 PNG QR code linking to `https://bizdnai.com/w/{company_id}/{widget_id}`

Useful for printing on business cards, flyers, or displays.

## 🎭 Avatar Widget (January 2026)

### Features
- **6 languages**: RU, EN, KZ, KY, UZ, UK
- **Voice**: Hello + Waiting (10s, 30s, 60s timer)
- **Greeting on language change**
- **Neural network background**

### Pricing Limits
- **PRO**: 1 avatar
- **ENTERPRISE**: 5 avatars
- Individual company limits via SuperAdmin

### SuperAdmin Bot
- Edit avatar limits per tier (🎭 button)
- Edit AI package prices (Avatar $99)
- Set individual company avatar limits

### Widget Creation
- Bot checks avatar/social widget limits
- Error message if limit exceeded

🎭 Avatar Widget (Embedded Web Widget)
Видео-аватар для встраивания на любой сайт. Повышает лидогенерацию через интерактивное общение.

📦 Установка на сайт
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <!-- ⚠️ ОБЯЗАТЕЛЬНО для мобильных! -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    <!-- Контент сайта -->
    
    <script src="https://bizdnai.com/widget-source/bizdnaii-avatar-widget.js"></script>
</body>
</html>
📐 Размеры (настраиваются в app.jsx)
Элемент	Размер	Где менять
Превью (закрытый)	160x200px	style={{ width: '160px', height: '200px' }} строка ~363
Canvas превью	160x200	width="160" height="200" строка ~365
Select языка	160px	style={{ width: '160px' }} строка ~355
Открытый виджет	80vw x 75vh	width: 'min(80vw, 380px)', height: 'min(75vh, 680px)' строка ~289
Видео canvas	220x265px	width="220" height="265" строка ~296
Контейнер видео	265px высота	style={{ height: '265px' }} строка ~294
🎤 Голосовой сценарий
Открытие виджета → Приветствие на выбранном языке (hello_*.mp3)
Ожидание ответа → Через 10с, 30с, 60с говорит "Жду" (waiting_*.mp3)
Смена языка → Новое приветствие на новом языке
После первого сообщения пользователя → Голос полностью отключается (не мешает общаться)
✨ Кнопка "Нажмите" на превью
Текст на 6 языках: ru="Нажмите", en="Push", kz="Басыңыз", ky="Басыңыз", uz="Bosing", uk="Натисніть"
Пульсирующее неоновое свечение (glow анимация 3s)
Стрелка ➜ вместо облачка
🗂 Файлы системы
Назначение	Путь на сервере
Исходный код виджета	/root/dnai-sales/frontend/avatar-widget/src/app.jsx
Собранный JS файл	/var/www/bizdnai/widget-source/bizdnaii-avatar-widget.js
Видео аватара (7 состояний)	/var/www/bizdnai/avatar/videos/*.mp4
Аудио голоса (6 языков)	/var/www/bizdnai/avatar/audio/voice/*.mp3
Тестовая страница	/var/www/bizdnai/test-avatar-widget.html
📹 Видео файлы (состояния аватара)
greeting.mp4 - приветствие
waiting_blink.mp4 - ожидание (моргание)
waiting_call.mp4 - ожидание (призыв)
thinking.mp4 - думает
speaking.mp4 - говорит
confused.mp4 - не понял
thanking.mp4 - благодарит
🔊 Аудио файлы
Формат: {type}_{lang}.mp3

hello_ru.mp3, hello_en.mp3, hello_kz.mp3, hello_kg.mp3, hello_uz.mp3, hello_ua.mp3
waiting_ru.mp3, waiting_en.mp3, waiting_kz.mp3, waiting_kg.mp3, waiting_uz.mp3, waiting_ua.mp3
Маппинг языков UI → аудио:

ky → kg (Кыргызстан)
uk → ua (Украина)
🔧 Сборка и деплой
cd /root/dnai-sales/frontend/avatar-widget
npm install           # первый раз
npm run build
cp dist/bizdnaii-avatar-widget.js /var/www/bizdnai/widget-source/
🌍 Поддерживаемые языки
Код	Язык	Флаг
ru	Русский	🇷🇺
en	English	🇺🇸
kz	Қазақша	🇰🇿
ky	Кыргызча	🇰🇬
uz	O'zbekcha	🇺🇿
uk	Українська	🇺🇦
⚠️ КРИТИЧНО для мобильных устройств
Без meta viewport виджет будет МИКРОСКОПИЧЕСКИМ!

<meta name="viewport" content="width=device-width, initial-scale=1.0">
Эта строка ОБЯЗАТЕЛЬНА в <head> страницы. Без неё браузер рендерит страницу как десктопную (980px) и масштабирует.

🧪 Тестирование
Открыть: https://bizdnai.com/test-avatar-widget.html

🎭 Avatar Widget Updates (9 Jan 2026)
Универсальный лоадер виджетов
Создан единый скрипт для встраивания на сайты клиентов — автоматически определяет какой виджет загружать.

Установка на сайт клиента
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://bizdnai.com/widget-source/bizdnaii-widget.js"></script>
Логика выбора
Условие	Загружается
web_avatar_enabled=true	bizdnaii-avatar-widget.js
Иначе	bizdnaii-widget-classic.js
Файлы
Файл	Размер	Назначение
bizdnaii-widget.js	1.5KB	Лоадер
bizdnaii-avatar-widget.js	40KB	Аватар
bizdnaii-widget-classic.js	37KB	Классика
Проверка лимитов аватара
При открытии /avatar/{company_id}/{widget_id}:

API проверяет avatar_limit компании
Если avatar_limit = 0 → редирект на /w/{company_id}/{widget_id} (классика)
Если лимит есть → показывает аватар
API изменения
GET /sales/companies/{id}/widgets/{widget_id} теперь возвращает:

{
  "widget_type": "avatar",
  "is_active": false,
  "redirect_url": "/w/1/23"
}
SuperAdmin: Web Avatar управление
Меню: 📊 Компании → 🎭 Web Avatar
Показывает:

Статус ✅/❌
Тариф и лимит по тарифу
Текущий override лимит
Кнопки:

Включить/Выключить web_avatar_enabled
Установить индивидуальный лимит
Файлы изменены
Файл	Изменения
backend/models.py	Добавлен avatar_limit в Company
backend/routers/sales_agent.py	web_avatar_enabled и avatar_limit в API
bot/superadmin_bot.py	Toggle кнопка, показ лимитов
/var/www/bizdnai/avatar/index.html	Обработка redirect_url
Мобильная адаптация (viewport fix)
КРИТИЧНО: Страницы должны содержать meta viewport!

<meta name="viewport" content="width=device-width, initial-scale=1.0">
Без этого виджет микроскопический на мобильных.

Размеры виджета (текущие)
Элемент	Размер
Превью	160x200px
Открытый виджет	80vw x 75vh
Видео canvas	220x265px
Голосовой сценарий
Открытие → Приветствие на языке
Ожидание → 10с, 30с, 60с говорит "Жду"
После сообщения пользователя → Голос ОТКЛЮЧАЕТСЯ
Кнопка "Нажмите"
6 языков: ru="Нажмите", en="Push", kz/ky="Басыңыз", uz="Bosing", uk="Натисніть"
Пульсация glow 3s
Стрелка ➜
Сборка
# Avatar widget
cd /root/dnai-sales/frontend/avatar-widget
npm run build
cp dist/bizdnaii-avatar-widget.js /var/www/bizdnai/widget-source/
# Classic widget
cd /root/dnai-sales/frontend/widget
npm run build
cp dist/bizdnaii-widget.js /var/www/bizdnai/widget-source/bizdnaii-widget-classic.js


#🔌 Widget → CRM Integration
Описание
Автоматическая отправка лидов из виджетов (Instagram, Web и др.) в CRM клиента.

Поддерживаемые CRM
Bitrix24 ✅ (реализовано)
AMO CRM (планируется)
KOMMO CRM (планируется)
Salesforce (планируется)
Как работает
Виджет → Диалог с AI → Сбор контактов → Подтверждение → Bitrix24
Что создаётся в Bitrix24:
Контакт — Имя + Телефон
Сделка — Название, Стадия NEW, AI анализ в комментарии
Управление
Менеджер (Telegram бот)
Кнопка 🔌 Интеграция CRM в главном меню
Toggle ON/OFF через inline кнопку
МУЛЬТИ режим: каждая компания управляет отдельно
SuperAdmin
Интеграции → компания → настройка webhook URL
Поддерживаемые поля: integration_enabled, integration_type, bitrix24_webhook_url
Настройка Bitrix24
Bitrix24 → Приложения → Вебхуки → Входящий вебхук
Добавить права: crm.contact.add, crm.deal.add
Скопировать URL формата:
https://COMPANY.bitrix24.kz/rest/USER_ID/WEBHOOK_KEY/
Вставить в SuperAdmin → Интеграции → {компания}
API Endpoints
Метод	Endpoint	Описание
GET	/sales/companies/all	Получить статус интеграции
POST	/sales/company/upsert	Вкл/выкл интеграции
Файлы
Файл	Назначение
backend/routers/sales_agent.py	Функция send_lead_to_bitrix24()
bot/handlers.py	Кнопка интеграции для менеджера
backend/models.py	Поля Company: integration_enabled, integration_type, bitrix24_webhook_url
💰 Pricing System
Динамическая страница тарифов
URL: https://bizdnai.com/sales/pricing.html

Тарифы (ежемесячно)
Тариф	Цена	Лиды	Веб	Соц	Аватары	1С + CRM
FREE	$0	20	1	0	0	❌
BASIC	$19	100	1	2	1	❌
PRO	$39	200	1	5	2	✅
ENTERPRISE	$99	1000	3	10	5	✅
AI Пакеты (разово)
Пакет	Цена	Описание
🎯 Базовый	$0	Стандартное приветствие, базовая квалификация
📊 Стандарт	$99	Персонализация, FAQ
⚡ Продвинутый	$199	База знаний, сценарии
🎨 Кастомный	$399	Полная настройка
🎭 Аватар	$299	Подключение аватаров
🔌 Интеграция 1С + CRM	$600	Bitrix24, AMO, KOMMO, Salesforce
Управление ценами (SuperAdmin)
Кнопка 💳 Тарифы в SuperAdmin боте:

💰 {tier} → изменить цену тарифа
👥 {tier} → изменить лимит лидов
🎭 {tier} → изменить лимит аватаров
🤖 {package} → изменить цену AI пакета
Все цены хранятся в БД и автоматически отображаются на pricing.html.

База данных
Таблица tier_settings
tier VARCHAR(20) PRIMARY KEY,    -- free, basic, pro, enterprise
name_ru VARCHAR(50),
price_usd INTEGER,
leads_limit INTEGER,
web_widgets_limit INTEGER,
social_widgets_limit INTEGER,
avatar_limit INTEGER
Таблица ai_agent_packages
package VARCHAR(20) PRIMARY KEY, -- basic, standard, advanced, custom, avatar, integration
name_ru VARCHAR(50),
price_usd INTEGER,
sort_order INTEGER
API Endpoints
Метод	Endpoint	Описание
GET	/sales/tiers	Список тарифов
GET	/sales/ai-packages	Список AI пакетов
GET	/sales/pricing.html	Динамическая страница
PATCH	/sales/tiers/{tier}	Обновить тариф
PATCH	/sales/ai-packages/{package}	Обновить пакет

---

## 📅 События (Events)

### Обзор
Система событий позволяет администраторам назначать задачи менеджерам и отслеживать их выполнение.

### Расположение кода
| Компонент | Файл |
|-----------|------|
| **События менеджера** | `bot/crm_handlers.py` |
| **Карточка менеджера** | `bot/handlers.py` |
| **Backend API** | `backend/routers/crm.py` |

### Фильтры событий

#### Для Менеджера
- **"Сегодня"** — события на текущую дату
- **"Неделя"** — от сегодня до +6 дней (7 дней всего)
- **"Все"** — без фильтров
- **"История"** — завершённые события (completed/cancelled)

#### Для Админа (Карточка менеджера)
Показывает последние 3 будущих события, назначенные админом:
- Фильтр: `created_by_user_id`, дата >= сегодня, статус `pending`
- Лимит: 20 событий

### Настройки
- **Время по умолчанию**: 12:00 (изменено с 10:00)
- **Лимит для менеджеров**: 50 событий (было 5)
- **Лимит для админа**: 20 событий (было 5)

### API Endpoints

### Исправленные баги (31.01.2026)
1. ✅ Фильтр "Неделя" показывал старые события → Исправлено
2. ✅ Увеличен лимит запроса с 5 до 50 событий
3. ✅ Восстановлен обработчик "История"
4. ✅ Восстановлена кнопка "Назад"

