#!/usr/bin/env python3
"""Refactor widget endpoints to use widget_id instead of channel_name"""

with open('backend/routers/sales_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("🔧 Step 1: Adding new ID-based endpoints...")

# Find the get_widget_config endpoint and add new ID-based version
old_get_endpoint = """@router.get("/companies/{company_id}/widgets/{channel_name}")
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
        raise HTTPException(status_code=404, detail="Widget not found")"""

new_get_endpoint = """@router.get("/companies/{company_id}/widgets/{widget_id:int}")
async def get_widget_by_id(company_id: int, widget_id: int, db: AsyncSession = Depends(get_db)):
    """Get widget configuration by ID"""
    result = await db.execute(
        select(SocialWidget).where(
            SocialWidget.company_id == company_id,
            SocialWidget.id == widget_id,
            SocialWidget.is_active == True
        )
    )
    widget = result.scalar_one_or_none()
    
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    return {
        "id": widget.id,
        "company_id": widget.company_id,
        "channel_name": widget.channel_name,
        "greeting_message": widget.greeting_message,
        "greetings": {
            "ru": widget.greeting_ru or widget.greeting_message,
            "en": widget.greeting_en or widget.greeting_message,
            "kz": widget.greeting_kz or widget.greeting_message,
            "ky": widget.greeting_ky or widget.greeting_message,
            "uz": widget.greeting_uz or widget.greeting_message,
            "uk": widget.greeting_uk or widget.greeting_message
        },
        "is_active": widget.is_active
    }


# Keep old endpoint for backward compatibility
@router.get("/companies/{company_id}/widgets/{channel_name}")
async def get_widget_config(company_id: int, channel_name: str, db: AsyncSession = Depends(get_db)):
    """Get widget configuration by channel name (deprecated, use ID)"""
    result = await db.execute(
        select(SocialWidget).where(
            SocialWidget.company_id == company_id,
            SocialWidget.channel_name == channel_name,
            SocialWidget.is_active == True
        )
    )
    widget = result.scalar_one_or_none()
    
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")"""

content = content.replace(old_get_endpoint, new_get_endpoint)
print("✅ Added ID-based GET endpoint")

# Update DELETE endpoint to use widget_id
old_delete = """@router.delete("/companies/{company_id}/widgets/{channel_name}")
async def delete_social_widget(
    company_id: int,
    channel_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete (deactivate) social media widget"""
    try:
        result = await db.execute(
            select(SocialWidget).where(
                SocialWidget.company_id == company_id,
                SocialWidget.channel_name == channel_name
            )
        )"""

new_delete = """@router.delete("/companies/{company_id}/widgets/{widget_id:int}")
async def delete_social_widget(
    company_id: int,
    widget_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete (deactivate) social media widget by ID"""
    try:
        result = await db.execute(
            select(SocialWidget).where(
                SocialWidget.company_id == company_id,
                SocialWidget.id == widget_id
            )
        )"""

content = content.replace(old_delete, new_delete)
print("✅ Updated DELETE endpoint to use widget_id")

# Remove uniqueness check from widget creation
old_creation = """        # Allow multiple widgets per channel (no uniqueness check)"""
if old_creation not in content:
    # Pattern to find and remove
    import re
    pattern = r'        # Check if widget already exists.*?(?=        # Generate translations|        # Create widget)'
    content = re.sub(pattern, '        # Allow multiple widgets per channel\n', content, flags=re.DOTALL)
    print("✅ Removed uniqueness constraint")

# Update widget URL generation
content = content.replace(
    "widget_url = f'https://bizdnai.com/w/{company_id}/{channel_name}'",
    "widget_url = f'https://bizdnai.com/w/{company_id}/{widget.id}'"
)
print("✅ Updated URL generation to use widget ID")

with open('backend/routers/sales_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Backend refactoring complete!")
