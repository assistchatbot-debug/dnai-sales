from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import companies, sales_agent, widget, crm, whatsapp
import logging
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app = FastAPI(title="BizDNAii Sales Agent API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies.router)
app.include_router(sales_agent.router)
app.include_router(widget.router)
app.include_router(crm.router)
app.include_router(whatsapp.router)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        from sqlalchemy import text
        try:
            await conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS sales_agent_session_id UUID"))
            await conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS product_match_score FLOAT"))
            await conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS selection_criteria JSONB DEFAULT '{}'"))
            await conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS conversation_summary TEXT"))
            await conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS recommended_products JSONB DEFAULT '[]'"))
            await conn.commit()
        except Exception as e:
            logging.warning(f"Migration warning: {e}")

@app.get("/")
@limiter.limit("10/minute")
async def root(request: Request):
    return {"message": "BizDNAii Sales Agent API is running"}

@app.get("/logs")
@limiter.limit("5/minute")
async def get_logs(request: Request, lines: int = 50):
    if not os.path.exists("app.log"):
        return {"logs": "No log file found."}
    try:
        with open("app.log", "r") as f:
            import collections
            last_lines = collections.deque(f, maxlen=lines)
            return {"logs": "".join(last_lines)}
    except Exception as e:
        return {"logs": f"Error reading logs: {str(e)}"}

@app.get("/widget-enabled")
async def check_widget_enabled():
    """Check if widget is enabled"""
    import os
    enabled = os.path.exists('/var/www/bizdnai/widget_enabled.txt')
    return {"enabled": enabled}
