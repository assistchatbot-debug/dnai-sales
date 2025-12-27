#!/usr/bin/env python3
"""Add DELETE endpoint for widget deletion"""

with open('backend/routers/sales_agent.py', 'r') as f:
    content = f.read()

print("🔧 Adding DELETE endpoint...")

# Find the last widget endpoint and add DELETE after it
insert_point = '''@router.get("/companies/{company_id}/widgets/{channel_name}")
async def get_widget_config('''

delete_endpoint = '''@router.delete("/companies/{company_id}/widgets/{channel_name}")
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
        )
        widget = result.scalar_one_or_none()
        
        if not widget:
            raise HTTPException(status_code=404, detail='Widget not found')
        
        # Soft delete - just deactivate
        widget.is_active = False
        await db.commit()
        
        return {'message': 'Widget deleted successfully'}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f'Delete widget error: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/companies/{company_id}/widgets/{channel_name}")
async def get_widget_config('''

content = content.replace(insert_point, delete_endpoint)
print("✅ Added DELETE endpoint")

with open('backend/routers/sales_agent.py', 'w') as f:
    f.write(content)

print("\n✅ Done! Restart backend:")
print("docker-compose restart backend")
