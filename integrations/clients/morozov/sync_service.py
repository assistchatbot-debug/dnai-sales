"""Сервис синхронизации остатков"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from datetime import datetime
import json

from config import settings
from bitrix24_client import Bitrix24Client
from onec_client import OneCClient
from database import async_session_maker, SyncLog, StockSnapshot, ProductMapping
from sqlalchemy import select


class SyncService:
    """Сервис для синхронизации остатков между 1С и Bitrix24"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.bitrix24 = Bitrix24Client()
        self.onec = OneCClient()
    
    async def start_scheduler(self):
        """Запуск планировщика синхронизации"""
        self.scheduler.add_job(
            self.sync_stock_to_bitrix24,
            'cron',
            hour=settings.sync_schedule_hour,
            minute=settings.sync_schedule_minute,
            id='sync_stock',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info(f"Scheduler started. Stock sync scheduled at {settings.sync_schedule_hour:02d}:{settings.sync_schedule_minute:02d}")
    
    async def stop_scheduler(self):
        """Остановка планировщика"""
        self.scheduler.shutdown()
        await self.bitrix24.close()
        await self.onec.close()
        logger.info("Scheduler stopped")
    
    async def sync_stock_to_bitrix24(self):
        """Синхронизация остатков из 1С в Bitrix24"""
        logger.info("Starting stock synchronization from 1C to Bitrix24")
        
        async with async_session_maker() as session:
            try:
                stock_balances = await self.onec.get_stock_balances()
                logger.info(f"Retrieved {len(stock_balances)} stock items from 1C")
                
                # Сохраняем снимок остатков
                for item in stock_balances:
                    snapshot = StockSnapshot(
                        product_code=item["product_code"],
                        product_name=item["product_name"],
                        quantity=item["quantity"],
                        warehouse=item.get("warehouse", "Основной склад")
                    )
                    session.add(snapshot)
                
                await session.commit()
                
                # Обновляем остатки в Bitrix24
                updated_count = 0
                error_count = 0
                
                for item in stock_balances:
                    try:
                        stmt = select(ProductMapping).where(
                            ProductMapping.onec_product_code == item["product_code"]
                        )
                        result = await session.execute(stmt)
                        mapping = result.scalar_one_or_none()
                        
                        if mapping:
                            success = await self.bitrix24.update_product_quantity(
                                mapping.bitrix24_product_id,
                                item["quantity"]
                            )
                            
                            if success:
                                updated_count += 1
                            else:
                                error_count += 1
                        else:
                            logger.warning(f"No mapping found for 1C product {item['product_code']}")
                    
                    except Exception as e:
                        logger.error(f"Error updating product {item['product_code']}: {e}")
                        error_count += 1
                
                # Логируем результат
                log_entry = SyncLog(
                    sync_type="stock_to_bitrix24",
                    direction="1c_to_bitrix24",
                    status="success" if error_count == 0 else "partial_success",
                    request_data=json.dumps({"total_items": len(stock_balances)}),
                    response_data=json.dumps({
                        "updated": updated_count,
                        "errors": error_count
                    })
                )
                session.add(log_entry)
                await session.commit()
                
                logger.info(f"Stock sync completed. Updated: {updated_count}, Errors: {error_count}")
            
            except Exception as e:
                logger.error(f"Error during stock synchronization: {e}")
                
                log_entry = SyncLog(
                    sync_type="stock_to_bitrix24",
                    direction="1c_to_bitrix24",
                    status="error",
                    error_message=str(e)
                )
                session.add(log_entry)
                await session.commit()
