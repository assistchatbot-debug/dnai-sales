from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from fastapi.responses import Response
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/widget", tags=["widget"])

@router.get("/{company_id}/script.js")
@limiter.limit("60/minute")
async def get_widget_script(request: Request, company_id: int):
    js_code = f"""
    (function() {{
        console.log("Initializing BizDNAii Widget for Company {company_id}");
    }})();
    """
    return Response(content=js_code, media_type="application/javascript")
