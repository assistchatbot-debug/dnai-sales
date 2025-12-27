#!/usr/bin/env python3
"""Add greeting_message to API and create widget config endpoint"""

with open('backend/routers/sales_agent.py', 'r') as f:
    content = f.read()

print("🔧 Updating widget API...")

# 1. Fix list_widgets to include greeting_message
old_list = '''@router.get("/companies/{company_id}/widgets")
async def list_widgets(company_id:int,db:AsyncSession=Depends(get_db)):
    r=await db.execute(select(SocialWidget).where(SocialWidget.company_id==company_id,SocialWidget.is_active==True))
    return {"widgets":[{"id":w.id,"channel_name":w.channel_name,"url":f"https://bizdnai.com/w/{company_id}/{w.channel_name}"}for w in r.scalars().all()]}'''

new_list = '''@router.get("/companies/{company_id}/widgets")
async def list_widgets(company_id:int,db:AsyncSession=Depends(get_db)):
    r=await db.execute(select(SocialWidget).where(SocialWidget.company_id==company_id,SocialWidget.is_active==True))
    return {"widgets":[{"id":w.id,"channel_name":w.channel_name,"greeting_message":w.greeting_message,"url":f"https://bizdnai.com/w/{company_id}/{w.channel_name}"}for w in r.scalars().all()]}'''

content = content.replace(old_list, new_list)
print("✅ Added greeting_message to list_widgets")

# 2. Add new endpoint to get widget config by channel_name (insert after create_widget)
widget_config_endpoint = '''

@router.get("/companies/{company_id}/widgets/{channel_name}")
async def get_widget_config(company_id: int, channel_name: str, db: AsyncSession = Depends(get_db)):
    """Get widget configuration by channel name"""
    result = await db.execute(
        select(SocialWidget).where(
            SocialWidget.company_id == company_id,
            SocialWidget.channel_name == channel_name,
            SocialWidget.is_active == True
        )
    )
    widget = result.scalar_one_or_none()
    
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    return {
        "id": widget.id,
        "channel_name": widget.channel_name,
        "greeting_message": widget.greeting_message,
        "company_id": widget.company_id
    }
'''

# Find where to insert (after create_widget, before delete if exists, or at end of widgets section)
if '@router.get("/companies/{company_id}/widgets/{channel_name}")' not in content:
    # Insert after create_widget
    insert_point = content.find('@router.post("/companies/{company_id}/widgets")')
    # Find end of create_widget function
    next_router = content.find('\n@router', insert_point + 100)
    if next_router > 0:
        content = content[:next_router] + widget_config_endpoint + content[next_router:]
    else:
        content += widget_config_endpoint
    print("✅ Added get_widget_config endpoint")

with open('backend/routers/sales_agent.py', 'w') as f:
    f.write(content)

print("\n✅ Backend API updated!")
