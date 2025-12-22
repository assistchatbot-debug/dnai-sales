from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, BackgroundTasks
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
                    "model": "anthropic/claude-3-haiku:beta",
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
from models import SalesAgentConfig, ProductSelectionSession, VoiceMessage, Lead, Interaction, UserPreference, Company
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import logging
import os
import httpx
import re
from services.ai_service import ai_service
from services.voice_service import voice_service
from services.telegram_service import telegram_service
from services.email_service import email_service
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix='/sales', tags=['sales_agent'])

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

async def get_or_create_lead(db: AsyncSession, company_id: int, user_id: str, username: str = None, new_session: bool = False):
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
        source = 'telegram' if uid_val else 'web'
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
            import os
            company_bot_token = os.getenv('BOT_TOKEN')
            company_manager_id = os.getenv('MANAGER_CHAT_ID')
            company_email = os.getenv('MANAGER_EMAIL', 'kabzhanov@mail.ru')
            logging.warning(f'⚠️ Company {company_id} not found, using .env fallback')
        
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
        
        catalog = []
        
        # Get company for multitenancy
        result = await db.execute(select(Company).where(Company.id == company_id))
        company = result.scalars().first()
        
        # 🔐 MULTITENANCY: Get company-specific AI or fallback to default
        from services.ai_service import get_ai_service
        company_ai = ai_service  # Default
        ai_source = ".env (default)"
        
        if company and company.ai_endpoint and company.ai_api_key:
            company_ai = get_ai_service(
                company_id=company_id,
                ai_endpoint=company.ai_endpoint,
                ai_api_key=company.ai_api_key
            )
            ai_source = f"DB (company {company_id})"
        
        logging.info(f"🤖 MULTITENANCY AI REQUEST: using {ai_source}")
        
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
        
        
        # Extract name using AI (most reliable method)
        extracted_name = None
        
        # Only try to extract if we don't have a name yet
        if not lead.contact_info or not lead.contact_info.get('name'):
            try:
                # Build conversation text for AI
                conversation_text = ""
                for msg in history[-10:]:  # Last 10 messages
                    sender = "Клиент" if msg.get('sender') == 'user' else "Бот"
                    conversation_text += f"{sender}: {msg.get('text', '')}\n"
                conversation_text += f"Бот: {ai_response}\n"
                
                # Ask AI to extract name
                extract_prompt = f"""Из этого диалога извлеки имя клиента. Ответь ТОЛЬКО именем, без ничего лишнего. Если имя не найдено, ответь: НЕТ

Диалог:
{conversation_text}

Имя клиента:"""
                
                extract_response = await ai_service.get_product_recommendation(
                    user_query=extract_prompt,
                    history=[],
                    product_catalog=[]
                )
                
                # Clean response
                name_candidate = extract_response.strip().split('\n')[0].strip()
                
                if name_candidate and name_candidate.upper() != 'НЕТ' and len(name_candidate) > 1 and len(name_candidate) < 30:
                    extracted_name = name_candidate.capitalize()
                    logging.info(f'✨ AI extracted name: {extracted_name}')
                    
            except Exception as e:
                logging.warning(f'⚠️ AI name extraction failed: {e}')
        
        # Save name if found
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
        
        # Check for confirmation words ONLY if we have phone and name
        confirm_words = ['да', 'верно', 'правильно', 'yes', 'подтверждаю', 'ок', 'ok']
        is_confirmed = any(w in chat_data.message.lower() for w in confirm_words)
        
        # Check if bot asked for confirmation in recent messages
        has_confirm_q = False
        for msg in history[-3:]:
            if msg.get('sender') == 'bot':
                bot_text = msg.get('text', '').lower()
                if 'верно' in bot_text or 'правильно' in bot_text or 'подтвердите' in bot_text or 'correct' in bot_text or 'confirm' in bot_text:
                    has_confirm_q = True
                    break
        
        saved_phone = lead.contact_info.get('phone') if lead.contact_info else None
        
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
            
            summary = await ai_service.generate_conversation_summary(full_history, language)
            
            # Extract temperature from summary
            import re
            temp_match = re.search(r'Готовность[:\s]+(\w+)', summary, re.IGNORECASE)
            if temp_match:
                temp_word = temp_match.group(1).lower()
                if 'горяч' in temp_word or 'hot' in temp_word:
                    temperature = '🔥 горячий'
                elif 'холод' in temp_word or 'cold' in temp_word:
                    temperature = '❄️ холодный'
                else:
                    temperature = '🌤 теплый'
            else:
                temperature = '🌤 теплый'
            
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
        'description': company.description,
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
    
    await email_service.send_email(
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

@router.get('/health/db')
async def check_db_health(db: AsyncSession = Depends(get_db)):
    """Check database connection"""
    try:
        await db.execute(select(Lead).limit(1))
        return {'status': 'ok', 'database': 'connected'}
    except Exception as e:
        return {'status': 'error', 'database': str(e)}


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
    catalog = []
    
    ai_response = await ai_service.get_product_recommendation(
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
            'ai_api_key': c.ai_api_key
        } for c in companies]
    except Exception as e:
        logging.error(f'Get all companies error: {e}')
        return []
