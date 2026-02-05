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
        
        # Get deals
        deals_result = await db.execute(text("""
            SELECT id, deal_number, deal_amount, deal_currency, status, confirmed, confirmed_at, payment_date, payment_doc_number
            FROM lead_deals WHERE lead_id = :lid ORDER BY deal_number
        """), {'lid': lead_id})
        deals = [
            {
                "id": d[0],
                "deal_number": d[1], 
                "deal_amount": float(d[2]) if d[2] else 0, 
                "deal_currency": d[3] or 'KZT', 
                "status": d[4],
                "confirmed": d[5] or False,
                "confirmed_at": str(d[6])[:10] if d[6] else None,
                "payment_date": str(d[7]) if d[7] else None,
                "payment_doc_number": d[8] if d[8] else None
            }
            for d in deals_result.fetchall()
        ]
        
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
            'notes': notes,
            'deals': deals
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



async def get_sort_order(db, company_id: int, status_id) -> int:
    """Get sort_order by status_id for multi-tenancy support"""
    result = await db.execute(text("""
        SELECT sort_order FROM lead_status_settings 
        WHERE company_id = :cid AND id = :sid
    """), {'cid': company_id, 'sid': int(status_id)})
    return result.scalar() or 0

async def get_status_id_by_sort(db, company_id: int, sort_order: int) -> int:
    """Get status_id by sort_order for multi-tenancy support"""
    result = await db.execute(text("""
        SELECT id FROM lead_status_settings 
        WHERE company_id = :cid AND sort_order = :sort
    """), {'cid': company_id, 'sort': sort_order})
    return result.scalar() or 0

@router.patch("/{company_id}/leads/{lead_id}/status")
async def update_lead_status(company_id: int, lead_id: int, data: dict = Body(...)):
    """Update lead status and award coins (with protection)"""
    new_status = data.get('status')
    original_new_status = str(new_status)  # Запомнить до сброса
    manager_id = data.get('manager_id')
    
    # Определение sort_order будет внутри async with
    original_sort_order = 0

    
    async with get_db_session() as db:
        # 0. Определить sort_order для нового статуса (мультитенантность)
        if str(new_status).isdigit():
            original_sort_order = await get_sort_order(db, company_id, int(new_status))
        
        # "Повторная сделка" (sort_order=21) → сбросить на "В работе" (sort_order=2)
        if original_sort_order == 21:
            in_progress_id = await get_status_id_by_sort(db, company_id, 2)
            if in_progress_id:
                new_status = str(in_progress_id)
        
        # 1. Получить ТЕКУЩИЙ статус лида
        current_result = await db.execute(text("""
            SELECT status FROM leads WHERE id = :lid AND company_id = :cid
        """), {'lid': lead_id, 'cid': company_id})
        current_status = current_result.scalar() or '4'
        
        # 2. Тот же статус — игнорировать
        if str(new_status) == str(current_status):
            return {"status": "same", "message": "Статус не изменился"}
        
        # 3. Преобразовать текстовые статусы в числа
        status_map = {'new': 4, 'in_progress': 8, 'negotiation': 12, 'awaiting_payment': 16, 'completed': 20, 'rejected': 24}
        if not str(current_status).isdigit():
            current_status = status_map.get(current_status, 4)
        if not str(new_status).isdigit():
            new_status = status_map.get(new_status, 4)
        
        # Получить sort_order и coins для обоих статусов
        orders_result = await db.execute(text("""
            SELECT id, sort_order, coins, emoji, name FROM lead_status_settings 
            WHERE company_id = :cid AND id IN (:current, :new)
        """), {'cid': company_id, 'current': int(current_status), 'new': int(new_status)})
        orders = {r[0]: {'sort': r[1], 'coins': r[2], 'emoji': r[3], 'name': r[4]} for r in orders_result.fetchall()}
        
        current_data = orders.get(int(current_status), {'sort': 0, 'coins': 0})
        new_data = orders.get(int(new_status), {'sort': 0, 'coins': 0, 'emoji': '🆕', 'name': 'Новый'})
        
        current_order = current_data['sort']
        new_order = new_data['sort']
        
        # 4. Проверка на переходы между статусами
        # Используем original_new_status для проверки (до сброса 28→8)
        new_status_int = int(original_new_status) if original_new_status.isdigit() else int(new_status)
        current_status_int = int(current_status)
        
        # Получить sort_order для текущего статуса
        current_sort = await get_sort_order(db, company_id, current_status_int) if str(current_status).isdigit() else 0
        new_sort = original_sort_order  # Уже получен выше
        
        # Отказ (sort=6) — можно нажать в любой момент
        if new_sort == 6:
            pass  # Всегда разрешён
        # Повторная сделка (sort=21) — разрешена из Завершён (sort=5) или Отказ (sort=6)
        elif new_sort == 21:
            if current_sort not in [5, 6]:
                return {"status": "error", "message": "Повторная сделка только после Завершён или Отказ"}
        # Из Завершён (sort=5) можно только в Отказ или Повторную
        elif current_sort == 5:
            if new_sort not in [6, 21]:
                return {"status": "error", "message": "Из Завершён только Отказ или Повторная"}
        # Из Отказа (sort=6) можно только в Повторную
        elif current_sort == 6:
            if new_sort != 21:
                return {"status": "error", "message": "Из Отказа только Повторная сделка"}
        # Обычные статусы — только последовательно (разница ≤ 1)
        elif abs(new_order - current_order) > 1:
            return {"status": "error", "message": "Нельзя перепрыгивать статусы"}
        
        # 5. Определить изменение монет
        # Повторная сделка (sort=21) — брать coins из этого статуса
        if original_sort_order == 21:
            repeat_id = await get_status_id_by_sort(db, company_id, 21)
            repeat_result = await db.execute(text("""
                SELECT coins FROM lead_status_settings WHERE company_id = :cid AND id = :rid
            """), {'cid': company_id, 'rid': repeat_id})
            coins_change = repeat_result.scalar() or 0
        elif new_order > current_order:
            coins_change = new_data['coins']  # Вперёд: +coins нового
        else:
            coins_change = -current_data['coins']  # Назад: -coins текущего
        
        emoji = new_data.get('emoji', '🆕')
        name = new_data.get('name', 'Новый')
        status_id = int(new_status)
        
        # 6. Update lead
        await db.execute(text("""
            UPDATE leads SET status = :status, status_emoji = :emoji, status_name = :name,
                   status_changed_at = NOW()
            WHERE id = :lid AND company_id = :cid
        """), {'status': new_status, 'emoji': emoji, 'name': name, 'lid': lead_id, 'cid': company_id})
        
        # 7. Award/deduct coins
        if coins_change and manager_id:
            await db.execute(text("""
                UPDATE company_managers SET coins = coins + :coins 
                WHERE company_id = :cid AND user_id = :uid
            """), {'coins': coins_change, 'cid': company_id, 'uid': manager_id})
        
        await db.commit()
        
        # Если статус "Завершён" (sort=5) — создать сделку и запросить сумму
        if new_order == 5:
            # Получить валюту компании
            curr_result = await db.execute(text("""
                SELECT currency FROM companies WHERE id = :cid
            """), {'cid': company_id})
            currency = curr_result.scalar() or 'KZT'
            
            # Определить номер сделки
            count_result = await db.execute(text("""
                SELECT COUNT(*) FROM lead_deals WHERE lead_id = :lid
            """), {'lid': lead_id})
            deal_count = count_result.scalar() or 0
            deal_number = deal_count + 1
            
            # Получить имя менеджера
            mgr_result = await db.execute(text("""
                SELECT full_name FROM company_managers WHERE company_id = :cid AND user_id = :uid
            """), {'cid': company_id, 'uid': manager_id})
            mgr_name = mgr_result.scalar() or 'Менеджер'
            
            # Создать запись сделки (без суммы)
            deal_result = await db.execute(text("""
                INSERT INTO lead_deals (lead_id, company_id, manager_id, manager_name, deal_number, deal_currency, status)
                VALUES (:lid, :cid, :mid, :mname, :dnum, :curr, 'pending_amount')
                RETURNING id
            """), {'lid': lead_id, 'cid': company_id, 'mid': manager_id, 'mname': mgr_name, 'dnum': deal_number, 'curr': currency})
            deal_id = deal_result.scalar()
            
            # Обновить текущий deal_id в leads
            await db.execute(text("""
                UPDATE leads SET current_deal_id = :did, current_deal_status = 'pending_amount' WHERE id = :lid
            """), {'did': deal_id, 'lid': lead_id})
            await db.commit()
            
            return {
                "status": "ok", 
                "status_name": name, 
                "coins_earned": coins_change or 0,
                "requires_amount": True,
                "deal_id": deal_id,
                "currency": currency
            }
        
        return {"status": "ok", "status_name": name, "coins_earned": coins_change or 0}




@router.patch("/{company_id}/leads/{lead_id}/deal/{deal_id}")
async def save_deal_amount(company_id: int, lead_id: int, deal_id: int, data: dict = Body(...)):
    """Save deal amount and update manager stats"""
    amount = data.get('amount', 0)
    manager_id = data.get('manager_id')
    
    async with get_db_session() as db:
        # 1. Обновить сумму и статус в lead_deals
        await db.execute(text("""
            UPDATE lead_deals SET deal_amount = :amount, status = 'completed'
            WHERE id = :did
        """), {'amount': amount, 'did': deal_id})
        
        # 2. Получить deal_number и currency
        result = await db.execute(text("""
            SELECT deal_number, deal_currency FROM lead_deals WHERE id = :did
        """), {'did': deal_id})
        row = result.fetchone()
        deal_number = row[0] if row else 1
        currency = row[1] if row else 'KZT'
        
        # 3. Обновить leads.deal_amount и статус
        await db.execute(text("""
            UPDATE leads SET deal_amount = :amount, deal_currency = :curr, current_deal_status = 'completed'
            WHERE id = :lid
        """), {'amount': amount, 'curr': currency, 'lid': lead_id})
        
        # 4. Обновить статистику менеджера
        if manager_id:
            await db.execute(text("""
                UPDATE company_managers 
                SET total_deal_amount = COALESCE(total_deal_amount, 0) + :amount,
                    deals_count = COALESCE(deals_count, 0) + 1
                WHERE company_id = :cid AND user_id = :mid
            """), {'amount': amount, 'cid': company_id, 'mid': manager_id})
        
        # 5. Получить данные лида и менеджера для уведомления
        lead_result = await db.execute(text("""
            SELECT contact_info FROM leads WHERE id = :lid
        """), {'lid': lead_id})
        lead_row = lead_result.fetchone()
        client_name = ''
        if lead_row and lead_row[0]:
            try:
                import json
                contact = json.loads(lead_row[0]) if isinstance(lead_row[0], str) else lead_row[0]
                client_name = contact.get('name', '')
            except:
                pass
        
        mgr_result = await db.execute(text("""
            SELECT full_name FROM company_managers WHERE company_id = :cid AND user_id = :mid
        """), {'cid': company_id, 'mid': manager_id})
        mgr_row = mgr_result.fetchone()
        manager_name = mgr_row[0] if mgr_row else 'Менеджер'
        
        await db.commit()
        
        return {
            "status": "ok", 
            "deal_number": deal_number, 
            "currency": currency,
            "notify_admin": True,
            "deal_id": deal_id,
            "deal_amount": amount,
            "lead_id": lead_id,
            "client_name": client_name,
            "manager_name": manager_name
        }


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
        # Manager info с deals_count и total_deal_amount
        mgr = await db.execute(text("""
            SELECT full_name, coins, deals_count, total_deal_amount 
            FROM company_managers WHERE company_id = :cid AND user_id = :uid
        """), {'cid': company_id, 'uid': user_id})
        mgr_row = mgr.fetchone()
        
        if not mgr_row:
            return {"full_name": "", "coins": 0, "leads_count": 0, "deals_count": 0}
        
        # Count leads
        leads = await db.execute(text("""
            SELECT COUNT(*) FROM leads WHERE company_id = :cid AND assigned_user_id = :uid
        """), {'cid': company_id, 'uid': user_id})
        leads_count = leads.scalar() or 0
        
        return {
            "full_name": mgr_row[0],
            "coins": mgr_row[1] or 0,
            "leads_count": leads_count,
            "deals_count": mgr_row[2] or 0,
            "total_deal_amount": float(mgr_row[3]) if mgr_row[3] else 0
        }


# === LEADERBOARD ===

@router.get("/{company_id}/leaderboard")
async def get_leaderboard(company_id: int, period: str = 'all', sort: str = 'coins'):
    """Get managers leaderboard with period filter and sorting
    
    period: week, month, all
    sort: coins, amount, deals
    """
    from datetime import datetime, timedelta
    
    async with get_db_session() as db:
        # Определить дату начала периода
        if period == 'week':
            start_date = datetime.now() - timedelta(days=7)
        elif period == 'month':
            start_date = datetime.now() - timedelta(days=30)
        else:
            start_date = None
        
        # Получить базовую инфо менеджеров
        result = await db.execute(text("""
            SELECT user_id, full_name, coins, deals_count, total_deal_amount
            FROM company_managers 
            WHERE company_id = :cid AND is_active = TRUE
        """), {'cid': company_id})
        managers = {r[0]: {
            "user_id": r[0], 
            "full_name": r[1], 
            "coins": r[2] or 0,
            "deals_count": r[3] or 0,
            "total_deal_amount": float(r[4]) if r[4] else 0
        } for r in result.fetchall()}
        
        # Если период — пересчитать сделки за период
        if start_date and managers:
            deals_result = await db.execute(text("""
                SELECT manager_id, COUNT(*), COALESCE(SUM(deal_amount), 0)
                FROM lead_deals 
                WHERE company_id = :cid AND status = 'completed' AND created_at >= :start
                GROUP BY manager_id
            """), {'cid': company_id, 'start': start_date})
            
            for r in deals_result.fetchall():
                if r[0] in managers:
                    managers[r[0]]["deals_count"] = r[1] or 0
                    managers[r[0]]["total_deal_amount"] = float(r[2]) if r[2] else 0
            
            # Для периода — обнулить тех у кого нет сделок за период
            for m in managers.values():
                if start_date:
                    # Это временно - берём из lead_deals за период
                    pass
        
        # Сортировка
        managers_list = list(managers.values())
        if sort == 'amount':
            managers_list.sort(key=lambda x: x['total_deal_amount'], reverse=True)
        elif sort == 'deals':
            managers_list.sort(key=lambda x: x['deals_count'], reverse=True)
        else:  # coins
            managers_list.sort(key=lambda x: x['coins'], reverse=True)
        
        return managers_list[:10]


@router.patch("/{company_id}/statuses/{status_id}")
async def update_status_coins(company_id: int, status_id: int, data: dict):
    """Update coins for a status"""
    coins = data.get('coins')
    if coins is None:
        return {"error": "coins required"}
    
    async with get_db_session() as db:
        await db.execute(text("""
            UPDATE lead_status_settings 
            SET coins = :coins 
            WHERE id = :sid AND company_id = :cid
        """), {'coins': coins, 'sid': status_id, 'cid': company_id})
        await db.commit()
        return {"status": "ok", "coins": coins}



@router.patch("/{company_id}/deals/{deal_id}/document")
async def save_deal_document(company_id: int, deal_id: int, data: dict = Body(...)):
    """Save payment document number and date"""
    from datetime import datetime
    payment_doc_number = data.get('payment_doc_number', '')
    payment_date_str = data.get('payment_date')  # формат: YYYY-MM-DD
    
    # Конвертировать строку в date объект
    payment_date = None
    if payment_date_str:
        try:
            payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d").date()
        except:
            pass
    
    async with get_db_session() as db:
        await db.execute(text("""
            UPDATE lead_deals 
            SET payment_doc_number = :doc, payment_date = :pdate
            WHERE id = :did AND company_id = :cid
        """), {'doc': payment_doc_number, 'pdate': payment_date, 'did': deal_id, 'cid': company_id})
        await db.commit()
        return {"status": "ok"}

@router.patch("/{company_id}/deals/{deal_id}/confirm")
async def confirm_deal(company_id: int, deal_id: int):
    """Confirm a deal (admin only)"""
    async with get_db_session() as db:
        await db.execute(text("""
            UPDATE lead_deals 
            SET confirmed = TRUE, confirmed_at = NOW()
            WHERE id = :did AND company_id = :cid
        """), {'did': deal_id, 'cid': company_id})
        await db.commit()
        return {"status": "ok", "confirmed": True}

@router.delete("/{company_id}/managers/{user_id}")
async def delete_manager(company_id: int, user_id: int):
    """Delete manager for re-registration"""
    async with get_db_session() as db:
        await db.execute(text("""
            DELETE FROM company_managers WHERE company_id = :cid AND user_id = :uid
        """), {'cid': company_id, 'uid': user_id})
        await db.commit()
        return {"status": "ok"}



@router.get("/{company_id}/leads/{lead_id}/full_report")
async def get_full_report(company_id: int, lead_id: int):
    """Get full AI report with conversation history"""
    async with get_db_session() as db:
        # Lead info
        result = await db.execute(text("""
            SELECT contact_info, ai_summary, conversation_summary, temperature
            FROM leads WHERE company_id = :cid AND id = :lid
        """), {'cid': company_id, 'lid': lead_id})
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        contact = row[0] or {}
        name = contact.get('name', 'Клиент')
        phone = contact.get('phone', '')
        temp = contact.get('temperature', '')
        ai_summary = row[1] or ''
        
        # Conversation history
        history_result = await db.execute(text("""
            SELECT content, outcome FROM interactions 
            WHERE lead_id = :lid ORDER BY created_at
        """), {'lid': lead_id})
        rows = history_result.fetchall()
        conversation = []
        for r in rows:
            if r[0]:  # user message
                conversation.append({"sender": "user", "text": r[0]})
            if r[1]:  # bot response
                conversation.append({"sender": "bot", "text": r[1]})
        
        return {
            "name": name,
            "phone": phone,
            "temperature": temp,
            "ai_summary": ai_summary,
            "conversation_history": conversation
        }

# === СОБЫТИЯ И НАПОМИНАНИЯ ===

@router.post("/{company_id}/events")
async def create_event(company_id: int, data: dict = Body(...)):
    """Create scheduled event for lead"""
    lead_id = data.get('lead_id')
    user_id = data.get('user_id')
    event_type = data.get('event_type')
    title = data.get('title', '')
    description = data.get('description', '')
    scheduled_at = data.get('scheduled_at')
    remind_before = data.get('remind_before_minutes', 30)
    created_by_user_id = data.get('created_by_user_id')
    
    from datetime import datetime
    
    # Преобразовать строку в datetime
    if isinstance(scheduled_at, str):
        scheduled_at = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
    
    async with get_db_session() as db:
        result = await db.execute(text("""
            INSERT INTO lead_events_schedule 
            (company_id, lead_id, user_id, event_type, title, description, scheduled_at, remind_before_minutes, created_by_user_id)
            VALUES (:cid, :lid, :uid, :type, :title, :desc, :sched, :remind, :creator)
            RETURNING id
        """), {'cid': company_id, 'lid': lead_id, 'uid': user_id, 'type': event_type, 
               'title': title, 'desc': description, 'sched': scheduled_at, 'remind': remind_before, 'creator': created_by_user_id})
        event_id = result.scalar()
        await db.commit()
        return {"id": event_id, "status": "ok"}


@router.get("/{company_id}/events")
async def get_user_events(company_id: int, user_id: int = None, offset: int = 0, limit: int = 50, event_type: str = None, is_recurring: bool = None):
    """Get events for user"""
    async with get_db_session() as db:
        query = """
            SELECT e.id, e.lead_id, e.event_type, e.title, e.description, 
                   e.scheduled_at, e.status, l.contact_info, e.is_recurring, e.recurring_pattern
            FROM lead_events_schedule e
            LEFT JOIN leads l ON e.lead_id = l.id
            WHERE e.company_id = :cid AND e.status = 'pending'
        """
        params = {'cid': company_id}
        if user_id:
            query += " AND (e.user_id = :uid OR e.created_by_user_id = :uid)"
            params['uid'] = user_id
        if event_type:
            query += " AND e.event_type = :etype"
            params['etype'] = event_type
        if is_recurring is not None:
            query += " AND e.is_recurring = :rec"
            params['rec'] = is_recurring
        query += " ORDER BY e.scheduled_at LIMIT :lim OFFSET :off"
        params['lim'] = limit
        params['off'] = offset
        
        result = await db.execute(text(query), params)
        events = []
        for r in result.fetchall():
            contact = r[7] or {}
            events.append({
                'id': r[0], 'lead_id': r[1], 'event_type': r[2], 'title': r[3],
                'description': r[4], 'scheduled_at': str(r[5]), 'status': r[6],
                'client_name': contact.get('name', 'Клиент'),
                'is_recurring': r[8] if len(r) > 8 else False,
                'recurring_pattern': r[9] if len(r) > 9 else None
            })
        return events




@router.get("/{company_id}/events/history")
async def get_events_history(company_id: int, user_id: int = None, offset: int = 0, limit: int = 50):
    """Get completed/missed events"""
    async with get_db_session() as db:
        query = """
            SELECT e.id, e.lead_id, e.event_type, e.title, e.description, 
                   e.scheduled_at, e.status, l.contact_info
            FROM lead_events_schedule e
            LEFT JOIN leads l ON e.lead_id = l.id
            WHERE e.company_id = :cid AND e.status IN ('done', 'missed', 'cancelled')
        """
        params = {'cid': company_id}
        if user_id:
            query += " AND (e.user_id = :uid OR e.created_by_user_id = :uid)"
            params['uid'] = user_id
        query += " ORDER BY e.scheduled_at DESC LIMIT :lim OFFSET :off"
        params['lim'] = limit
        params['off'] = offset
        
        result = await db.execute(text(query), params)
        events = []
        for r in result.fetchall():
            contact = r[7] or {}
            events.append({
                'id': r[0], 'lead_id': r[1], 'event_type': r[2], 'title': r[3],
                'description': r[4], 'scheduled_at': str(r[5]), 'status': r[6],
                'client_name': contact.get('name', 'Клиент')
            })
        return events

@router.get("/{company_id}/leads/{lead_id}/events")
async def get_lead_events(company_id: int, lead_id: int):
    """Get events for specific lead"""
    async with get_db_session() as db:
        result = await db.execute(text("""
            SELECT id, event_type, title, description, scheduled_at, status
            FROM lead_events_schedule
            WHERE company_id = :cid AND lead_id = :lid AND status = 'pending'
            ORDER BY scheduled_at
        """), {'cid': company_id, 'lid': lead_id})
        return [{'id': r[0], 'event_type': r[1], 'title': r[2], 'description': r[3],
                 'scheduled_at': str(r[4]), 'status': r[5]} for r in result.fetchall()]


@router.patch("/{company_id}/events/{event_id}")
async def update_event(company_id: int, event_id: int, data: dict = Body(...)):
    """Update event status or reschedule"""
    status = data.get('status')
    new_time = data.get('scheduled_at')
    
    async with get_db_session() as db:
        if status:
            await db.execute(text("""
                UPDATE lead_events_schedule SET status = :status
                WHERE id = :eid AND company_id = :cid
            """), {'status': status, 'eid': event_id, 'cid': company_id})
        if new_time:
            await db.execute(text("""
                UPDATE lead_events_schedule SET scheduled_at = CAST(:time AS TIMESTAMP), reminder_sent = FALSE
                WHERE id = :eid AND company_id = :cid
            """), {'time': new_time, 'eid': event_id, 'cid': company_id})
        
        # Recurring support
        is_recurring = data.get('is_recurring')
        recurring_pattern = data.get('recurring_pattern')
        if is_recurring is not None:
            await db.execute(text("""
                UPDATE lead_events_schedule SET is_recurring = :rec, recurring_pattern = :pat
                WHERE id = :eid AND company_id = :cid
            """), {'rec': is_recurring, 'pat': recurring_pattern, 'eid': event_id, 'cid': company_id})
        await db.commit()
        return {"status": "ok"}


@router.get("/pending-reminders")
async def get_pending_reminders():
    """Get events that need reminder (for scheduler)"""
    async with get_db_session() as db:
        result = await db.execute(text("""
            SELECT e.id, e.company_id, e.lead_id, e.user_id, e.event_type, 
                   e.title, e.description, e.scheduled_at, e.remind_before_minutes,
                   l.contact_info
            FROM lead_events_schedule e
            LEFT JOIN leads l ON e.lead_id = l.id
            WHERE e.status = 'pending' 
              AND e.reminder_sent = FALSE
              AND e.scheduled_at - (e.remind_before_minutes || ' minutes')::interval <= NOW()
              AND e.scheduled_at > NOW()
        """))
        events = []
        for r in result.fetchall():
            contact = r[9] or {}
            events.append({
                'id': r[0], 'company_id': r[1], 'lead_id': r[2], 'user_id': r[3],
                'event_type': r[4], 'title': r[5], 'description': r[6],
                'scheduled_at': str(r[7]), 'remind_before': r[8],
                'client_name': contact.get('name', 'Клиент'),
                'client_phone': contact.get('phone', '')
            })
        return events


@router.patch("/events/{event_id}/reminder-sent")
async def mark_reminder_sent(event_id: int):
    """Mark reminder as sent"""
    async with get_db_session() as db:
        await db.execute(text("""
            UPDATE lead_events_schedule SET reminder_sent = TRUE WHERE id = :eid
        """), {'eid': event_id})
        await db.commit()
        return {"status": "ok"}



@router.delete("/{company_id}/events/{event_id}")
async def delete_event(company_id: int, event_id: int):
    """Delete event completely"""
    async with get_db_session() as db:
        await db.execute(text("""
            DELETE FROM lead_events_schedule 
            WHERE id = :eid AND company_id = :cid
        """), {'eid': event_id, 'cid': company_id})
        await db.commit()
        return {"status": "ok", "deleted": event_id}

