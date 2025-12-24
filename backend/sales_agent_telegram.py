from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import attributes
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
    language: Optional[str] = 'ru'
    callback_data: Optional[str] = None  # Для inline кнопок

def extract_phone_number(text: str) -> Optional[str]:
    phone_pattern = re.compile(r'\b(?:\+?7|8)?[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b')
    match = phone_pattern.search(text)
    if match:
        return re.sub(r'\D', '', match.group())
    return None

def extract_name(text: str) -> Optional[str]:
    clean_text = text.strip()
    
    ignore_words = {
        'привет', 'здравствуйте', 'добрый', 'день', 'утро', 'вечер',
        'маркетинг', 'продажи', 'финансы', 'управление', 'sales', 'marketing', 
        'finance', 'management', 'нет', 'да', 'yes', 'no', 'хорошо', 'ok'
    }
    
    phone_match = re.search(r'\b\d{10,12}\b', clean_text)
    if phone_match:
        name_part = clean_text[:phone_match.start()].strip()
        if name_part and 2 <= len(name_part) <= 30:
            words = name_part.split()
            if 1 <= len(words) <= 3:
                words_lower = [w.lower() for w in words]
                if not any(w in ignore_words for w in words_lower):
                    return name_part
        return None
    
    words_lower = [w.lower() for w in clean_text.split()]
    if any(w in ignore_words for w in words_lower):
        return None
    
    if len(clean_text) > 30 or len(clean_text) < 2:
        return None
    if any(char.isdigit() for char in clean_text):
        return None
    
    words = clean_text.split()
    if 1 <= len(words) <= 2:
        return clean_text
    
    return None

@router.post('/{company_id}/config')
async def configure_sales_agent(request: Request, company_id: int, config: SalesConfigUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SalesAgentConfig).where(SalesAgentConfig.company_id == company_id))
    sales_config = result.scalars().first()
    
    if not sales_config:
        sales_config = SalesAgentConfig(company_id=company_id)
        db.add(sales_config)
    
    if config.ai_prompt is not None:
        sales_config.ai_prompt = config.ai_prompt
    if config.product_parameters is not None:
        sales_config.product_parameters = config.product_parameters
    if config.supported_languages is not None:
        sales_config.supported_languages = config.supported_languages
    
    await db.commit()
    return {'status': 'configured'}

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
        await db.refresh(lead)
    return lead

async def get_user_language(db: AsyncSession, user_id: str, fallback: str = 'ru'):
    uid_val = int(user_id) if user_id and user_id.isdigit() else None
    if uid_val is None: return fallback
    result = await db.execute(select(UserPreference).where(UserPreference.telegram_user_id == uid_val))
    pref = result.scalars().first()
    return pref.language_code if pref else fallback

async def get_conversation_history(db: AsyncSession, lead_id: int, limit: int = 20):
    result = await db.execute(
        select(Interaction)
        .where(Interaction.lead_id == lead_id)
        .order_by(Interaction.created_at.asc())
    )
    interactions = result.scalars().all()
    history = []
    for interaction in interactions:
        if interaction.content and interaction.content not in ['received', 'sent', '[system: request confirmation]']:
            history.append({'sender': 'user', 'text': interaction.content})
        if interaction.outcome and interaction.outcome not in ['received', 'sent']:
            history.append({'sender': 'bot', 'text': interaction.outcome})
    logging.info(f'📚 Loaded history: {len(history)} messages for lead {lead_id}')
    return history[-limit:]

async def background_send_notifications(lead_contact: str, history: list, summary: str, phone: str):
    try:
        logging.info(f'📬 Starting background notification tasks for {phone}')
        try:
            await telegram_service.send_lead_notification(lead_contact=lead_contact, conversation_history=history, ai_summary=summary, lead_phone=phone)
            logging.info(f'✅ Telegram notification completed for {phone}')
        except Exception as e:
            logging.error(f'❌ Telegram notification failed: {e}')
        try:
            await email_service.send_lead_notification(lead_contact=lead_contact, conversation_history=history, ai_summary=summary, lead_phone=phone)
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
        
        language = chat_data.language or await get_user_language(db, user_id, fallback='ru')
        logging.info(f'🌐 Using language: {language} for user {user_id}')

        if not session_id:
            new_session = ProductSelectionSession(company_id=company_id, user_id=user_id)
            db.add(new_session)
            await db.flush()
            session_id = str(new_session.id)
        
        history = await get_conversation_history(db, lead_id, limit=20)
        
        confirmation_status = lead.contact_info.get('confirmation_status') if isinstance(lead.contact_info, dict) else None
        message_lower = chat_data.message.lower().strip()
        
        # Обработка callback от inline кнопок
        if chat_data.callback_data:
            if chat_data.callback_data == 'confirm_yes':
                # Подтверждение
                lead.contact_info['confirmation_status'] = 'confirmed'
                lead.status = 'contacted'
                attributes.flag_modified(lead, 'contact_info')
                await db.commit()
                await db.refresh(lead)
                
                ai_response = "Отлично!\n\nНаш менеджер свяжется с вами в ближайшее время для подключения пробного периода.\n\nГотов ответить на любые вопросы."
                
                interaction = Interaction(company_id=company_id, lead_id=lead_id, type='text', content='[button: confirm]', outcome=ai_response)
                db.add(interaction)
                await db.commit()
                
                full_history = history + [{'sender': 'user', 'text': 'Подтвердил контакты'}, {'sender': 'bot', 'text': ai_response}]
                summary = await ai_service.generate_conversation_summary(full_history, language)
                background_tasks.add_task(background_send_notifications, lead_contact=lead.contact_info['name'], history=full_history, summary=summary, phone=lead.contact_info['phone'])
                logging.info(f'📬 Report scheduled after button confirmation for lead {lead_id}')
                
                return {'session_id': session_id, 'response': ai_response, 'action': 'continue', 'remove_keyboard': True}
            
            elif chat_data.callback_data == 'edit_name':
                # Исправление имени
                lead.contact_info['confirmation_status'] = 'editing_name'
                attributes.flag_modified(lead, 'contact_info')
                await db.commit()
                await db.refresh(lead)
                
                ai_response = "Укажите, пожалуйста, правильное имя:"
                interaction = Interaction(company_id=company_id, lead_id=lead_id, type='text', content='[button: edit_name]', outcome=ai_response)
                db.add(interaction)
                await db.commit()
                
                return {'session_id': session_id, 'response': ai_response, 'action': 'continue', 'remove_keyboard': True}
            
            elif chat_data.callback_data == 'edit_phone':
                # Исправление телефона
                lead.contact_info['confirmation_status'] = 'editing_phone'
                attributes.flag_modified(lead, 'contact_info')
                await db.commit()
                await db.refresh(lead)
                
                ai_response = "Укажите, пожалуйста, правильный номер телефона:"
                interaction = Interaction(company_id=company_id, lead_id=lead_id, type='text', content='[button: edit_phone]', outcome=ai_response)
                db.add(interaction)
                await db.commit()
                
                return {'session_id': session_id, 'response': ai_response, 'action': 'continue', 'remove_keyboard': True}
        
        # Обработка текстовых сообщений в режиме подтверждения
        if confirmation_status == 'pending':
            if message_lower in ['да', 'yes', 'верно', 'correct', 'да все верно', 'все верно']:
                lead.contact_info['confirmation_status'] = 'confirmed'
                lead.status = 'contacted'
                attributes.flag_modified(lead, 'contact_info')
                await db.commit()
                await db.refresh(lead)
                
                catalog = []
                ai_response = await ai_service.get_product_recommendation(user_query=chat_data.message, history=history, product_catalog=catalog, language=language)
                
                interaction = Interaction(company_id=company_id, lead_id=lead_id, type='text', content=chat_data.message, outcome=ai_response)
                db.add(interaction)
                await db.commit()
                
                full_history = history + [{'sender': 'user', 'text': chat_data.message}, {'sender': 'bot', 'text': ai_response}]
                summary = await ai_service.generate_conversation_summary(full_history, language)
                background_tasks.add_task(background_send_notifications, lead_contact=lead.contact_info['name'], history=full_history, summary=summary, phone=lead.contact_info['phone'])
                logging.info(f'📬 Report scheduled after confirmation for lead {lead_id}')
                
                return {'session_id': session_id, 'response': ai_response, 'action': 'continue'}
            
            # Автоопределение неявного исправления
            else:
                new_name = extract_name(chat_data.message)
                new_phone = extract_phone_number(chat_data.message)
                
                if new_name and new_name != lead.contact_info.get('name'):
                    lead.contact_info['name'] = new_name
                    lead.contact_info['confirmation_status'] = 'pending'
                    attributes.flag_modified(lead, 'contact_info')
                    await db.commit()
                    await db.refresh(lead)
                    logging.info(f'✏️ Name auto-updated to: {new_name} for lead {lead_id}')
                    
                    confirmation_prompt_template = f"""Ты помощник BizDNAi. Клиент только что обновил свое имя.

ТЕКУЩИЕ ДАННЫЕ КЛИЕНТА:
Имя: {lead.contact_info['name']}
Телефон: {lead.contact_info['phone']}

ТВОЯ ЗАДАЧА: Покажи клиенту обновленные данные для проверки в формате:

"Данные обновлены. Проверьте:

Имя: [Имя]
Телефон: [Телефон]

Все верно? (Да / Исправить имя / Исправить телефон)"

ЯЗЫК ОТВЕТА: {language}"""
                    
                    catalog = []
                    ai_response = await ai_service.get_product_recommendation(
                        user_query=chat_data.message, 
                        history=history, 
                        product_catalog=catalog, 
                        system_prompt=confirmation_prompt_template,
                        language=language
                    )
                    interaction = Interaction(company_id=company_id, lead_id=lead_id, type='text', content=chat_data.message, outcome=ai_response)
                    db.add(interaction)
                    await db.commit()
                    
                    # Возвращаем с inline кнопками
                    return {
                        'session_id': session_id, 
                        'response': ai_response, 
                        'action': 'continue',
                        'show_confirmation_keyboard': True,
                        'contact_name': lead.contact_info['name'],
                        'contact_phone': lead.contact_info['phone']
                    }
                
                elif new_phone and new_phone != lead.contact_info.get('phone'):
                    lead.contact_info['phone'] = new_phone
                    lead.contact_info['confirmation_status'] = 'pending'
                    attributes.flag_modified(lead, 'contact_info')
                    await db.commit()
                    await db.refresh(lead)
                    logging.info(f'📞 Phone auto-updated to: {new_phone} for lead {lead_id}')
                    
                    confirmation_prompt_template = f"""Ты помощник BizDNAi. Клиент только что обновил свой телефон.

ТЕКУЩИЕ ДАННЫЕ КЛИЕНТА:
Имя: {lead.contact_info['name']}
Телефон: {lead.contact_info['phone']}

ТВОЯ ЗАДАЧА: Покажи клиенту обновленные данные для проверки в формате:

"Данные обновлены. Проверьте:

Имя: [Имя]
Телефон: [Телефон]

Все верно? (Да / Исправить имя / Исправить телефон)"

ЯЗЫК ОТВЕТА: {language}"""
                    
                    catalog = []
                    ai_response = await ai_service.get_product_recommendation(
                        user_query=chat_data.message, 
                        history=history, 
                        product_catalog=catalog, 
                        system_prompt=confirmation_prompt_template,
                        language=language
                    )
                    interaction = Interaction(company_id=company_id, lead_id=lead_id, type='text', content=chat_data.message, outcome=ai_response)
                    db.add(interaction)
                    await db.commit()
                    
                    return {
                        'session_id': session_id, 
                        'response': ai_response, 
                        'action': 'continue',
                        'show_confirmation_keyboard': True,
                        'contact_name': lead.contact_info['name'],
                        'contact_phone': lead.contact_info['phone']
                    }
        
        elif confirmation_status == 'editing_name':
            name = extract_name(chat_data.message)
            if name:
                lead.contact_info['name'] = name
                lead.contact_info['confirmation_status'] = 'pending'
                attributes.flag_modified(lead, 'contact_info')
                await db.commit()
                await db.refresh(lead)
                logging.info(f'✏️ Name updated to: {name} for lead {lead_id}')
            
            confirmation_prompt_template = f"""Ты помощник BizDNAi. Клиент только что обновил свое имя.

ТЕКУЩИЕ ДАННЫЕ КЛИЕНТА:
Имя: {lead.contact_info['name']}
Телефон: {lead.contact_info['phone']}

ТВОЯ ЗАДАЧА: Покажи клиенту обновленные данные для проверки в формате:

"Данные обновлены. Проверьте:

Имя: [Имя]
Телефон: [Телефон]

Все верно? (Да / Исправить имя / Исправить телефон)"

ЯЗЫК ОТВЕТА: {language}"""
            
            catalog = []
            ai_response = await ai_service.get_product_recommendation(
                user_query=chat_data.message, 
                history=history, 
                product_catalog=catalog, 
                system_prompt=confirmation_prompt_template,
                language=language
            )
            interaction = Interaction(company_id=company_id, lead_id=lead_id, type='text', content=chat_data.message, outcome=ai_response)
            db.add(interaction)
            await db.commit()
            
            return {
                'session_id': session_id, 
                'response': ai_response, 
                'action': 'continue',
                'show_confirmation_keyboard': True,
                'contact_name': lead.contact_info['name'],
                'contact_phone': lead.contact_info['phone']
            }
        
        elif confirmation_status == 'editing_phone':
            phone_number = extract_phone_number(chat_data.message)
            if phone_number:
                lead.contact_info['phone'] = phone_number
                lead.contact_info['confirmation_status'] = 'pending'
                attributes.flag_modified(lead, 'contact_info')
                await db.commit()
                await db.refresh(lead)
                logging.info(f'📞 Phone updated to: {phone_number} for lead {lead_id}')
            
            confirmation_prompt_template = f"""Ты помощник BizDNAi. Клиент только что обновил свой телефон.

ТЕКУЩИЕ ДАННЫЕ КЛИЕНТА:
Имя: {lead.contact_info['name']}
Телефон: {lead.contact_info['phone']}

ТВОЯ ЗАДАЧА: Покажи клиенту обновленные данные для проверки в формате:

"Данные обновлены. Проверьте:

Имя: [Имя]
Телефон: [Телефон]

Все верно? (Да / Исправить имя / Исправить телефон)"

ЯЗЫК ОТВЕТА: {language}"""
            
            catalog = []
            ai_response = await ai_service.get_product_recommendation(
                user_query=chat_data.message, 
                history=history, 
                product_catalog=catalog, 
                system_prompt=confirmation_prompt_template,
                language=language
            )
            interaction = Interaction(company_id=company_id, lead_id=lead_id, type='text', content=chat_data.message, outcome=ai_response)
            db.add(interaction)
            await db.commit()
            
            return {
                'session_id': session_id, 
                'response': ai_response, 
                'action': 'continue',
                'show_confirmation_keyboard': True,
                'contact_name': lead.contact_info['name'],
                'contact_phone': lead.contact_info['phone']
            }
        
        # Обычная логика
        catalog = []
        ai_response = await ai_service.get_product_recommendation(user_query=chat_data.message, history=history, product_catalog=catalog, language=language)
        
        interaction = Interaction(company_id=company_id, lead_id=lead_id, type='text', content=chat_data.message, outcome=ai_response)
        db.add(interaction)
        await db.commit()
        
        logging.info(f'💾 Saved: User=\'{chat_data.message[:30]}...\' Bot=\'{ai_response[:30]}...\'')
        
        phone_number = chat_data.phone or extract_phone_number(chat_data.message)
        if phone_number and not lead.contact_info.get('phone'):
            if not isinstance(lead.contact_info, dict):
                lead.contact_info = {}
            lead.contact_info['phone'] = phone_number
            attributes.flag_modified(lead, 'contact_info')
            await db.commit()
            await db.refresh(lead)
            logging.info(f'✅ Phone saved: {phone_number} for lead {lead_id}')
        
        name = extract_name(chat_data.message)
        if name and not lead.contact_info.get('name'):
            if not isinstance(lead.contact_info, dict):
                lead.contact_info = {}
            lead.contact_info['name'] = name
            attributes.flag_modified(lead, 'contact_info')
            await db.commit()
            await db.refresh(lead)
            logging.info(f'✅ Name saved: {name} for lead {lead_id}')
        
        await db.refresh(lead)
        
        # Если собрали оба контакта → запрашиваем подтверждение с inline кнопками
        if isinstance(lead.contact_info, dict) and lead.contact_info.get('phone') and lead.contact_info.get('name'):
            if not lead.contact_info.get('confirmation_status'):
                lead.contact_info['confirmation_status'] = 'pending'
                attributes.flag_modified(lead, 'contact_info')
                await db.commit()
                logging.info(f'✋ Awaiting confirmation for lead {lead_id}')
                
                confirmation_prompt_template = f"""Ты помощник BizDNAi. Ты только что собрал контакты клиента.

ДАННЫЕ КЛИЕНТА:
Имя: {lead.contact_info['name']}
Телефон: {lead.contact_info['phone']}

ТВОЯ ЗАДАЧА: Покажи клиенту его данные для проверки в ТОЧНОМ формате:

"Проверьте, пожалуйста, ваши данные:

Имя: [Имя]
Телефон: [Телефон]

Все верно? (Да / Исправить имя / Исправить телефон)"

НЕ ДОБАВЛЯЙ ничего лишнего! ЯЗЫК ОТВЕТА: {language}"""
                
                catalog = []
                confirmation_response = await ai_service.get_product_recommendation(
                    user_query="показать подтверждение", 
                    history=history + [{'sender': 'user', 'text': chat_data.message}, {'sender': 'bot', 'text': ai_response}], 
                    product_catalog=catalog, 
                    system_prompt=confirmation_prompt_template,
                    language=language
                )
                
                confirm_interaction = Interaction(company_id=company_id, lead_id=lead_id, type='text', content='[system: request confirmation]', outcome=confirmation_response)
                db.add(confirm_interaction)
                await db.commit()
                
                return {
                    'session_id': session_id, 
                    'response': confirmation_response, 
                    'action': 'continue',
                    'show_confirmation_keyboard': True,
                    'contact_name': lead.contact_info['name'],
                    'contact_phone': lead.contact_info['phone']
                }
        
        return {'session_id': session_id, 'response': ai_response, 'action': 'continue'}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logging.error(f'Backend Error: {e}')
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {str(e)}')

@router.post('/{company_id}/voice')
async def process_voice(request: Request, company_id: int, file: UploadFile = File(...), session_id: str = Form(...), user_id: str = Form(None), username: str = Form(None), language: str = Form('ru'), db: AsyncSession = Depends(get_db)):
    user_id = user_id or 'telegram_user'
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='File too large')
        
    safe_filename = f'{uuid.uuid4()}.ogg'
    file_location = f'/tmp/{safe_filename}'
    with open(file_location, 'wb+') as file_object:
        file_object.write(file.file.read())
    
    try:
        transcribed_text = await voice_service.transcribe_audio(file_location, language=language)
    finally:
        if os.path.exists(file_location):
            os.remove(file_location)

    lead = await get_or_create_lead(db, company_id, user_id, username)
    lead_id = lead.id
    
    history = await get_conversation_history(db, lead_id, limit=20)
    catalog = []
    
    ai_response = await ai_service.get_product_recommendation(user_query=transcribed_text, history=history, product_catalog=catalog, language=language)

    interaction = Interaction(company_id=company_id, lead_id=lead_id, type='voice', content=transcribed_text, outcome=ai_response)
    db.add(interaction)
    await db.commit()

    return {'text': transcribed_text, 'response': ai_response, 'language': language}
