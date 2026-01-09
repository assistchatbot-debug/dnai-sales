from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
import httpx
import os
import logging

async def analyze_lead_temperature(history: list) -> str:
    """Analyze conversation to determine lead temperature"""
    try:
        conversation = "\n".join([f"{m.get('sender')}: {m.get('text')}" for m in history[-10:]])
        prompt = f"""Проанализируй диалог и определи температуру лида. Ответь ОДНИМ словом: горячий, теплый или холодный
Диалог:
{conversation}
Температура:"""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-oss-120b:exacto",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 20
                }
            )
            if resp.status_code == 200:
                temp = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip().lower()
                if "горяч" in temp:
                    return "🔥 ГОРЯЧИЙ"
                elif "холод" in temp:
                    return "❄️ холодный"
        return "🌤 теплый"
    except Exception as e:
        logging.error(f"Temperature error: {e}")
        return "🌤 теплый"
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.future import select
from database import get_db
from models import SalesAgentConfig, ProductSelectionSession, VoiceMessage, Lead, Interaction, UserPreference, Company, Company, SocialWidget, WebWidget
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import logging
import os
import httpx
import re
from services.ai_service import ai_service, get_ai_service
from services.voice_service import voice_service
from services.telegram_service import telegram_service
from services.email_service import email_service
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix='/sales', tags=['sales_agent'])

async def translate_greeting(text: str, target_lang: str) -> str:
    """Translate greeting using OpenRouter AI (Claude 3 Haiku)"""
    lang_map = {
        'en': 'English',
        'kz': 'Kazakh (Қазақша)',
        'ky': 'Kyrgyz (Кыргызча)',
        'uz': 'Uzbek (O\'zbekcha)',
        'uk': 'Ukrainian (Українська)'
    }
    
    if target_lang not in lang_map:
        logging.warning(f'Unknown target language: {target_lang}')
        return text
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-oss-120b:exacto",
                    "messages": [{
                        "role": "user",
                        "content": f"Translate this text to {lang_map[target_lang]}. Keep the same tone, style and formatting (line breaks). Return ONLY the translation with nothing else:\\n\\n{text}"
                    }],
                    "max_tokens": 500
                }
            )
            if resp.status_code == 200:
                translated = resp.json()["choices"][0]["message"]["content"].strip()
                logging.info(f'✅ Translated to {target_lang}: {translated[:50]}...')
                return translated
            else:
                logging.error(f'Translation API error: {resp.status_code}')
    except Exception as e:
        logging.error(f'Translation error [{target_lang}]: {e}')
    
    return text  # Fallback to original on error


class SalesConfigUpdate(BaseModel):
    ai_prompt: Optional[str] = None
    product_parameters: Optional[Dict[str, Any]] = None
    supported_languages: Optional[list] = None

class ChatMessage(BaseModel):
    session_id: Optional[str] = None
    message: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    fingerprint: Optional[Dict[str, Any]] = None
    phone: Optional[str] = None
    language: Optional[str] = 'ru'
    new_session: Optional[bool] = False
    source: Optional[str] = None  # 'telegram' or 'web'

def extract_phone_number(text: str) -> Optional[str]:
    cleaned = re.sub(r'[\s\-\(\)]', '', text)
    patterns = [r'\+?\d{10,15}', r'\d{3,4}\d{6,7}']
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            return match.group(0)
    return None

@router.post('/{company_id}/configure')
@limiter.limit('5/minute')
async def configure_sales_agent(request: Request, company_id: int, config: SalesConfigUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SalesAgentConfig).where(SalesAgentConfig.company_id == company_id))
    agent_config = result.scalars().first()
    if not agent_config:
        agent_config = SalesAgentConfig(company_id=company_id)
        db.add(agent_config)
    if config.ai_prompt: agent_config.ai_prompt = config.ai_prompt
    if config.product_parameters: agent_config.product_parameters = config.product_parameters
    if config.supported_languages: agent_config.supported_languages = config.supported_languages
    await db.commit()
    return {'status': 'updated'}

async def get_or_create_lead(db: AsyncSession, company_id: int, user_id: str, username: str = None, new_session: bool = False, source: str = None):
    uid_val = int(user_id) if user_id and user_id.isdigit() else None
    logging.info(f'🔧 get_or_create_lead: user_id={user_id}, uid_val={uid_val}, new_session={new_session}')
    lead = None
    
    if uid_val is not None:
        # Telegram user - search by telegram_user_id
        result = await db.execute(select(Lead).where(Lead.telegram_user_id == uid_val, Lead.company_id == company_id))
        lead = result.scalars().first()
        
        # If new_session requested, DELETE lead completely (for testing)
        # TODO: После тестирования изменить на сохранение истории
        if lead and new_session:
            logging.info(f'🗑 new_session=True, DELETING lead {lead.id} completely (test mode)')
            from sqlalchemy import delete
            # Delete interactions first (foreign key)
            await db.execute(delete(Interaction).where(Interaction.lead_id == lead.id))
            # Delete the lead itself
            await db.execute(delete(Lead).where(Lead.id == lead.id))
            await db.commit()
            logging.info(f'✅ Lead {lead.id} deleted, will create new one')
            # Don't return - fall through to create new lead below
            lead = None
    else:
        # Web user - search by visitor_id in contact_info
        from sqlalchemy import cast, String
        result = await db.execute(
            select(Lead).where(
                Lead.company_id == company_id,
                Lead.contact_info['visitor_id'].astext == user_id
            )
        )
        lead = result.scalars().first()

    if not lead:
        contact_info = {'username': username, 'visitor_id': user_id} if user_id else {'username': username}
        source = source or ('telegram' if uid_val else 'web')
        lead = Lead(company_id=company_id, telegram_user_id=uid_val, contact_info=contact_info, status='new', source=source)
        db.add(lead)
        await db.commit()
        await db.flush()
    return lead

async def get_user_language(db: AsyncSession, user_id: str):
    uid_val = int(user_id) if user_id and user_id.isdigit() else None
    if uid_val is None: return 'ru'
    result = await db.execute(select(UserPreference).where(UserPreference.telegram_user_id == uid_val))
    pref = result.scalars().first()
    return pref.language_code if pref else 'ru'

async def get_conversation_history(db: AsyncSession, lead_id: int, limit: int = 20):
    result = await db.execute(
        select(Interaction)
        .where(Interaction.lead_id == lead_id)
        .order_by(Interaction.created_at.asc())
    )
    interactions = result.scalars().all()
    history = []
    for interaction in interactions:
        if interaction.content and interaction.content not in ['received', 'sent']:
            history.append({'sender': 'user', 'text': interaction.content})
        if interaction.outcome and interaction.outcome not in ['received', 'sent']:
            history.append({'sender': 'bot', 'text': interaction.outcome})
    logging.info(f'📚 Loaded history: {len(history)} messages for lead {lead_id}')
    return history[-limit:]

async def background_send_notifications(lead_contact: str, history: list, summary: str, phone: str, company_id: int = 1):
    """
    Sends notifications to both Telegram and Email using company data from DB
    """
    try:
        logging.info(f'📬 Starting background notification tasks for {phone}, company_id={company_id}')
        
        # Get company from DB for multitenancy
        from database import get_db_session
        from models import Company
        
        async with get_db_session() as db:
            result = await db.execute(select(Company).where(Company.id == company_id))
            company = result.scalars().first()
        
        if company:
            company_bot_token = company.bot_token
            company_manager_id = company.manager_chat_id
            company_email = company.email
            logging.info(f'📧 Company {company_id}: email={company_email}, manager={company_manager_id}')
        else:
            logging.error(f'❌ Company {company_id} not found in database - cannot send notifications')
            return  # Don't send notifications if company not found
        
        # Send to Telegram using company's bot and manager
        try:
            await telegram_service.send_lead_notification(
                lead_contact=lead_contact,
                conversation_history=history,
                ai_summary=summary,
                lead_phone=phone,
                bot_token=company_bot_token,
                manager_chat_id=company_manager_id
            )
            logging.info(f'✅ Telegram notification completed for {phone}')
        except Exception as e:
            logging.error(f'❌ Telegram notification failed: {e}')
        
        # Send to Email using company email
        try:
            await email_service.send_lead_notification(
                lead_contact=lead_contact,
                conversation_history=history,
                ai_summary=summary,
                lead_phone=phone,
                to_email=company_email
            )
            logging.info(f'✅ Email notification completed for {phone}')
        except Exception as e:
            logging.error(f'❌ Email notification failed: {e}')
            
        logging.info(f'✅ All notifications completed for {phone}')
    except Exception as e:
        logging.error(f'❌ Background notification task failed: {e}')

@router.post('/{company_id}/chat')
@limiter.limit('100/minute')
async def sales_chat(request: Request, company_id: int, chat_data: ChatMessage, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    try:
        session_id = chat_data.session_id
        user_id = chat_data.user_id or 'web_user'
        
        source = chat_data.source or 'web'
        logging.info(f'📥 Incoming: user_id={user_id}, source={source}, username={chat_data.username}')
        lead = await get_or_create_lead(db, company_id, user_id, chat_data.username, chat_data.new_session)
        logging.info(f'📊 Lead created/found: id={lead.id}, telegram_user_id={lead.telegram_user_id}')
        if lead.source != source:
            lead.source = source
            await db.commit()
        lead_id = lead.id
        
        # Use language from request, fallback to DB
        language = chat_data.language or await get_user_language(db, user_id)

        if not session_id:
            new_session = ProductSelectionSession(company_id=company_id, user_id=user_id)
            db.add(new_session)
            await db.flush()
            session_id = str(new_session.id)
        
        history = await get_conversation_history(db, lead_id, limit=20)
        logging.info(f"📚🔍 DEBUG company_id={company_id}, lead_id={lead_id}, history len={len(history)}")
        
        # 🏢 MULTITENANCY: Get company-specific AI service
        result = await db.execute(select(Company).where(Company.id == company_id))
        company = result.scalars().first()
        if company and company.ai_endpoint and company.ai_api_key:
            company_ai = get_ai_service(company_id, company.ai_endpoint, company.ai_api_key)
        else:
            company_ai = ai_service  # Fallback to default
        
        catalog = []
        ai_response = await company_ai.get_product_recommendation(
            user_query=chat_data.message,
            history=history,
            product_catalog=catalog,
            language=language
        )
        
        interaction = Interaction(
            company_id=company_id, 
            lead_id=lead_id, 
            type='text', 
            content=chat_data.message,
            outcome=ai_response
        )
        db.add(interaction)
        await db.commit()
        
        logging.info(f'💾 Saved: User=\'{chat_data.message[:30]}...\' Bot=\'{ai_response[:30]}...\'')
        
        
        # Extract name from AI confirmation message (most reliable)
        import re
        extracted_name = None
        full_messages = history + [{'sender': 'bot', 'text': ai_response}]
        
        logging.info(f'🔍 Extracting name from {len(full_messages)} messages')
        
        # FIRST: Try to extract from AI confirmation messages (most accurate)
        for msg in reversed(full_messages):
            if msg.get('sender') == 'bot':
                text = msg.get('text', '')
                # Look for "Вас зовут: Имя" or "зовут: Имя"
                match = re.search(r'(?:Вас\s+)?зовут[:\s]+([А-ЯЁA-Z][а-яёa-z]+)', text, re.IGNORECASE)
                if match:
                    extracted_name = match.group(1).capitalize()
                    logging.info(f'✨ Found name from AI confirmation: {extracted_name}')
                    break
        
        # SECOND: If no confirmation yet, try user direct answers
        if not extracted_name:
            for msg in reversed(full_messages):
                if msg.get('sender') == 'user':
                    text = msg.get('text', '').strip()
                    
                    # Only simple patterns to avoid false positives
                    patterns = [
                        (r'меня зовут\s+([А-ЯЁA-Z][а-яёa-z]+)', 'меня зовут'),
                        (r'^([А-ЯЁA-Z][а-яёa-z]{2,})$', 'single name')
                    ]
                    
                    for pattern, desc in patterns:
                        match = re.search(pattern, text)
                        if match:
                            candidate = match.group(1).capitalize()
                            # Strong filter
                            if len(candidate) > 2 and candidate.lower() not in ['да', 'нет', 'ок', 'уже', 'три', 'раза', 'хорошо', 'спасибо', 'привет']:
                                extracted_name = candidate
                                logging.info(f'✨ Found name from user: {extracted_name} via {desc}')
                                break
                    
                    if extracted_name:
                        break
        
        if extracted_name:
            if not lead.contact_info:
                lead.contact_info = {}
            lead.contact_info['name'] = extracted_name
            flag_modified(lead, 'contact_info')
            await db.commit()
            logging.info(f'💾 Name saved to DB: {extracted_name}')
        else:
            logging.info('⚠️ No name extracted from conversation')

        phone_number = chat_data.phone or extract_phone_number(chat_data.message)
        
        # Save phone to contact_info
        if phone_number:
            if not lead.contact_info:
                lead.contact_info = {}
            if 'phone' not in lead.contact_info:
                lead.contact_info['phone'] = phone_number
                flag_modified(lead, 'contact_info')
                await db.commit()
                logging.info(f'✅ Phone saved: {phone_number}')
        
        
        saved_phone = lead.contact_info.get('phone') if lead.contact_info else None
        
        # Use AI to detect if user confirmed (works in ANY language!)
        is_confirmed = False
        if saved_phone:
            confirmation_prompt = f"""Пользователь ответил: "{chat_data.message}"

Это положительное подтверждение (да, согласен, верно, ok и т.д.) или отрицание?
Ответь ОДНИМ словом: ДА или НЕТ"""
            
            try:
                confirm_check = await ai_service.get_product_recommendation(
                    user_query=confirmation_prompt,
                    history=[],
                    product_catalog=[]
                )
                is_confirmed = 'да' in confirm_check.lower() or 'yes' in confirm_check.lower()
                logging.info(f'🤖 AI confirmation check: "{chat_data.message}" → {confirm_check} → {is_confirmed}')
            except Exception as e:
                logging.error(f'❌ AI confirmation check failed: {e}')
                # Fallback to simple keywords for critical cases
                simple_confirms = ['да', 'yes', 'ок', 'ok', '+', '👍']
                is_confirmed = any(w in chat_data.message.lower() for w in simple_confirms)
        
        # Check if bot asked for confirmation in recent messages
        # More robust: check if bot message contains both phone and name (confirmation pattern)
        has_confirm_q = False
        for msg in history[-3:]:
            if msg.get('sender') == 'bot':
                bot_text = msg.get('text', '').lower()
                # Check for multilingual confirmation keywords
                confirm_keywords = ['верно', 'правильно', 'подтвердите', 'correct', 'confirm', 
                                   'дұрыс', 'рас', 'туура', 'to\'g\'ri', 'вірно']  # KZ, KG, UZ, UA
                # OR check if message contains phone pattern (summary message)
                has_keyword = any(kw in bot_text for kw in confirm_keywords)
                has_phone_pattern = bool(re.search(r'\+?\d[\d\s()-]{7,}', bot_text))
                
                if has_keyword or has_phone_pattern:
                    has_confirm_q = True
                    break
        
        # DEBUG: Log confirmation conditions
        logging.info(f'🔍 Confirm check: phone={saved_phone}, confirmed={is_confirmed}, has_q={has_confirm_q}, status={lead.status}')
        logging.info(f'🔍 History last 3: {[m.get("text", "")[:50] for m in history[-3:]]}')
        
        # Send report ONLY after explicit confirmation
        if saved_phone and is_confirmed and has_confirm_q and lead.status != 'confirmed':
            lead.status = 'confirmed'
            flag_modified(lead, 'status')
            await db.commit()
            logging.info(f'✅ CONFIRMED: {saved_phone}')
            
            full_history = history + [
                {'sender': 'user', 'text': chat_data.message},
                {'sender': 'bot', 'text': ai_response}
            ]
            
            # Получаем язык менеджера из компании
            company_result = await db.execute(select(Company).where(Company.id == company_id))
            company_obj = company_result.scalars().first()
            manager_lang = company_obj.default_language if company_obj and company_obj.default_language else "ru"
            
            summary = await ai_service.generate_conversation_summary(full_history, language, manager_language=manager_lang)
            
            # Extract temperature from AI summary
            summary_lower = summary.lower()
            if 'горячий' in summary_lower or 'hot' in summary_lower or '🔥' in summary:
                temperature = '🔥 горячий'
            elif 'холодный' in summary_lower or 'cold' in summary_lower or '❄️' in summary:
                temperature = '❄️ холодный'
            else:
                temperature = '🌤 теплый'
            
            # Добавляем температуру в начало если её там нет
            if '🌡 Температура:' not in summary:
                summary = f"🌡 Температура: {temperature}\n\n" + summary
            # Save temperature to lead contact_info
            if not lead.contact_info:
                lead.contact_info = {}
            lead.contact_info['temperature'] = temperature
            flag_modified(lead, 'contact_info')
            await db.commit()
            logging.info(f'🌡 Temperature saved: {temperature}')
            
            background_tasks.add_task(
                background_send_notifications,
                lead_contact=(lead.contact_info.get('name') if lead.contact_info else None) or chat_data.username or user_id,
                history=full_history,
                summary=summary,
                phone=lead.contact_info.get('phone') if lead.contact_info else phone_number,
                company_id=company_id
            )
            logging.info(f'📬 Background task added for Telegram & Email notifications')
        
        return {'session_id': session_id, 'response': ai_response, 'action': 'continue'}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logging.error(f'Backend Error: {e}')
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {str(e)}')




@router.get('/all-leads')
async def get_all_leads(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Get ALL leads from all companies"""
    try:
        result = await db.execute(
            select(Lead).order_by(Lead.created_at.desc()).limit(limit)
        )
        leads = result.scalars().all()
        
        leads_data = []
        for lead in leads:
            source = 'Telegram' if lead.telegram_user_id else 'Web'
            if lead.source:
                source = lead.source
            contact = lead.contact_info or {}
            temperature = contact.get('temperature', 'warm')
            created_at = lead.created_at.strftime('%Y-%m-%d %H:%M') if lead.created_at else "Unknown"
            
            leads_data.append({
                'id': lead.id,
                'company_id': lead.company_id,
                'telegram_user_id': lead.telegram_user_id,
                'contact_info': lead.contact_info,
                'status': lead.status,
                'source': source,
                'temperature': temperature,
                'created_at': created_at
            })
        
        return {'leads': leads_data, 'count': len(leads_data)}
    except Exception as e:
        logging.error(f'Get all leads error: {e}')
        return {'leads': [], 'count': 0}


# === Company Management Endpoints ===

@router.get('/company/{company_id}')
async def get_company(company_id: int, db: AsyncSession = Depends(get_db)):
    """Get company details by ID"""
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalars().first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {
        'id': company.id,
        'name': company.name,
        'bin_iin': company.bin_iin,
        'phone': company.phone,
        'whatsapp': company.whatsapp,
        'email': company.email,
        'descriptions': {
            'ru': company.description,
            'en': company.description_en,
            'kz': company.description_kz,
            'ky': company.description_ky,
            'uz': company.description_uz,
            'uk': company.description_uk
        },
        'logo_url': company.logo_url
    }

@router.post('/company/upsert')
async def upsert_company(data: dict, db: AsyncSession = Depends(get_db)):
    """Create or update company"""
    company_id = data.get('id')
    
    if company_id:
        # Update existing
        result = await db.execute(select(Company).where(Company.id == company_id))
        company = result.scalars().first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        logging.info(f'📝 Updating company {company_id}')
    else:
        # Create new
        company = Company()
        db.add(company)
        logging.info(f'➕ Creating new company')
    
    # Update fields
    if 'name' in data:
        company.name = data['name']
    if 'bin_iin' in data:
        company.bin_iin = data['bin_iin']
    if 'phone' in data:
        company.phone = data['phone']
    if 'whatsapp' in data:
        company.whatsapp = data['whatsapp']
    if 'email' in data:
        company.email = data['email']
    if 'description' in data:
        company.description = data['description']
        # Auto-translate company description to other languages
        company.description_en = await translate_greeting(data['description'], 'en')
        company.description_kz = await translate_greeting(data['description'], 'kz')
        company.description_ky = await translate_greeting(data['description'], 'ky')
        company.description_uz = await translate_greeting(data['description'], 'uz')
        company.description_uk = await translate_greeting(data['description'], 'uk')
        logging.info(f'✅ Auto-translated company description for ID {company.id}')
    if 'logo_url' in data:
        company.logo_url = data['logo_url']
    
    # Multitenancy fields
    if 'bot_token' in data:
        company.bot_token = data['bot_token']
        logging.info(f'🔐 Updated bot_token for company {company_id}')
    if 'manager_chat_id' in data:
        company.manager_chat_id = data['manager_chat_id']
        logging.info(f'👤 Updated manager_chat_id for company {company_id}: {data["manager_chat_id"]}')
    if 'ai_endpoint' in data:
        company.ai_endpoint = data['ai_endpoint']
        logging.info(f'🤖 Updated ai_endpoint for company {company_id}')
    if 'ai_api_key' in data:
        company.ai_api_key = data['ai_api_key']
        logging.info(f'🔑 Updated ai_api_key for company {company_id}')
    if 'web_avatar_enabled' in data:
        company.web_avatar_enabled = bool(data['web_avatar_enabled'])
        logging.info(f'🎭 Updated web_avatar_enabled for company {company_id}: {data["web_avatar_enabled"]}')
    if 'avatar_limit' in data:
        company.avatar_limit = int(data['avatar_limit'])
        logging.info(f'🎭 Updated avatar_limit for company {company_id}: {data["avatar_limit"]}')
    
    await db.commit()
    await db.refresh(company)
    
    logging.info(f'✅ Company saved: {company.id} - {company.name}')
    return {'id': company.id, 'status': 'ok', 'name': company.name}

@router.post('/company/{company_id}/upload-logo')
async def upload_company_logo(company_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Upload company logo"""
    import os
    import uuid
    
    # Create upload directory
    upload_dir = '/var/www/bizdnai/logos'
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
    filename = f'company_{company_id}_{uuid.uuid4().hex[:8]}.{ext}'
    file_path = os.path.join(upload_dir, filename)
    
    # Save file
    with open(file_path, 'wb') as f:
        f.write(await file.read())
    
    # Update company logo_url
    logo_url = f'/logos/{filename}'
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalars().first()
    
    if company:
        company.logo_url = logo_url
        await db.commit()
        logging.info(f'📷 Logo uploaded for company {company_id}: {logo_url}')
        return {'status': 'ok', 'logo_url': logo_url}
    else:
        raise HTTPException(status_code=404, detail="Company not found")

@router.post('/{company_id}/contact-manager')
async def contact_manager(company_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """Send message to company manager"""
    user_id = data.get('user_id')
    message_text = data.get('message')
    
    # Get lead info
    lead = await get_or_create_lead(db, company_id, user_id)
    contact_info = lead.contact_info or {}
    
    # Get company
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalars().first()
    
    if not company or not company.email:
        return {'status': 'error', 'message': 'No company email configured'}
    
    # Send email
    email_text = f"""Сообщение от клиента:

Имя: {contact_info.get('name', 'Не указано')}
Телефон: {contact_info.get('phone', 'Не указано')}
Telegram ID: {user_id}

Сообщение:
{message_text}
"""
    
    await email_service.send_html_email(
        to_email=company.email,
        subject=f"Сообщение от клиента - {company.name}",
        body=email_text
    )
    
    # Save to interactions
    interaction = Interaction(
        lead_id=lead.id,
        company_id=company_id,
        content=message_text,
        outcome='Сообщение отправлено менеджеру'
    )
    db.add(interaction)
    await db.commit()
    
    logging.info(f'📧 Manager message sent for company {company_id}')
    return {'status': 'ok'}


@router.get('/companies/list')
async def list_companies(db: AsyncSession = Depends(get_db)):
    """List all companies/bots for SuperAdmin"""
    try:
        result = await db.execute(select(Company))
        companies = result.scalars().all()
        
        return {
            'companies': [
                {'id': c.id, 'name': c.name, 'subdomain': c.subdomain}
                for c in companies
            ]
        }
    except Exception as e:
        print(f"Error listing companies: {e}")
        return {'companies': []}

@router.get('/{company_id}/leads')
async def get_leads(company_id: int, limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Get recent leads for a company with enhanced details"""
    try:
        result = await db.execute(
            select(Lead).where(Lead.company_id == company_id)
            .order_by(Lead.created_at.desc())
            .limit(limit)
        )
        leads = result.scalars().all()
        
        leads_data = []
        for lead in leads:
            # Determine source
            source = 'Telegram' if lead.telegram_user_id else 'Web'
            if lead.source:
                source = lead.source # Use DB field if available
            
            # Extract temperature
            contact = lead.contact_info or {}
            temperature = contact.get('temperature', 'warm') # Default to warm
            
            # Format date
            created_at = lead.created_at.strftime('%Y-%m-%d %H:%M') if lead.created_at else "Unknown"

            leads_data.append({
                'id': lead.id,
                'telegram_user_id': lead.telegram_user_id,
                'contact_info': lead.contact_info,
                'status': lead.status,
                'source': source,
                'temperature': temperature,
                'created_at': created_at
            })
        
        return {'leads': leads_data, 'count': len(leads_data)}
    except Exception as e:
        logging.error(f'Error getting leads: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/{company_id}/leads/count')
async def get_lead_count(company_id: int, period: str = 'week', db: AsyncSession = Depends(get_db)):
    """Get lead count for day/week/month"""
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    if period == 'day':
        since = now - timedelta(days=1)
    elif period == 'month':
        since = now - timedelta(days=30)
    else:  # week
        since = now - timedelta(days=7)
    
    try:
        result = await db.execute(
            select(Lead).where(
                Lead.company_id == company_id,
                Lead.created_at >= since
            )
        )
        leads = result.scalars().all()
        return {'count': len(leads), 'period': period}
    except Exception as e:
        logging.error(f'Error counting leads: {e}')
        raise HTTPException(status_code=500, detail=str(e))

# Widget enabled state (in-memory for now, can be moved to DB)
widget_states = {}

@router.get('/{company_id}/widget-enabled')
async def check_widget_enabled(company_id: int):
    """Check if widget is enabled for company"""
    enabled = widget_states.get(company_id, True)  # Default enabled
    return {'enabled': enabled, 'company_id': company_id}

@router.post('/{company_id}/widget-enabled')
async def set_widget_enabled(company_id: int, enabled: bool = True):
    """Enable/disable widget for company"""
    widget_states[company_id] = enabled
    logging.info(f'Widget for company {company_id} set to: {enabled}')
    return {'enabled': enabled, 'company_id': company_id}

@router.get('/{company_id}/company-info')
async def get_company_info(company_id: int, db: AsyncSession = Depends(get_db)):
    """Get company information for widget (logo, name, etc.)"""
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalars().first()
    
    if not company:
        logging.warning(f'⚠️ Company {company_id} not found, returning defaults')
        return {
            'logo_url': 'https://bizdnai.com/logo.png',
            'company_name': 'BizDNAi',
            'description': None
        }
    
    logging.info(f'✅ Company info loaded from DB: logo={company.logo_url}, name={company.name}')
    
    return {
        'logo_url': company.logo_url or 'https://bizdnai.com/logo.png',
        'company_name': company.name or 'BizDNAi',
        'descriptions': {
            'ru': company.description,
            'en': company.description_en,
            'kz': company.description_kz,
            'ky': company.description_ky,
            'uz': company.description_uz,
            'uk': company.description_uk
        }
    }


@router.get('/widget/config')
async def get_widget_config(request: Request, db: AsyncSession = Depends(get_db)):
    """Get web widget config by domain from Referer header"""
    try:
        from urllib.parse import urlparse
        from models import WebWidget
        
        referer = request.headers.get('referer', '')
        if not referer:
            raise HTTPException(status_code=400, detail='Referer header required')
        
        domain = urlparse(referer).netloc.replace('www.', '')
        if not domain:
            raise HTTPException(status_code=400, detail='Invalid referer')
        
        result = await db.execute(
            select(WebWidget).where(WebWidget.domain == domain)
        )
        widget = result.scalars().first()
        
        if not widget:
            raise HTTPException(status_code=404, detail=f'Widget not found for domain: {domain}')
        
        result = await db.execute(select(Company).where(Company.id == widget.company_id))
        company = result.scalars().first()
        
        if not company:
            raise HTTPException(status_code=404, detail='Company not found')
        
        return {
            'company_id': company.id,
            'company_name': company.name,
            'web_avatar_enabled': company.web_avatar_enabled or False,
            'logo_url': company.logo_url or 'https://bizdnai.com/logo.png',
            'is_active': widget.is_active,
            'greetings': {
                'ru': widget.greeting_ru,
                'en': widget.greeting_en,
                'kz': widget.greeting_kz,
                'ky': widget.greeting_ky,
                'uz': widget.greeting_uz,
                'uk': widget.greeting_uk
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f'Get widget config error: {e}')
        raise HTTPException(status_code=500, detail=str(e))


# ============= Web Widget Management Endpoints =============

@router.get('/{company_id}/web-widgets')
async def list_web_widgets(company_id: int, db: AsyncSession = Depends(get_db)):
    """List all web widgets for company"""
    try:
        result = await db.execute(
            select(WebWidget)
            .where(WebWidget.company_id == company_id)
            .order_by(WebWidget.created_at.desc())
        )
        widgets = result.scalars().all()
        return [{
            'id': w.id,
            'domain': w.domain if hasattr(w, 'domain') else None,
            'greeting_ru': w.greeting_ru if hasattr(w, 'greeting_ru') else None,
            'is_active': w.is_active,
            'created_at': w.created_at.isoformat() if w.created_at else None
        } for w in widgets]
    except Exception as e:
        logging.error(f'List widgets error: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/{company_id}/web-widgets')
async def create_web_widget(company_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Create new web widget"""
    try:
        data = await request.json()
        domain = data.get('domain', '').strip().lower()
        greeting_ru = data.get('greeting_ru', '').strip()
        
        if not domain or not greeting_ru:
            raise HTTPException(status_code=400, detail='Domain and greeting_ru required')
        
        # Create widget (using SocialWidget model for now)
        widget = WebWidget(
            company_id=company_id,
            domain=domain,
            greeting_ru=greeting_ru,  # Using channel_name as domain
            is_active=True
        )
        
        # Auto-translate greeting to other languages
        widget.greeting_en = await translate_greeting(greeting_ru, 'en')
        widget.greeting_kz = await translate_greeting(greeting_ru, 'kz')
        widget.greeting_ky = await translate_greeting(greeting_ru, 'ky')
        widget.greeting_uz = await translate_greeting(greeting_ru, 'uz')
        widget.greeting_uk = await translate_greeting(greeting_ru, 'uk')
        logging.info(f'✅ Auto-translated greeting for widget')
        
        db.add(widget)
        await db.commit()
        await db.refresh(widget)
        
        return {'id': widget.id, 'domain': domain, 'message': 'Widget created'}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f'Create widget error: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/{company_id}/web-widgets/{widget_id}')
async def delete_web_widget(company_id: int, widget_id: int, db: AsyncSession = Depends(get_db)):
    """Delete web widget"""
    try:
        result = await db.execute(
            select(WebWidget)
            .where(WebWidget.id == widget_id)
            .where(WebWidget.company_id == company_id)
        )
        widget = result.scalars().first()
        if not widget:
            raise HTTPException(status_code=404, detail='Widget not found')
        
        await db.delete(widget)
        await db.commit()
        
        return {'message': 'Widget deleted'}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f'Delete widget error: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.patch('/{company_id}/web-widgets/{widget_id}')
async def update_web_widget(company_id: int, widget_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Update widget greeting or domain"""
    try:
        data = await request.json()
        greeting_ru = data.get('greeting_ru', '').strip() if data.get('greeting_ru') else None
        domain = data.get('domain', '').strip() if data.get('domain') else None
        
        if not greeting_ru and not domain:
            raise HTTPException(status_code=400, detail='greeting_ru or domain required')
        
        result = await db.execute(
            select(WebWidget)
            .where(WebWidget.id == widget_id)
            .where(WebWidget.company_id == company_id)
        )
        widget = result.scalars().first()
        if not widget:
            raise HTTPException(status_code=404, detail='Widget not found')
        
        # Update greeting if provided
        if greeting_ru:
            widget.greeting_ru = greeting_ru
            # Auto-translate to other languages
            widget.greeting_en = await translate_greeting(greeting_ru, 'en')
            widget.greeting_kz = await translate_greeting(greeting_ru, 'kz')
            widget.greeting_ky = await translate_greeting(greeting_ru, 'ky')
            widget.greeting_uz = await translate_greeting(greeting_ru, 'uz')
            widget.greeting_uk = await translate_greeting(greeting_ru, 'uk')
        
        # Update domain if provided
        if domain:
            widget.domain = domain
        
        await db.commit()
        
        return {'id': widget.id, 'domain': widget.domain, 'greeting_ru': widget.greeting_ru}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f'Update widget error: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@router.patch('/{company_id}/web-widgets/{widget_id}/toggle')
async def toggle_web_widget(company_id: int, widget_id: int, db: AsyncSession = Depends(get_db)):
    """Toggle widget active status"""
    try:
        result = await db.execute(
            select(WebWidget)
            .where(WebWidget.id == widget_id)
            .where(WebWidget.company_id == company_id)
        )
        widget = result.scalars().first()
        if not widget:
            raise HTTPException(status_code=404, detail='Widget not found')
        
        widget.is_active = not widget.is_active
        await db.commit()
        
        return {'id': widget.id, 'domain': widget.domain, 'is_active': widget.is_active}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f'Toggle widget error: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/health/db')
async def check_db_health(db: AsyncSession = Depends(get_db)):
    """Check database connection"""
    try:
        await db.execute(select(Lead).limit(1))
        return {'status': 'ok', 'database': 'connected'}
    except Exception as e:
        return {'status': 'error', 'database': str(e)}



@router.patch('/companies/{company_id}/language')
async def update_company_language(company_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Update company default language (for manager reports)"""
    from models import Company
    data = await request.json()
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalars().first()
    if company:
        company.default_language = data.get('language', 'ru')
        await db.commit()
        logging.info(f"✅ Company {company_id} language updated to {company.default_language}")
        return {"status": "ok", "language": company.default_language}
    raise HTTPException(status_code=404, detail="Company not found")

@router.post('/{company_id}/voice')
@limiter.limit('10/minute')
async def process_voice(request: Request, company_id: int, file: UploadFile = File(...), session_id: str = Form(...), user_id: str = Form(None), username: str = Form(None), language: str = Form('ru'), db: AsyncSession = Depends(get_db)):
    user_id = user_id or 'web_user'
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='File too large')
        
    safe_filename = f'{uuid.uuid4()}.webm'
    file_location = f'/tmp/{safe_filename}'
    with open(file_location, 'wb+') as file_object:
        file_object.write(file.file.read())
    
    try:
        # Use language from widget, fallback to DB preference
        if not language or language == 'ru':
            db_lang = await get_user_language(db, user_id)
            if db_lang:
                language = db_lang
        transcribed_text = await voice_service.transcribe_audio(file_location, language=language)
    finally:
        if os.path.exists(file_location):
            os.remove(file_location)

    lead = await get_or_create_lead(db, company_id, user_id, username)
    lead_id = lead.id
    
    history = await get_conversation_history(db, lead_id, limit=20)
    # 🏢 MULTITENANCY: Get company-specific AI
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalars().first()
    if company and company.ai_endpoint and company.ai_api_key:
        company_ai = get_ai_service(company_id, company.ai_endpoint, company.ai_api_key)
    else:
        company_ai = ai_service
    
    catalog = []
    
    ai_response = await company_ai.get_product_recommendation(
        user_query=transcribed_text,
        history=history,
        product_catalog=catalog,
        language=language
    )

    interaction = Interaction(
        company_id=company_id, 
        lead_id=lead_id, 
        type='voice', 
        content=transcribed_text,
        outcome=ai_response
    )
    db.add(interaction)
    await db.commit()

    return {'text': transcribed_text, 'response': ai_response, 'language': language}



@router.get('/companies/all')
async def get_all_companies(db: AsyncSession = Depends(get_db)):
    """Get all companies for SuperAdmin"""
    try:
        result = await db.execute(select(Company).order_by(Company.id))
        companies = result.scalars().all()
        
        return [{
            'id': c.id,
            'name': c.name,
            'email': c.email,
            'phone': c.phone,
            'whatsapp': c.whatsapp,
            'bin_iin': c.bin_iin,
            'description': c.description,
            'logo_url': c.logo_url,
            'bot_token': c.bot_token,
            'manager_chat_id': c.manager_chat_id,
            'ai_endpoint': c.ai_endpoint,
            'ai_api_key': c.ai_api_key,
            'tier': c.tier,
            'tier_expiry': c.tier_expiry.isoformat() if c.tier_expiry else None,
            'web_avatar_enabled': c.web_avatar_enabled or False,
            'avatar_limit': c.avatar_limit
        } for c in companies]
    except Exception as e:
        logging.error(f'Get all companies error: {e}')
        return []


from services.transliterate import transliterate_to_english

@router.patch('/companies/{company_id}/tier')
async def update_company_tier(company_id: int, tier_data: dict, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if 'tier' in tier_data:
        company.tier = tier_data['tier']
    if 'tier_expiry' in tier_data:
        from datetime import datetime
        expiry = tier_data['tier_expiry']
        if expiry and isinstance(expiry, str):
            company.tier_expiry = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
    await db.commit()
    return {'id': company.id, 'tier': company.tier, 'tier_expiry': str(company.tier_expiry) if company.tier_expiry else None}

@router.get("/companies/{company_id}/widgets")
async def list_widgets(company_id:int,db:AsyncSession=Depends(get_db)):
    r=await db.execute(select(SocialWidget).where(SocialWidget.company_id==company_id,SocialWidget.is_active==True))
    return {"widgets":[{"id":w.id,"channel_name":w.channel_name,"greeting_message":w.greeting_message,"widget_type":getattr(w,"widget_type","classic"),"url":f"https://bizdnai.com/w/{company_id}/{w.id}"}for w in r.scalars().all()]}

@router.post("/companies/{company_id}/widgets")
async def create_widget(company_id:int,data:dict,db:AsyncSession=Depends(get_db)):
    from sqlalchemy import func as sqlfunc
    from models import TierSettings
    
    ch=transliterate_to_english(data.get("channel_name",""))
    if not ch:raise HTTPException(400,"channel_name required")
    
    widget_type = data.get("widget_type", "classic")
    if widget_type == "avatar":
        count_q = await db.execute(select(sqlfunc.count(SocialWidget.id)).where(SocialWidget.company_id==company_id, SocialWidget.widget_type=="avatar", SocialWidget.is_active==True))
        current = count_q.scalar() or 0
        
        comp_q = await db.execute(select(Company).where(Company.id==company_id))
        comp = comp_q.scalars().first()
        
        limit = 0
        if comp:
            comp_limit = getattr(comp, 'avatar_limit', None)
            if comp_limit is not None:
                limit = comp_limit
            elif hasattr(comp, 'tier') and comp.tier:
                tier_q = await db.execute(select(TierSettings).where(TierSettings.tier==comp.tier))
                tier = tier_q.scalars().first()
                limit = getattr(tier, 'avatar_limit', 0) if tier else 0
        
        if current >= limit:
            raise HTTPException(400, f"Лимит аватаров ({limit}) достигнут. Обратитесь в поддержку для увеличения.")
    else:
        # Check social widgets limit for classic
        count_q = await db.execute(select(sqlfunc.count(SocialWidget.id)).where(SocialWidget.company_id==company_id, SocialWidget.is_active==True))
        current = count_q.scalar() or 0
        
        comp_q = await db.execute(select(Company).where(Company.id==company_id))
        comp = comp_q.scalars().first()
        
        limit = 0
        if comp and hasattr(comp, 'tier') and comp.tier:
            tier_q = await db.execute(select(TierSettings).where(TierSettings.tier==comp.tier))
            tier = tier_q.scalars().first()
            limit = tier.social_widgets_limit if tier else 0
        
        if current >= limit:
            raise HTTPException(400, f"Лимит соц. виджетов ({limit}) достигнут. Обновите тариф.")
    
    # Allow multiple widgets per channel - no uniqueness check
    w=SocialWidget(company_id=company_id,channel_name=ch,greeting_message=data.get("greeting_message","Здравствуйте!"),widget_type=data.get("widget_type","classic"),is_active=True)
    # Auto-translate greeting
    base_greeting = data.get("greeting_message","Здравствуйте!")
    w.greeting_ru = base_greeting
    w.greeting_en = await translate_greeting(base_greeting, 'en')
    w.greeting_kz = await translate_greeting(base_greeting, 'kz')
    w.greeting_ky = await translate_greeting(base_greeting, 'ky')
    w.greeting_uz = await translate_greeting(base_greeting, 'uz')
    w.greeting_uk = await translate_greeting(base_greeting, 'uk')
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return {"id":w.id,"channel_name":w.channel_name,"url":f"https://bizdnai.com/w/{company_id}/{w.id}"}



@router.get("/{company_id}/leads/stats")
async def get_leads_stats(company_id: int, db: AsyncSession = Depends(get_db)):
    """Get leads statistics for company"""
    from sqlalchemy import func
    
    # Total leads count
    total_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.company_id == company_id)
    )
    total = total_result.scalar() or 0
    
    # Count by source
    source_result = await db.execute(
        select(Lead.source, func.count(Lead.id))
        .where(Lead.company_id == company_id)
        .group_by(Lead.source)
    )
    
    sources = {}
    for source, count in source_result.all():
        sources[source or 'unknown'] = count
    
    return {
        "total": total,
        "by_source": sources
    }

@router.delete("/companies/{company_id}/widgets/{widget_id:int}")
async def delete_social_widget(
    company_id: int,
    widget_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete (deactivate) social media widget"""
    try:
        result = await db.execute(
            select(SocialWidget).where(
                SocialWidget.company_id == company_id,
                SocialWidget.id == widget_id
            )
        )
        widget = result.scalar_one_or_none()
        
        if not widget:
            raise HTTPException(status_code=404, detail='Widget not found')
        
        # Soft delete - just deactivate
        widget.is_active = False
        await db.commit()
        
        return {'message': 'Widget deleted successfully'}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f'Delete widget error: {e}')
        raise HTTPException(status_code=500, detail=str(e))



@router.patch("/companies/{company_id}/widgets/{widget_id:int}")
async def update_social_widget(company_id: int, widget_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """Update social widget (greeting, channel_name)"""
    result = await db.execute(
        select(SocialWidget).where(
            SocialWidget.id == widget_id,
            SocialWidget.company_id == company_id
        )
    )
    widget = result.scalars().first()
    
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    # Update greeting with auto-translation
    if 'greeting_message' in data:
        widget.greeting_message = data['greeting_message']
        widget.greeting_ru = data['greeting_message']
        # Auto-translate
        widget.greeting_en = await translate_greeting(data['greeting_message'], 'en')
        widget.greeting_kz = await translate_greeting(data['greeting_message'], 'kz')
        widget.greeting_ky = await translate_greeting(data['greeting_message'], 'ky')
        widget.greeting_uz = await translate_greeting(data['greeting_message'], 'uz')
        widget.greeting_uk = await translate_greeting(data['greeting_message'], 'uk')
        logging.info(f'✅ Auto-translated social widget greeting #{widget_id}')
    
    # Update channel name
    if 'channel_name' in data:
        widget.channel_name = data['channel_name']
    
    await db.commit()
    await db.refresh(widget)
    
    return {
        'id': widget.id,
        'channel_name': widget.channel_name,
        'greeting_message': widget.greeting_message,
        'status': 'updated'
    }

@router.get("/companies/{company_id}/widgets/{widget_id:int}")
async def get_widget_by_id(company_id:int,widget_id:int,db:AsyncSession=Depends(get_db)):
    """Get widget by ID with avatar limit check"""
    r=await db.execute(select(SocialWidget).where(SocialWidget.company_id==company_id,SocialWidget.id==widget_id,SocialWidget.is_active==True))
    w=r.scalar_one_or_none()
    if not w:raise HTTPException(404,"Widget not found")
    
    # Check avatar limit for avatar widgets
    widget_type = getattr(w, 'widget_type', 'classic') or 'classic'
    redirect_url = None
    is_active = w.is_active
    
    if widget_type == 'avatar':
        # Get company and check avatar_limit
        comp = await db.execute(select(Company).where(Company.id == company_id))
        company = comp.scalar_one_or_none()
        if company:
            avatar_limit = company.avatar_limit or 0
            if avatar_limit <= 0:
                # No avatar allowed, redirect to classic widget
                redirect_url = f"/w/{company_id}/{widget_id}"
                is_active = False
    
    return {"id":w.id,"company_id":w.company_id,"channel_name":w.channel_name,"widget_type":widget_type,"greeting_message":w.greeting_message,"greetings":{"ru":w.greeting_ru or w.greeting_message,"en":w.greeting_en or w.greeting_message,"kz":w.greeting_kz or w.greeting_message,"ky":w.greeting_ky or w.greeting_message,"uz":w.greeting_uz or w.greeting_message,"uk":w.greeting_uk or w.greeting_message},"is_active":is_active,"redirect_url":redirect_url}



# === Tier Settings Endpoints ===

@router.get('/tiers')
async def get_tiers(db: AsyncSession = Depends(get_db)):
    """Get all tier pricing plans"""
    from models import TierSettings
    result = await db.execute(select(TierSettings).where(TierSettings.is_active == True).order_by(TierSettings.sort_order))
    tiers = result.scalars().all()
    return [{
        'tier': t.tier,
        'name_ru': t.name_ru,
        'price_usd': t.price_usd,
        'leads_limit': t.leads_limit,
        'web_widgets_limit': t.web_widgets_limit,
        'social_widgets_limit': t.social_widgets_limit,
        'features_ru': t.features_ru or []
    } for t in tiers]

@router.get('/ai-packages')
async def get_ai_packages(db: AsyncSession = Depends(get_db)):
    """Get all AI agent packages"""
    from models import AIAgentPackage
    result = await db.execute(select(AIAgentPackage).where(AIAgentPackage.is_active == True).order_by(AIAgentPackage.sort_order))
    packages = result.scalars().all()
    return [{
        'package': p.package,
        'name_ru': p.name_ru,
        'price_usd': p.price_usd,
        'features_ru': p.features_ru or []
    } for p in packages]

@router.get('/{company_id}/tier-usage')
async def get_tier_usage(company_id: int, db: AsyncSession = Depends(get_db)):
    """Get company tier and usage stats"""
    from models import TierSettings
    from datetime import datetime, timedelta
    
    # Get company
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get tier settings
    tier_result = await db.execute(select(TierSettings).where(TierSettings.tier == (company.tier or 'free')))
    tier = tier_result.scalars().first()
    
    # Count leads this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    leads_result = await db.execute(
        select(Lead).where(Lead.company_id == company_id, Lead.created_at >= month_start)
    )
    leads_this_month = len(leads_result.scalars().all())
    
    # Count widgets
    web_widgets_result = await db.execute(select(WebWidget).where(WebWidget.company_id == company_id, WebWidget.is_active == True))
    web_widgets_count = len(web_widgets_result.scalars().all())
    
    social_widgets_result = await db.execute(select(SocialWidget).where(SocialWidget.company_id == company_id, SocialWidget.is_active == True))
    social_widgets_count = len(social_widgets_result.scalars().all())
    
    return {
        'company_id': company_id,
        'company_name': company.name,
        'current_tier': company.tier or 'free',
        'tier_name': tier.name_ru if tier else '🆓 FREE',
        'tier_expiry': company.tier_expiry.isoformat() if company.tier_expiry else None,
        'leads_used': leads_this_month,
        'leads_limit': tier.leads_limit if tier else 20,
        'web_widgets_used': web_widgets_count,
        'web_widgets_limit': tier.web_widgets_limit if tier else 1,
        'social_widgets_used': social_widgets_count,
        'social_widgets_limit': tier.social_widgets_limit if tier else 0,
        'ai_package': company.ai_package or 'basic'
    }


@router.get('/pricing.html', response_class=HTMLResponse)
async def get_pricing_html(db: AsyncSession = Depends(get_db)):
    """Generate dynamic pricing HTML page from database with language switcher"""
    from fastapi.responses import HTMLResponse
    from models import TierSettings, AIAgentPackage
    
    # Get tiers
    tiers_result = await db.execute(select(TierSettings).where(TierSettings.is_active == True).order_by(TierSettings.sort_order))
    tiers = tiers_result.scalars().all()
    
    # Get AI packages
    packages_result = await db.execute(select(AIAgentPackage).where(AIAgentPackage.is_active == True).order_by(AIAgentPackage.sort_order))
    packages = packages_result.scalars().all()
    
    # Generate tier cards with data attributes for both languages
    tier_cards = ""
    for t in tiers:
        tier_cards += f"""
        <div class="tier-card">
            <div class="tier-name">{t.name_ru}</div>
            <div class="tier-price">${t.price_usd}<span style="font-size:0.5em;color:#888" data-ru="/мес" data-en="/mo">/мес</span></div>
            <ul class="tier-features">
                <li>👥 {t.leads_limit} <span data-ru="лидов/мес" data-en="leads/mo">лидов/мес</span></li>
                <li>🌐 {t.web_widgets_limit} <span data-ru="веб-виджет" data-en="web widget">веб-виджет</span></li>
                <li>📱 {t.social_widgets_limit} <span data-ru="соц. виджетов" data-en="social widgets">соц. виджетов</span></li>
                <li>🎭 {t.avatar_limit} <span data-ru="{'аватар' if t.avatar_limit == 1 else 'аватаров'}" data-en="{'avatar' if t.avatar_limit == 1 else 'avatars'}">{'аватар' if t.avatar_limit == 1 else 'аватаров'}</span></li>
            </ul>
        </div>"""
    
    # AI package translations
    ai_names = {
        'basic': ('🎯 Базовый', '🎯 Basic'),
        'standard': ('📊 Стандарт', '📊 Standard'),
        'advanced': ('⚡ Продвинутый', '⚡ Advanced'),
        'custom': ('🎨 Кастомный', '🎨 Custom'),
        'avatar': ('🎭 Аватар', '🎭 Avatar')
    }
    ai_features = {
        'basic': ('Стандартное приветствие, базовая квалификация, сбор контактов', 'Standard greeting, basic qualification, contact collection'),
        'standard': ('Персонализация, расширенная квалификация, FAQ', 'Personalization, extended qualification, FAQ training'),
        'advanced': ('База знаний, умная квалификация, сценарии', 'Knowledge base, smart qualification, dialog scripts'),
        'custom': ('Полная настройка', 'Full customization, CRM integration, 24/7 support'),
        'avatar': ('Подключение аватаров', 'Avatar setup & configuration')
    }
    
    # Generate package rows
    package_rows = ""
    for p in packages:
        name_ru, name_en = ai_names.get(p.package, (p.name_ru, p.name_ru))
        feat_ru, feat_en = ai_features.get(p.package, ('...', '...'))
        package_rows += f"""
        <tr>
            <td><strong data-ru="{name_ru}" data-en="{name_en}">{name_ru}</strong></td>
            <td class="price">${p.price_usd}</td>
            <td data-ru="{feat_ru}" data-en="{feat_en}">{feat_ru}</td>
        </tr>"""
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title data-ru="Тарифы BizDNAi 2026" data-en="BizDNAi Pricing 2026">Тарифы BizDNAi 2026</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: linear-gradient(135deg, #667eea, #764ba2); padding: 40px 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 20px; padding: 40px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); position: relative; }}
        .lang-switcher {{ position: absolute; top: 20px; right: 20px; }}
        .lang-btn {{ padding: 8px 16px; border: 2px solid #667eea; background: white; color: #667eea; border-radius: 20px; cursor: pointer; font-weight: bold; transition: all 0.3s; }}
        .lang-btn:hover, .lang-btn.active {{ background: #667eea; color: white; }}
        h1 {{ text-align: center; color: #667eea; margin-bottom: 10px; font-size: 2.5em; }}
        h2 {{ color: #444; margin: 30px 0 20px; padding-bottom: 10px; border-bottom: 3px solid #667eea; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; margin: 30px 0; }}
        .tier-card {{ background: white; border: 2px solid #eee; border-radius: 12px; padding: 25px; transition: all 0.3s; }}
        .tier-card:hover {{ border-color: #667eea; box-shadow: 0 8px 24px rgba(102,126,234,0.2); transform: translateY(-5px); }}
        .tier-name {{ font-size: 1.5em; font-weight: bold; color: #333; margin-bottom: 10px; }}
        .tier-price {{ font-size: 2em; font-weight: bold; color: #667eea; margin-bottom: 15px; }}
        .tier-features {{ list-style: none; padding: 0; }}
        .tier-features li {{ padding: 8px 0; color: #555; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 15px; text-align: left; }}
        td {{ padding: 12px 15px; border-bottom: 1px solid #eee; }}
        .price {{ font-size: 1.3em; font-weight: bold; color: #667eea; }}
        .note {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px; }}
        .contact {{ text-align: center; margin-top: 40px; padding-top: 30px; border-top: 2px solid #eee; }}
        .contact a {{ color: #667eea; text-decoration: none; margin: 0 15px; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="lang-switcher">
            <button class="lang-btn active" onclick="setLang('ru')">🇷🇺 RU</button>
            <button class="lang-btn" onclick="setLang('en')">🇺🇸 EN</button>
        </div>
        
        <h1 data-ru="💎 Тарифы BizDNAi 2026" data-en="💎 BizDNAi Pricing 2026">💎 Тарифы BizDNAi 2026</h1>
        <p style="text-align:center;color:#666;margin-bottom:40px" data-ru="Автоматизация продаж с AI-помощником" data-en="Sales automation with AI assistant">Автоматизация продаж с AI-помощником</p>
        
        <h2 data-ru="📅 Месячная подписка" data-en="📅 Monthly Subscription">📅 Месячная подписка</h2>
        <div class="grid">{tier_cards}</div>
        
        <h2 data-ru="🤖 Настройка AI Агента" data-en="🤖 AI Agent Setup">🤖 Настройка AI Агента</h2>
        <div class="note" data-ru="⚠️ Разовый платёж" data-en="⚠️ One-time payment">⚠️ Разовый платёж</div>
        <table>
            <thead>
                <tr>
                    <th data-ru="Пакет" data-en="Package">Пакет</th>
                    <th data-ru="Цена" data-en="Price">Цена</th>
                    <th data-ru="Включено" data-en="Included">Включено</th>
                </tr>
            </thead>
            <tbody>{package_rows}</tbody>
        </table>
        
        <div class="contact">
            <h3 style="color:#667eea;margin-bottom:15px" data-ru="📞 Контакты" data-en="📞 Contact Us">📞 Контакты</h3>
            <a href="https://bizdnai.com">🌐 bizdnai.com</a>
            <a href="mailto:ceo@bizdnai.com">✉️ ceo@bizdnai.com</a>
        </div>
    </div>
    
    <script>
        let currentLang = localStorage.getItem('pricing_lang') || 'ru';
        
        function setLang(lang) {{
            currentLang = lang;
            localStorage.setItem('pricing_lang', lang);
            
            document.querySelectorAll('.lang-btn').forEach(btn => {{
                btn.classList.remove('active');
                if (btn.textContent.includes(lang.toUpperCase())) btn.classList.add('active');
            }});
            
            document.querySelectorAll('[data-ru][data-en]').forEach(el => {{
                el.textContent = el.getAttribute('data-' + lang);
            }});
            
            document.documentElement.lang = lang;
        }}
        
        // Apply saved language on load
        setLang(currentLang);
    </script>
</body>
</html>"""
    
    return HTMLResponse(content=html)


@router.post('/{company_id}/send-pricing-email')
async def send_pricing_email(company_id: int, db: AsyncSession = Depends(get_db)):
    """Send pricing HTML to company manager email"""
    from models import TierSettings, AIAgentPackage
    
    # Get company
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalars().first()
    if not company or not company.email:
        return {'status': 'error', 'message': 'No email configured'}
    
    # Get tiers
    tiers_result = await db.execute(select(TierSettings).where(TierSettings.is_active == True).order_by(TierSettings.sort_order))
    tiers = tiers_result.scalars().all()
    
    # Get packages
    packages_result = await db.execute(select(AIAgentPackage).where(AIAgentPackage.is_active == True).order_by(AIAgentPackage.sort_order))
    packages = packages_result.scalars().all()
    
    # Generate HTML email
    tier_rows = ""
    for t in tiers:
        features = ", ".join(t.features_ru or [])
        tier_rows += f"<tr><td><b>{t.name_ru}</b></td><td>${t.price_usd}/мес</td><td>{t.leads_limit} лидов</td><td>{t.web_widgets_limit} веб + {t.social_widgets_limit} соц.</td></tr>"
    
    package_rows = ""
    for p in packages:
        features = ", ".join(p.features_ru or [])
        package_rows += f"<tr><td><b>{p.name_ru}</b></td><td>${p.price_usd}</td><td>{features[:100]}...</td></tr>"
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h1 style="color: #667eea;">💎 Тарифы BizDNAi 2026</h1>
        
        <h2>📅 Месячная подписка</h2>
        <table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <tr style="background: #667eea; color: white;">
                <th>Тариф</th><th>Цена</th><th>Лиды</th><th>Виджеты</th>
            </tr>
            {tier_rows}
        </table>
        
        <h2>🤖 Настройка AI Агента (разово)</h2>
        <table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <tr style="background: #667eea; color: white;">
                <th>Пакет</th><th>Цена</th><th>Включено</th>
            </tr>
            {package_rows}
        </table>
        
        <p style="margin-top: 30px; text-align: center;">
            <a href="https://bizdnai.com/sales/pricing.html" style="display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 15px 40px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 18px;">📄 Подробнее о тарифах</a>
        </p>
        <p style="text-align: center; margin-top: 20px;">
            📧 Для смены тарифа: <b>ceo@bizdnai.com</b>
        </p>
    </body>
    </html>
    """
    
    try:
        await email_service.send_html_email(
            to_email=company.email,
            subject="💎 Тарифы BizDNAi 2026",
            html_body=html_body
        )
        logging.info(f"✅ Pricing email sent to {company.email}")
        return {'status': 'ok', 'email': company.email}
    except Exception as e:
        logging.error(f"Failed to send pricing email: {e}")
        return {'status': 'error', 'message': str(e)}


@router.patch('/tiers/{tier}')
async def update_tier(tier: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update tier settings (SuperAdmin only)"""
    from models import TierSettings
    
    result = await db.execute(select(TierSettings).where(TierSettings.tier == tier))
    tier_obj = result.scalars().first()
    
    if not tier_obj:
        raise HTTPException(status_code=404, detail="Tier not found")
    
    if 'price_usd' in data:
        tier_obj.price_usd = int(data['price_usd'])
    if 'leads_limit' in data:
        tier_obj.leads_limit = int(data['leads_limit'])
    if 'web_widgets_limit' in data:
        tier_obj.web_widgets_limit = int(data['web_widgets_limit'])
    if 'social_widgets_limit' in data:
        tier_obj.social_widgets_limit = int(data['social_widgets_limit'])
    if 'avatar_limit' in data:
        tier_obj.avatar_limit = int(data['avatar_limit'])
    
    await db.commit()
    await db.refresh(tier_obj)
    
    logging.info(f"✅ Tier {tier} updated: {data}")
    
    return {
        'tier': tier_obj.tier,
        'price_usd': tier_obj.price_usd,
        'leads_limit': tier_obj.leads_limit,
        'status': 'updated'
    }


@router.patch('/ai-packages/{package}')
async def update_ai_package(package: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update AI package price"""
    from models import AIAgentPackage
    result = await db.execute(select(AIAgentPackage).where(AIAgentPackage.package == package))
    pkg = result.scalars().first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    if 'price_usd' in data:
        pkg.price_usd = int(data['price_usd'])
    await db.commit()
    return {'package': pkg.package, 'price_usd': pkg.price_usd, 'status': 'updated'}
