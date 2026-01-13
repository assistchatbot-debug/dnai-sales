from fastapi import APIRouter, HTTPException, Query
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
