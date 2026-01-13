"""Конфигурация приложения"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения"""
    
    # Битрикс24
    bitrix24_webhook_url: str
    bitrix24_domain: str
    
    # 1С
    onec_base_url: str
    onec_username: str
    onec_password: str
    onec_http_service_path: str = "/hs/bitrix-integration"
    
    # База данных
    database_url: str
    
    # OpenRouter
    openrouter_api_key: str
    openrouter_model: str = "openai/gpt-oss-120b"
    
    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    
    # Сервер
    server_host: str = "0.0.0.0"
    server_port: int = 8008
    log_level: str = "INFO"
    
    # Синхронизация
    sync_schedule_hour: int = 0
    sync_schedule_minute: int = 0
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
