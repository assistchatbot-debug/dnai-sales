"""
Step detection and dynamic prompt for lead collection.
Upload to server and run to fix the looping issue.
"""

STEP_PROMPTS = {
    'ask_sphere': """Ты консультант BizDNAi. Спроси клиента какую сферу бизнеса он хочет автоматизировать.
Пример: "Какую сферу хотели бы автоматизировать? Например: Маркетинг, Финансы, Продажи."
Ответ должен быть коротким, 1-2 предложения.""",

    'confirm_sphere': """Ты консультант BizDNAi. Клиент назвал сферу "{sphere}". 
Подтверди что поможешь с этой сферой и спроси есть ли ещё сферы.
Пример: "Отлично! Автоматизация {sphere} ускорит процессы. Есть ещё сфера для улучшения?"
Ответ должен быть коротким.""",

    'ask_name': """Ты консультант BizDNAi. Клиент сказал что больше сфер нет.
Предложи бесплатный тестовый период и спроси имя.
Пример: "Давайте подключим бесплатный тестовый период! Как вас зовут?"
Ответ должен быть коротким.""",

    'ask_phone': """Ты консультант BizDNAi. Клиента зовут "{name}".
Поприветствуй по имени и попроси номер телефона.
Пример: "Приятно познакомиться, {name}! Укажите номер телефона для связи."
Ответ должен быть коротким.""",

    'confirm_data': """Ты консультант BizDNAi. Покажи данные клиента и спроси подтверждение.
Имя: {name}
Телефон: {phone}
Скажи: "Имя: {name}\nТелефон: {phone}\n\nВсё верно?"
Ответ ТОЛЬКО это, ничего больше.""",

    'thank_you': """Ты консультант BizDNAi. Клиент подтвердил данные.
Поблагодари и скажи что менеджер свяжется.
Пример: "Спасибо! Наш менеджер свяжется с вами для подключения тестового периода."
Ответ должен быть коротким.""",
}

def detect_step(history, user_message):
    """Detect current dialogue step based on history"""
    
    # Get last bot message
    last_bot_msg = None
    for msg in reversed(history):
        if msg.get('sender') == 'bot':
            last_bot_msg = msg.get('text', '').lower()
            break
    
    # Check for phone in message
    import re
    has_phone = bool(re.search(r'\d{6,}', user_message))
    
    # Check for "no" answers
    no_words = ['нет', 'больше нет', 'никакую', 'не нужно', 'хватит', 'достаточно']
    is_no = any(w in user_message.lower() for w in no_words)
    
    # Check for "yes" confirmation
    yes_words = ['да', 'верно', 'правильно', 'ок', 'yes']
    is_yes = any(w in user_message.lower() for w in yes_words)
    
    # Detect step
    if not history or len(history) <= 1:
        return 'ask_sphere', {}
    
    if last_bot_msg and 'есть ещё сфера' in last_bot_msg:
        if is_no:
            return 'ask_name', {}
        else:
            # User mentioned another sphere
            return 'confirm_sphere', {'sphere': user_message}
    
    if last_bot_msg and 'как вас зовут' in last_bot_msg:
        # User gave their name
        return 'ask_phone', {'name': user_message.strip()}
    
    if last_bot_msg and 'номер телефона' in last_bot_msg:
        if has_phone:
            # Extract name from history
            name = extract_name_from_history(history)
            phone = re.search(r'\d{6,}', user_message).group()
            return 'confirm_data', {'name': name, 'phone': phone}
    
    if last_bot_msg and 'всё верно' in last_bot_msg:
        if is_yes:
            return 'thank_you', {}
        else:
            return 'ask_name', {}  # Re-collect
    
    # If sphere mentioned in user message
    spheres = ['маркетинг', 'финансы', 'продажи', 'hr', 'логистик', 'производств']
    for s in spheres:
        if s in user_message.lower():
            return 'confirm_sphere', {'sphere': user_message}
    
    # Default - ask sphere
    return 'ask_sphere', {}

def extract_name_from_history(history):
    """Extract client name from history"""
    for i, msg in enumerate(history):
        if msg.get('sender') == 'bot' and 'как вас зовут' in msg.get('text', '').lower():
            if i + 1 < len(history) and history[i + 1].get('sender') == 'user':
                return history[i + 1].get('text', '').strip()
    return 'Клиент'

def get_step_prompt(step, params):
    """Get prompt for current step"""
    prompt = STEP_PROMPTS.get(step, STEP_PROMPTS['ask_sphere'])
    return prompt.format(**params) if params else prompt
