from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, Text, JSON, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET, ARRAY
import uuid
from database import Base

# --- EXISTING SYSTEM MODELS (Scaffolded) ---

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    subdomain = Column(String, unique=True, index=True)
    
    # Company details
    bin_iin = Column(String)  # ИИН/БИН компании
    phone = Column(String)  # Телефон компании
    whatsapp = Column(String)  # WhatsApp компании
    email = Column(String)  # Email для уведомлений
    description = Column(Text)  # Краткое описание компании
    description_en = Column(Text, nullable=True)
    description_kz = Column(Text, nullable=True)
    description_ky = Column(Text, nullable=True)
    description_uz = Column(Text, nullable=True)
    description_uk = Column(Text, nullable=True)
    logo_url = Column(String)  # URL логотипа компании
    
    # Bot configuration
    bot_token = Column(String)  # Токен Telegram бота компании
    manager_chat_id = Column(BigInteger)  # Chat ID менеджера компании
    
    # AI configuration
    ai_endpoint = Column(Text)  # AI API endpoint URL
    ai_api_key = Column(Text)  # AI API key
    
    settings = Column(JSONB, default={})
    default_language = Column(String, default="ru")
    
    # Subscription tier
    tier = Column(String, default="free")  # free, basic, pro, enterprise
    tier_expiry = Column(DateTime(timezone=True), nullable=True)
    ai_package = Column(String(20), default='basic')
    leads_used_this_month = Column(Integer, default=0)
    leads_reset_date = Column(DateTime, nullable=True)
    
    
    # Relationships
    web_widgets = relationship("WebWidget", back_populates="company")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    products = relationship("Product", back_populates="company")
    leads = relationship("Lead", back_populates="company")
    social_widgets=relationship("SocialWidget",back_populates="company",cascade="all, delete-orphan")
    social_widgets = relationship("SocialWidget", back_populates="company", cascade="all, delete-orphan")

    sales_config = relationship("SalesAgentConfig", back_populates="company", uselist=False)

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    category = Column(String)
    name = Column(String, index=True)
    description = Column(Text)
    attributes = Column(JSONB)
    pricing = Column(JSONB)
    inventory = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # EXTENSIONS for Sales Agent
    technical_specifications = Column(JSONB, default=lambda: {})
    selection_parameters = Column(JSONB, default=lambda: {})
    competitor_comparison = Column(JSONB, default=lambda: {})
    media_assets = Column(JSONB, default=lambda: {})
    
    company = relationship("Company", back_populates="products")

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    telegram_user_id = Column(BigInteger, index=True, nullable=True)
    contact_info = Column(JSONB)
    status = Column(String, default="new")
    source = Column(String)
    assigned_employee_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # EXTENSIONS for Sales Agent
    sales_agent_session_id = Column(UUID(as_uuid=True), nullable=True)
    product_match_score = Column(Float, nullable=True)
    selection_criteria = Column(JSONB, default=lambda: {})
    conversation_summary = Column(Text, nullable=True)
    recommended_products = Column(JSONB, default=lambda: [])
    
    company = relationship("Company", back_populates="leads")

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    personal_info = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- NEW SALES AGENT MODELS ---

class SalesAgentConfig(Base):
    __tablename__ = "sales_agent_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), unique=True)
    
    ai_prompt = Column(Text)
    conversation_flow = Column(JSONB)
    product_parameters = Column(JSONB)
    
    company_info = Column(JSONB)
    competitor_data = Column(JSONB)
    
    web_widget_config = Column(JSONB)
    telegram_bot_token = Column(String)
    
    supported_languages = Column(JSONB, default=["ru", "en"])
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    company = relationship("Company", back_populates="sales_config")

class ProductSelectionSession(Base):
    __tablename__ = "product_selection_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"))
    
    user_id = Column(String, nullable=True)
    channel = Column(String, default="telegram")
    
    current_step = Column(String, default="welcome")
    session_status = Column(String, default="active")
    
    collected_parameters = Column(JSONB, default=lambda: {})
    product_recommendations = Column(JSONB, default=lambda: [])
    conversation_history = Column(JSONB, default=lambda: [])
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())

class VoiceMessage(Base):
    __tablename__ = "voice_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("product_selection_sessions.id"))
    company_id = Column(Integer, ForeignKey("companies.id"))
    
    transcribed_text = Column(Text)
    transcription_language = Column(String)
    confidence_score = Column(Float)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WebSession(Base):
    __tablename__ = "web_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"))
    session_token = Column(String, unique=True, index=True)
    
    user_data = Column(JSONB)
    chat_history = Column(JSONB)
    
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())

class UserPreference(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, unique=True, index=True)
    language_code = Column(String, default="ru")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Interaction(Base):
    __tablename__ = "interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    lead_id = Column(Integer, ForeignKey("leads.id"))
    type = Column(String)
    content = Column(Text)
    outcome = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UIText(Base):
    __tablename__ = "ui_texts"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    key = Column(String, index=True)
    language_code = Column(String, index=True)
    text = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SocialWidget(Base):
    __tablename__="social_widgets"
    id=Column(Integer,primary_key=True,index=True)
    company_id=Column(Integer,ForeignKey("companies.id"),nullable=False)
    channel_name=Column(String(50),nullable=False,index=True)
    greeting_message=Column(Text)  # Deprecated, use greeting_ru
    # Multilingual greetings
    greeting_ru=Column(Text)  # Russian
    greeting_en=Column(Text)  # English
    greeting_kz=Column(Text)  # Kazakh
    greeting_ky=Column(Text)  # Kyrgyz
    greeting_uz=Column(Text)  # Uzbek
    greeting_uk=Column(Text)  # Ukrainian
    is_active=Column(Boolean,default=True)
    created_at=Column(DateTime(timezone=True),server_default=func.now())
    company=relationship("Company",back_populates="social_widgets")


class WebWidget(Base):
    """Web widget for embedding on websites"""
    __tablename__ = 'web_widgets'
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    domain = Column(Text, nullable=False, index=True)
    greeting_ru = Column(Text, nullable=True)
    greeting_en = Column(Text, nullable=True)
    greeting_kz = Column(Text, nullable=True)
    greeting_ky = Column(Text, nullable=True)
    greeting_uz = Column(Text, nullable=True)
    greeting_uk = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    company = relationship("Company", back_populates="web_widgets")

class TierSettings(Base):
    __tablename__ = 'tier_settings'
    tier = Column(String(20), primary_key=True)
    name_ru = Column(String(50), nullable=False)
    price_usd = Column(Integer, nullable=False)
    leads_limit = Column(Integer, nullable=False)
    web_widgets_limit = Column(Integer, nullable=False)
    social_widgets_limit = Column(Integer, nullable=False)
    features_ru = Column(ARRAY(Text), default=[])
    ai_setup_level = Column(String(20), default='basic')
    support_level = Column(String(20), default='email')
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, server_default=func.now())

class AIAgentPackage(Base):
    __tablename__ = 'ai_agent_packages'
    package = Column(String(20), primary_key=True)
    name_ru = Column(String(50), nullable=False)
    price_usd = Column(Integer, nullable=False)
    features_ru = Column(ARRAY(Text), default=[])
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, server_default=func.now())
