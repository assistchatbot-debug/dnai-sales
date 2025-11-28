from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from models import SalesAgentConfig, ProductSelectionSession, VoiceMessage, Lead, Interaction, UserPreference
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import logging
import os
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

async def get_or_create_lead(db: AsyncSession, company_id: int, user_id: str, username: str = None):
    uid_val = int(user_id) if user_id and user_id.isdigit() else None
    if uid_val is not None:
        result = await db.execute(select(Lead).where(Lead.telegram_user_id == uid_val, Lead.company_id == company_id))
        lead = result.scalars().first()
    else:
        lead = None

    if not lead:
        contact_info = {'username': username} if username else {}
        lead = Lead(company_id=company_id, telegram_user_id=uid_val, contact_info=contact_info, status='new')
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

async def background_send_notifications(lead_contact: str, history: list, summary: str, phone: str):
    """
    Sends notifications to both Telegram and Email
    """
    try:
        logging.info(f'📬 Starting background notification tasks for {phone}')
        
        # Send to Telegram
        try:
            await telegram_service.send_lead_notification(
                lead_contact=lead_contact,
                conversation_history=history,
                ai_summary=summary,
                lead_phone=phone
            )
            logging.info(f'✅ Telegram notification completed for {phone}')
        except Exception as e:
            logging.error(f'❌ Telegram notification failed: {e}')
        
        # Send to Email
        try:
            await email_service.send_lead_notification(
                lead_contact=lead_contact,
                conversation_history=history,
                ai_summary=summary,
                lead_phone=phone
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
        
        lead = await get_or_create_lead(db, company_id, user_id, chat_data.username)
        lead_id = lead.id
        
        language = await get_user_language(db, user_id)

        if not session_id:
            new_session = ProductSelectionSession(company_id=company_id, user_id=user_id)
            db.add(new_session)
            await db.flush()
            session_id = str(new_session.id)
        
        history = await get_conversation_history(db, lead_id, limit=20)
        
        catalog = []
        ai_response = await ai_service.get_product_recommendation(
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
        
        phone_number = chat_data.phone or extract_phone_number(chat_data.message)
        
        if phone_number:
            logging.info(f'✅ Phone received: {phone_number} for lead {lead_id}')
            
            full_history = history + [
                {'sender': 'user', 'text': chat_data.message},
                {'sender': 'bot', 'text': ai_response}
            ]
            
            summary = await ai_service.generate_conversation_summary(full_history, language)
            
            background_tasks.add_task(
                background_send_notifications,
                lead_contact=chat_data.username or user_id,
                history=full_history,
                summary=summary,
                phone=phone_number
            )
            logging.info(f'📬 Background task added for Telegram & Email notifications')
        
        return {'session_id': session_id, 'response': ai_response, 'action': 'continue'}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logging.error(f'Backend Error: {e}')
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {str(e)}')

@router.post('/{company_id}/voice')
@limiter.limit('10/minute')
async def process_voice(request: Request, company_id: int, file: UploadFile = File(...), session_id: str = Form(...), user_id: str = Form(None), username: str = Form(None), db: AsyncSession = Depends(get_db)):
    user_id = user_id or 'web_user'
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='File too large')
        
    safe_filename = f'{uuid.uuid4()}.webm'
    file_location = f'/tmp/{safe_filename}'
    with open(file_location, 'wb+') as file_object:
        file_object.write(file.file.read())
    
    try:
        language = await get_user_language(db, user_id)
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
