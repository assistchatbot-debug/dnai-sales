#!/usr/bin/env python3
import os, shutil
from datetime import datetime

BASE = "/root/dnai-sales"
BACKUP = f"{BASE}/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

print("📦 Backup...")
os.makedirs(BACKUP, exist_ok=True)
for f in ["backend/models.py","backend/routers/sales_agent.py","bot/handlers.py","bot/states.py"]:
    src,dst = f"{BASE}/{f}", f"{BACKUP}/{f}"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
print(f"✅ {BACKUP}")

print("1️⃣ transliterate.py...")
os.makedirs(f"{BASE}/backend/services", exist_ok=True)
open(f"{BASE}/backend/services/transliterate.py",'w').write('''def transliterate_to_english(text: str) -> str:
    p={'instagram':'instagram','инстаграм':'instagram','facebook':'facebook','вк':'vk','telegram':'telegram'}
    t=text.lower().strip()
    if t in p: return p[t]
    tr={'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ж':'zh','з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'ts','ч':'ch','ш':'sh','щ':'sch','ы':'y','э':'e','ю':'yu','я':'ya'}
    r=''.join([c if c.isalnum() and ord(c)<128 else tr.get(c,'_') if c not in ' -_' else '_' for c in t])
    while '__' in r: r=r.replace('__','_')
    return r.strip('_') or 'widget'
''')
print("✅")

print("2️⃣ models.py...")
c=open(f"{BASE}/backend/models.py").read()
if 'class SocialWidget' not in c:
    c+='\n\nclass SocialWidget(Base):\n    __tablename__="social_widgets"\n    id=Column(Integer,primary_key=True,index=True)\n    company_id=Column(Integer,ForeignKey("companies.id"),nullable=False)\n    channel_name=Column(String(50),nullable=False,index=True)\n    greeting_message=Column(Text)\n    is_active=Column(Boolean,default=True)\n    created_at=Column(DateTime(timezone=True),server_default=func.now())\n    company=relationship("Company",back_populates="social_widgets")\n'
if 'social_widgets = relationship' not in c:
    c=c.replace('    sales_config = relationship("SalesAgentConfig", back_populates="company", uselist=False)','    social_widgets=relationship("SocialWidget",back_populates="company",cascade="all, delete-orphan")\n    sales_config = relationship("SalesAgentConfig", back_populates="company", uselist=False)')
open(f"{BASE}/backend/models.py",'w').write(c)
print("✅")

print("3️⃣ sales_agent.py...")
c=open(f"{BASE}/backend/routers/sales_agent.py").read()
if 'SocialWidget' not in c:
    c=c.replace('from models import SalesAgentConfig, ProductSelectionSession, VoiceMessage, Lead, Interaction, UserPreference, Company','from models import SalesAgentConfig, ProductSelectionSession, VoiceMessage, Lead, Interaction, UserPreference, Company, SocialWidget')
if '/companies/{company_id}/widgets' not in c:
    c+='\n\nfrom services.transliterate import transliterate_to_english\n\n@router.get("/companies/{company_id}/widgets")\nasync def list_widgets(company_id:int,db:AsyncSession=Depends(get_db)):\n    r=await db.execute(select(SocialWidget).where(SocialWidget.company_id==company_id,SocialWidget.is_active==True))\n    return {"widgets":[{"id":w.id,"channel_name":w.channel_name,"url":f"https://bizdnai.com/w/{company_id}/{w.channel_name}"}for w in r.scalars().all()]}\n\n@router.post("/companies/{company_id}/widgets")\nasync def create_widget(company_id:int,data:dict,db:AsyncSession=Depends(get_db)):\n    ch=transliterate_to_english(data.get("channel_name",""))\n    if not ch:raise HTTPException(400,"channel_name required")\n    r=await db.execute(select(SocialWidget).where(SocialWidget.company_id==company_id,SocialWidget.channel_name==ch))\n    if r.scalar_one_or_none():raise HTTPException(400,f"Widget {ch} exists")\n    w=SocialWidget(company_id=company_id,channel_name=ch,greeting_message=data.get("greeting_message","Здравствуйте!"),is_active=True)\n    db.add(w)\n    await db.commit()\n    await db.refresh(w)\n    return {"id":w.id,"channel_name":w.channel_name,"url":f"https://bizdnai.com/w/{company_id}/{ch}"}\n'
open(f"{BASE}/backend/routers/sales_agent.py",'w').write(c)
print("✅")

print("4️⃣ states.py...")
c=open(f"{BASE}/bot/states.py").read()
if 'ManagerFlow' not in c:
    c+='\n\nclass ManagerFlow(StatesGroup):\n    entering_channel_name=State()\n    entering_greeting=State()\n'
open(f"{BASE}/bot/states.py",'w').write(c)
print("✅")

print("5️⃣ handlers.py...")
c=open(f"{BASE}/bot/handlers.py").read()
if 'Manager menu with buttons' not in c:
    c=c.replace('@router.message(Command(\'start\'))\nasync def cmd_start(message: types.Message, state: FSMContext):\n    await state.set_state(SalesFlow.qualifying)\n    await start_session(message.from_user.id)\n    \n    await message.answer(\n        "Привет! Я Умный Агент (BizDNAi).\\n\\n🚀 Я новое поколение корпоративного AI.\\n\\nЯ помогу подобрать идеальное решение.\\nПишите или говорите, и я вам отвечу.\\n\\nДля смены языка используйте /lang",\n        reply_markup=get_start_keyboard()\n    )','@router.message(Command(\'start\'))\nasync def cmd_start(message: types.Message, state: FSMContext):\n    # Manager menu with buttons\n    if is_manager(message.from_user.id,message.bot):\n        from aiogram.types import ReplyKeyboardMarkup,KeyboardButton\n        kb=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📊 Статус"),KeyboardButton(text="📋 Лиды")],[KeyboardButton(text="📢 Каналы"),KeyboardButton(text="🌐 Виджет")],[KeyboardButton(text="❓ Помощь")]],resize_keyboard=True)\n        await message.answer("🤖 <b>Меню</b>",reply_markup=kb,parse_mode=\'HTML\')\n        return\n    await state.set_state(SalesFlow.qualifying)\n    await start_session(message.from_user.id)\n    await message.answer("Привет! Я Умный Агент (BizDNAi).\\n\\n🚀 Я новое поколение корпоративного AI.\\n\\nЯ помогу подобрать идеальное решение.\\nПишите или говорите, и я вам отвечу.\\n\\nДля смены языка используйте /lang",reply_markup=get_start_keyboard())')
if "'каналы' in text_lower" not in c:
    c=c.replace('    # Help\n    elif \'помощь\' in text_lower or \'help\' in text_lower:','    # Каналы\n    elif \'каналы\' in text_lower:\n        company_id=message.bot.company_id\n        try:\n            async with aiohttp.ClientSession() as session:\n                async with session.get(f\'{API_BASE_URL}/companies/{company_id}/widgets\') as resp:\n                    if resp.status==200:\n                        data=await resp.json()\n                        widgets=data.get(\'widgets\',[])\n                        msg="📢 <b>Каналы</b>\\n\\n📱 Telegram: ✅\\n🌐 Widget: ✅\\n\\n"\n                        if widgets:\n                            msg+="<b>Социальные сети:</b>\\n"\n                            for i,w in enumerate(widgets,1):msg+=f"{i}. {w[\'channel_name\']} - {w[\'url\']}\\n"\n                        else:msg+="<i>Нет каналов</i>\\n"\n                        msg+="\\n💡 <b>создать канал</b>"\n                        await message.answer(msg,parse_mode=\'HTML\')\n        except Exception as e:\n            await message.answer(f"❌ {str(e)[:50]}")\n    # Help\n    elif \'помощь\' in text_lower or \'help\' in text_lower:')
open(f"{BASE}/bot/handlers.py",'w').write(c)
print("✅")

print("\n🔍 Verify...")
ok=True
for n,p in [("transliterate",os.path.exists(f"{BASE}/backend/services/transliterate.py")),("SocialWidget","class SocialWidget" in open(f"{BASE}/backend/models.py").read()),("rel","social_widgets = relationship" in open(f"{BASE}/backend/models.py").read()),("import","SocialWidget" in open(f"{BASE}/backend/routers/sales_agent.py").read()),("API","/companies/{company_id}/widgets" in open(f"{BASE}/backend/routers/sales_agent.py").read()),("ManagerFlow","ManagerFlow" in open(f"{BASE}/bot/states.py").read()),("menu","Manager menu with buttons" in open(f"{BASE}/bot/handlers.py").read()),("каналы","'каналы' in text_lower" in open(f"{BASE}/bot/handlers.py").read())]:
    print(f"{'✅' if p else '❌'} {n}")
    if not p:ok=False

if ok:
    print("\n"+"="*60)
    print("✅ SUCCESS!")
    print("="*60)
    print("\nNext: docker-compose restart backend bot")
    print(f"Backup: {BACKUP}")
else:
    print("\n❌ FAILED")
    print(f"Restore: cp -r {BACKUP}/* {BASE}/")
