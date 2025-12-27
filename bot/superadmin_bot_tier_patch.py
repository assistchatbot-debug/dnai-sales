# === Tier Management Patch ===
# Вставить этот код ПЕРЕД @dp.message() в superadmin_bot.py

@dp.message(F.text == "🎯 Установить тариф")
async def start_set_tier(message: types.Message, state: FSMContext):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/companies/all', timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    companies = await resp.json()
                    if not companies:
                        await message.answer("📋 Нет компаний")
                        return
                    text = "🎯 <b>Установить тариф</b>\n\nВыберите компанию:\n\n"
                    for i, c in enumerate(companies, 1):
                        tier = c.get('tier', 'free')
                        expiry = c.get('tier_expiry', 'N/A')
                        if expiry and expiry != 'N/A': expiry = expiry[:10]
                        text += f"{i}. {c['name']} ({tier}, до: {expiry})\n"
                    await state.update_data(companies=companies)
                    await state.set_state(CompanyFlow.selecting_company_for_tier)
                    await message.answer(text, parse_mode='HTML')
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)[:40]}")

@dp.message(CompanyFlow.selecting_company_for_tier)
async def select_company_for_tier(message: types.Message, state: FSMContext):
    try:
        num = int(message.text.strip()) - 1
        data = await state.get_data()
        companies = data.get('companies', [])
        if 0 <= num < len(companies):
            company = companies[num]
            await state.update_data(selected_company=company)
            tier_keyboard = ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="free"), KeyboardButton(text="basic")],
                [KeyboardButton(text="pro"), KeyboardButton(text="enterprise")],
                [KeyboardButton(text="◀️ Назад")]
            ], resize_keyboard=True)
            await state.set_state(CompanyFlow.selecting_tier)
            await message.answer(f"🎯 Компания: <b>{company['name']}</b>\n\nВыберите тариф:", parse_mode='HTML', reply_markup=tier_keyboard)
        else:
            await message.answer("❌ Неверный номер")
    except ValueError:
        await message.answer("❌ Введите номер")

@dp.message(CompanyFlow.selecting_tier)
async def select_tier(message: types.Message, state: FSMContext):
    tier = message.text.strip().lower()
    if tier == "◀️ назад":
        await state.clear()
        await message.answer("⬅️", reply_markup=get_company_menu_keyboard())
        return
    if tier not in ['free', 'basic', 'pro', 'enterprise']:
        await message.answer("❌ Выберите тариф из списка")
        return
    await state.update_data(new_tier=tier)
    await state.set_state(CompanyFlow.entering_tier_days)
    await message.answer(f"📅 Тариф: <b>{tier}</b>\n\nВведите дней:", parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="30"), KeyboardButton(text="90"), KeyboardButton(text="365")]], resize_keyboard=True))

@dp.message(CompanyFlow.entering_tier_days)
async def enter_tier_days(message: types.Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        if days <= 0 or days > 3650:
            await message.answer("❌ От 1 до 3650 дней")
            return
        data = await state.get_data()
        company = data.get('selected_company', {})
        tier = data.get('new_tier', 'free')
        from datetime import datetime, timedelta
        expiry = (datetime.now() + timedelta(days=days)).isoformat()
        async with aiohttp.ClientSession() as session:
            async with session.patch(f"{API_BASE_URL}/sales/companies/{company['id']}/tier", json={'tier': tier, 'tier_expiry': expiry}, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    await message.answer(f"✅ Тариф установлен!\n🏢 {company['name']}\n🎯 {tier}\n📅 {days} дней\n⏰ До: {expiry[:10]}", reply_markup=get_company_menu_keyboard())
                else:
                    await message.answer(f"⚠️ Ошибка: {resp.status}")
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число")

@dp.message(F.text == "⏰ Продлить тариф")
async def start_extend_tier(message: types.Message, state: FSMContext):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/sales/companies/all', timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    companies = await resp.json()
                    companies_with_tier = [c for c in companies if c.get('tier', 'free') != 'free']
                    if not companies_with_tier:
                        await message.answer("📋 Нет компаний с тарифом")
                        return
                    text = "⏰ <b>Продлить тариф</b>\n\n"
                    for i, c in enumerate(companies_with_tier, 1):
                        expiry = c.get('tier_expiry', 'N/A')
                        if expiry and expiry != 'N/A': expiry = expiry[:10]
                        text += f"{i}. {c['name']} ({c.get('tier')}, до: {expiry})\n"
                    await state.update_data(companies=companies_with_tier)
                    await state.set_state(CompanyFlow.selecting_company_for_extend)
                    await message.answer(text, parse_mode='HTML')
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)[:40]}")

@dp.message(CompanyFlow.selecting_company_for_extend)
async def select_company_for_extend(message: types.Message, state: FSMContext):
    try:
        num = int(message.text.strip()) - 1
        data = await state.get_data()
        companies = data.get('companies', [])
        if 0 <= num < len(companies):
            company = companies[num]
            await state.update_data(selected_company=company)
            await state.set_state(CompanyFlow.entering_extend_days)
            await message.answer(f"⏰ Продление: <b>{company['name']}</b>\nТариф: {company.get('tier')}\n\nВведите дней:", parse_mode='HTML',
                reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="30"), KeyboardButton(text="90"), KeyboardButton(text="365")]], resize_keyboard=True))
    except ValueError:
        await message.answer("❌ Введите номер")

@dp.message(CompanyFlow.entering_extend_days)
async def enter_extend_days(message: types.Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        if days <= 0 or days > 3650:
            await message.answer("❌ От 1 до 3650 дней")
            return
        data = await state.get_data()
        company = data.get('selected_company', {})
        from datetime import datetime, timedelta
        current_expiry = company.get('tier_expiry')
        base_date = datetime.now()
        if current_expiry:
            try:
                base_date = datetime.fromisoformat(current_expiry.replace('Z', '+00:00'))
                if base_date < datetime.now(base_date.tzinfo): base_date = datetime.now()
            except: pass
        new_expiry = (base_date + timedelta(days=days)).isoformat()
        async with aiohttp.ClientSession() as session:
            async with session.patch(f"{API_BASE_URL}/sales/companies/{company['id']}/tier", json={'tier_expiry': new_expiry}, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    await message.answer(f"✅ Продлён!\n🏢 {company['name']}\n➕ {days} дней\n⏰ До: {new_expiry[:10]}", reply_markup=get_company_menu_keyboard())
                else:
                    await message.answer(f"⚠️ Ошибка: {resp.status}")
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число")
