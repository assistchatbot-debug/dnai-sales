#!/usr/bin/env python3
"""Add leads statistics endpoint"""

with open('backend/routers/sales_agent.py', 'r') as f:
    content = f.read()

print("🔧 Adding /leads/stats endpoint...")

# Add new endpoint after list_widgets
stats_endpoint = '''

@router.get("/{company_id}/leads/stats")
async def get_leads_stats(company_id: int, db: AsyncSession = Depends(get_db)):
    """Get leads statistics for company"""
    from sqlalchemy import func
    
    # Total leads count
    total_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.company_id == company_id)
    )
    total = total_result.scalar() or 0
    
    # Count by source
    source_result = await db.execute(
        select(Lead.source, func.count(Lead.id))
        .where(Lead.company_id == company_id)
        .group_by(Lead.source)
    )
    
    sources = {}
    for source, count in source_result.all():
        sources[source or 'unknown'] = count
    
    return {
        "total": total,
        "by_source": sources
    }
'''

# Find where to insert (after get_widget_config or similar)
insert_point = content.find('@router.post("/companies/{company_id}/widgets")')
if insert_point > 0:
    # Find end of that function
    next_router = content.find('\n@router', insert_point + 100)
    if next_router > 0:
        content = content[:next_router] + stats_endpoint + content[next_router:]
        print("✅ Added stats endpoint")

with open('backend/routers/sales_agent.py', 'w') as f:
    f.write(content)

print("\n✅ Backend API ready!")
