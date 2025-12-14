/**
 * BizDNAii Widget
 * Version: 4.0
 * Date: 2025-12-11
 * 
 * Changes: Dialog shift left 10px, pointer events for hold-to-record, reset creates new lead
 */

import { useState, useEffect, useRef } from 'preact/hooks';
import { X, Send, Mic, Square } from 'lucide-preact';

export function App() {
    const [isOpen, setIsOpen] = useState(false);
    const [widgetEnabled, setWidgetEnabled] = useState(true);
    const [language, setLanguage] = useState(localStorage.getItem('bizdnaii_widget_lang') || 'ru');
    const [showTooltip, setShowTooltip] = useState(false);
    const [visitorId, setVisitorId] = useState(localStorage.getItem('bizdnaii_vid') || `v_${Math.random().toString(36).substr(2, 9)}`);

    const texts = {
        ru: {
            intro: 'Здравствуйте!\nЯ умный помощник BizDNAi.\n\nАвтоматизация бизнеса: Маркетинг, Финансы, Продажи...',
            placeholder: 'Сообщение...',
            thinking: 'Думаю...',
            error: 'Ошибка сервера',
            online: 'Online',
            tooltip: 'Напишите нам...'
        },
        en: {
            intro: 'Hello!\nI am the smart assistant of BizDNAi.\n\nBusiness automation: Marketing, Finance, Sales...',
            placeholder: 'Message...',
            thinking: 'Thinking...',
            error: 'Server error',
            online: 'Online',
            tooltip: 'Write to us...'
        }
    };

    const t = texts[language] || texts.ru;

    const [messages, setMessages] = useState([{ id: 1, text: t.intro, sender: 'bot' }]);
    const [inputText, setInputText] = useState("");
    const [isRecording, setIsRecording] = useState(false);
    const [isTyping, setIsTyping] = useState(false);
    const messagesEndRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const chunksRef = useRef([]);
    const streamRef = useRef(null);
    const isRecordingRef = useRef(false);

    useEffect(() => {
        if (isOpen) { setShowTooltip(false); return; }
        const showTimeout = setTimeout(() => setShowTooltip(true), 500);
        const interval = setInterval(() => {
            setShowTooltip(true);
            setTimeout(() => setShowTooltip(false), 5000);
        }, 8000);
        return () => { clearTimeout(showTimeout); clearInterval(interval); };
    }, [isOpen]);

    useEffect(() => {
        const handleLangChange = (e) => {
            const newLang = e.detail?.language || 'ru';
            setLanguage(newLang);
            setMessages([{ id: 1, text: texts[newLang]?.intro || texts.ru.intro, sender: 'bot' }]);
        };
        window.addEventListener('bizdnaii-language-change', handleLangChange);
        const storedLang = localStorage.getItem('bizdnaii_widget_lang');
        if (storedLang && storedLang !== language) {
            setLanguage(storedLang);
            setMessages([{ id: 1, text: texts[storedLang]?.intro || texts.ru.intro, sender: 'bot' }]);
        }
        return () => window.removeEventListener('bizdnaii-language-change', handleLangChange);
    }, []);

    useEffect(() => { localStorage.setItem('bizdnaii_vid', visitorId); }, [visitorId]);
    // Check if widget is enabled
    useEffect(() => {
        fetch('/sales/1/widget-enabled')
            .then(r => r.json())
            .then(data => setWidgetEnabled(data.enabled !== false))
            .catch(() => setWidgetEnabled(true));
    }, []);

    const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    useEffect(() => { scrollToBottom(); }, [messages, isOpen]);

    const handleSend = async () => {
        if (!inputText.trim()) return;
        if (!widgetEnabled) {
            setMessages(prev => [...prev, { id: Date.now(), text: 'Виджет временно отключен / Widget temporarily disabled', sender: 'bot', isError: true }]);
            return;
        }
        const userMsg = inputText;
        setInputText("");
        setMessages(prev => [...prev, { id: Date.now(), text: userMsg, sender: 'user' }]);
        setIsTyping(true);
        try {
            const response = await fetch('/sales/1/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userMsg, session_id: "web-session", user_id: visitorId, language: language })
            });
            if (!response.ok) throw new Error(`Server: ${response.status}`);
            const data = await response.json();
            setMessages(prev => [...prev, { id: Date.now(), text: data.response, sender: 'bot' }]);
        } catch (e) {
            console.error("Chat Error:", e);
            setMessages(prev => [...prev, { id: Date.now(), text: t.error, sender: 'bot', isError: true }]);
        } finally { setIsTyping(false); }
    };

    const handleKeyPress = (e) => { if (e.key === 'Enter') handleSend(); };

    // Start recording
    const startRecording = async () => {
        if (isRecordingRef.current) return;
        isRecordingRef.current = true;
        setIsRecording(true);

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = stream;
            mediaRecorderRef.current = new MediaRecorder(stream);
            chunksRef.current = [];
            mediaRecorderRef.current.ondataavailable = (ev) => { if (ev.data.size > 0) chunksRef.current.push(ev.data); };
            mediaRecorderRef.current.onstop = async () => {
                const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm;codecs=opus' });
                if (streamRef.current) {
                    streamRef.current.getTracks().forEach(track => track.stop());
                    streamRef.current = null;
                }
                await sendVoice(audioBlob);
            };
            mediaRecorderRef.current.start();
        } catch (err) {
            console.error("Microphone error:", err);
            isRecordingRef.current = false;
            setIsRecording(false);
        }
    };

    // Stop recording
    const stopRecording = () => {
        if (!isRecordingRef.current) return;
        isRecordingRef.current = false;
        setIsRecording(false);
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
            mediaRecorderRef.current.stop();
        }
    };

    // Use Pointer Events for cross-platform support
    const handlePointerDown = (e) => {
        e.preventDefault();
        e.target.setPointerCapture(e.pointerId);
        startRecording();
    };

    const handlePointerUp = (e) => {
        e.preventDefault();
        stopRecording();
    };

    const sendVoice = async (audioBlob) => {
        setMessages(prev => [...prev, { id: Date.now(), text: t.thinking, sender: 'user' }]);
        setIsTyping(true);
        const formData = new FormData();
        formData.append('file', audioBlob, 'voice.webm');
        formData.append('session_id', 'web-session');
        formData.append('user_id', visitorId);
        formData.append('language', language);
        try {
            const response = await fetch('/sales/1/voice', { method: 'POST', body: formData });
            const data = await response.json();
            if (data.text) {
                setMessages(prev => {
                    const updated = [...prev];
                    updated[updated.length - 1] = { id: Date.now() - 1, text: `🗣 ${data.text}`, sender: 'user' };
                    return updated;
                });
            }
            if (data.response) setMessages(prev => [...prev, { id: Date.now(), text: data.response, sender: 'bot' }]);
        } catch (e) {
            console.error(e);
            setMessages(prev => [...prev, { id: Date.now(), text: t.error, sender: 'bot', isError: true }]);
        } finally { setIsTyping(false); }
    };

    // Reset - create NEW visitor ID = new lead
    const resetChat = () => {
        const newId = `v_${Math.random().toString(36).substr(2, 9)}`;
        setVisitorId(newId);
        localStorage.setItem('bizdnaii_vid', newId);
        setMessages([{ id: 1, text: t.intro, sender: 'bot' }]);
    };

    return (
        <div className="fixed bottom-4 z-50 font-sans" style={{ right: '40px' }}>
            {isOpen && (
                <div className="mb-4 w-80 h-[500px] bg-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-slate-700" style={{ marginRight: '-30px' }}>
                    <div className="bg-indigo-600 p-4 flex justify-between items-center">
                        <div className="flex items-center gap-2">
                            <img src="https://bizdnai.com/logo.png" className="w-8 h-8 rounded-full" alt="" />
                            <div>
                                <h3 className="font-bold text-sm text-white">BizDNAi</h3>
                                <span className="text-xs text-green-300 flex items-center gap-1">● {t.online}</span>
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <button onClick={resetChat} className="hover:bg-white/10 p-1 rounded text-white" title="Новый диалог">🔄</button>
                            <button onClick={() => setIsOpen(false)} className="text-white"><X size={18} /></button>
                        </div>
                    </div>
                    <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-900/50">
                        {messages.map(m => (
                            <div key={m.id} className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-[80%] p-3 rounded-2xl text-sm whitespace-pre-line text-white ${m.sender === 'user' ? 'bg-indigo-600' : 'bg-slate-700'} ${m.isError ? 'bg-red-500' : ''}`}>
                                    {m.text}
                                </div>
                            </div>
                        ))}
                        {isTyping && (
                            <div className="flex justify-start">
                                <div className="bg-slate-700 p-4 rounded-2xl flex gap-1">
                                    <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"></div>
                                    <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                                    <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>
                    <div className="p-3 bg-slate-800 border-t border-slate-700">
                        <div className="flex gap-1.5 items-center">
                            <input type="text" value={inputText} onInput={(e) => setInputText(e.target.value)} onKeyPress={handleKeyPress} placeholder={t.placeholder} className="flex-1 min-w-0 bg-slate-700 text-white rounded-full px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                            <button onClick={handleSend} className="p-2.5 bg-indigo-600 rounded-full hover:bg-indigo-700 shrink-0">
                                <Send size={22} className="text-white" />
                            </button>
                            {/* Hold to record - Pointer Events */}
                            <button
                                onPointerDown={handlePointerDown}
                                onPointerUp={handlePointerUp}
                                onPointerCancel={handlePointerUp}
                                className={`p-2.5 rounded-full shrink-0 ${isRecording ? 'bg-red-500 animate-pulse' : 'bg-slate-700 hover:bg-slate-600'}`}
                                style={{ touchAction: 'none' }}
                            >
                                {isRecording ? <Square size={22} className="text-white" /> : <Mic size={22} className="text-white" />}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <div className="relative">
                <div className={`absolute bottom-full right-0 mb-2 whitespace-nowrap bg-white text-slate-800 px-4 py-2 rounded-full shadow-lg text-sm font-medium transition-all duration-500 ${!isOpen && showTooltip ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2 pointer-events-none'}`}>
                    {t.tooltip}
                    <div className="absolute bottom-0 right-6 transform translate-y-1/2 rotate-45 w-2 h-2 bg-white"></div>
                </div>
                <button onClick={() => setIsOpen(!isOpen)} className="w-16 h-16 rounded-full bg-indigo-600 flex items-center justify-center shadow-2xl relative">
                    {!isOpen && <span className="absolute inset-0 rounded-full bg-indigo-600 opacity-75" style={{ animation: 'ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite' }}></span>}
                    <div className="relative z-10">
                        {isOpen ? <X size={28} className="text-white" /> : <img src="https://bizdnai.com/logo.png" className="w-8 h-8 rounded-full" alt="Chat" />}
                    </div>
                </button>
            </div>

            <style>{`@keyframes ping { 75%, 100% { transform: scale(1.8); opacity: 0; } }`}</style>
        </div>
    )
}
