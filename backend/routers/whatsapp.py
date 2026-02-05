"""
WhatsApp Setup Router
Endpoints for WhatsApp pairing integration
"""

from fastapi import APIRouter, HTTPException, Query, Body
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from uuid import uuid4
import logging
import httpx
import os
import re
import qrcode
import io
import base64

from database import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/sales/api/whatsapp', tags=['WhatsApp'])

# Config from env
GATEWAY_URL = os.getenv('GATEWAY_URL', 'http://localhost:18789')
GATEWAY_TOKEN = os.getenv('GATEWAY_TOKEN', '')
MANAGER_CHAT_ID = os.getenv('MANAGER_CHAT_ID', '803934700')
TELEGRAM_BOT_TOKEN = os.getenv('SUPER_ADMIN_CHAT_ID', '')  # Contains token if exists

# ============================================================================
# 1. PHONE LOOKUP - Find company by phone number
# ============================================================================

@router.post("/lookup")
async def lookup_company_by_phone(phone: str = Body(..., embed=True)):
    """
    Lookup company by phone number.
    
    Request:
    {
      "phone": "+77473973326"
    }
    
    Response:
    {
      "found": true,
      "company": {
        "id": 1,
        "name": "ООО ДНАи",
        "email": "..."
      }
    }
    """
    # Validate phone format
    phone = phone.strip()
    if not re.match(r'^\+7\d{10}$', phone):
        raise HTTPException(status_code=400, detail="Invalid phone format. Use +7XXXXXXXXXX")
    
    async with get_db_session() as db:
        try:
            result = await db.execute(
                text("""
                    SELECT id, name, email 
                    FROM companies 
                    WHERE phone = :phone
                    LIMIT 1
                """),
                {"phone": phone}
            )
            row = result.fetchone()
            
            if row:
                return {
                    "found": True,
                    "company": {
                        "id": row[0],
                        "name": row[1],
                        "email": row[2]
                    },
                    "error": None
                }
            else:
                return {
                    "found": False,
                    "company": None,
                    "error": "Company not found"
                }
        except Exception as e:
            logger.error(f"Lookup error: {e}")
            raise HTTPException(status_code=500, detail="Database error")


# ============================================================================
# 2. CREATE PAIRING SESSION - Start WhatsApp pairing with OpenClaw
# ============================================================================

@router.post("/pairing/create")
async def create_pairing_session(
    company_id: int = Body(..., embed=True),
    phone: str = Body(..., embed=True),
    language: str = Body("ru", embed=True)
):
    """
    Create pairing session and request QR from OpenClaw Gateway.
    
    Request:
    {
      "company_id": 1,
      "phone": "+77473973326",
      "language": "ru"
    }
    
    Response:
    {
      "pairing_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "pending",
      "qr_code": "data:image/png;base64,...",
      "expires_at": "2026-02-05T16:40:00Z"
    }
    """
    
    # Validate inputs
    phone = phone.strip()
    if not re.match(r'^\+7\d{10}$', phone):
        raise HTTPException(status_code=400, detail="Invalid phone format")
    
    if language not in ['ru', 'en']:
        language = 'ru'
    
    async with get_db_session() as db:
        try:
            # 1. Verify company exists
            company_result = await db.execute(
                text("SELECT id, name FROM companies WHERE id = :id"),
                {"id": company_id}
            )
            company = company_result.fetchone()
            
            if not company:
                raise HTTPException(status_code=404, detail="Company not found")
            
            # 2. Generate pairing_id
            pairing_id = str(uuid4())
            expires_at = datetime.utcnow() + timedelta(minutes=5)
            
            # 3. Call OpenClaw Gateway to start pairing (or use mock for testing)
            try:
                # Try to call real gateway first
                async with httpx.AsyncClient() as client:
                    gateway_response = await client.post(
                        f"{GATEWAY_URL}/api/whatsapp/pairing/start",
                        json={
                            "company_id": company_id,
                            "phone": phone
                        },
                        headers={
                            "Authorization": f"Bearer {GATEWAY_TOKEN}"
                        },
                        timeout=10.0
                    )
                    
                    if gateway_response.status_code == 200:
                        gateway_data = gateway_response.json()
                        qr_code = gateway_data.get('qr_code', '')
                        pairing_code = gateway_data.get('pairing_code', '')
                    else:
                        raise Exception("Gateway returned error")
                    
            except Exception as e:
                logger.warning(f"Gateway unavailable, using mock QR: {e}")
                # Generate mock QR code for testing
                pairing_code = f"{company_id:03d}-{phone[-6:]}"
                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                qr.add_data(pairing_code)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                qr_bytes = buffer.getvalue()
                qr_code = f"data:image/png;base64,{base64.b64encode(qr_bytes).decode()}"
            
            # 4. Insert or update into whatsapp_pairings (UPSERT)
            await db.execute(
                text("""
                    INSERT INTO whatsapp_pairings 
                    (id, company_id, phone, qr_code, pairing_code, status, 
                     language, expires_at, created_at)
                    VALUES 
                    (:id, :company_id, :phone, :qr_code, :pairing_code, 
                     'pending', :language, :expires_at, CURRENT_TIMESTAMP)
                    ON CONFLICT (company_id) DO UPDATE SET
                        id = :id,
                        phone = :phone,
                        qr_code = :qr_code,
                        pairing_code = :pairing_code,
                        status = 'pending',
                        language = :language,
                        expires_at = :expires_at,
                        linked_at = NULL
                """),
                {
                    "id": pairing_id,
                    "company_id": company_id,
                    "phone": phone,
                    "qr_code": qr_code,
                    "pairing_code": pairing_code,
                    "language": language,
                    "expires_at": expires_at
                }
            )
            await db.commit()
            
            logger.info(f"Pairing session created: {pairing_id} for company {company_id}")
            
            return {
                "pairing_id": pairing_id,
                "status": "pending",
                "qr_code": qr_code,
                "expires_at": expires_at.isoformat() + "Z",
                "expires_in": 300
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Pairing creation error: {e}")
            raise HTTPException(status_code=500, detail="Error creating pairing session")


# ============================================================================
# 3. CHECK PAIRING STATUS - Frontend polling
# ============================================================================

@router.get("/pairing/status")
async def check_pairing_status(pairing_id: str = Query(...)):
    """
    Check current status of WhatsApp pairing.
    Frontend polls this every 2 seconds.
    
    Query: ?pairing_id=550e8400-e29b-41d4-a716-446655440000
    
    Response:
    {
      "status": "pending|linked|failed|expired",
      "company_id": 1,
      "account_name": "business_company1",
      "error": null
    }
    """
    
    async with get_db_session() as db:
        try:
            result = await db.execute(
                text("""
                    SELECT id, company_id, status, account_name, expires_at
                    FROM whatsapp_pairings
                    WHERE id = :id
                """),
                {"id": pairing_id}
            )
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Pairing not found")
            
            row_id, company_id, status, account_name, expires_at = row
            
            # Check if expired
            if status == 'pending' and datetime.utcnow() > expires_at:
                await db.execute(
                    text("UPDATE whatsapp_pairings SET status = 'expired' WHERE id = :id"),
                    {"id": pairing_id}
                )
                await db.commit()
                status = 'expired'
            
            return {
                "status": status,
                "company_id": company_id,
                "account_name": account_name,
                "error": None
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Status check error: {e}")
            raise HTTPException(status_code=500, detail="Error checking status")


# ============================================================================
# 4. WEBHOOK - Receives notification from OpenClaw when WhatsApp linked
# ============================================================================

@router.post("/pairing/webhook")
async def whatsapp_pairing_webhook(
    company_id: int = Body(..., embed=True),
    pairing_id: str = Body(..., embed=True),
    status: str = Body(..., embed=True),
    account_name: str = Body(None, embed=True)
):
    """
    Webhook callback from OpenClaw Gateway when WhatsApp pairing completes.
    
    Called by: OpenClaw when WhatsApp account is successfully linked
    
    Request:
    {
      "company_id": 1,
      "pairing_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "linked",
      "account_name": "business_company1"
    }
    """
    
    if status not in ['linked', 'failed']:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    async with get_db_session() as db:
        try:
            # Update whatsapp_pairings table
            await db.execute(
                text("""
                    UPDATE whatsapp_pairings
                    SET status = :status, 
                        account_name = :account_name,
                        linked_at = CASE WHEN :status = 'linked' THEN CURRENT_TIMESTAMP ELSE NULL END
                    WHERE id = :id
                """),
                {
                    "id": pairing_id,
                    "status": status,
                    "account_name": account_name
                }
            )
            await db.commit()
            
            # Fetch company details for notification
            company_result = await db.execute(
                text("""
                    SELECT id, name, phone FROM companies WHERE id = :id
                """),
                {"id": company_id}
            )
            company = company_result.fetchone()
            
            if company:
                company_name = company[1]
                company_phone = company[2]
                
                # Send Telegram notification to Rashid
                if status == 'linked':
                    await send_telegram_notification(
                        MANAGER_CHAT_ID,
                        f"""✅ WhatsApp Successfully Connected!
                        
Company: {company_name}
Company ID: {company_id}
Phone: {company_phone}
Account: {account_name}
Linked At: {datetime.utcnow().isoformat()}"""
                    )
                    logger.info(f"WhatsApp linked for company {company_id}")
                else:
                    await send_telegram_notification(
                        MANAGER_CHAT_ID,
                        f"""❌ WhatsApp Pairing Failed

Company: {company_name}
Company ID: {company_id}
Phone: {company_phone}"""
                    )
                    logger.warning(f"WhatsApp pairing failed for company {company_id}")
            
            return {"ok": True, "status": status}
            
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            raise HTTPException(status_code=500, detail="Webhook processing error")


# ============================================================================
# HELPER: Send Telegram Notification
# ============================================================================

async def send_telegram_notification(chat_id: str, message: str):
    """Send notification to Telegram"""
    try:
        # Extract bot token from SUPER_ADMIN_CHAT_ID if it contains token
        # Format: "bot_token:chat_id" or just chat_id
        if ':' in str(TELEGRAM_BOT_TOKEN):
            token_part = str(TELEGRAM_BOT_TOKEN).split(':')[0]
        else:
            token_part = TELEGRAM_BOT_TOKEN
        
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{token_part}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                },
                timeout=5.0
            )
    except Exception as e:
        logger.error(f"Telegram notification error: {e}")
        # Don't fail the webhook if Telegram is down
        pass
