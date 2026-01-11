#!/bin/bash
set -e

echo "🗄️ Инициализация таблиц в базе данных..."

cd /root/dnai-sales/integrations/clients/morozov

docker-compose exec middleware python -c "
import asyncio
from database import init_db

async def main():
    print('Создание таблиц...')
    await init_db()
    print('✅ Таблицы успешно созданы!')

asyncio.run(main())
"

echo "🎉 Инициализация БД завершена!"
