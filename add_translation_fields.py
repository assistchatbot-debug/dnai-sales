#!/usr/bin/env python3
"""Add translation fields to SocialWidget model"""

with open('backend/models.py', 'r') as f:
    content = f.read()

print("🔧 Adding translation fields to SocialWidget...")

# Find SocialWidget class and add translation fields
old_widget = '''class SocialWidget(Base):
    __tablename__="social_widgets"
    id=Column(Integer,primary_key=True,index=True)
    company_id=Column(Integer,ForeignKey("companies.id"),nullable=False)
    channel_name=Column(String(50),nullable=False,index=True)
    greeting_message=Column(Text)
    is_active=Column(Boolean,default=True)
    created_at=Column(DateTime(timezone=True),server_default=func.now())
    company=relationship("Company",back_populates="social_widgets")'''

new_widget = '''class SocialWidget(Base):
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
    company=relationship("Company",back_populates="social_widgets")'''

content = content.replace(old_widget, new_widget)
print("✅ Added 6 translation fields")

with open('backend/models.py', 'w') as f:
    f.write(content)

print("\n✅ Done! Now need to:")
print("1. Create Alembic migration")
print("2. Update widget creation API to generate translations")
print("3. Update frontend to use correct language")
