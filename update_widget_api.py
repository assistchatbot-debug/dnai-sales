#!/usr/bin/env python3
"""Add auto-translation to widget creation API"""

with open('backend/routers/sales_agent.py', 'r') as f:
    content = f.read()

print("🔧 Adding auto-translation logic...")

# Find widget creation and add translation generation
old_create = '''        # Create widget
        widget = SocialWidget(
            company_id=company_id,
            channel_name=channel_name,
            greeting_message=greeting_message or f'Здравствуйте! Добро пожаловать в {company.name}!',
            is_active=True
        )
        
        db.add(widget)
        await db.commit()
        await db.refresh(widget)'''

new_create = '''        # Generate translations using company's AI endpoint
        from services.ai_service import get_ai_service
        
        base_greeting = greeting_message or f'Здравствуйте! Добро пожаловать в {company.name}!'
        
        # Initialize AI service with company credentials
        ai_service = get_ai_service(
            company_id=company_id,
            ai_endpoint=company.ai_endpoint,
            ai_api_key=company.ai_api_key
        )
        
        # Generate translations
        translations = {}
        languages = {
            'ru': 'Russian',
            'en': 'English', 
            'kz': 'Kazakh',
            'ky': 'Kyrgyz',
            'uz': 'Uzbek',
            'uk': 'Ukrainian'
        }
        
        for lang_code, lang_name in languages.items():
            if lang_code == 'ru':
                translations[lang_code] = base_greeting
            else:
                try:
                    prompt = f"Translate this greeting to {lang_name}, keep the same tone and style:\\n\\n{base_greeting}"
                    translation = await ai_service.get_product_recommendation(
                        user_query=prompt,
                        history=[],
                        product_catalog=[],
                        language=lang_code
                    )
                    translations[lang_code] = translation
                except Exception as e:
                    logging.warning(f"Translation to {lang_name} failed: {e}, using base greeting")
                    translations[lang_code] = base_greeting
        
        # Create widget with all translations
        widget = SocialWidget(
            company_id=company_id,
            channel_name=channel_name,
            greeting_message=base_greeting,  # Backward compatibility
            greeting_ru=translations.get('ru', base_greeting),
            greeting_en=translations.get('en', base_greeting),
            greeting_kz=translations.get('kz', base_greeting),
            greeting_ky=translations.get('ky', base_greeting),
            greeting_uz=translations.get('uz', base_greeting),
            greeting_uk=translations.get('uk', base_greeting),
            is_active=True
        )
        
        db.add(widget)
        await db.commit()
        await db.refresh(widget)'''

content = content.replace(old_create, new_create)
print("✅ Added auto-translation logic")

with open('backend/routers/sales_agent.py', 'w') as f:
    f.write(content)

print("\n✅ Done! Restart backend to apply changes:")
print("docker-compose restart backend")
