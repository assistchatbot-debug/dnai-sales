# 🤖 BizDNAi Sales Agent

**Intelligent AI-powered sales assistant for Telegram with voice recognition and multi-language support.**

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-blue.svg)](https://docs.aiogram.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)

## 🚀 Features

- ✅ **AI-Powered Conversations** - GPT-based product recommendations
- 🎤 **Voice Recognition** - OpenAI Whisper for speech-to-text
- 🌍 **Multi-Language Support** - Russian, English, Kazakh, Kyrgyz, Uzbek, Ukrainian
- 📊 **Lead Management** - Automatic lead tracking and interaction logging
- 🔄 **Async Architecture** - High-performance async/await with SQLAlchemy
- 🐳 **Docker Deployment** - One-command deployment with Docker Compose

## 🏗️ Architecture
┌─────────────────┐ │ Telegram Bot │ ◄─── User Interaction └────────┬────────┘ │ ▼ ┌─────────────────┐ │ FastAPI │ ◄─── REST API │ Backend │ └────────┬────────┘ │ ├──► OpenRouter (GPT) ├──► OpenAI Whisper (STT) │ ▼ ┌─────────────────┐ │ PostgreSQL │ ◄─── Database │ (AsyncPG) │ └─────────────────┘


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

id, name, subdomain, settings, default_language, created_at
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
🔧 Environment Variables
Create a 
.env
 file with the following variables:

bash
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token

# API Configuration
API_BASE_URL=http://backend:8000

# Database (AsyncPG)
DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname?ssl=require

# AI Services
OPENROUTER_API_KEY=sk-or-v1-...
OPENAI_API_KEY=sk-proj-...
AI_MODEL=openai/gpt-oss-120b:exacto

# Company
COMPANY_ID=1
🚀 Quick Start
1. Clone Repository
bash
git clone [https://github.com/assistchatbot-debug/dnai-sales.git](https://github.com/assistchatbot-debug/dnai-sales.git)
cd dnai-sales
2. Configure Environment
bash
cp .env.example .env
# Edit .env with your credentials
3. Deploy with Docker
bash
docker-compose up -d --build
4. Check Logs
bash
docker-compose logs -f bot
docker-compose logs -f backend

📁 Project Structure
dnai-sales/
├── backend/
│   ├── routers/
│   │   ├── companies.py      # Company management
│   │   ├── sales_agent.py    # AI chat & voice
│   │   └── widget.py         # Web widget
│   ├── services/
│   │   ├── ai_service.py     # GPT integration
│   │   └── voice_service.py  # Whisper STT
│   ├── database.py           # Async DB session
│   ├── models.py             # SQLAlchemy models
│   ├── main.py               # FastAPI app
│   └── requirements.txt
├── bot/
│   ├── handlers.py           # Telegram handlers
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
POST /sales/{company_id}/chat - Text chat
POST /sales/{company_id}/voice - Voice message processing
POST /sales/{company_id}/configure - Agent configuration
Companies
POST /companies/ - Create company
GET /companies/{company_id} - Get company details
Monitoring
GET / - Health check
GET /logs - Application logs
🤖 Bot Commands
/start - Initialize bot and select language
/lang - Change language
/log - View backend logs (admin)
🌍 Supported Languages
🇬🇧 English (en)
🇷🇺 Русский (ru)
🇰🇿 Қазақша (kk)
🇰🇬 Кыргызча (ky)
🇺🇿 O'zbekcha (uz)
🇺🇦 Українська (uk)
🐛 Troubleshooting
Bot not responding
bash
docker-compose logs bot
docker-compose restart bot
Database connection errors
bash
# Check DATABASE_URL in .env
# Ensure SSL is enabled for managed databases
DATABASE_URL=postgresql+asyncpg://...?ssl=require
Async/await errors
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

Implementation Plan - Update README.md
Goal Description
Update the README.md file to reflect the current state of the project, including recently added features like the Email Service and multi-channel notifications. Also, add a "Roadmap" section to outline future development.

User Review Required
 Review the "Roadmap" section to ensure it aligns with the user's vision.
 Confirm the Environment Variables for Email Service.
Proposed Changes
Documentation
[MODIFY] 
README.md
Features: Add "Multi-Channel Notifications" (Telegram + Email).
Architecture: Mention Email Service.
Tech Stack: Add Email (SMTP) details.
Project Structure: Add backend/services/email_service.py and backend/services/telegram_service.py.
Environment Variables: Add Email configuration (EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASSWORD, ADMIN_EMAIL).
Roadmap: Add a new section with planned features (CRM Integration, Analytics Dashboard, Voice Output, Payment Integration).
Verification Plan
Manual Verification
Visual Check: Render the markdown and ensure it looks correct and covers all points.
User Review: Ask the user to review the content, especially the Roadmap and Env Vars.
