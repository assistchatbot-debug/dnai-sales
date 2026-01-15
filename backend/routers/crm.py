from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy import text
from typing import Optional
from pydantic import BaseModel
from database import get_db_session

router = APIRouter(prefix='/crm', tags=['CRM'])

class LeadStatusUpdate(BaseModel):
    status_emoji: str
    status_name: str
    user_id: int
    user_name: str

class LeadAssign(BaseModel):
    user_id: int
    user_name: str

class NoteCreate(BaseModel):
    user_id: int
    user_name: str
    content: str
    is_voice: bool = False

@router.get('/{company_id}/leads')
async def get_leads(company_id: int, status_emoji: Optional[str] = None, limit: int = Query(default=50, le=200)):
    async with get_db_session() as db:
        query = "SELECT id, contact_info, status_emoji, status_name, temperature, assigned_user_name, ai_summary, created_at FROM leads WHERE company_id = :cid"
        params = {'cid': company_id}
        if status_emoji:
            query += " AND status_emoji = :emoji"
            params['emoji'] = status_emoji
        query += " ORDER BY created_at DESC LIMIT :lim"
        params['lim'] = limit
        result = await db.execute(text(query), params)
        return [{'id': r[0], 'name': r[1].get('name') if r[1] else None, 'phone': r[1].get('phone') if r[1] else None,
                 'status_emoji': r[2] or '🟢', 'status_name': r[3] or 'Новый', 'temperature': r[4] or 50,
                 'assigned_user_name': r[5], 'ai_summary': r[6], 'created_at': r[7].isoformat() if r[7] else None} for r in result.fetchall()]

@router.get('/{company_id}/leads/{lead_id}')
async def get_lead(company_id: int, lead_id: int):
    async with get_db_session() as db:
        result = await db.execute(text("SELECT id, contact_info, status_emoji, status_name, temperature, assigned_user_name, ai_summary, conversation_summary, created_at FROM leads WHERE id = :lid AND company_id = :cid"), {'lid': lead_id, 'cid': company_id})
        r = result.fetchone()
        if not r:
            raise HTTPException(404, "Lead not found")
        events = await db.execute(text("SELECT id, event_type, actor_name, data, created_at FROM lead_events WHERE lead_id = :lid ORDER BY created_at DESC LIMIT 30"), {'lid': lead_id})
        notes = await db.execute(text("SELECT id, user_name, content, is_voice, created_at FROM lead_notes WHERE lead_id = :lid ORDER BY created_at DESC"), {'lid': lead_id})
        return {'id': r[0], 'name': r[1].get('name') if r[1] else None, 'phone': r[1].get('phone') if r[1] else None, 'contact_info': r[1],
                'status_emoji': r[2], 'status_name': r[3], 'temperature': r[4], 'assigned_user_name': r[5], 'ai_summary': r[6], 'conversation_summary': r[7], 'created_at': r[8].isoformat() if r[8] else None,
                'events': [{'id': e[0], 'type': e[1], 'actor_name': e[2], 'data': e[3], 'created_at': e[4].isoformat() if e[4] else None} for e in events.fetchall()],
                'notes': [{'id': n[0], 'user_name': n[1], 'content': n[2], 'is_voice': n[3], 'created_at': n[4].isoformat() if n[4] else None} for n in notes.fetchall()]}

@router.patch('/{company_id}/leads/{lead_id}/status')
async def update_status(company_id: int, lead_id: int, data: LeadStatusUpdate):
    async with get_db_session() as db:
        coins_result = await db.execute(text("SELECT coins FROM lead_status_settings WHERE company_id = :cid AND emoji = :emoji"), {'cid': company_id, 'emoji': data.status_emoji})
        coins = (coins_result.fetchone() or [0])[0]
        await db.execute(text("UPDATE leads SET status_emoji = :emoji, status_name = :name, status_changed_at = NOW() WHERE id = :lid"), {'emoji': data.status_emoji, 'name': data.status_name, 'lid': lead_id})
        await db.execute(text("INSERT INTO lead_events (company_id, lead_id, event_type, actor_user_id, actor_name, data) VALUES (:cid, :lid, 'status_changed', :uid, :uname, :data)"),
                        {'cid': company_id, 'lid': lead_id, 'uid': data.user_id, 'uname': data.user_name, 'data': f'{{"emoji":"{data.status_emoji}","name":"{data.status_name}"}}'})
        if coins:
            await db.execute(text("INSERT INTO manager_coins (company_id, user_id, user_name, total_coins, weekly_coins) VALUES (:cid, :uid, :uname, :c, :c) ON CONFLICT (company_id, user_id) DO UPDATE SET total_coins = manager_coins.total_coins + :c, weekly_coins = manager_coins.weekly_coins + :c"),
                            {'cid': company_id, 'uid': data.user_id, 'uname': data.user_name, 'c': coins})
        await db.commit()
        return {'success': True, 'coins_earned': coins}

@router.patch('/{company_id}/leads/{lead_id}/assign')
async def assign_lead(company_id: int, lead_id: int, data: LeadAssign):
    async with get_db_session() as db:
        await db.execute(text("UPDATE leads SET assigned_user_id = :uid, assigned_user_name = :uname WHERE id = :lid"), {'uid': data.user_id, 'uname': data.user_name, 'lid': lead_id})
        await db.execute(text("INSERT INTO lead_events (company_id, lead_id, event_type, actor_user_id, actor_name, data) VALUES (:cid, :lid, 'assigned', :uid, :uname, '{}')"), {'cid': company_id, 'lid': lead_id, 'uid': data.user_id, 'uname': data.user_name})
        await db.commit()
        return {'success': True}

@router.post('/{company_id}/leads/{lead_id}/notes')
async def add_note(company_id: int, lead_id: int, data: NoteCreate):
    async with get_db_session() as db:
        result = await db.execute(text("INSERT INTO lead_notes (company_id, lead_id, user_id, user_name, content, is_voice) VALUES (:cid, :lid, :uid, :uname, :content, :voice) RETURNING id"),
                                 {'cid': company_id, 'lid': lead_id, 'uid': data.user_id, 'uname': data.user_name, 'content': data.content, 'voice': data.is_voice})
        await db.commit()
        return {'success': True, 'note_id': result.fetchone()[0]}

@router.get('/{company_id}/statuses')
async def get_statuses(company_id: int):
    async with get_db_session() as db:
        result = await db.execute(text("SELECT id, emoji, name, coins, max_time_minutes, is_final FROM lead_status_settings WHERE company_id = :cid ORDER BY sort_order"), {'cid': company_id})
        return [{'id': r[0], 'emoji': r[1], 'name': r[2], 'coins': r[3], 'max_time_minutes': r[4], 'is_final': r[5]} for r in result.fetchall()]

@router.get('/{company_id}/templates')
async def get_templates(company_id: int):
    async with get_db_session() as db:
        result = await db.execute(text("SELECT id, name, content FROM reply_templates WHERE company_id = :cid ORDER BY sort_order"), {'cid': company_id})
        return [{'id': r[0], 'name': r[1], 'content': r[2]} for r in result.fetchall()]

@router.get('/{company_id}/coins/leaderboard')
async def get_leaderboard(company_id: int):
    async with get_db_session() as db:
        result = await db.execute(text("SELECT user_id, user_name, total_coins, weekly_coins FROM manager_coins WHERE company_id = :cid ORDER BY weekly_coins DESC LIMIT 10"), {'cid': company_id})
        return [{'user_id': r[0], 'user_name': r[1], 'total_coins': r[2], 'weekly_coins': r[3]} for r in result.fetchall()]

@router.get('/{company_id}/stats')
async def get_stats(company_id: int):
    async with get_db_session() as db:
        by_status = await db.execute(text("SELECT status_emoji, COUNT(*) FROM leads WHERE company_id = :cid GROUP BY status_emoji"), {'cid': company_id})
        total = await db.execute(text("SELECT COUNT(*) FROM leads WHERE company_id = :cid"), {'cid': company_id})
        today = await db.execute(text("SELECT COUNT(*) FROM leads WHERE company_id = :cid AND created_at >= CURRENT_DATE"), {'cid': company_id})
        return {'total': total.scalar(), 'today': today.scalar(), 'by_status': {r[0] or '🟢': r[1] for r in by_status.fetchall()}}

# ============ MANAGERS ============

@router.get('/{company_id}/managers')
async def get_managers(company_id: int):
    """Get all managers of company"""
    async with get_db_session() as db:
        result = await db.execute(text("""
            SELECT id, user_id, telegram_username, full_name, is_active, created_at
            FROM company_managers WHERE company_id = :cid AND is_active = TRUE
            ORDER BY created_at
        """), {'cid': company_id})
        return [{'id': r[0], 'user_id': r[1], 'telegram_username': r[2], 'full_name': r[3], 
                 'is_active': r[4], 'created_at': r[5].isoformat() if r[5] else None} for r in result.fetchall()]



@router.post("/{company_id}/managers")
async def register_manager(company_id: int, data: dict = Body(...)):
    """Register new manager for company"""
    user_id = data.get('telegram_id')
    telegram_username = data.get('telegram_username', '')
    full_name = data.get('full_name', 'Менеджер')
    
    async with get_db_session() as db:
        # Check if already exists
        result = await db.execute(text("""
            SELECT id FROM company_managers 
            WHERE company_id = :cid AND user_id = :uid
        """), {'cid': company_id, 'uid': user_id})
        
        if result.fetchone():
            return {"status": "exists", "message": "Already registered"}
        
        # Insert new manager
        await db.execute(text("""
            INSERT INTO company_managers (company_id, user_id, telegram_username, full_name, is_active)
            VALUES (:cid, :uid, :username, :name, true)
        """), {'cid': company_id, 'uid': user_id, 'username': telegram_username, 'name': full_name})
        
        await db.commit()
        return {"status": "ok", "message": "Registered successfully"}

@router.get("/{company_id}/leads/{lead_id}")
async def get_lead_details(company_id: int, lead_id: int):
    """Get single lead details"""
    async with get_db_session() as db:
        result = await db.execute(text("""
            SELECT id, contact_info, status, source, created_at, telegram_user_id
            FROM leads WHERE company_id = :cid AND id = :lid
        """), {'cid': company_id, 'lid': lead_id})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Lead not found")
        return {
            'id': row[0],
            'contact_info': row[1],
            'status': row[2],
            'source': row[3],
            'created_at': str(row[4]) if row[4] else None,
            'telegram_user_id': row[5]
        }



@router.get('/{company_id}/managers/{user_id}')
async def get_manager(company_id: int, user_id: int):
    """Check if user is a manager"""
    async with get_db_session() as db:
        result = await db.execute(text("""
            SELECT id, full_name FROM company_managers 
            WHERE company_id = :cid AND user_id = :uid AND is_active = TRUE
        """), {'cid': company_id, 'uid': user_id})
        row = result.fetchone()
        if not row:
            raise HTTPException(404, "Not a manager")
        return {'id': row[0], 'full_name': row[1]}

@router.post('/{company_id}/managers')
async def add_manager(company_id: int, data: dict):
    """Add new manager (self-registration via /join)"""
    async with get_db_session() as db:
        try:
            await db.execute(text("""
                INSERT INTO company_managers (company_id, user_id, telegram_username, full_name)
                VALUES (:cid, :uid, :username, :name)
            """), {'cid': company_id, 'uid': data['user_id'], 'username': data.get('telegram_username', ''), 'name': data.get('full_name', '')})
            await db.commit()
            return {'success': True}
        except Exception as e:
            if 'unique' in str(e).lower():
                raise HTTPException(409, "Already registered")
            raise HTTPException(500, str(e))

@router.delete('/{company_id}/managers/{user_id}')
async def remove_manager(company_id: int, user_id: int):
    """Deactivate manager"""
    async with get_db_session() as db:
        await db.execute(text("""
            UPDATE company_managers SET is_active = FALSE WHERE company_id = :cid AND user_id = :uid
        """), {'cid': company_id, 'uid': user_id})
        await db.commit()
        return {'success': True}

@router.patch("/{company_id}/leads/{lead_id}/status")
async def update_lead_status(company_id: int, lead_id: int, data: dict = Body(...)):
    """Update lead status and award coins"""
    new_status = data.get('status')
    manager_id = data.get('manager_id')
    
    async with get_db_session() as db:
        # Update lead status
        await db.execute(text("""
            UPDATE leads SET status = :status WHERE id = :lid AND company_id = :cid
        """), {'status': new_status, 'lid': lead_id, 'cid': company_id})
        
        # Get status info for coins
        status_result = await db.execute(text("""
            SELECT name, coins FROM lead_status_settings 
            WHERE company_id = :cid AND id = :sid
        """), {'cid': company_id, 'sid': int(new_status) if new_status.isdigit() else 1})
        status_row = status_result.fetchone()
        
        coins_earned = 0
        status_name = new_status
        
        if status_row:
            status_name = status_row[0]
            coins_earned = status_row[1] or 0
            
            # Award coins to manager
            if coins_earned > 0 and manager_id:
                await db.execute(text("""
                    UPDATE company_managers SET coins = coins + :coins 
                    WHERE company_id = :cid AND user_id = :uid
                """), {'coins': coins_earned, 'cid': company_id, 'uid': manager_id})
        
        # Log event
        await db.execute(text("""
            INSERT INTO lead_events (company_id, lead_id, event_type, data)
            VALUES (:cid, :lid, 'status_changed', :data)
        """), {'cid': company_id, 'lid': lead_id, 'data': f'{{"status": "{new_status}", "manager_id": {manager_id}}}'})
        
        await db.commit()
        return {"status": "ok", "status_name": status_name, "coins_earned": coins_earned}


@router.post("/{company_id}/leads/{lead_id}/notes")
async def add_lead_note(company_id: int, lead_id: int, data: dict = Body(...)):
    """Add note to lead"""
    note_text = data.get('text', '')
    user_id = data.get('manager_id')
    user_name = data.get('user_name', 'Менеджер')
    is_voice = data.get('is_voice', False)
    
    async with get_db_session() as db:
        await db.execute(text("""
            INSERT INTO lead_notes (company_id, lead_id, user_id, user_name, content, is_voice)
            VALUES (:cid, :lid, :uid, :uname, :content, :voice)
        """), {'cid': company_id, 'lid': lead_id, 'uid': user_id, 'uname': user_name, 'content': note_text, 'voice': is_voice})
        await db.commit()
        return {"status": "ok"}


@router.get("/{company_id}/managers/{user_id}")
async def get_manager_info(company_id: int, user_id: int):
    """Get manager info with stats"""
    async with get_db_session() as db:
        result = await db.execute(text("""
            SELECT full_name, coins, 
                   (SELECT COUNT(*) FROM lead_events WHERE data::text LIKE :uid_pattern) as leads_count,
                   (SELECT COUNT(*) FROM leads WHERE company_id = :cid AND status = 'deal') as deals_count
            FROM company_managers WHERE company_id = :cid AND user_id = :uid
        """), {'cid': company_id, 'uid': user_id, 'uid_pattern': f'%{user_id}%'})
        row = result.fetchone()
        if row:
            return {"full_name": row[0], "coins": row[1] or 0, "leads_count": row[2] or 0, "deals_count": row[3] or 0}
        return {"coins": 0, "leads_count": 0, "deals_count": 0}


@router.get("/{company_id}/leaderboard")
async def get_leaderboard(company_id: int):
    """Get managers leaderboard"""
    async with get_db_session() as db:
        result = await db.execute(text("""
            SELECT full_name, coins FROM company_managers 
            WHERE company_id = :cid AND is_active = TRUE
            ORDER BY coins DESC LIMIT 10
        """), {'cid': company_id})
        return [{"full_name": r[0], "coins": r[1] or 0} for r in result.fetchall()]

