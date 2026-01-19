"""Основной FastAPI сервер"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from pydantic import BaseModel
from typing import Optional
from loguru import logger
from contextlib import asynccontextmanager
import sys
import json

from config import settings
from database import init_db, get_session, SyncLog, ProductMapping
from bitrix24_client import Bitrix24Client
from onec_client import OneCClient
from ai_reports import AIReportsService
from sync_service import SyncService
from telegram_bot import TelegramBot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


# Настройка логирования
logger.remove()
logger.add(sys.stderr, level=settings.log_level)
logger.add("logs/app.log", rotation="1 day", retention="30 days", level=settings.log_level)


# Модели данных
class AIReportRequest(BaseModel):
    """Запрос на генерацию ИИ-отчёта"""
    query: str


class ProductMappingCreate(BaseModel):
    """Создание маппинга товара"""
    bitrix24_product_id: str
    bitrix24_product_name: str
    onec_product_code: str
    onec_product_name: str


# Lifecycle management

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация и завершение приложения"""
    logger.info("Starting application...")
    
    await init_db()
    logger.info("Database initialized")
    
    sync_service = SyncService()
    await sync_service.start_scheduler()
    logger.info("Sync scheduler started")
    
    # Отправка уведомления о запуске
    if settings.telegram_bot_token and settings.telegram_chat_id:
        telegram = TelegramBot(settings.telegram_bot_token, settings.telegram_chat_id)
        await telegram.send_message("🚀 *Middleware запущен*\n\nСистема интеграции 1С-Битрикс24 готова к работе")
        await telegram.close()
    
    yield
    
    logger.info("Shutting down application...")
    await sync_service.stop_scheduler()


# Создание приложения
app = FastAPI(
    title="1C-Bitrix24 Integration Middleware",
    description="Middleware для интеграции 1С:Бухгалтерия (KZ) с Битрикс24",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Проверка работоспособности сервиса"""
    return {
        "status": "running",
        "service": "1C-Bitrix24 Integration Middleware",
        "version": "1.0.0"
    }


@app.post("/webhook/bitrix24/deal")
async def bitrix24_deal_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """Webhook для обработки событий сделок из Bitrix24"""
    try:
        # Bitrix24 отправляет данные как form data
        form_data = await request.form()
        data = dict(form_data)
        
        logger.info(f"Received webhook data: {data}")
        
        event = data.get("event")
        if not event or event not in ["ONCRMDEALADD", "ONCRMDEALUPDATE"]:
            return {"status": "ignored", "message": f"Not a deal event: {event}"}
        
        # Получаем ID сделки из data[FIELDS][ID]
        deal_id = data.get("data[FIELDS][ID]")
        if not deal_id:
            logger.error(f"Deal ID not found in data: {data}")
            raise HTTPException(status_code=400, detail="Deal ID not found")
        
        logger.info(f"Processing deal {deal_id} from event {event}")
        background_tasks.add_task(process_deal_to_1c, deal_id, session)
        
        return {
            "status": "accepted",
            "message": f"Deal {deal_id} queued for processing"
        }
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def process_deal_to_1c(deal_id: str, session: AsyncSession):
    """Обработка сделки и отправка в 1С"""
    bitrix24 = Bitrix24Client()
    onec = OneCClient()
    telegram = None
    
    if settings.telegram_bot_token and settings.telegram_chat_id:
        telegram = TelegramBot(settings.telegram_bot_token, settings.telegram_chat_id)
    
    try:
        logger.info(f"Processing deal {deal_id} for 1C")

        # ЗАЩИТА #1: integration_enabled
        if not settings.is_integration_enabled():
            logger.info(f"Integration OFF, skip {deal_id}")
            return
        
        # ЗАЩИТА #2: дубликат
        existing = await onec.find_invoice_by_deal_id(deal_id)
        if existing:
            logger.info(f"Invoice {existing} exists, skip {deal_id}")
            return


        # ЗАЩИТА #1: Проверка integration_enabled
        if not settings.is_integration_enabled():
            logger.info(f"Integration disabled, skipping deal {deal_id}")
            return
        
        # ЗАЩИТА #2: Проверка дубликата
        existing_invoice = await onec.find_invoice_by_deal_id(deal_id)
        if existing_invoice:
            logger.info(f"✅ Invoice {existing_invoice} already exists for deal {deal_id}, skipping")
            return
        
        deal = await bitrix24.get_deal(deal_id)
        logger.info(f"Deal data: {deal}")
        
        # Проверка категории и стадии
        category_id = deal.get("CATEGORY_ID")
        stage_id = deal.get("STAGE_ID")
        is_kaspi_category = category_id == "7"
        is_success_stage = stage_id in ["C7:UC_JI5V4B", "C7:WON"]
        
        stage_id = deal.get("STAGE_ID")
        
        is_kaspi_category = category_id == "7"
        is_success_stage = stage_id in ["C7:UC_JI5V4B", "C7:WON"]
        kaspi_order_number = deal.get("UF_CRM_IM_ORDER_NUMBER", "")
        
        # Только сделки Kaspi с номером заказа
        if not (is_kaspi_category and is_success_stage):
            logger.info(f"Deal {deal_id} skipped: cat={category_id}, stage={stage_id}")
            return
        
        products = await bitrix24.get_deal_products(deal_id)
        contact_id = deal.get("CONTACT_ID")
        contact = await bitrix24.get_contact(contact_id) if contact_id else {}
        
        customer_name = contact.get("NAME", "") + " " + contact.get("LAST_NAME", "")
        customer_phone = contact.get("PHONE", [{}])[0].get("VALUE", "") if contact.get("PHONE") else ""
        
        # Получаем товары с артикулами из Bitrix24
        mapped_products = []
        for product in products:
            product_id = product.get("PRODUCT_ID")
            # Получаем полную информацию о товаре
            product_full = await bitrix24.get_product(product_id)
            
            # Берем артикул из PROPERTY_225 (Артикул Kaspi/1C)
            article = product_full.get("PROPERTY_225", {})
            if isinstance(article, dict):
                article = article.get("value", "")
            
            if article:
                mapped_products.append({
                    "article": article,  # Артикул для поиска в 1С
                    "name": product.get("PRODUCT_NAME", ""),
                    "quantity": int(product.get("QUANTITY", 1)),
                    "price": float(product.get("PRICE", 0))
                })
        
        if not mapped_products:
            logger.error(f"No mapped products for deal {deal_id}")
            if telegram:
                await telegram.notify_error(f"Нет маппинга товаров для сделки {deal_id}")
            return
        
        order_data = {
            "deal_id": deal_id,
            "deal_title": deal.get("TITLE", ""),
            "customer": {
                "name": customer_name.strip() or "Клиент Kaspi",
                "phone": customer_phone
            },
            "products": mapped_products,
            "total_amount": float(deal.get("OPPORTUNITY", 0)),
            "payment_type": "Kaspi"
        }
        
        result = await onec.create_order(order_data)
        
        if result.get("success"):
            order_number = result.get("order_number")
            await bitrix24.update_deal_field(deal_id, "UF_1C_ORDER_ID", order_number)
            from datetime import datetime
            order_date = datetime.now().strftime("%d.%m.%Y")
            await bitrix24.add_deal_comment(
                deal_id,
                f"✅ Накладная №{order_number} от {order_date} создана в 1С"
            )
            
            # Telegram уведомление
            if telegram:
                await telegram.notify_order_created(
                    deal_id, 
                    order_number, 
                    customer_name.strip() or "Клиент Kaspi"
                )
            
            log_entry = SyncLog(
                sync_type="order_to_1c",
                direction="bitrix24_to_1c",
                status="success",
                entity_id=deal_id,
                request_data=json.dumps(order_data),
                response_data=json.dumps(result)
            )
            session.add(log_entry)
            await session.commit()
            
            logger.info(f"Order {order_number} created in 1C for deal {deal_id}")
        else:
            error_msg = result.get("error", "Unknown error")
            if telegram:
                await telegram.notify_error(f"Ошибка создания накладной для сделки {deal_id}: {error_msg}")
    
    except Exception as e:
        logger.error(f"Error processing deal {deal_id}: {e}", exc_info=True)
        if telegram:
            await telegram.notify_error(f"Ошибка обработки сделки {deal_id}: {str(e)}")
    
    finally:
        await bitrix24.close()
        await onec.close()
        if telegram:
            await telegram.close()


@app.post("/api/ai-report")
async def generate_ai_report(request: AIReportRequest):
    """Генерация аналитического отчёта через ИИ"""
    ai_service = AIReportsService()
    
    try:
        logger.info(f"Generating AI report for query: {request.query}")
        report = await ai_service.generate_report(request.query)
        return {"report": report}
    
    except Exception as e:
        logger.error(f"Error generating AI report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        await ai_service.close()


@app.post("/api/sync/stock")
async def trigger_stock_sync(background_tasks: BackgroundTasks):
    """Ручной запуск синхронизации остатков"""
    sync_service = SyncService()
    background_tasks.add_task(sync_service.sync_stock_to_bitrix24)
    
    return {
        "status": "started",
        "message": "Stock synchronization started"
    }


@app.post("/api/mapping/product")
async def create_product_mapping(
    mapping: ProductMappingCreate,
    session: AsyncSession = Depends(get_session)
):
    """Создать маппинг товара"""
    try:
        new_mapping = ProductMapping(
            bitrix24_product_id=mapping.bitrix24_product_id,
            bitrix24_product_name=mapping.bitrix24_product_name,
            onec_product_code=mapping.onec_product_code,
            onec_product_name=mapping.onec_product_name
        )
        
        session.add(new_mapping)
        await session.commit()
        
        logger.info(f"Created product mapping: {mapping.bitrix24_product_id} -> {mapping.onec_product_code}")
        
        return {
            "status": "success",
            "message": "Product mapping created"
        }
    
    except Exception as e:
        logger.error(f"Error creating product mapping: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mapping/products")
async def get_product_mappings(session: AsyncSession = Depends(get_session)):
    """Получить все маппинги товаров"""
    stmt = select(ProductMapping)
    result = await session.execute(stmt)
    mappings = result.scalars().all()
    
    return {
        "mappings": [
            {
                "id": m.id,
                "bitrix24_product_id": m.bitrix24_product_id,
                "bitrix24_product_name": m.bitrix24_product_name,
                "onec_product_code": m.onec_product_code,
                "onec_product_name": m.onec_product_name
            }
            for m in mappings
        ]
    }


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        
        # Callback query (кнопки аналитики)
        if "callback_query" in data:
            callback = data["callback_query"]
            chat_id = str(callback["message"]["chat"]["id"])
            callback_data = callback["data"]
            tg = TelegramBot(settings.telegram_bot_token, chat_id, bitrix24)
            await tg.handle_callback(callback_data, chat_id)
            return {"ok": True}
        
        msg = data.get('message', {})
        text = msg.get('text', '')
        chat_id = msg.get('chat', {}).get('id')
        
        if not chat_id:
            return {"ok": True}
        
        tg = TelegramBot(settings.telegram_bot_token, str(chat_id), bitrix24)
        
        # Команды
        if text in ['/start', '/analytics', '📊']:
            await tg.send_analytics_menu(str(chat_id))
        elif '📦' in text:
            await tg.send_message("⏳ Загружаю остатки...")
            from stock_report import get_stock_report
            report = await get_stock_report(settings.onec_base_url, settings.onec_username, settings.onec_password)
            await tg.send_message(report)
        
        return {"ok": True}
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        return {"ok": False}
