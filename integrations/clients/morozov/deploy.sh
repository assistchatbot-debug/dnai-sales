#!/bin/bash
set -e

echo "🚀 Начало развёртывания 1C-Bitrix24 Integration..."

cd /root/dnai-sales/integrations/clients/morozov

if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден!"
    exit 1
fi

echo "✅ Файл .env найден"

echo "🛑 Остановка старых контейнеров..."
docker-compose down 2>/dev/null || true

echo "🔨 Сборка Docker образа..."
docker-compose build

mkdir -p logs

echo "▶️ Запуск middleware..."
docker-compose up -d

sleep 5
if docker-compose ps | grep -q "Up"; then
    echo "✅ Middleware успешно запущен!"
    echo "📊 Статус:"
    docker-compose ps
    echo ""
    echo "🌐 API: http://178.128.20.100:8000"
else
    echo "❌ Ошибка запуска"
    docker-compose logs
    exit 1
fi

echo ""
echo "🎉 Развёртывание завершено!"
