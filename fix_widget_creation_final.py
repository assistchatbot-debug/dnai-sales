#!/usr/bin/env python3
"""Fix widget creation: remove uniqueness check and use widget ID in URL"""

with open('backend/routers/sales_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Fixing widget creation...")

# Remove uniqueness check (line 848-849)
old_code = """    r=await db.execute(select(SocialWidget).where(SocialWidget.company_id==company_id,SocialWidget.channel_name==ch))
    if r.scalar_one_or_none():raise HTTPException(400,f"Widget {ch} exists")"""

new_code = """    # Allow multiple widgets per channel - no uniqueness check"""

content = content.replace(old_code, new_code)
print("✅ Removed uniqueness check")

# Fix URL to use widget ID instead of channel_name
old_url = """return {"id":w.id,"channel_name":w.channel_name,"url":f"https://bizdnai.com/w/{company_id}/{ch}"}"""
new_url = """return {"id":w.id,"channel_name":w.channel_name,"url":f"https://bizdnai.com/w/{company_id}/{w.id}"}"""

content = content.replace(old_url, new_url)
print("✅ Updated URL to use widget ID")

with open('backend/routers/sales_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Widget creation fixed!")
