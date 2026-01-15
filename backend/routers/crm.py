"""CRM Router - Clean version without duplicates"""
from fastapi import APIRouter, HTTPException, Body, Query
from sqlalchemy import text
from typing import Optional
from database import get_db_session

router = APIRouter(prefix='/crm', tags=['CRM'])

# === LEADS ===

@router.get("/{company_id}/leads")
async def get_leads(company_id: int, limit: int = Query(default=50, le=200)):
    """Get leads with assigned info"""
    async with get_db_session() as db:
        result = await db.execute(text("""
            SELECT id, contact_info, status, source, created_at, telegram_user_id,
                   assigned_user_id, assigned_user_name, ai_summary, conversation_summary,
                   temperature, status_emoji, status_name
            FROM leads WHERE company_id = :cid
            ORDER BY created_at DESC LIMIT :lim
        """), {'cid': company_id, 'lim': limit})
        leads = []
        for row in result.fetchall():
            leads.append({
                'id': row[0],
                'contact_info': row[1],
                'status': row[2],
                'source': row[3],
                'created_at': str(row[4]) if row[4] else None,
                'telegram_user_id': row[5],
                'assigned_user_id': row[6],
                'assigned_user_name': row[7],
                'ai_summary': row[8],
                'conversation_summary': row[9],
                'temperature': row[10],
                'status_emoji': row[11] or '🆕',
                'status_name': row[12] or 'Новый'
            })
        return leads


@router.get("/{company_id}/leads/{lead_id}")
async def get_lead_details(company_id: int, lead_id: int):
    """Get single lead with all details"""
    async with get_db_session() as db:
        result = await db.execute(text("""
            SELECT id, contact_info, status, source, created_at, telegram_user_id,
                   assigned_user_id, assigned_user_name, ai_summary, conversation_summary,
                   temperature, status_emoji, status_name
            FROM leads WHERE company_id = :cid AND id = :lid
        """), {'cid': company_id, 'lid': lead_id})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Lead not found")
        # Get notes
        notes_result = await db.execute(text("""
            SELECT user_name, content, created_at FROM lead_notes 
            WHERE lead_id = :lid ORDER BY created_at DESC LIMIT 5
        """), {'lid': lead_id})
        notes = [{"user_name": n[0], "content": n[1], "created_at": str(n[2]) if n[2] else None} 
                 for n in notes_result.fetchall()]
        
        return {
            'id': row[0],
            'contact_info': row[1],
            'status': row[2],
            'source': row[3],
            'created_at': str(row[4]) if row[4] else None,
            'telegram_user_id': row[5],
            'assigned_user_id': row[6],
            'assigned_user_name': row[7],
            'ai_summary': row[8],
            'conversation_summary': row[9],
            'temperature': row[10],
            'status_emoji': row[11] or '🆕',
            'status_name': row[12] or 'Новый',
            'notes': notes
        }


@router.patch("/{company_id}/leads/{lead_id}/assign")
async def assign_lead(company_id: int, lead_id: int, data: dict = Body(...)):
    """Assign lead to manager, set status, award +1 coin"""
    user_id = data.get('user_id')
    user_name = data.get('user_name', 'Менеджер')
    
    async with get_db_session() as db:
        # Получить имя менеджера из БД
        mgr_result = await db.execute(text("""
            SELECT full_name FROM company_managers 
            WHERE company_id = :cid AND user_id = :uid
        """), {'cid': company_id, 'uid': user_id})
        mgr_row = mgr_result.fetchone()
        if mgr_row and mgr_row[0]:
            user_name = mgr_row[0]
        
        # Обновить лид
        await db.execute(text("""
            UPDATE leads 
            SET assigned_user_id = :uid, assigned_user_name = :uname, 
                status = 'in_progress', status_emoji = '📞', status_name = 'В работе',
                status_changed_at = NOW()
            WHERE id = :lid AND company_id = :cid
        """), {'uid': user_id, 'uname': user_name, 'lid': lead_id, 'cid': company_id})
        
        # Начислить +1 монетку менеджеру
        await db.execute(text("""
            UPDATE company_managers SET coins = coins + 1 
            WHERE company_id = :cid AND user_id = :uid
        """), {'cid': company_id, 'uid': user_id})
        
        # Записать событие
        await db.execute(text("""
            INSERT INTO lead_events (company_id, lead_id, event_type, data)
            VALUES (:cid, :lid, 'assigned', :data)
        """), {'cid': company_id, 'lid': lead_id, 'data': f'{{"user_id": {user_id}, "user_name": "{user_name}"}}'})
        
        await db.commit()
        return {"status": "ok", "coins_earned": 1}


@router.patch("/{company_id}/leads/{lead_id}/status")
async def update_lead_status(company_id: int, lead_id: int, data: dict = Body(...)):
    """Update lead status and award coins"""
    new_status = data.get('status')
    manager_id = data.get('manager_id')
    
    async with get_db_session() as db:
        # Get status info
        status_result = await db.execute(text("""
            SELECT id, emoji, name, coins FROM lead_status_settings 
            WHERE company_id = :cid AND id = :sid
        """), {'cid': company_id, 'sid': int(new_status) if str(new_status).isdigit() else 1})
        status_row = status_result.fetchone()
        
        if status_row:
            status_id, emoji, name, coins = status_row
        else:
            emoji, name, coins = '🆕', 'Новый', 0
        
        # Update lead
        await db.execute(text("""
            UPDATE leads SET status = :status, status_emoji = :emoji, status_name = :name,
                   status_changed_at = NOW()
            WHERE id = :lid AND company_id = :cid
        """), {'status': new_status, 'emoji': emoji, 'name': name, 'lid': lead_id, 'cid': company_id})
        
        # Award coins
        if coins and manager_id:
            await db.execute(text("""
                UPDATE company_managers SET coins = coins + :coins 
                WHERE company_id = :cid AND user_id = :uid
            """), {'coins': coins, 'cid': company_id, 'uid': manager_id})
        
        await db.commit()
        return {"status": "ok", "status_name": name, "coins_earned": coins or 0}


@router.post("/{company_id}/leads/{lead_id}/notes")
async def add_lead_note(company_id: int, lead_id: int, data: dict = Body(...)):
    """Add note to lead"""
    content = data.get('text', '')
    user_id = data.get('manager_id')
    user_name = data.get('user_name', 'Менеджер')
    is_voice = data.get('is_voice', False)
    
    async with get_db_session() as db:
        await db.execute(text("""
            INSERT INTO lead_notes (company_id, lead_id, user_id, user_name, content, is_voice)
            VALUES (:cid, :lid, :uid, :uname, :content, :voice)
        """), {'cid': company_id, 'lid': lead_id, 'uid': user_id, 'uname': user_name, 'content': content, 'voice': is_voice})
        await db.commit()
        return {"status": "ok"}


# === STATUSES ===

@router.get("/{company_id}/statuses")
async def get_statuses(company_id: int):
    """Get lead status settings"""
    async with get_db_session() as db:
        result = await db.execute(text("""
            SELECT id, emoji, name, coins FROM lead_status_settings 
            WHERE company_id = :cid ORDER BY sort_order
        """), {'cid': company_id})
        return [{"code": str(r[0]), "emoji": r[1], "name": r[2], "coins": r[3]} for r in result.fetchall()]


# === MANAGERS ===

@router.get("/{company_id}/managers")
async def get_managers(company_id: int):
    """Get all managers with coins"""
    async with get_db_session() as db:
        result = await db.execute(text("""
            SELECT id, user_id, telegram_username, full_name, is_active, coins, created_at
            FROM company_managers WHERE company_id = :cid AND is_active = TRUE
            ORDER BY coins DESC
        """), {'cid': company_id})
        return [{"id": r[0], "user_id": r[1], "telegram_username": r[2], 
                 "full_name": r[3], "is_active": r[4], "coins": r[5] or 0,
                 "created_at": str(r[6]) if r[6] else None} for r in result.fetchall()]


@router.post("/{company_id}/managers")
async def register_manager(company_id: int, data: dict = Body(...)):
    """Register or update manager"""
    user_id = data.get('telegram_id')
    username = data.get('telegram_username', '')
    full_name = data.get('full_name', 'Менеджер')
    update_existing = data.get('update_existing', False)
    
    async with get_db_session() as db:
        result = await db.execute(text("""
            SELECT id, full_name FROM company_managers WHERE company_id = :cid AND user_id = :uid
        """), {'cid': company_id, 'uid': user_id})
        existing = result.fetchone()
        
        if existing:
            if update_existing:
                await db.execute(text("""
                    UPDATE company_managers SET full_name = :name, telegram_username = :uname
                    WHERE company_id = :cid AND user_id = :uid
                """), {'cid': company_id, 'uid': user_id, 'name': full_name, 'uname': username})
                await db.commit()
                return {"status": "updated"}
            return {"status": "exists", "full_name": existing[1]}
        
        await db.execute(text("""
            INSERT INTO company_managers (company_id, user_id, telegram_username, full_name, is_active, coins)
            VALUES (:cid, :uid, :uname, :name, true, 0)
        """), {'cid': company_id, 'uid': user_id, 'uname': username, 'name': full_name})
        await db.commit()
        return {"status": "ok"}


@router.get("/{company_id}/managers/{user_id}")
async def get_manager_info(company_id: int, user_id: int):
    """Get manager stats"""
    async with get_db_session() as db:
        # Manager info
        mgr = await db.execute(text("""
            SELECT full_name, coins FROM company_managers WHERE company_id = :cid AND user_id = :uid
        """), {'cid': company_id, 'uid': user_id})
        mgr_row = mgr.fetchone()
        
        if not mgr_row:
            return {"full_name": "", "coins": 0, "leads_count": 0, "deals_count": 0}
        
        # Count leads
        leads = await db.execute(text("""
            SELECT COUNT(*) FROM leads WHERE company_id = :cid AND assigned_user_id = :uid
        """), {'cid': company_id, 'uid': user_id})
        leads_count = leads.scalar() or 0
        
        # Count deals
        deals = await db.execute(text("""
            SELECT COUNT(*) FROM leads WHERE company_id = :cid AND assigned_user_id = :uid AND status_name IN ('Сделка', 'Завершён', 'Закрыт')
        """), {'cid': company_id, 'uid': user_id})
        deals_count = deals.scalar() or 0
        
        return {
            "full_name": mgr_row[0],
            "coins": mgr_row[1] or 0,
            "leads_count": leads_count,
            "deals_count": deals_count
        }


# === LEADERBOARD ===

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

@router.delete("/{company_id}/managers/{user_id}")
async def delete_manager(company_id: int, user_id: int):
    """Delete manager for re-registration"""
    async with get_db_session() as db:
        await db.execute(text("""
            DELETE FROM company_managers WHERE company_id = :cid AND user_id = :uid
        """), {'cid': company_id, 'uid': user_id})
        await db.commit()
        return {"status": "ok"}

