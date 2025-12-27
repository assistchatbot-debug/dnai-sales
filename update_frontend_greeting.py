#!/usr/bin/env python3
"""Update frontend to load greeting from widget API"""

with open('frontend/widget/standalone.html', 'r') as f:
    content = f.read()

print("🔧 Updating frontend...")

# 1. Add function to parse URL and get channel_name
old_parse = "        const companyId = urlParams.get('company') || '1';"

new_parse = """        // Parse URL: /w/{company_id}/{channel_name}
        const pathParts = window.location.pathname.split('/').filter(p => p);
        let companyId = '1';
        let channelName = null;
        
        if (pathParts[0] === 'w' && pathParts.length >= 2) {
            companyId = pathParts[1];
            channelName = pathParts[2] || null;
        } else {
            // Fallback to query params
            companyId = urlParams.get('company') || '1';
        }"""

content = content.replace(old_parse, new_parse)
print("✅ Added URL parsing for channel_name")

# 2. Replace hardcoded greetings with API load
old_greeting_def = "        const greetings = { ru: 'Здравствуйте!\\nЯ умный помощник BizDNAi.\\n\\nАвтоматизация бизнеса: Маркетинг, Финансы, Продажи...', en: 'Hello!\\nI am the smart assistant of BizDNAi.\\n\\nBusiness automation: Marketing, Finance, Sales...', kz: 'Сәлеметсіз бе!\\nМен BizDNAi ақылды көмекшісімін.\\n\\nБизнесті автоматтандыру: Маркетинг, Қаржы, Сату...', kg: 'Саламатсызбы!\\nМен BizDNAi акылдуу жардамчысымын.\\n\\nБизнести автоматташтыруу: Маркетинг, Финансы, Сатуу...', uz: 'Salom!\\nMen BizDNAi aqlli yordamchisiman.\\n\\nBiznesni avtomatlashtirish: Marketing, Moliya, Sotish...', ua: 'Вітаю!\\nЯ розумний помічник BizDNAi.\\n\\nАвтоматизація бізнесу: Маркетинг, Фінанси, Продажі...' };"

new_greeting_def = """        // Default greetings (fallback)
        const defaultGreetings = { 
            ru: 'Здравствуйте!\\nЯ умный помощник BizDNAi.\\n\\nАвтоматизация бизнеса: Маркетинг, Финансы, Продажи...', 
            en: 'Hello!\\nI am the smart assistant of BizDNAi.',
            kz: 'Сәлеметсіз бе!\\nМен BizDNAi ақылды көмекшісімін.',
        };
        let customGreeting = null;"""

content = content.replace(old_greeting_def, new_greeting_def)
print("✅ Replaced hardcoded greetings with variable")

# 3. Load widget config if channel_name exists
old_company_load = "        fetch(`${API}/company-info`).then(r => r.json()).then(data => {"

new_widget_load = """        // Load widget-specific greeting if channel_name is provided
        if (channelName) {
            fetch(`${API}/companies/${companyId}/widgets/${channelName}`)
                .then(r => r.json())
                .then(data => {
                    if (data.greeting_message) {
                        customGreeting = data.greeting_message;
                        console.log('✅ Loaded custom greeting for', channelName);
                    }
                })
                .catch(e => console.log('No custom greeting, using default'));
        }
        
        fetch(`${API}/company-info`).then(r => r.json()).then(data => {"""

content = content.replace(old_company_load, new_widget_load)
print("✅ Added widget config loading")

# 4. Update resetChat to use custom greeting
old_reset = "        function resetChat() { sessionId = null; messages.innerHTML = ''; addMsg(greetings[langSelect.value] || greetings.ru, false); }"

new_reset = "        function resetChat() { sessionId = null; messages.innerHTML = ''; addMsg(customGreeting || defaultGreetings[langSelect.value] || defaultGreetings.ru, false); }"

content = content.replace(old_reset, new_reset)
print("✅ Updated resetChat to use custom greeting")

with open('frontend/widget/standalone.html', 'w') as f:
    f.write(content)

print("\n✅ Frontend updated!")
