#!/usr/bin/env python3
"""Add ID-based GET endpoint for widgets"""

with open('backend/routers/sales_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Adding ID-based endpoint...")

# Find where to insert new endpoint (before the channel_name endpoint)
marker = '@router.get("/companies/{company_id}/widgets/{channel_name}")'

if marker in content:
    # Create new ID-based endpoint
    new_endpoint = '''@router.get("/companies/{company_id}/widgets/{widget_id:int}")
async def get_widget_by_id(company_id:int,widget_id:int,db:AsyncSession=Depends(get_db)):
    """Get widget by ID"""
    r=await db.execute(select(SocialWidget).where(SocialWidget.company_id==company_id,SocialWidget.id==widget_id,SocialWidget.is_active==True))
    w=r.scalar_one_or_none()
    if not w:raise HTTPException(404,"Widget not found")
    return {"id":w.id,"company_id":w.company_id,"channel_name":w.channel_name,"greeting_message":w.greeting_message,"greetings":{"ru":w.greeting_ru or w.greeting_message,"en":w.greeting_en or w.greeting_message,"kz":w.greeting_kz or w.greeting_message,"ky":w.greeting_ky or w.greeting_message,"uz":w.greeting_uz or w.greeting_message,"uk":w.greeting_uk or w.greeting_message},"is_active":w.is_active}

'''
    
    # Insert before the old endpoint
    content = content.replace(marker, new_endpoint + marker)
    print("✅ Added ID-based GET endpoint")
    
    with open('backend/routers/sales_agent.py', 'w', encoding='utf-8') as f:
        f.write(content)
else:
    print("❌ Marker not found")

